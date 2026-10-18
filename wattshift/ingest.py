"""SMARD chart-data adapter, retries/cache, SQLite upsert and provenance.
The chart-data endpoint is publicly used by SMARD, not a guaranteed stable API.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from contextlib import closing
import time
from urllib.request import Request, urlopen
import pandas as pd

BASE = 'https://www.smard.de/app/chart_data'
ROOT = Path(__file__).resolve().parents[1]
GENERATION = {'1223':'lignite','1224':'nuclear','1225':'wind_offshore','1226':'hydro','1227':'other_conventional','1228':'other_renewable','4066':'biomass','4067':'wind_onshore','4068':'solar','4069':'coal','4070':'pumped_storage','4071':'gas'}


def utc(value):
    return pd.Timestamp(value, tz='UTC') if pd.Timestamp(value).tzinfo is None else pd.Timestamp(value).tz_convert('UTC')


def fetch_json(url, cache_dir=None, ttl=3600):
    target = Path(cache_dir)/ (hashlib.sha256(url.encode()).hexdigest()+'.json') if cache_dir else None
    if target and target.exists() and time.time()-target.stat().st_mtime < ttl:
        return json.loads(target.read_text())
    error=None
    for attempt in range(3):
        try:
            request=Request(url,headers={'User-Agent':'WattShift/1.0 research portfolio'})
            with urlopen(request,timeout=35) as response: raw=response.read()
            data=json.loads(raw)
            if target:
                target.parent.mkdir(parents=True,exist_ok=True)
                temp=target.with_suffix('.tmp');temp.write_bytes(raw);temp.replace(target)
            return data
        except Exception as exc:
            error=exc
            if attempt<2:time.sleep(0.5*2**attempt)
    raise RuntimeError(f'SMARD request failed: {url}: {error}')


def fetch_series(filter_id, start, end, resolution='hour', cache_dir=None):
    start,end=utc(start),utc(end)
    if start>=end:raise ValueError('start must precede end')
    index=fetch_json(f'{BASE}/{filter_id}/DE/index_{resolution}.json',cache_dir)
    stamps=sorted(index['timestamps'])
    start_ms,end_ms=int(start.timestamp()*1000),int(end.timestamp()*1000)
    selected=[s for i,s in enumerate(stamps) if s<end_ms and (i==len(stamps)-1 or stamps[i+1]>start_ms)]
    def get(stamp):
        url=f'{BASE}/{filter_id}/DE/{filter_id}_DE_{resolution}_{stamp}.json'
        return fetch_json(url,cache_dir).get('series',[])
    with ThreadPoolExecutor(max_workers=6) as pool: blocks=list(pool.map(get,selected))
    rows={int(t):float(v) for block in blocks for t,v in block if start_ms<=t<end_ms and v is not None}
    if not rows:return pd.Series(dtype=float,name=str(filter_id))
    series=pd.Series(rows,name=str(filter_id)).sort_index()
    series.index=pd.to_datetime(series.index,unit='ms',utc=True)
    return series


def normalize_prices(series,resolution):
    if resolution not in ('hour','quarterhour'):raise ValueError('Unsupported resolution')
    minutes=60 if resolution=='hour' else 15
    frame=pd.DataFrame({'price_eur_mwh':series})
    frame.index.name='start_utc'
    frame['end_utc']=frame.index+pd.Timedelta(minutes=minutes)
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:raise ValueError('Invalid timestamps')
    return frame


def carbon_estimate(generation, factors=None):
    factors=factors or json.loads((ROOT/'config/emissions.json').read_text())['factors']
    generation=generation.copy()
    # Germany's final reactors closed 15 April 2023; explicit structural zero after closure, not generic imputation.
    if '1224' in generation:
        mask=generation.index>=pd.Timestamp('2023-04-16',tz='UTC')
        generation.loc[mask,'1224']=generation.loc[mask,'1224'].fillna(0)
    cols=[c for c in factors if c in generation]
    # Require every modeled category, and no missing interval values; missing is not zero.
    out=pd.Series(float('nan'),index=generation.index,name='carbon_g_kwh')
    if set(cols)!=set(factors):return out
    complete=generation[cols].notna().all(axis=1)&(generation[cols]>=0).all(axis=1)
    denom=generation[cols].sum(axis=1)
    numerator=sum(generation[c]*factor for c,factor in factors.items())
    out.loc[complete & (denom>0)]=(numerator/denom).loc[complete & (denom>0)]
    return out


def save_db(frame,path,metadata):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(path,timeout=30)) as con, con:
        con.execute('PRAGMA journal_mode=WAL')
        con.execute('CREATE TABLE IF NOT EXISTS intervals(start_utc TEXT PRIMARY KEY,end_utc TEXT NOT NULL,price_eur_mwh REAL NOT NULL,carbon_g_kwh REAL,retrieved_at TEXT NOT NULL,resolution TEXT NOT NULL)')
        con.execute('CREATE TABLE IF NOT EXISTS ingestion_runs(id INTEGER PRIMARY KEY,metadata TEXT NOT NULL)')
        for ts,row in frame.iterrows():
            carbon=row.get('carbon_g_kwh')
            con.execute('INSERT INTO intervals VALUES(?,?,?,?,?,?) ON CONFLICT(start_utc) DO UPDATE SET end_utc=excluded.end_utc,price_eur_mwh=excluded.price_eur_mwh,carbon_g_kwh=COALESCE(excluded.carbon_g_kwh,intervals.carbon_g_kwh),retrieved_at=excluded.retrieved_at,resolution=excluded.resolution',
                        (ts.isoformat(),row['end_utc'].isoformat(),float(row.price_eur_mwh),None if pd.isna(carbon) else float(carbon),metadata['retrieved_at'],metadata['resolution']))
        con.execute('INSERT INTO ingestion_runs(metadata) VALUES(?)',(json.dumps(metadata),))


def ingest(start,end,out='data/processed',resolution='hour',generation=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    cache=out.parent/'raw/cache'
    frame=normalize_prices(fetch_series('4169',start,end,resolution,cache),resolution)
    if frame.empty:raise ValueError('SMARD returned no prices for requested dates')
    if generation:
        series=[fetch_series(fid,start,end,resolution,cache) for fid in GENERATION]
        gen=pd.concat(series,axis=1).reindex(frame.index)
        gen.to_csv(out/'generation.csv',index_label='start_utc')
        frame['carbon_g_kwh']=carbon_estimate(gen)
    else:frame['carbon_g_kwh']=float('nan')
    frame.to_csv(out/'prices.csv')
    meta={'source':'SMARD / Bundesnetzagentur','source_url':'https://www.smard.de','adapter_url':BASE,
          'license_url':'https://www.smard.de/home/downloadcenter/download-marktdaten/',
          'retrieved_at':datetime.now(timezone.utc).isoformat(),'requested_start':str(start),'requested_end':str(end),
          'actual_start':frame.index.min().isoformat(),'actual_end':frame.end_utc.max().isoformat(),
          'resolution':resolution,'price_unit':'EUR/MWh','generation_unit':'MWh per source interval',
          'rows':len(frame),'carbon_rows':int(frame.carbon_g_kwh.notna().sum()),
          'publication_times':'not supplied by this endpoint; retrospective retrieval must not be treated as archived issue-time truth',
          'carbon_method':'config/emissions.json; retrospective domestic lifecycle proxy; not a live carbon forecast',
          'sha256':hashlib.sha256((out/'prices.csv').read_bytes()).hexdigest()}
    (out/'provenance.json').write_text(json.dumps(meta,indent=2))
    save_db(frame,out/'wattshift.db',meta)
    return meta


def main():
    p=argparse.ArgumentParser();p.add_argument('--start',default=(pd.Timestamp.now(tz='UTC')-pd.Timedelta(days=14)).date().isoformat());p.add_argument('--end',default=(pd.Timestamp.now(tz='UTC')+pd.Timedelta(days=2)).date().isoformat());p.add_argument('--out',default=os.getenv('WATTSHIFT_DATA','data/processed'));p.add_argument('--resolution',choices=['hour','quarterhour'],default='quarterhour');p.add_argument('--generation',action='store_true');a=p.parse_args()
    print(json.dumps(ingest(a.start,a.end,a.out,a.resolution,a.generation),indent=2))
if __name__=='__main__':main()
