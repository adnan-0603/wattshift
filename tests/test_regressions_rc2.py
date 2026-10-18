"""Regressions for rc1 readiness defects and policy/runtime divergence."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math

import pytest
from fastapi.testclient import TestClient
from wattshift import api
from wattshift.controller import decision, forecast_decision, reconcile
from wattshift.scheduling import best_start
from wattshift.policies import best_start as replay_start

UTC=timezone.utc
T=datetime(2026,10,18,10,tzinfo=UTC)


def snapshot(now=T):
    return {
        'schema_version': 1, 'mode':'market snapshot',
        'retrieved_at':now.isoformat(),
        'prices':[{'start':(now-timedelta(minutes=15*(24-i))).isoformat(),
                   'end':(now-timedelta(minutes=15*(23-i))).isoformat(), 'price':50} for i in range(24)],
        'forecast_meta':{'issue_time':now.isoformat()},
        'forecast':[{'start':(now+timedelta(hours=i)).isoformat(), 'p50':20, 'published':None} for i in range(168)],
        'simulation':{'jobs': []}
    }


def test_fresh_ready_and_timestamp_validation():
    s=snapshot()
    assert api.check_readiness(s,now=T)['live_data_ready'] is True
    s['retrieved_at']='2000-01-01T00:00:00+00:00'
    with pytest.raises(api.HTTPException) as e:api.check_readiness(s,now=T)
    assert e.value.status_code==503
    assert api.check_readiness(s,now=T,allow_stale_demo=True)['status']=='stale-demo-ready'
    s=snapshot();s['forecast']=s['forecast'][:20]
    with pytest.raises(api.HTTPException):api.check_readiness(s,now=T)
    s=snapshot();s['prices'][-1]['start']='broken'
    with pytest.raises(api.HTTPException):api.check_readiness(s,now=T)
    s=snapshot();s['prices'][-2]['end']=(T-timedelta(days=10)).isoformat()
    with pytest.raises(api.HTTPException):api.check_readiness(s,now=T)
    s=snapshot();s['forecast'][24]['p50']=None
    with pytest.raises(api.HTTPException):api.check_readiness(s,now=T)


def test_price_coverage_needed_not_only_retrieval_time():
    s=snapshot()
    for row in s['prices']:
        row['start']=(datetime.fromisoformat(row['start'])-timedelta(days=10)).isoformat()
        row['end']=(datetime.fromisoformat(row['end'])-timedelta(days=10)).isoformat()
    with pytest.raises(api.HTTPException):api.check_readiness(s,now=T)


def test_historical_replay_explicitly_nonlive():
    s=snapshot();s['mode']='historical replay';s['retrieved_at']='2000-01-01T00:00:00Z'
    assert api.check_readiness(s,now=T)['live_data_ready'] is False


def test_ready_endpoint_fails_stale_and_malformed(monkeypatch,tmp_path):
    data=tmp_path/'console.json';s=snapshot();s['retrieved_at']='2000-01-01T00:00:00Z'
    data.write_text(json.dumps(s))
    monkeypatch.setattr(api,'DATA',tmp_path)
    monkeypatch.delenv('WATTSHIFT_ALLOW_STALE_DEMO',raising=False)
    with TestClient(api.app) as c:
        assert c.get('/ready').status_code==503
        monkeypatch.setenv('WATTSHIFT_ALLOW_STALE_DEMO','1')
        r=c.get('/ready');assert r.status_code==200
        assert r.json()['live_data_ready'] is False
        assert r.json()['status']=='stale-demo-ready'
        assert c.get('/forecast').json()['data_mode']=='market snapshot'
        assert c.get('/forecast').json()['retrieved_at']==s['retrieved_at']
        (tmp_path/'controller-state.json').write_text('not json')
        assert c.get('/jobs').status_code==503


def signal(now=T,values=(100,100,10,10,50,50)):
    return {'data_mode':'market snapshot', 'retrieved_at':now.isoformat(),
            'issue_time':now.isoformat(),
            'intervals':[{'start':(now+timedelta(hours=i)).isoformat(), 'p50':float(v), 'published':None}
                         for i,v in enumerate(values)]}


def test_shared_policy_earliest_tie_and_gap():
    prices=[70,50,10,10,10,10]
    assert best_start(prices,0,6,2)==2
    assert best_start(prices,0,6,2)==replay_start(prices,0,6,2)
    assert best_start([float('nan'),3,1,None,1],0,5,2)==1
    assert best_start([None, float('nan')],0,2,1) is None
    with pytest.raises(ValueError):best_start(prices,-1,6,1)


def test_forecast_selects_cheapest_not_current_threshold():
    on,why,start=forecast_decision(signal(),T,T+timedelta(hours=4),2*3600)
    assert on is False
    assert start==(T+timedelta(hours=2)).isoformat()
    assert 'deferred' in why
    active,_,_=forecast_decision(signal(),T+timedelta(hours=2),T+timedelta(hours=4),2*3600)
    assert active is True


def test_forecast_nonpreemptive_deadline_stale_and_missing_data():
    s=signal()
    assert forecast_decision(s,T,T+timedelta(hours=6),7200,running=True)[0] is True
    assert forecast_decision(s,T,T+timedelta(seconds=400),360)[0] is True
    stale=deepcopy(s);stale['retrieved_at']='2000-01-01T00:00:00Z'
    assert 'stale' in forecast_decision(stale,T,T+timedelta(hours=6),3600)[1]
    broken=deepcopy(s);broken['intervals'][2]['start']=(T+timedelta(minutes=137)).isoformat()
    assert 'discontinuous' in forecast_decision(broken,T,T+timedelta(hours=6),3600)[1]
    assert 'unavailable' in forecast_decision(None,T,T+timedelta(hours=6),3600)[1]
    assert forecast_decision(s,T+timedelta(minutes=30),T+timedelta(hours=2,minutes=30),2*3600)[0] is True  # no 2 full hours


def test_controller_only_releases_its_admission_check():
    class Kube:
        def __init__(self,running=False):self.calls=[];self.running=running
        def get(self,path):
            if path.endswith('/workloads'):
                return {'items':[{'metadata':{'name':'w','resourceVersion':'12',
                       'ownerReferences':[{'kind':'Job','name':'j'}]},
                       'spec':{'active':True}, 'status': {'admissionChecks': [
                           {'name':'wattshift-forecast','state':'Pending','message':''},
                           {'name':'other-check','state':'Ready','message':'other'}],
                           'conditions':[{'type':'Admitted','status':'True'}] if self.running else []}}]}
            return {'metadata':{'labels':{'wattshift.dev/managed':'true'},
                                'annotations':{'wattshift.dev/checkpoint-enabled':'true',
                                               'wattshift.dev/estimated-seconds':'7200',
                                               'wattshift.dev/deadline':(T+timedelta(hours=4)).isoformat()}},
                    'status':{'active':1 if self.running else 0}}
        def patch_status(self,path,body):self.calls.append((path,body))
    k=Kube();results=reconcile(k,now=T,forecast=signal())
    assert results[0]['status']=='deferred'
    assert results[0]['planned_start_utc']==(T+timedelta(hours=2)).isoformat()
    assert k.calls == []   # No Workload.spec.active write; initial check is Pending.
    k=Kube(running=True);results=reconcile(k,now=T,forecast=signal())
    assert not k.calls  # Existing admitted Workload is unsafe to mutate retrospectively.
    assert results[0]['status']=='already-admitted-ungated'


def test_invalid_managed_job_does_not_prevent_others():
    class Kube:
        def __init__(self):self.calls=[]
        def get(self,path):
            if path.endswith('/workloads'):
                return {'items':[{'metadata':{'name':n,'resourceVersion':'1',
                        'ownerReferences':[{'kind':'Job','name':n}]},'spec':{'active':True},
                        'status':{'admissionChecks':[{'name':'wattshift-forecast','state':'Pending'}]}}
                        for n in ('bad','good')]}
            return {'metadata':{'labels':{'wattshift.dev/managed':'true'}, 'annotations':{
                'wattshift.dev/checkpoint-enabled':'true',
                'wattshift.dev/estimated-seconds':'banana' if path.endswith('bad') else '7200',
                'wattshift.dev/deadline':(T+timedelta(hours=4)).isoformat()}}}
        def patch_status(self,path,body):self.calls.append((path,body))
    result=reconcile(Kube(),now=T,forecast=signal())
    assert [row['status'] for row in result]==['error','deferred']

def test_invalid_plan_request_bounded(monkeypatch,tmp_path):
    s=snapshot();(tmp_path/'console.json').write_text(json.dumps(s))
    monkeypatch.setattr(api,'DATA',tmp_path)
    with TestClient(api.app) as c:
        r=c.post('/plan',json={'release':T.isoformat(),'deadline':(T+timedelta(days=30)).isoformat()})
        assert r.status_code==422


def test_forecast_persisted_start_does_not_drift_after_boundary():
    s=signal()
    initial=forecast_decision(s,T,T+timedelta(hours=5),7200)
    assert initial[0] is False
    due=T+timedelta(hours=2,seconds=20)
    # A fresh recomputation would exclude the just-started 12:00 price bucket,
    # potentially deferring again. The persisted plan must become executable.
    eligible,reason,started=forecast_decision(s,due,T+timedelta(hours=5),7200,
                                               planned_start=initial[2])
    assert eligible is True and started==initial[2]
    assert 'previous planned start reached' in reason
