"""Read-only market/forecast API plus pure simulation; no public job mutation."""
import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI,HTTPException,Response
from pydantic import BaseModel,Field
from prometheus_client import Counter,Gauge,generate_latest,CONTENT_TYPE_LATEST
from .simulator import Interval,plan,timestamp
from .controller import FRESHNESS_SECONDS

app=FastAPI(title='WattShift',version='1.0.0rc3')
DATA=Path(os.getenv('WATTSHIFT_DATA','data/processed'))
requests=Counter('wattshift_api_requests_total','API requests',['path','status'])
freshness=Gauge('wattshift_data_age_seconds','Seconds since successful data retrieval')
price_g=Gauge('wattshift_price_eur_mwh','Latest available market price (see interval timestamp)')
carbon_g=Gauge('wattshift_carbon_estimate_g_kwh','Latest available domestic lifecycle estimate')
power_g=Gauge('wattshift_assumed_job_power_watts','Assumed facility watts for most recent simulated job')
saving_g=Gauge('wattshift_simulated_savings_eur','Replay estimated electricity savings')


def snapshot():
    try:
        result=json.loads((DATA/'console.json').read_text())
        if not isinstance(result,dict):raise ValueError('Invalid snapshot root')
        return result
    except (OSError,ValueError) as exc:
        raise HTTPException(503,'Dataset not ready; ingest/export first') from exc


def check_readiness(s,now=None,allow_stale_demo=False):
    """Validate both contract and live freshness; demo bypass is explicit and labelled."""
    now=now or datetime.now(timezone.utc)
    if s.get('schema_version')!=1 or s.get('mode') not in ('historical replay','market snapshot'):
        raise HTTPException(503,'Invalid data schema or mode')
    if not isinstance(s.get('prices'),list) or len(s['prices'])<24:
        raise HTTPException(503,'No market intervals')
    if not isinstance(s.get('forecast'),list) or len(s['forecast'])!=168:
        raise HTTPException(503,'Forecast horizon incomplete')
    try:
        end=timestamp(s['prices'][-1]['end'])
        first=timestamp(s['prices'][0]['start'])
        if first >= end:raise ValueError('Invalid market range')
        issue=timestamp(s['forecast_meta']['issue_time'])
        starts=[timestamp(r['start']) for r in s['forecast']]
        if any(b-a != timedelta(hours=1) for a,b in zip(starts,starts[1:])):
            raise ValueError('Forecast is not hourly and consecutive')
        if not isinstance(s['simulation']['jobs'],list):raise ValueError('Missing simulation jobs')
        retrieved=timestamp(s['retrieved_at'])
        for record in s['forecast']:
            price=record.get('published') if record.get('published') is not None else record.get('p50')
            if price is None or not isinstance(price,(float,int)) or not math.isfinite(price):
                raise ValueError('Missing/nonfinite forecast price')
        # Near-live market tail must be contiguous (older historical gaps are allowed).
        tail=s['prices'][-24:]
        if any(timestamp(a['end'])!=timestamp(b['start']) for a,b in zip(tail,tail[1:])):
            raise ValueError('Recent market interval gap')
        if any(timestamp(x['end'])<=timestamp(x['start']) for x in tail):
            raise ValueError('Invalid market interval')
        if any(not isinstance(x.get('price'),(int,float)) or not math.isfinite(x['price']) for x in tail):
            raise ValueError('Invalid market price')
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        raise HTTPException(503,'Invalid snapshot timestamps or required fields') from exc
    if s['mode']=='historical replay':
        return {'status':'historical-demo-ready','mode':s['mode'],'retrieved_at':s['retrieved_at'],'live_data_ready':False}
    # Dataset retrieval may be recent even when the actual interval collection is
    # old/truncated; separately enforce market coverage and issued forecast age.
    ages=((now-retrieved).total_seconds(),(now-issue).total_seconds())
    fresh=(all(-300 <= a <= FRESHNESS_SECONDS for a in ages)
           and now-timedelta(hours=12)<=end<=now+timedelta(days=3)
           and starts[0]<=now+timedelta(hours=1) and starts[-1]>=now)
    if not fresh and not allow_stale_demo:
        raise HTTPException(503,'Market snapshot stale or incomplete; refresh required')
    return {'status':'ready' if fresh else 'stale-demo-ready','mode':s['mode'],
            'retrieved_at':s['retrieved_at'],'live_data_ready':fresh}


