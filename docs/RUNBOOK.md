# Running WattShift

## Local Console and API

Use Python 3.12 and Node 24. For notebooks and asset regeneration, also install `requirements-dev.txt`; the video generator needs ffmpeg. Create `.venv`, install `requirements.lock.txt` plus pytest, then `make export`. This executes the model/replay and creates the API snapshot. The public Console already contains a saved source snapshot.

`npm --prefix apps/console ci` then `npm --prefix apps/console run dev` starts public mode. `make api` serves FastAPI on localhost:8000; `VITE_MODE=cluster npm --prefix apps/console run dev` uses Vite's `/api` proxy. Public mode never reports live job execution. API docs: `/docs`; readiness: `/ready`; data: `/forecast`, `/prices`, `/savings`, `/jobs`; metrics: `/metrics`; retrospective calculator: `POST /plan`.

`make refresh` fetches recent prices and generation, recalculates forecasts and replaces the snapshot atomically. Upstream failure should fail the run rather than manufacture data. Check source retrieval time and missing carbon before presenting a result. At 13:20 Europe/Berlin the cluster CronJob refreshes; the daily GitHub Action runs at 14:25 UTC. Publication and data availability can lag; tomorrow is only solid when actually retrieved.

## Full local cluster

Prerequisites: Docker daemon, kind 0.31.0, kubectl compatible with Kubernetes 1.35, Git, Python dependencies, sufficient memory (suggest 8 GiB free) and internet access for images/manifests. `make doctor` reports unavailable dependencies. `make up` creates the isolated wattshift cluster, builds/loads both images, installs Kueue, generates a Grafana Secret, applies resources and waits for rollouts. Re-running is intended to be idempotent. Node image, Kueue and application images are pinned in source.

Kubeconfig: `.local/kubeconfig`; context: `kind-wattshift`. Never substitute the production kubeconfig. Console ingress is localhost:8080. `make stack-verify` checks deployments. `make demo-jobs` submits the CPU checkpoint example. For an isolated fresh cluster, `python scripts/cluster_acceptance.py --lite` (or omit `--lite` with the full stack) stops the policy controller **before creating a new job**, checks that the Kueue AdmissionCheck stays Pending and no Pod starts, restores the controller, verifies check release and then tests CPU checkpoint pause/resume. The acceptance script restores the controller replica count in `finally`. It fails if the demo Job already exists, rather than deleting it.

`make grafana` forwards localhost:3000. Username: admin. Retrieve the locally generated password from the `grafana-admin` Secret only when signing in; do not commit it. Dashboard provisioning is in `observability/grafana-dashboard.json`. Power and savings panels are explicitly assumed/simulated. Capture an actual dashboard screenshot only after targets are up. No fabricated screenshot is included.

The **default** policy for new annotated managed jobs is now forecast-based, hour-aligned, non-preemptive admission (eligible windows are selected using published prices if available, else issued P50). A legacy policy may explicitly opt in with `wattshift.dev/policy: price-threshold`; only that option uses 80/85 €/MWh hysteresis. A job needs a valid `wattshift.dev/deadline` and `wattshift.dev/estimated-seconds` for forecast admission; missing, stale, broken signals or absent deadline fail open, and deadline urgency overrides prices. Selected planned starts are retained across the polling interval. **First-admission guard:** ClusterQueue requires `wattshift-forecast` AdmissionCheck, initially Pending. The controller writes `Ready` to its Workload status check only when eligible; Kueue remains responsible for Job suspension. The old polling race is addressed in source, but real kind/Kueue acceptance remains required to verify actual runtime. Missing/stale forecasts intentionally fail open for forward progress (not for savings).

Bundled data becomes stale. Only this *local demo* has `WATTSHIFT_ALLOW_STALE_DEMO=1`, so `/ready` may say `stale-demo-ready` with `live_data_ready:false`. The controller still refuses stale signals. In strict live mode, readiness returns HTTP 503 until data/forecast/coverage are refreshed. See [rc2 audit](reviews/rc2-source-audit.md). Missing or stale signals fail open. A suspended Kubernetes Job loses its running Pod; checkpoint-enabled code is required. The demo is CPU hashing, not an LLM training performance benchmark. PVC data belongs to this kind cluster; `make down` destroys that local cluster and its data. Export anything valuable first.

## GitHub Pages and releases

No origin is configured. Choose the intended repository explicitly; the connected account differed from the portfolio handle in the design. Do not infer ownership from a portfolio name. Enable Pages with GitHub Actions and allow the daily workflow to write its branch. Protected-branch policies may require changing the refresh workflow to a PR workflow. The Pages job and the daily job both deploy directly: pushes made with GITHUB_TOKEN do not trigger another workflow automatically.

`ci.yml`: backend tests, source validation, Console tests/build and Docker builds. `cluster.yml`: manually dispatched actual kind acceptance. `pages.yml`: static site deployment. `daily.yml`: source refresh, badge, commit and Pages deployment. None has run remotely yet.

Do not retroactively invent v0.1–v1.0 release events. `scripts/release.py TAG` checks clean Git state, fresh real cluster evidence matching HEAD, tests and an explicitly configured origin before creating/pushing a tag and GitHub release. Review release notes for the actual phase first. This package is a local release candidate.

## বাংলায় শুরু

প্রথমে README-এর Quickstart অনুসরণ করলে Console দেখা যাবে। `docs/METHOD.md` থেকে data ও হিসাব বুঝুন; `notebooks/01-understand-energy.ipynb`-এ ছোট উদাহরণ আছে। `docs/reviews/final-review.md`-তে কোনটি পরীক্ষা হয়েছে এবং কোনটির জন্য বাস্তব cluster/GPU প্রয়োজন, আলাদা করে দেওয়া আছে। পুরোনো মাস্টার্সের কাজ `legacy/`-তে অক্ষত আছে।

### 8 GB Mac / no GPU deployment

`make stack-lite` deploys API, Console, admission controller, ingress and Kueue without Grafana or Prometheus. It still needs Docker Desktop/kind and may exceed memory available to Docker; no success or fixed RAM bound is guaranteed. Run `python scripts/cluster_acceptance.py --lite` on a *fresh isolated* cluster after the gate becomes Active. Check via `kubectl --kubeconfig .local/kubeconfig --context kind-wattshift get admissionchecks,clusterqueues` and `kubectl ... -n wattshift get workloads -o yaml`. Do not treat standalone Kaggle GPU sessions as a Kubernetes node.
