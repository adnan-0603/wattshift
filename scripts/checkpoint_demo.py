"""Record real local CPU process stop/resume evidence, not a K8s claim."""
import json,signal,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[1];folder=root/'.local/checkpoint-demo';folder.mkdir(parents=True,exist_ok=True)
for p in folder.glob('*.json'):p.unlink()
checkpoint=folder/'resumed.json';baseline=folder/'baseline.json'
cmd=[sys.executable,'-m','wattshift.worker','--checkpoint',str(checkpoint),'--steps','100','--delay','.02']
p=subprocess.Popen(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
limit=time.monotonic()+15
while (not checkpoint.exists() or json.loads(checkpoint.read_text())['step']<10) and time.monotonic()<limit:time.sleep(.02)
if not checkpoint.exists():p.kill();raise RuntimeError('Worker did not checkpoint')
p.send_signal(signal.SIGTERM);p.communicate(timeout=10)
saved=json.loads(checkpoint.read_text())
subprocess.run(cmd,cwd=root,check=True,capture_output=True)
subprocess.run([sys.executable,'-m','wattshift.worker','--checkpoint',str(baseline),'--steps','100','--delay','0'],cwd=root,check=True,capture_output=True)
a=json.loads(checkpoint.read_text());b=json.loads(baseline.read_text());assert a==b
result={'execution':'real local CPU processes','stop_exit_code':p.returncode,'checkpoint_step_at_stop':saved['step'],'final_step':a['step'],'resumed_matches_uninterrupted':True,'final_digest':a['digest'],'kubernetes_execution':False}
(root/'docs/reviews/checkpoint-evidence.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
