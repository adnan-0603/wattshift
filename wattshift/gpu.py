"""Optional real NVIDIA GPU sampling. Never rents hardware or changes power caps."""
import argparse
import csv
import json
from pathlib import Path
import shutil
import subprocess
import time


def sample(seconds,output):
    if not shutil.which('nvidia-smi'):raise RuntimeError('nvidia-smi unavailable: real NVIDIA GPU measurement was NOT performed')
    rows=[];end=time.monotonic()+seconds
    while time.monotonic()<end:
        raw=subprocess.check_output(['nvidia-smi','--query-gpu=timestamp,index,name,power.draw,power.limit,utilization.gpu','--format=csv,noheader,nounits'],text=True)
        for row in csv.reader(raw.splitlines()):
            rows.append([time.time()]+[x.strip() for x in row])
        time.sleep(1)
    path=Path(output);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['epoch_seconds','gpu_timestamp','gpu_index','gpu_name','watts','power_limit_watts','utilization_percent']);w.writerows(rows)
    energies={}
    for index in set(r[2] for r in rows):
        samples=[r for r in rows if r[2]==index]
        values=[]
        for a,b in zip(samples,samples[1:]):
            try:values.append((float(a[4])+float(b[4]))/2*(b[0]-a[0])/3600000)
            except ValueError:pass
        energies[index]=sum(values) if values else None
    result={'measurement':'real nvidia-smi samples','gpu_kwh':energies,'facility_energy_included':False,'output':str(path)}
    path.with_suffix('.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--seconds',type=int,default=60);p.add_argument('--output',default='reports/gpu.csv');a=p.parse_args()
    if a.seconds<2:p.error('at least 2 seconds required')
    try:sample(a.seconds,a.output)
    except RuntimeError as e:p.exit(2,str(e)+'\n')
