"""CPU checkpoint demo. Not an actual GPU training workload."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import time

STOP=False

def stop(*_):
    global STOP
    STOP=True


def run(path,steps=200,delay=.05,seed='wattshift'):
    global STOP
    STOP=False
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    state={'step':0,'digest':hashlib.sha256(seed.encode()).hexdigest(),'seed':seed,'target_steps':steps}
    if path.exists():
        state=json.loads(path.read_text())
        if state.get('seed')!=seed or state.get('target_steps')!=steps:raise ValueError('Checkpoint belongs to another workload')
        if not 0<=state['step']<=steps:raise ValueError('Invalid checkpoint progress')
    while state['step']<steps and not STOP:
        value=hashlib.sha256((state['digest']+str(state['step'])).encode()).hexdigest()
        state={**state,'digest':value,'step':state['step']+1}
        temporary=path.with_suffix('.tmp')
        with temporary.open('w') as f:json.dump(state,f);f.flush();os.fsync(f.fileno())
        temporary.replace(path)
        if delay:time.sleep(delay)
    print(json.dumps({**state,'finished':state['step']==steps}),flush=True)
    return 0 if state['step']==steps else 75

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--checkpoint',default='/checkpoints/job/state.json');p.add_argument('--steps',type=int,default=200);p.add_argument('--delay',type=float,default=.05);p.add_argument('--seed',default='wattshift');a=p.parse_args()
    if a.steps<1 or a.delay<0:p.error('steps must be positive and delay nonnegative')
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    raise SystemExit(run(a.checkpoint,a.steps,a.delay,a.seed))
