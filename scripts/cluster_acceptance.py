#!/usr/bin/env python3
"""Live admission-gate + checkpoint recovery acceptance (requires real kind/Kueue).

Do not run without an isolated WattShift cluster. This command creates one
CPU-only sample Job and changes Workload.active for controlled recovery tests;
the WattShift controller NEVER writes Workload.active in normal operation.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import cluster

NS = 'wattshift'
JOB = 'wattshift-checkpoint-demo'
CHECK = 'wattshift-forecast'


def run(*args):
    return subprocess.check_output(cluster.kubectl(*args), text=True)


def wait_for(check, timeout=180):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if check():
            return
        time.sleep(2)
    raise RuntimeError('Acceptance condition timed out')


def get_json(*args):
    return json.loads(run(*args, '-o', 'json'))


def workloads():
    return get_json('-n', NS, 'get', 'workloads')['items']


def job_workload():
    return next((w for w in workloads() if any(
        r.get('kind') == 'Job' and r.get('name') == JOB
        for r in w['metadata'].get('ownerReferences', []))), None)


def progress():
    try:
        return int(run('-n', NS, 'exec', 'deployment/wattshift-api', '--', 'python', '-c',
                  "import json;print(json.load(open('/data/checkpoint-demo/state.json'))['step'])").strip())
    except subprocess.CalledProcessError:
        return 0


def verify(lite=False):
    # App smoke checks before touching the controller.
    run('-n', NS, 'exec', 'deployment/wattshift-api', '--', 'python', '-c',
        "import json,urllib.request;x=json.load(urllib.request.urlopen('http://wattshift-console/api/snapshot'));assert x['prices']")
    if not lite:
        run('-n', NS, 'exec', 'deployment/wattshift-api', '--', 'python', '-c',
            "import json,urllib.request;x=json.load(urllib.request.urlopen('http://wattshift-prometheus:9090/api/v1/targets'));assert any(t['health']=='up' and t['labels'].get('job')=='wattshift' for t in x['data']['activeTargets'])")

    controller = get_json('-n', NS, 'get', 'deployment', 'wattshift-controller')
    original_replicas = controller['spec'].get('replicas', 1)
    if original_replicas != 1:
        raise RuntimeError('Acceptance requires exactly one running WattShift controller')
    try:
        get_json('-n', NS, 'get', 'job', JOB)
    except subprocess.CalledProcessError:
        pass
    else:
        raise RuntimeError('Demo Job already exists: use a fresh isolated cluster or manually retire it; no automatic deletion')

    # Controller absent: Kueue MUST NOT admit freshly created workloads.
    run('-n', NS, 'scale', 'deployment/wattshift-controller', '--replicas=0')
    try:
        wait_for(lambda: not get_json('-n', NS, 'get', 'pods', '-l', 'app=wattshift-controller')['items'])
        template=json.loads(subprocess.check_output([sys.executable,
                       str(cluster.ROOT/'scripts/demo_jobs.py')], text=True))
        cluster.KUBECONFIG.parent.mkdir(parents=True,exist_ok=True)
        demo=cluster.ROOT/'.local/demo-job.json'
        demo.write_text(json.dumps(template))
        run('apply','-f',str(demo))
        wait_for(lambda: job_workload() is not None)

        def gated():
            w=job_workload()
            if not w: return False
            checks=w.get('status',{}).get('admissionChecks',[])
            return any(c.get('name')==CHECK and c.get('state')=='Pending' for c in checks)

        wait_for(gated)
        time.sleep(5)  # More than a zero-time read; first-admission race smoke test.
        w=job_workload()
        if any(c.get('type')=='Admitted' and c.get('status')=='True'
               for c in w.get('status',{}).get('conditions',[])):
            raise AssertionError('Kueue admitted before WattShift gate released')
        if get_json('-n',NS,'get','pods','-l',f'job-name={JOB}')['items']:
            raise AssertionError('Job Pod appeared while admission controller was stopped')

        # Controller can now release its check. With bundled stale market data
        # the explicit fail-open policy releases immediately; this is NOT proof
        # of a real forecast selecting the cheapest future window.
        run('-n',NS,'scale','deployment/wattshift-controller','--replicas=1')
        run('-n',NS,'rollout','status','deployment/wattshift-controller','--timeout=180s')
        wait_for(lambda:any(c.get('name')==CHECK and c.get('state')=='Ready' for c in
                      (job_workload() or {}).get('status',{}).get('admissionChecks',[])))
        wait_for(lambda:any(c.get('type')=='Admitted' and c.get('status')=='True' for c in
                      (job_workload() or {}).get('status',{}).get('conditions',[])))
        wait_for(lambda:progress()>5)
        w=job_workload()
        name=w['metadata']['name']

        # Controlled operator interruption; normal controller never changes active.
        run('-n',NS,'patch','workload',name,'--type=merge','-p','{"spec":{"active":false}}')
        wait_for(lambda:get_json('-n',NS,'get','job',JOB).get('spec',{}).get('suspend') is True)
        wait_for(lambda:not get_json('-n',NS,'get','pods','-l',f'job-name={JOB}')['items'])
        stopped=progress()
        time.sleep(3)
        if progress()!=stopped:
            raise AssertionError('Checkpoint advanced after all Pods stopped')
        run('-n',NS,'patch','workload',name,'--type=merge','-p','{"spec":{"active":true}}')
        wait_for(lambda:progress()>stopped)
        commit_result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=cluster.ROOT,
                                       text=True, capture_output=True)
        commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None
        evidence={'verified_at':datetime.now(timezone.utc).isoformat(),
                  'commit': commit,
                  'cluster':'kind-wattshift','profile':'lite' if lite else 'full',
                  'gate_pending_without_controller':True,
                  'released_by_admission_check':True,
                  'checkpoint_step_when_stopped':stopped,
                  'checkpoint_step_after_resume':progress(),
                  'note':'CPU-only Kueue integration. Historical snapshot fail-open; no GPU or energy savings verified.'}
        out=cluster.ROOT/'.local/cluster-acceptance-verified.json'
        out.write_text(json.dumps(evidence,indent=2)+'\n')
        print(json.dumps(evidence,indent=2))
    finally:
        run('-n',NS,'scale','deployment/wattshift-controller',f'--replicas={original_replicas}')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--lite',action='store_true',help='Skip Prometheus, for the reduced RAM stack')
    args=p.parse_args()
    verify(lite=args.lite)
