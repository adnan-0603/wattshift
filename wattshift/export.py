"""Generate the common Console contract for static and API modes."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from .forecast import load_prices,backtest,predict
from .policies import replay


def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    if isinstance(value,(np.integer,)):return int(value)
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    return value


def records(frame):
    result=[]
    for ts,row in frame.iterrows():
        end=pd.Timestamp(row['end_utc'])
        result.append({'start':ts.isoformat(),'end':end.isoformat(),'price':float(row.price_eur_mwh),'carbon':None if pd.isna(row.get('carbon_g_kwh')) else float(row.carbon_g_kwh)})
    return result


def build(history_path='data/historical/prices.csv',carbon_path='data/summer/prices.csv',live_path='data/live/prices.csv',out='data/processed'):
    history=load_prices(history_path)
    if Path(carbon_path).exists():
        carbon=load_prices(carbon_path)
        if Path('data/winter/prices.csv').exists():
            carbon=pd.concat([carbon,load_prices('data/winter/prices.csv')]).sort_index()
        history['carbon_g_kwh']=carbon.carbon_g_kwh.reindex(history.index)
    test,metrics=backtest(history)
    origin=pd.Timestamp(metrics['origin'])
    # Repeat-lag carbon is a forecast proxy; only observations older than issue time.
    carbon_actual=history.carbon_g_kwh.reindex(test.index).to_numpy() if 'carbon_g_kwh' in history else None
    lagcarbon=history.carbon_g_kwh.reindex(test.index-pd.Timedelta(days=7)).to_numpy() if 'carbon_g_kwh' in history else None
    if lagcarbon is not None and not np.isfinite(lagcarbon).any():lagcarbon=None
    sim=replay(test.actual,test.p50,carbon_actual,lagcarbon)
    forecast=test.drop(columns=['actual']);meta=metrics
    active=history.copy();mode='historical replay';retrieved=json.loads(Path(history_path).with_name('provenance.json').read_text())['retrieved_at']
    if Path(live_path).exists():
        live=load_prices(live_path)
        current_carbon=Path(live_path).parent.parent/'current-carbon/prices.csv'
        if current_carbon.exists():
            cc=load_prices(current_carbon)
            live['carbon_g_kwh']=cc.carbon_g_kwh.reindex(live.index)
        if not live.empty:
            active=pd.concat([history,live]).sort_index();active=active[~active.index.duplicated(keep='last')]
            retrieved=json.loads(Path(live_path).with_name('provenance.json').read_text())['retrieved_at']
            issue=pd.Timestamp.now(tz='UTC').floor('h')
            forecast,meta=predict(active,issue,7)
            mode='market snapshot'
    forecast_rows=[]
    issue=pd.Timestamp(meta.get('issue_time',metrics['origin']))
    carbon_history=active.loc[(active.index<issue)&(active.index>=issue-pd.Timedelta(days=14))]
    carbon_profile=carbon_history.groupby(carbon_history.index.hour).carbon_g_kwh.mean() if 'carbon_g_kwh' in carbon_history else pd.Series(dtype=float)
    for ts,row in forecast.iterrows():
        market=active.price_eur_mwh.get(ts)
        # Treat future price as published only if actually retrieved now, not retrospective backtest truth.
        published=None
        if mode=='market snapshot' and ts>=pd.Timestamp(meta['issue_time']):
            window=active.loc[(active.index>=ts)&(active.index<ts+pd.Timedelta(hours=1))]
            if len(window) and window.index[0]==ts and pd.Timestamp(window.end_utc.iloc[-1])==ts+pd.Timedelta(hours=1) and all(pd.Timestamp(window.end_utc.iloc[i])==window.index[i+1] for i in range(len(window)-1)):
                durations=(pd.to_datetime(window.end_utc,utc=True)-window.index).dt.total_seconds()
                published=float(np.average(window.price_eur_mwh,weights=durations))
        forecast_rows.append({'start':ts.isoformat(),'p10':row.p10,'p50':row.p50,'p90':row.p90,'published':published,'carbon_proxy':carbon_profile.get(ts.hour,float('nan'))})
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    payload={'schema_version':1,'mode':mode,'source':'SMARD / Bundesnetzagentur · CC BY 4.0',
             'source_url':'https://www.smard.de','retrieved_at':retrieved,'built_at':datetime.now(timezone.utc).isoformat(),
             'prices':records(active),'forecast':forecast_rows,'forecast_meta':meta,'backtest':metrics,'simulation':sim,
             'carbon_note':'Domestic production-weighted lifecycle proxy; includes explicit factor assumptions; excludes imports/pumped storage. Missing carbon is N/A.',
             'job_mode':'static demo: no live job execution',
             'seasons':{'Winter':'2024-12-26','Spring':'2024-04-15','Summer':'2024-06-03','Autumn':'2024-10-15'}}
    payload=clean(payload)
    temp=out/'console.tmp';temp.write_text(json.dumps(payload,separators=(',',':'),allow_nan=False));temp.replace(out/'console.json')
    (out/'backtest.json').write_text(json.dumps(clean(metrics),indent=2))
    (out/'simulation.json').write_text(json.dumps(clean(sim),indent=2))
    return payload

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--history',default='data/historical/prices.csv');p.add_argument('--carbon',default='data/summer/prices.csv');p.add_argument('--live',default='data/live/prices.csv');p.add_argument('--out',default=os.getenv('WATTSHIFT_DATA','data/processed'));a=p.parse_args()
    result=build(a.history,a.carbon,a.live,a.out);print(json.dumps({'mode':result['mode'],'rows':len(result['prices']),'backtest':result['backtest'],'policies':result['simulation']['totals']},indent=2))
