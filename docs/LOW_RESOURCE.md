# Zero-cost / 8 GB Apple M1 testing plan

**Hardware:** Apple Silicon M1, 8 GB physical RAM, no local CUDA GPU. **Budget: €0**. No credit card, paid VM, managed Kubernetes/GPU or paid GPU time is required for offline development.

1. Close unneeded apps. First run Python in a venv: `python -m pytest -q`, `python scripts/validate.py`, `python -m wattshift.export --out /tmp/wattshift-rc4-export`. This uses CPU and no Kubernetes.
2. Run the frontend **separately** from forecasting where possible. Dependency install `npm ci` needs network access to npm but not payment. Run `npm test`, `npm run test:ui`, `npm run build` before shipping.
3. If Docker Desktop is already available, try `make stack-lite` (API, Console, Kueue/AdmissionCheck controller, ingress; no monitoring). Do *not* promise even this reduced kind stack will fit in 8 GB total Mac memory. It needs a live smoke test on your machine and Docker memory must not starve macOS. Full `make up` runs monitoring too; avoid it first.
4. Default `WATTSHIFT_ALLOW_STALE_DEMO=1` in the **local kind API manifest only** permits viewing bundled data. `/ready` reports `stale-demo-ready` and `live_data_ready:false`; never represent stale data as live. Controller refuses stale forecasts and fails open.
5. Free Kaggle GPU (when user quota exists) can validate PyTorch/T4 training/checkpoint/resume in an *independent notebook*. It is **not** automatically a kind/Kueue GPU worker. GPU VRAM is not added to your Mac's host RAM. Save notebook artifacts before the session ends; keep any billing/paid accelerator disabled.
6. To demonstrate cost savings, always label them retrospective **estimated electricity energy-component only**. Never label them GPU rental savings or real-time savings before measured verification.

See [RC3 audit](reviews/rc3-admission-audit.md). A lightweight workflow is more honest and more usable than claiming untested all-in-one local deployment.

**Archive note:** The reviewed source uses system UI fonts in rc2; standalone binary font files from the uploaded rc1 archive are intentionally not redistributed. The rc1 files stay in the user’s original untouched archive.
