from datetime import datetime,timedelta,timezone
from pathlib import Path
import json,os,signal,sqlite3,subprocess,sys,time
from contextlib import closing
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from wattshift import api
from wattshift.ingest import normalize_prices,carbon_estimate,save_db
from wattshift.forecast import features,predict
from wattshift.policies import best_start,replay
from wattshift.controller import decision,reconcile
from wattshift.simulator import Interval,plan

T=datetime(2024,6,1,tzinfo=timezone.utc)
def market(prices):return [Interval(T+timedelta(hours=i),T+timedelta(hours=i+1),T,float(p)) for i,p in enumerate(prices)]
def scheduled(rows,**kw):
 opts=dict(decision_at=T,release=T,deadline=T+timedelta(hours=4),duration_minutes=120,gpu_count=1,gpu_watts=1000,host_watts=0,pue=1);opts.update(kw);return plan(rows,**opts)

def test_energy_units_and_deadline():
 r=scheduled(market([100,100,10,10]));assert r['baseline']['energy_cost_eur']==pytest.approx(.2);assert r['selected']['energy_cost_eur']==pytest.approx(.02)
 assert r['selected']['end_utc']==(T+timedelta(hours=4)).isoformat()
def test_gaps_not_crossed():
 rs=market([10,20,30,40]);assert best_start([np.nan,1,3],0,3,2)==1
 with pytest.raises(ValueError):scheduled([rs[0],rs[2]])
def test_no_invented_carbon():assert scheduled(market([1,2,3,4]))['estimated_carbon_saving_kg'] is None
def test_negative_baseline_percentage():assert scheduled(market([-1,-2,-3,-4]))['energy_cost_saving_pct'] is None
def test_publication_cutoff():
 rs=market([100,100,1,1]);r=rs[2];rs[2]=Interval(r.start,r.end,T+timedelta(days=1),r.price_eur_mwh)
 assert scheduled(rs)['selected']['start_utc']==T.isoformat()
def test_quarter_hour_energy():
 rs=[Interval(T+timedelta(minutes=i*15),T+timedelta(minutes=(i+1)*15),T,100) for i in range(4)]
 assert scheduled(rs,duration_minutes=60)['selected']['energy_cost_eur']==pytest.approx(.1)
def test_unknown_carbon_objective_rejected():
 with pytest.raises(ValueError):scheduled(market([1,2,3,4]),objective='carbon')
def test_carbon_weighting_and_missing():
 index=pd.date_range('2024-06-01',periods=2,freq='h',tz='UTC');gen=pd.DataFrame({'a':[1,1],'b':[3,np.nan]},index=index)
 result=carbon_estimate(gen,{'a':100,'b':500});assert result.iloc[0]==400;assert pd.isna(result.iloc[1])
def test_ingest_is_idempotent(tmp_path):
 series=pd.Series([10,20],index=pd.date_range(T,periods=2,freq='h'));frame=normalize_prices(series,'hour');frame['carbon_g_kwh']=np.nan
 meta={'retrieved_at':T.isoformat(),'resolution':'hour'};db=tmp_path/'test.db'
 save_db(frame,db,meta);save_db(frame,db,meta)
 with closing(sqlite3.connect(db)) as c:assert c.execute('SELECT COUNT(*) FROM intervals').fetchone()[0]==2

def test_forecast_never_uses_future_actuals():
 idx=pd.date_range('2024-01-01',periods=24*65,freq='h',tz='UTC');v=40+10*np.sin(np.arange(len(idx))/24)
 frame=pd.DataFrame({'price_eur_mwh':v},index=idx);origin=idx[-24*7]
 p1,m=predict(frame,origin,n_estimators=5);changed=frame.copy();changed.loc[changed.index>=origin,'price_eur_mwh']=999999
 p2,_=predict(changed,origin,n_estimators=5);np.testing.assert_allclose(p1.p50,p2.p50);assert (p1.p10<=p1.p50).all();assert (p1.p50<=p1.p90).all()
def test_replay_forecast_decisions_and_regret():
 prices=np.tile([10,20,30,80],42);r=replay(prices,np.repeat(50,168),seed=7,count=10)
 assert r==replay(prices,np.repeat(50,168),seed=7,count=10)
 assert r['regret_eur_vs_hindsight']>=0
 for j in r['jobs']:
  for out in j['policies'].values():
   if out:assert out['start_slot']>=j['release_slot'] and out['end_slot']<=j['deadline_slot']
