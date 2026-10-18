"""Create a genuine release only after local tests and fresh cluster evidence.
Requires a configured origin and authenticated GitHub CLI; never guesses an account.
"""
import argparse,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('tag',choices=['v0.1','v0.1.1','v0.2','v0.3','v0.4','v0.5','v0.6','v1.0.0']);a=p.parse_args()
root=Path(__file__).resolve().parents[1]
proof=root/'.local/cluster-acceptance-verified.json'
if not proof.exists():sys.exit('No real cluster acceptance evidence: stable release refused.')
e=json.loads(proof.read_text());age=(datetime.now(timezone.utc)-datetime.fromisoformat(e['verified_at'])).total_seconds()
if not 0<=age<86400:sys.exit('Cluster acceptance evidence must be from the past 24 hours.')
if e.get('commit')!=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip():sys.exit('Evidence must match HEAD.')
subprocess.run([sys.executable,'-m','pytest','-q'],cwd=root,check=True)
if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():sys.exit('Commit reviewed source before release.')
subprocess.run(['git','remote','get-url','origin'],cwd=root,check=True)
subprocess.run(['git','tag','-a',a.tag,'-m',f'WattShift {a.tag}: verified release'],cwd=root,check=True)
subprocess.run(['git','push','origin',a.tag],cwd=root,check=True)
subprocess.run(['gh','release','create',a.tag,'--title',f'WattShift {a.tag}','--notes-file','docs/RELEASE_NOTES.md'],cwd=root,check=True)