@app.middleware('http')
async def count_request(request,call_next):
    response=await call_next(request)
    route=request.scope.get('route');path=getattr(route,'path','unmatched')
    requests.labels(path,str(response.status_code)).inc()
    return response

@app.get('/health')
def health():return {'status':'ok'}

@app.get('/ready')
def ready():
    return check_readiness(snapshot(),allow_stale_demo=os.getenv('WATTSHIFT_ALLOW_STALE_DEMO')=='1')

@app.get('/snapshot')
def get_snapshot():return snapshot()

@app.get('/forecast')
def forecast():
    s=snapshot();return {'issue_time':s['forecast_meta']['issue_time'],'retrieved_at':s['retrieved_at'],'data_mode':s['mode'],'metadata':s['forecast_meta'],'intervals':s['forecast']}

@app.get('/prices')
def prices():
    s=snapshot();return {'mode':s['mode'],'source':s['source'],'retrieved_at':s['retrieved_at'],'intervals':s['prices']}

@app.get('/savings')
def savings():return snapshot()['simulation']

@app.get('/jobs')
def jobs():
    path=DATA/'controller-state.json'
    if not path.exists():return {'mode':'cluster','controller_connected':False,'jobs':[]}
    try:
        data=json.loads(path.read_text())
        if not isinstance(data,dict) or not isinstance(data.get('jobs'),list):raise ValueError('Invalid controller state')
        age=(datetime.now(timezone.utc)-timestamp(data['updated_at'])).total_seconds()
    except (OSError,ValueError,KeyError,TypeError) as exc:
        raise HTTPException(503,'Controller state invalid or unreadable') from exc
    return {**data,'controller_connected':0<=age<90,'age_seconds':age}

class PlanRequest(BaseModel):
    release:str
    deadline:str
    duration_minutes:int=Field(default=240,ge=15,le=7*24*60)
    gpu_count:int=Field(default=4,ge=1,le=1024)
    gpu_watts:float=Field(default=300,gt=0,le=2000,allow_inf_nan=False)
    host_watts:float=Field(default=100,ge=0,le=10000,allow_inf_nan=False)
    pue:float=Field(default=1.2,ge=1,le=3,allow_inf_nan=False)
    tariff_adder:float=Field(default=0,ge=0,le=2,allow_inf_nan=False)
    objective:str='cost'

@app.post('/plan')
def calculate(request:PlanRequest):
    s=snapshot()
    try:
        release=timestamp(request.release)
        deadline=timestamp(request.deadline)
        if (deadline-release).total_seconds()>14*86400:
            raise ValueError('Maximum planning window is 14 days')
        # Explicit retrospective calculator, not an online forecast controller.
        rows=[Interval(timestamp(r['start']),timestamp(r['end']),release,r['price'],r.get('carbon')) for r in s['prices']]
        result=plan(rows,decision_at=release,release=release,deadline=deadline,duration_minutes=request.duration_minutes,gpu_count=request.gpu_count,gpu_watts=request.gpu_watts,host_watts=request.host_watts,pue=request.pue,tariff_adder_eur_kwh=request.tariff_adder,objective=request.objective)
    except (ValueError,TypeError) as exc:raise HTTPException(422,str(exc))
    power_g.set((request.gpu_count*request.gpu_watts+request.host_watts)*request.pue)
    return {**result,'data_mode':'retrospective perfect-information calculator; not measured savings'}

@app.get('/metrics')
def metrics():
    try:
        s=snapshot();freshness.set(max(0,(datetime.now(timezone.utc)-timestamp(s['retrieved_at'])).total_seconds()))
        now=datetime.now(timezone.utc)
        current=[r for r in s['prices'] if timestamp(r['start'])<=now<timestamp(r['end'])]
        price_g.set(current[0]['price'] if current else float('nan'))
        carbon_g.set(current[0]['carbon'] if current and current[0].get('carbon') is not None else float('nan'))
        value=s['simulation']['totals']['cheapest']['saving_eur'];saving_g.set(value if value is not None else float('nan'))
    except (HTTPException,KeyError,TypeError,ValueError,AttributeError):pass
    return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)
