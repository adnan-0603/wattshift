"""Optional explicitly invoked power-cap experiment; restores original limit."""
import argparse,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--gpu',type=int,default=0);p.add_argument('--cap-watts',type=int,required=True);p.add_argument('--seconds',type=int,default=60);a=p.parse_args()
if a.cap_watts<=0 or a.seconds<2:p.error('Invalid cap/duration')
# User starts the same representative GPU workload separately for both windows.
original=float(subprocess.check_output(['nvidia-smi','-i',str(a.gpu),'--query-gpu=power.limit','--format=csv,noheader,nounits'],text=True).strip())
subprocess.run([sys.executable,'-m','wattshift.gpu','--seconds',str(a.seconds),'--output','reports/gpu-baseline.csv'],check=True)
try:
 subprocess.run(['nvidia-smi','-i',str(a.gpu),'-pl',str(a.cap_watts)],check=True)
 subprocess.run([sys.executable,'-m','wattshift.gpu','--seconds',str(a.seconds),'--output','reports/gpu-capped.csv'],check=True)
finally:subprocess.run(['nvidia-smi','-i',str(a.gpu),'-pl',str(original)],check=True)
print('Compare energy AND completed work/throughput; a lower watt value alone is not an efficiency result.')
