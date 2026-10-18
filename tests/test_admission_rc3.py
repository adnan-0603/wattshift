"""Kueue admission-gate correctness without any running cluster or GPU."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import json
import pytest
import yaml
from wattshift.controller import activate_admission_check, reconcile, CHECK_NAME, CHECK_CONTROLLER

T = datetime(2026, 10, 18, 10, tzinfo=timezone.utc)


def fake_signal(now=T):
    prices = [100, 100, 10, 10, 50, 50]
    return {'data_mode': 'market snapshot', 'retrieved_at': now.isoformat(),
            'issue_time': now.isoformat(), 'intervals': [
                {'start': (now+timedelta(hours=i)).isoformat(), 'p50':float(v)}
                for i,v in enumerate(prices)]}


def workload(name='train', state='Pending', active=True, admitted=False, checked=True):
    return {'metadata': {'name': f'wl-{name}', 'resourceVersion': '23', 'uid': 'workload-'+name,
                         'ownerReferences':[{'kind':'Job','name':name}]},
            'spec': {'active':active}, 'status': {
                'admissionChecks': ([{'name': CHECK_NAME,'state':state,'message':''}] if checked else []),
                'conditions': ([{'type':'Admitted','status':'True'}] if admitted else [])}}


def job(name='train', seconds='7200', deadline=None, **ann):
    annotations = {'wattshift.dev/checkpoint-enabled':'true',
                   'wattshift.dev/estimated-seconds':seconds,
                   'wattshift.dev/deadline': (deadline or T+timedelta(hours=4)).isoformat(),
                   **ann}
    return {'metadata': {'labels':{'wattshift.dev/managed':'true'}, 'annotations':annotations},
            'status': {}}


class FakeKube:
    def __init__(self, works, jobs=None):
        self.works=works
        self.jobs=jobs or {item['metadata']['ownerReferences'][0]['name']:job() for item in works}
        self.patches=[]
        self.check={'metadata':{'resourceVersion':'1','generation':1},
                    'spec':{'controllerName':CHECK_CONTROLLER},'status':{}}
    def get(self,path):
        if path.endswith('/workloads'):return {'items':deepcopy(self.works)}
        if '/admissionchecks/' in path:return deepcopy(self.check)
        if '/jobs/' in path:return deepcopy(self.jobs[path.split('/')[-1]])
        raise AssertionError(path)
    def patch_status(self,path,body):
        assert '/status' not in path
        assert set(body)=={'metadata','status'}
        self.patches.append((path,body))
        return {}


def test_gate_pending_until_selected_hour_then_ready():
    k=FakeKube([workload()])
    result=reconcile(k, now=T, forecast=fake_signal())
    assert result[0]['status']=='deferred'
    assert not k.patches
    saved={('train', 'workload-train'):result[0]['planned_start_utc']}
    result=reconcile(k, now=T+timedelta(hours=2,seconds=15), forecast=fake_signal(),previous_plans=saved)
    assert result[0]['status']=='awaiting-kueue'
    assert len(k.patches)==1
    path,patch=k.patches[0]
    assert path.endswith('/workloads/wl-train')
    assert patch['metadata']['resourceVersion']=='23'
    assert patch['status']['admissionChecks'][0]['state']=='Ready'
    assert 'spec' not in patch   # Kueue owns Job.suspend / Workload.active.


def test_missing_gate_is_not_a_permission_to_start():
    k=FakeKube([workload(checked=False)])
    result=reconcile(k,now=T,forecast=None)
    assert result[0]['status']=='gate-missing'
    assert k.patches==[]


def test_inactive_workload_not_reactivated():
    k=FakeKube([workload(active=False)])
    result=reconcile(k,now=T,forecast=None)
    assert result[0]['status']=='inactive' and not k.patches


def test_pending_gate_with_invalid_metadata_fails_closed():
    k=FakeKube([workload()], jobs={'train':job(seconds='bad')})
    result=reconcile(k,now=T,forecast=fake_signal())
    assert result[0]['status']=='error' and not k.patches


def test_ready_gate_never_revoked_or_patched_after_admission():
    k=FakeKube([workload(state='Ready',admitted=True)])
    result=reconcile(k,now=T,forecast=fake_signal())
    assert result[0]['status']=='admitted' and k.patches==[]


def test_preserve_other_check_when_releasing_our_gate():
    w=workload()
    w['status']['admissionChecks'].append({'name':'second','state':'Pending','message':'another controller'})
    k=FakeKube([w])
    result=reconcile(k,now=T,forecast=None)
    assert result[0]['status']=='awaiting-kueue'
    checks=k.patches[0][1]['status']['admissionChecks']
    assert checks[0]['state']=='Ready' and checks[1]==w['status']['admissionChecks'][1]


def test_check_activation_requires_expected_controller_and_resource_version():
    k=FakeKube([])
    assert activate_admission_check(k,T) is True
    patch=k.patches[0][1]
    assert patch['metadata']['resourceVersion']=='1'
    assert patch['status']['conditions'][0]['type']=='Active'
    assert patch['status']['conditions'][0]['status']=='True'
    k.check['spec']['controllerName']='malicious/other'
    with pytest.raises(ValueError,match='controllerName'):activate_admission_check(k,T)
    assert len(k.patches)==1


def test_healthy_check_activation_idempotent():
    k=FakeKube([])
    k.check['status']['conditions']=[{'type':'Active','status':'True','observedGeneration':1}]
    assert activate_admission_check(k,T) is False
    assert not k.patches


def test_clusterqueue_admission_check_and_scoped_rbac():
    root=Path(__file__).parents[1]
    queue=list(yaml.safe_load_all((root/'infra/kubernetes/queues.yaml').read_text()))
    cluster=next(x for x in queue if x['kind']=='ClusterQueue')
    check=next(x for x in queue if x['kind']=='AdmissionCheck')
    assert cluster['spec']['admissionChecks']==[CHECK_NAME]
    assert check['spec']['controllerName']==CHECK_CONTROLLER
    platform=list(yaml.safe_load_all((root/'infra/kubernetes/platform.yaml').read_text()))
    role=next(x for x in platform if x['kind']=='Role' and x['metadata']['name']=='wattshift-controller')
    assert any('workloads/status' in r['resources'] and 'patch' in r['verbs'] for r in role['rules'])
    assert all(not ('workloads' in r['resources'] and 'patch' in r['verbs']) for r in role['rules'])
    cr=next(x for x in platform if x['kind']=='ClusterRole' and x['metadata']['name']=='wattshift-admissioncheck-status')
    assert any('admissionchecks/status' in r['resources'] for r in cr['rules'])


def test_one_bad_workload_cannot_approve_other_workload():
    k=FakeKube([workload('bad'),workload('good')],
               {'bad':job(seconds='nan'), 'good':job(seconds='7200')})
    result=reconcile(k,now=T,forecast=None)
    assert [x['status'] for x in result]==['error','awaiting-kueue']
    assert len(k.patches)==1 and k.patches[0][0].endswith('wl-good')


def _api_error(status):
    import httpx
    request=httpx.Request('GET','https://kubernetes.test/api')
    response=httpx.Response(status,request=request)
    return httpx.HTTPStatusError(f'Kubernetes HTTP {status}',request=request,response=response)


def test_deleted_job_does_not_block_another():
    class GoneJob(FakeKube):
        def get(self,path):
            if path.endswith('/jobs/bad'):raise _api_error(404)
            return super().get(path)
    k=GoneJob([workload('bad'),workload('good')])
    result=reconcile(k,now=T,forecast=None)
    assert [x['status'] for x in result]==['job-unavailable','awaiting-kueue']
    assert len(k.patches)==1


def test_conflict_on_one_workload_still_releases_another():
    class Conflict(FakeKube):
        def patch_status(self,path,body):
            if path.endswith('wl-bad'):raise _api_error(409)
            return super().patch_status(path,body)
    k=Conflict([workload('bad'),workload('good')])
    result=reconcile(k,now=T,forecast=None)
    assert [x['status'] for x in result]==['status-conflict','awaiting-kueue']
    assert len(k.patches)==1 and k.patches[0][0].endswith('wl-good')


def test_ungated_already_admitted_reports_migration_hazard():
    k=FakeKube([workload(state='Pending',admitted=True)])
    result=reconcile(k,now=T,forecast=None)
    assert result[0]['status']=='already-admitted-ungated'
    assert not k.patches


def test_rejected_check_not_automatically_approved():
    k=FakeKube([workload(state='Rejected')])
    result=reconcile(k,now=T,forecast=None)
    assert result[0]['status']=='rejected'
    assert not k.patches
