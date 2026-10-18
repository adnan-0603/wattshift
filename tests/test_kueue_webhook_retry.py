"""Regression checks for Kueue webhook startup timing and hard failures."""
import subprocess
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import deploy


WEBHOOK_TEMPORARY_ERROR = (
    'Error from server (InternalError): failed calling webhook "mclusterqueue.kb.io": '
    'Post "https://kueue-webhook-service.kueue-system.svc:443/": '
    'dial tcp 10.96.103.77:443: connect: connection refused'
)


def finished(code, err='', out=''):
    return subprocess.CompletedProcess(['kubectl', 'apply'], code, stdout=out, stderr=err)


def test_queues_apply_immediately_when_webhook_is_ready(monkeypatch):
    calls=[]
    monkeypatch.setattr(deploy.subprocess, 'run', lambda *a, **k:(calls.append(a),finished(0))[1])
    monkeypatch.setattr(deploy.time, 'sleep', lambda s: pytest.fail('unexpected retry'))
    deploy.apply_kueue_queues()
    assert len(calls)==1


def test_queues_retry_transient_webhook_refusal(monkeypatch):
    responses=iter([finished(1,WEBHOOK_TEMPORARY_ERROR),finished(0,out='clusterqueue/wattshift-cpu created\n')])
    calls=[];waits=[]
    def fake_run(*args,**kwargs):
        calls.append(args)
        return next(responses)
    monkeypatch.setattr(deploy.subprocess,'run',fake_run)
    monkeypatch.setattr(deploy.time,'sleep',lambda seconds:waits.append(seconds))
    deploy.apply_kueue_queues(max_attempts=3, delay_seconds=2)
    assert len(calls)==2 and waits==[2]


def test_queues_fail_fast_on_real_api_schema_errors(monkeypatch):
    calls=[];diagnostics=[]
    monkeypatch.setattr(deploy.subprocess,'run',lambda *a,**k:(calls.append(a),finished(1,'Error from server (BadRequest): unknown field'))[1])
    monkeypatch.setattr(deploy,'kueue_webhook_diagnostics',lambda:diagnostics.append('shown'))
    monkeypatch.setattr(deploy.time,'sleep',lambda _:pytest.fail('schema error should not retry'))
    with pytest.raises(subprocess.CalledProcessError):
        deploy.apply_kueue_queues()
    assert len(calls)==1 and diagnostics==['shown']


def test_queues_stop_after_bounded_transient_retries(monkeypatch):
    calls=[];waits=[];diagnostics=[]
    monkeypatch.setattr(deploy.subprocess,'run',lambda *a,**k:(calls.append(a),finished(1,WEBHOOK_TEMPORARY_ERROR))[1])
    monkeypatch.setattr(deploy,'kueue_webhook_diagnostics',lambda:diagnostics.append('shown'))
    monkeypatch.setattr(deploy.time,'sleep',lambda seconds:waits.append(seconds))
    with pytest.raises(subprocess.CalledProcessError):
        deploy.apply_kueue_queues(max_attempts=3,delay_seconds=1)
    assert len(calls)==3 and waits==[1,1] and diagnostics==['shown']
