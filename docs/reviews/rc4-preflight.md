# WattShift v1.0.0rc4 — Independent preflight review (18 October 2026)

## Summary (বাংলা)

মূল rc3 ZIP অপরিবর্তিত রেখে নতুন source copy-তে অতিরিক্ত bug এবং CI সমস্যা সংশোধন করা হয়েছে। এখানে কোনো বাস্তব Kubernetes/GPU deployment করা হয়নি। তাই এটি **offline-tested preflight candidate**, production বা stable release নয়।

### Corrected defects

1. **Cached scheduled start vs changed deadline** — previously a remembered future start could be reused even if a revised deadline no longer allowed the job to finish. Revalidation added before reuse.
2. **Workload name reuse** — persisted plans are now keyed by `Job name + Workload UID`, preventing old plans from being applied to newly created Workloads with the same name.
3. **Stale owner Job UID** — the controller avoids approving a Workload that refers to an earlier Job with a reused name, when both UIDs are available.
4. **Cluster CI broken bootstrap** — `.github/workflows/cluster.yml` previously used `make up` (a bare kind cluster) before live acceptance. It now uses `make stack-lite` and `cluster_acceptance.py --lite`.
5. **Release proof mismatch** — successful live acceptance now includes a real Git commit SHA when tested in a git repository; stable tagging still requires the release script's safety gates.
6. **SQLite resource warnings** — file handles are explicitly closed after transactions.
7. **Version drift** — rc4 runtime image references and package versions aligned.

### Observed offline test outcomes

| Gate | Observed result |
|---|---|
| Original rc3 ZIP integrity | PASS (zip CRC and no unsafe entry paths) |
| Python regression suite after fixes | 55/55 PASS, including new regression tests |
| Warnings-as-errors on ResourceWarning | PASS |
| TypeScript Node planner unit tests | 5/5 PASS |
| `scripts/validate.py` offline data/manifests | PASS (32 YAML objects, 16,264 intervals, 168 hours, 48 jobs) |
| `scripts/review.py` | PASS, legacy prototype hash verified |
| Real CPU checkpoint stop → resume vs baseline | PASS (state/digest exact match, not Kubernetes) |
| Fresh offline export & FastAPI endpoint checks | PASS; local historical/live snapshot + plan calculator |
| Fresh Vite build & React browser tests | NOT RUN: node modules unavailable; npm offline cache lacks dependencies |
| Docker images, kind & Kubernetes Kueue admission | NOT RUN: docker/kind/kubectl unavailable |
| Real GPU run / measured energy | NOT RUN: no GPU in review environment |

### Known constraints and release blockers

- Kueue quota is reserved before AdmissionChecks complete, so deferring many jobs can hold quota unnecessarily. This is a known design constraint; alternative requeue strategy is future work.
- `AdmissionCheck` semantics checked against official Kueue documentation, but there is no live API/CRD integration proof in this runtime.
- Fresh React/Vite dependency install, browser tests, and Docker builds remain to be performed with network access on a compatible machine or free CI runner.
- CPU-only acceptance on a fresh isolated kind cluster is required to verify Pending → Ready → Admitted, Pod stop/checkpoint/resume and controller recovery.
- Laptop has 8 GiB RAM, no local NVIDIA GPU, and user does not want to pay. Try `make doctor` first, then lite stack only if free memory allows; do not run all services by default.
- Historical `7.78%` is a retrospective simulated electricity-energy saving, not measured GPU cost, cloud rental cost or realized carbon avoidance.
- Absence of unverified severe bugs is **not** proof of zero defects. Test coverage is limited; full branch/capacity/security auditing remains appropriate before stable release.

### After unzipping: offline-first commands

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt pytest
python -m pytest -q
python scripts/validate.py
python scripts/checkpoint_demo.py
```

Only after these pass, and if Docker/kind/kubectl are available, run `make doctor`, then `make stack-lite` and `python scripts/cluster_acceptance.py --lite` on the isolated WattShift cluster. **Do not** run `make down` before saving checkpoints: it deletes the named local kind cluster and its data.

Official Kueue AdmissionCheck documentation: https://kueue.sigs.k8s.io/docs/concepts/admission_check/
