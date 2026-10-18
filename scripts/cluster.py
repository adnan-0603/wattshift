#!/usr/bin/env python3
"""Explicit-context local kind lifecycle; no commands are run on import."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
NAME = 'wattshift'
CONTEXT = 'kind-wattshift'
KUBECONFIG = ROOT / '.local/kubeconfig'
CONFIG = ROOT / 'infra/kind/cluster.yaml'
NAMESPACE = ROOT / 'infra/kubernetes/base/namespace.yaml'
EVIDENCE = ROOT / '.local/phase0-verification.json'


def command(args, capture=False):
    result = subprocess.run(args, check=True, text=True, capture_output=capture,
                            env={**os.environ, 'KIND_EXPERIMENTAL_PROVIDER': 'docker'})
    return result.stdout.strip() if capture else ''


def kubectl(*args):
    return ['kubectl', '--kubeconfig', str(KUBECONFIG), '--context', CONTEXT, *args]


def doctor():
    missing = [name for name in ('docker','kind','kubectl','git') if shutil.which(name) is None]
    if missing:
        raise RuntimeError('Missing tools: '+', '.join(missing)+'. See docs/PHASE_0.md.')
    command(['docker','info'],capture=True)
    info = json.loads(command(['docker','info','--format','{{json .}}'],capture=True))
    if info.get('OSType') != 'linux':
        raise RuntimeError('Docker must be running Linux containers')
    print('Docker daemon reachable; Linux containers enabled.')
    print(command(['kind','version'],capture=True))
    print(command(['kubectl','version','--client','-o','json'],capture=True))
    print('Pinned reference: kind v0.31.0 with Kubernetes v1.35.0; newer kind versions require live verification.')
    if info.get('MemTotal',0) < 4*1024**3:
        print('NOTE: Docker has less than 4 GiB RAM. Later observability/model components may need more.')


def up():
    doctor()
    clusters = command(['kind','get','clusters'],capture=True).splitlines()
    KUBECONFIG.parent.mkdir(parents=True,exist_ok=True)
    if NAME not in clusters:
        command(['kind','create','cluster','--name',NAME,'--config',str(CONFIG),
                 '--kubeconfig',str(KUBECONFIG),'--wait','180s'])
    else:
        print('Existing wattshift cluster found; verifying it without recreation.')
        command(['kind','export','kubeconfig','--name',NAME,'--kubeconfig',str(KUBECONFIG)])
    KUBECONFIG.chmod(0o600)
    command(kubectl('apply','-f',str(NAMESPACE)))
    verify()


def verify():
    EVIDENCE.unlink(missing_ok=True)
    if not KUBECONFIG.exists():
        raise RuntimeError('Project kubeconfig missing; run make up first.')
    command(kubectl('wait','--for=condition=Ready','nodes','--all','--timeout=180s'))
    command(kubectl('-n','kube-system','rollout','status','deployment/coredns','--timeout=180s'))
    nodes = json.loads(command(kubectl('get','nodes','-o','json'),capture=True))
    if not nodes.get('items'):
        raise RuntimeError('No nodes found')
    expected_nodes = set(command(['kind','get','nodes','--name',NAME],capture=True).splitlines())
    if not expected_nodes or {node['metadata']['name'] for node in nodes['items']} != expected_nodes:
        raise RuntimeError('Unexpected cluster identity; refusing successful verification')
    for node in nodes['items']:
        version = node['status']['nodeInfo']['kubeletVersion']
        if version != 'v1.35.0':
            raise RuntimeError('Existing cluster version '+version+' does not match pinned v1.35.0')
    namespace = json.loads(command(kubectl('get','namespace',NAME,'-o','json'),capture=True))
    if namespace.get('status',{}).get('phase') != 'Active':
        raise RuntimeError('WattShift namespace is not Active')
    evidence = {'phase':0,'status':'runtime_verified','verified_at':datetime.now(timezone.utc).isoformat(),
                'cluster':NAME,'context':CONTEXT,'kubernetes_version':'v1.35.0',
                'checks':['nodes Ready','CoreDNS rollout complete','namespace Active'],
                'note':'No GitHub release was created by this check.'}
    EVIDENCE.write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence,indent=2))


def status():
    command(kubectl('get','nodes','-o','wide'))
    command(kubectl('get','pods','-A'))


def down():
    # Explicit invocation only. Does not use/delete the user's current context.
    command(['kind','delete','cluster','--name',NAME,'--kubeconfig',str(KUBECONFIG)])
    EVIDENCE.unlink(missing_ok=True)
    KUBECONFIG.unlink(missing_ok=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['doctor','up','verify','status','down'])
    args=p.parse_args()
    try:
        {'doctor':doctor,'up':up,'verify':verify,'status':status,'down':down}[args.action]()
    except (RuntimeError,subprocess.CalledProcessError,OSError,ValueError,KeyError) as exc:
        print('WattShift setup failed: '+str(exc),file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
