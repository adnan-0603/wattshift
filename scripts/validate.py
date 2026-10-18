"""Offline source/data gate; never presents YAML parsing as cluster validation."""
import json, pathlib, yaml, math
root=pathlib.Path(__file__).resolve().parents[1]
objects=[]
for p in (root/'infra/kubernetes').glob('*.yaml'):
 for obj in yaml.safe_load_all(p.read_text()):
  if obj:
   assert {'apiVersion','kind','metadata'}<=obj.keys(),p
   objects.append(obj)
s=json.loads((root/'apps/console/public/data/console.json').read_text())
assert s['schema_version']==1 and len(s['prices'])>=8784
assert len(s['forecast'])==168
for r in s['forecast']:
 if r['p10'] is not None:assert r['p10']<=r['p50']<=r['p90']
for job in s['simulation']['jobs']:
 for policy in job['policies'].values():
  if policy:assert job['release_slot']<=policy['start_slot']<policy['end_slot']<=job['deadline_slot']
assert s['simulation']['totals']['cheapest']['jobs']==48
for p in (root/'.github/workflows').glob('*.yml'):assert isinstance(yaml.safe_load(p.read_text()),dict)
print(f'Offline validation passed: {len(objects)} Kubernetes objects, {len(s["prices"])} intervals, 168 forecast hours, 48 feasible jobs. No cluster execution implied.')
