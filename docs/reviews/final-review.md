# Final candidate review

This review records the delivered source and **local evidence**, not a production deployment. Reviewed 18 October 2026. The requested end-to-end Phase 0–8 runtime story is **not fully complete**: this environment has no Docker/kind/kubectl or NVIDIA GPU, and no intended GitHub origin was configured. The supplied package contains the implementation and reproducible paths for those gates.

## Executed successfully

| Check | Result | Evidence |
|---|---|---|
| Python backend/lifecycle tests | 25 passed | `evidence/backend-test.log` |
| TypeScript calculator tests | 5 passed | `evidence/planner-test.log` |
| Console page navigation and calculator interaction | 1 passed | `evidence/console-test.log`; jsdom, charts mocked |
| TypeScript and Vite production build | Passed | `evidence/frontend-build.log`; prebuilt `preview/` in ZIP |
| Offline manifest/data validation | 29 objects, 16,264 intervals, 168 forecast hours, 48 feasible jobs | `evidence/validation.log` |
| Original archive integrity | SHA-256 matched | `evidence/source-review.log` |
| Actual local CPU interruption/resume | step10 → termination exit75 → step100; final digest identical to uninterrupted execution | `checkpoint-evidence.json` |
| Notebook code | 3 code cells executed in-process with IPython | Notebook metadata/outputs; `scripts/check_notebook.py` |
| Video | Approximately 120 seconds (119.93 s) | `docs/assets/evidence-walkthrough.mp4` |
| Real source retrieval and model replay | Completed; bundled provenance and numerical results | `data/*/provenance.json`, `results.json` |

The kernel-based notebook attempt failed because networking sockets were unavailable. Code cells were then executed in-process successfully; no live notebook-server claim is made. FastAPI tests passed with one upstream httpx deprecation warning. UI tests verify behavior, **not visual layout or actual ECharts rendering**. Browser visual QA was not available in this managed environment. Scientific PNGs were inspected independently; no mock Grafana screenshot is supplied.

## Results and interpretation

2024 archive: 8,784 native hourly UTC observations, including 457 negative observations in this UTC-year slice. Current observations retain quarter-hour resolution. Carbon is available for selected weeks/current intervals only. The date boundaries are UTC; a Berlin-calendar-year count can differ.

Held-out period: 25–31 December 2024 UTC; 48 generated jobs, seed42. Immediate €27.868770; cheapest forecast €25.699645; greenest lag proxy €26.559296. Cheapest saved €2.169125 / 7.783353%. Its carbon estimate fell by 0.222627 kgCO₂e; the greenest proxy **increased** carbon by 0.324635 kgCO₂e. Hindsight oracle €25.258060; forecast regret €0.441586. Forecast MAE 27.069907 €/MWh versus baseline 58.448214. Quantile coverage 80.357143% across 168 hours. These are simulated energy costs, not billed GPU charges or measured emissions.

## Requirements coverage and remaining work

| Register IDs | Implementation/evidence | Remaining acceptance |
|---|---|---|
| S01–S03 | Structure, Makefile, isolated cluster launcher, local history and release guard | Actual setup and GitHub milestone releases |
| D01–D04 | Real SMARD observations, factors, notebook, price/carbon and annual chart | ENTSO-E cross-validation not integrated; full-year carbon not supplied |
| I01–I03 | Client, SQLite upsert, Dockerfile, CronJob, PVC/settings/Secret | Docker build, persistence after cluster restart and scheduled execution |
| F01–F04 | Leakage test, chronological model/baseline, quantiles, API, regret, Console | Cluster serving, broader rolling-origin validation; carbon baseline uncalibrated |
| O01–O02 | Actual API metrics test, Prometheus config, Grafana six-panel JSON | Real scrape/PromQL and genuine dashboard screenshot |
| M01–M04 | Reproducible policies/trace, deadlines, constant power, results/chart | Capacity and checkpoint overhead remain explicit model omissions |
| C01–C04 | Workload.active policy source, CPU worker, checkpoint equality, cluster acceptance script | Real Kueue eviction/readmission and deadline behavior |
| U01–U03, U05–U12 | Five pages, same adapters, controls, price/carbon/quantile charts, static build | Browser visual/mobile QA, public/cluster runtime parity. Cumulative charts include EUR and estimated carbon on separate axes |
| U04 | Simulation timeline overlays actual price; cluster mode displays controller state | Live Gantt/event history, always-on inference deployment and paused-batch history are not implemented as live demonstrations |
| P01–P05 | Real GIF, snapshot badge/workflow, three-act README, diagrams and attribution | Deployed daily action/Pages and real one-command full stack |
| P06 | 2-minute local evidence walkthrough | Requested actual Console/Kueue/Grafana interaction recording remains pending |
| P07 | Three carousel images, CV sentence, pitch, embed snippet | No portfolio/LinkedIn publishing performed |
| G01 | nvidia-smi integration, optional DCGM manifest, power-cap script | Actual GPU measurements and matched-work cap comparison |

## Review fixes

- Reused Intl date formatters: eliminated repeated expensive formatter construction across the archive.
- Renamed deployment helper to `deploy.py` to avoid shadowing Python's standard `platform` module.
- Kept missing carbon as N/A and added a separately labelled prior-14-day carbon profile overlay.
- Required complete contiguous source coverage before labeling an hourly future price published.
- Changed winter calculator example to a period with real bundled generation coverage.
- Ensured Docker's seed comes from a committed public snapshot, allowing clean-checkout builds.
- Kueue owns Job suspension; the controller patches only Workload.active with resourceVersion.
- Stable release guard requires fresh real cluster evidence matching HEAD; no artificial historical tags.

## Reproduction and handoff

README and `docs/RUNBOOK.md` contain exact commands. `make up` is ready for a Docker-capable host but not certified here. `scripts/cluster_acceptance.py` checks actual API, Prometheus and stop/resume behavior. `docs/GPU.md` covers actual measurement. No new permission request is needed for ordinary local verification; paid GPU rental and an unidentified external repository were not assumed.

The original master's material remains unchanged in `legacy/`. The package excludes disposable caches, dependency directories, runtime databases, secrets and generated environment files. A Git bundle preserves the actual local development history without fabricating releases.
