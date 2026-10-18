"""Captioned evidence walkthrough; explicitly not a live cluster recording."""
from pathlib import Path
import json,subprocess
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parents[1];out=root/'docs/assets';work=root/'.local/video';work.mkdir(parents=True,exist_ok=True)
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
e=json.loads((root/'docs/reviews/checkpoint-evidence.json').read_text())
slides=[('WattShift','Same GPUs. Cheaper hours. Cleaner power.',None,['A local evidence walkthrough','Actual source data · simulated scheduling','Not a live Kubernetes or GPU demonstration']),('The signal','Real German market prices and estimated carbon','price-carbon.png',[]),('The platform','Source implementation; cluster acceptance pending','architecture.png',[]),('The result','Same 48 jobs; forecast decisions; held-out actual costs','comparison.png',[]),('Checkpoint / resume','Actual CPU execution evidence',None,[f"Interrupted at step {e['checkpoint_step_at_stop']} · exit {e['stop_exit_code']}",f"Resumed to step {e['final_step']}",'Final digest equals uninterrupted computation','Kubernetes execution: not performed']),('What is established','A reproducible candidate with explicit remaining gates',None,['Five-page Console · tested calculator · API','Real-data ingestion · quantile forecast · 48-job replay','Still required: Docker/kind acceptance and visual QA','Still required: Pages, live demo, Grafana screenshot, GPU'])]
for i,(title,sub,picture,lines) in enumerate(slides):
 im=Image.new('RGB',(1280,720),'#fafbfc');d=ImageDraw.Draw(im);d.rectangle((0,0,12,720),fill='#e8a329');d.text((55,38),title,font=ImageFont.truetype(bold,38),fill='#26384c');d.text((55,99),sub,font=ImageFont.truetype(font,21),fill='#526477')
 if picture:
  art=Image.open(out/picture).convert('RGB');art.thumbnail((1120,535));im.paste(art,((1280-art.width)//2,145))
 else:
  for j,line in enumerate(lines):d.text((65,220+j*70),line,font=ImageFont.truetype(font,25),fill='#26384c')
 d.text((55,686),f'WATTSHIFT / LOCAL EVIDENCE                         {i+1} / 6 · source and limits in README',font=ImageFont.truetype(font,15),fill='#526477');im.save(work/f'{i}.png')
concat=''.join(f"file '{i}.png'\nduration 20\n" for i in range(6))+"file '5.png'\n";(work/'list.txt').write_text(concat)
subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(work/'list.txt'),'-t','120','-r','15','-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p','-movflags','+faststart',str(out/'evidence-walkthrough.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print('Generated 120-second captioned evidence walkthrough (no live cluster claim).')
