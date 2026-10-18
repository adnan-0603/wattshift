"""Independently discovered rc4 scheduling and release regressions."""
from datetime import timedelta
from pathlib import Path
import yaml
from wattshift.controller import forecast_decision,reconcile
from test_admission_rc3 import FakeKube,fake_signal,job,workload,T


def test_changed_deadline_invalidates_persisted_start():
    saved=(T+timedelta(hours=4)).isoformat()
    admitted,reason,chosen=forecast_decision(fake_signal(),T,T+timedelta(hours=5),7200,planned_start=saved)
    assert chosen!=saved and reason!='awaiting previous planned start'


def test_owner_job_uid_mismatch_fails_closed():
    w=workload();w['metadata']['ownerReferences'][0]['uid']='deleted-job-uid'
    j=job();j['metadata']['uid']='reused-name-new-uid'
    k=FakeKube([w],{'train':j})
    assert reconcile(k,now=T,forecast=None)[0]['status']=='owner-uid-mismatch'
    assert not k.patches


def test_recreated_workload_does_not_inherit_old_plan():
    w=workload();w['metadata']['uid']='new-workload-uid'
    k=FakeKube([w])
    old={('train','old-workload-uid'):T.isoformat()}
    result=reconcile(k,now=T,forecast=fake_signal(),previous_plans=old)
    assert result[0]['status']=='deferred' and result[0]['workload_uid']=='new-workload-uid'
    assert not k.patches


def test_same_uid_reuses_planned_slot_without_hour_drift():
    w=workload();k=FakeKube([w])
    old={('train',w['metadata']['uid']):(T+timedelta(hours=2)).isoformat()}
    result=reconcile(k,now=T+timedelta(hours=2,seconds=20),forecast=fake_signal(),previous_plans=old)
    assert result[0]['status']=='awaiting-kueue' and len(k.patches)==1


def test_ci_stack_bootstrapped_before_live_acceptance():
    workflow=yaml.safe_load((Path(__file__).resolve().parents[1]/'.github/workflows/cluster.yml').read_text())
    steps=[s.get('run','') for s in workflow['jobs']['integration']['steps']]
    assert 'make stack-lite' in steps
    assert 'python scripts/cluster_acceptance.py --lite' in steps
    assert steps.index('make stack-lite')<steps.index('python scripts/cluster_acceptance.py --lite')
