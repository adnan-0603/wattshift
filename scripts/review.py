"""Dependency-free source review; deliberately does not assert runtime completion."""
from pathlib import Path
import ast
import hashlib
import json

root=Path(__file__).resolve().parents[1]
required=['README.md','Makefile','docs/ROADMAP.md','docs/PHASE_0.md','docs/REQUIREMENTS.md',
          'infra/kind/cluster.yaml','infra/kubernetes/base/namespace.yaml','scripts/cluster.py']
for name in required:
    if not (root/name).is_file():raise SystemExit('Missing required file: '+name)
for path in list((root/'scripts').glob('*.py'))+list((root/'tests').glob('*.py')):
    ast.parse(path.read_text())
archive=root/'legacy/wattshift-prototype.zip'
expected=(root/'legacy/SHA256SUMS').read_text().split()[0]
if archive.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()!=expected:raise SystemExit('Legacy archive changed')
print(json.dumps({'source_review':'passed','legacy_archive':'hash_verified' if archive.exists() else 'not included in source-only checkout',
                  'cluster_runtime':'separate make verify required','release_tag':'not created'},indent=2))
