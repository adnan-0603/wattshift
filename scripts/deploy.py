#!/usr/bin/env python3
"""Full local deployment orchestrator. Requires an actual Docker-capable machine."""
import argparse,base64,json,secrets,subprocess,sys,time
from pathlib import Path
import cluster
ROOT=Path(__file__).resolve().parents[1]

def run(args,input=None):subprocess.run(args,input=input,text=True,check=True,cwd=ROOT)
def up(lite=False):
    cluster.up()
    run(['docker','build','-t','wattshift/backend:1.0.0-rc4','.'])
    run(['docker','build','-t','wattshift/console:1.0.0-rc4','apps/console'])
    run(['kind','load','docker-image','wattshift/backend:1.0.0-rc4','wattshift/console:1.0.0-rc4','--name','wattshift'])
    run(cluster.kubectl('apply','--server-side','-f','https://github.com/kubernetes-sigs/kueue/releases/download/v0.20.1/manifests.yaml'))
    run(cluster.kubectl('-n','kueue-system','rollout','status','deployment/kueue-controller-manager','--timeout=240s'))
    # Create once; never print or place credentials in Git.
    result=subprocess.run(cluster.kubectl('-n','wattshift','get','secret','grafana-admin'),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if result.returncode:
        secret={'apiVersion':'v1','kind':'Secret','metadata':{'name':'grafana-admin','namespace':'wattshift'},'type':'Opaque','data':{'password':base64.b64encode(secrets.token_urlsafe(24).encode()).decode()}}
        run(cluster.kubectl('apply','-f','-'),json.dumps(secret))
    files=['queues.yaml','platform.yaml'] + ([] if lite else ['observability.yaml'])
    for file in files:
        run(cluster.kubectl('apply','-f',str(ROOT/'infra/kubernetes'/file)))
    verify(lite=lite)
    print('Console: http://localhost:8080' + ('' if lite else ' ; Grafana: make grafana (localhost:3000)'))


def gate_active():
    """Confirm the Kueue admission gate exists and the controller activated it."""
    check=json.loads(subprocess.check_output(cluster.kubectl('get','admissioncheck',
              'wattshift-forecast','-o','json'),text=True))
    clusterqueue=json.loads(subprocess.check_output(cluster.kubectl('get','clusterqueue',
              'wattshift-cpu','-o','json'),text=True))
    if check.get('spec',{}).get('controllerName') != 'wattshift.dev/forecast-admission':
        return False
    if 'wattshift-forecast' not in clusterqueue.get('spec',{}).get('admissionChecks',[]):
        return False
    if not any(c.get('type')=='Active' and c.get('status')=='True' for c in check.get('status',{}).get('conditions',[])):
        return False
    return any(c.get('type')=='Active' and c.get('status')=='True' for c in clusterqueue.get('status',{}).get('conditions',[]))


def verify(lite=False):
    cluster.verify()
    deployments=['wattshift-api','wattshift-console','wattshift-controller','wattshift-ingress']
    if not lite: deployments+=['wattshift-prometheus','wattshift-grafana']
    for name in deployments:
        run(cluster.kubectl('-n','wattshift','rollout','status','deployment/'+name,'--timeout=240s'))
    deadline=time.monotonic()+120
    while time.monotonic()<deadline and not gate_active():
        time.sleep(3)
    if not gate_active():
        raise RuntimeError('Kueue AdmissionCheck/ClusterQueue not Active; unsafe admission state')
    run(cluster.kubectl('-n','wattshift','get','cronjobs,pvc,localqueues'))
    (ROOT/'.local/full-stack-verified.json').write_text(json.dumps({'status':'rollouts and admission gate verified',
         'profile':'lite' if lite else 'full',
         'note':'Actual job/admission/checkpoint behavior requires cluster_acceptance.py and has not been implied by a rollout.'}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['up','verify','lite','verify-lite']);a=p.parse_args()
    try:{'up':lambda:up(False),'verify':lambda:verify(False),'lite':lambda:up(True),'verify-lite':lambda:verify(True)}[a.action]()
    except (subprocess.CalledProcessError,RuntimeError,OSError) as e:sys.exit('Platform operation failed: '+str(e))