def test_controller_hysteresis_deadline_and_stale():
 assert decision(100,80,True,T)==(False,'price above stop threshold')
 assert decision(83,80,False,T)[0] is False
 assert decision(79,80,False,T)[0] is True
 assert decision(None,80,False,T)[0] is True
 assert decision(999,80,False,T,T+timedelta(seconds=30),100)[0] is True

def test_controller_does_not_patch_workload_active_for_threshold_policy():
 class Kube:
  def __init__(self):self.calls=[]
  def get(self,path):
   if path.endswith('/workloads'):
    return {'items':[{'metadata':{'name':'w','resourceVersion':'1','ownerReferences':[{'kind':'Job','name':'j'}]},
                      'spec':{'active':True},'status':{'admissionChecks':[{'name':'wattshift-forecast','state':'Pending'}]}}]}
   return {'metadata':{'labels':{'wattshift.dev/managed':'true'},
                       'annotations':{'wattshift.dev/checkpoint-enabled':'true',
                                      'wattshift.dev/policy':'price-threshold'}}}
  def patch_status(self,path,body):self.calls.append((path,body))
 k=Kube()
 out=reconcile(k,999,now=T)
 assert out[0]['status']=='deferred' and not k.calls
 out=reconcile(k,10,now=T)
 assert out[0]['status']=='awaiting-kueue' and len(k.calls)==1
 assert k.calls[0][1]['status']['admissionChecks'][0]['state']=='Ready'
 assert 'spec' not in k.calls[0][1]

def test_checkpoint_resume_matches_uninterrupted(tmp_path):
 check=tmp_path/'resume.json';base=tmp_path/'baseline.json'
 cmd=[sys.executable,'-m','wattshift.worker','--checkpoint',str(check),'--steps','60','--delay','.02']
 proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 deadline=time.monotonic()+10
 while (not check.exists() or json.loads(check.read_text())['step']<3) and time.monotonic()<deadline:time.sleep(.02)
 assert check.exists();proc.send_signal(signal.SIGTERM);proc.communicate(timeout=10);assert proc.returncode==75
 saved=json.loads(check.read_text());assert 0<saved['step']<60
 subprocess.run(cmd,check=True,capture_output=True)
 subprocess.run([sys.executable,'-m','wattshift.worker','--checkpoint',str(base),'--steps','60','--delay','0'],check=True,capture_output=True)
 assert json.loads(check.read_text())==json.loads(base.read_text())

def test_api_returns_503_without_data(tmp_path,monkeypatch):
 monkeypatch.setattr(api,'DATA',tmp_path)
 with TestClient(api.app) as c:assert c.get('/health').status_code==200;assert c.get('/ready').status_code==503

def test_api_contract_and_plan(monkeypatch):
 monkeypatch.setenv('WATTSHIFT_ALLOW_STALE_DEMO','1')
 monkeypatch.setattr(api,'DATA',Path('data/processed'))
 with TestClient(api.app) as c:
  assert c.get('/ready').status_code==200
  assert len(c.get('/forecast').json()['intervals'])==168
  s=c.get('/snapshot').json();first=s['prices'][0]
  release=pd.Timestamp(first['start']);r=c.post('/plan',json={'release':release.isoformat(),'deadline':(release+pd.Timedelta(hours=12)).isoformat(),'duration_minutes':240})
  assert r.status_code==200;assert r.json()['data_mode'].startswith('retrospective')
  assert c.post('/plan',json={'release':'oops','deadline':'oops'}).status_code==422
  assert c.post('/plan',json={'release':release.isoformat(),'deadline':release.isoformat(),'gpu_count':0}).status_code==422
  assert 'wattshift_data_age_seconds' in c.get('/metrics').text

def test_manifest_scopes_and_resources():
 import yaml
 resources=list(yaml.safe_load_all(Path('infra/kubernetes/platform.yaml').read_text()))
 assert any(x['kind']=='CronJob' and x['spec']['concurrencyPolicy']=='Forbid' for x in resources)
 role=next(x for x in resources if x['kind']=='Role' and x['metadata']['name']=='wattshift-controller')
 assert all('delete' not in r['verbs'] and '*' not in r['verbs'] for r in role['rules'])
 assert all(r['resources']!=['jobs'] or 'patch' not in r['verbs'] for r in role['rules'])
