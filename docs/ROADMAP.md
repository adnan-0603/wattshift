# WattShift — agreed delivery sequence

Each phase: implement → automated checks → actual runtime/data review → record findings and fixes → release. A source scaffold, mocked test or screenshot is not proof of live operation. No phase is marked complete while its required runtime check is blocked. No invented perfect-result guarantee.

| Phase | Release after gate | Work | Acceptance evidence |
|---|---|---|---|
| 0 Setup | v0.1 | Repo, Makefile, kind, README skeleton | `make up` succeeds; nodes Ready; CoreDNS ready; namespace Active; repeated setup safe; GitHub repo/commit verified |
| 1 Understand data | v0.1.1 | SMARD prices and generation mix, estimated intensity, notebook | Source/provenance, units, publication times, timezone/DST, native interval checks; price and carbon charts |
| 2 Ingest | v0.2 | Python client, Docker, CronJob, PVC initially; ConfigMap and Secrets if needed | Real ingestion to durable storage; retry/idempotency/restart tests; Today page with price; scheduled run evidence |
| 3 Forecast | v0.3 | Baseline + LightGBM quantile D+2–D+7; FastAPI; probes/Service/Deployment | Time-based evaluation, P10/P50/P90 and coverage, baseline comparison, regret evaluation hooks; `/forecast` response; Forecast page + carbon overlay |
| 4 Observe | v0.4 | Prometheus metrics and Grafana | Gauge/counter semantics; scraped metrics, tested PromQL, live dashboard screenshot; freshness/error metrics |
| 5 Simulate | v0.5 | Job traces; immediate/cheapest/greenest policies; GPU power model | Same workload suite, no future leakage, deadlines/slack/capacity assumptions, cost/carbon comparisons and honest headline; Savings page |
| 6 Control | v0.6 | Kueue + CPU-emulated GPU jobs; checkpoint-aware controller | High-price stop, low-price restart FROM checkpoint, final result equivalence, idempotency, no missed work; live Jobs page and capacity/deadline handling |
| 7 Showcase | v1.0 | Calculator, public demo, daily workflow, hero GIF, README, video | Production build; public/cluster modes verified; real-data assets and freshness; 2-minute video; attribution and reproducible results |
| 8 Optional GPU | later optional tag | Rented/available GPU; DCGM/nvidia-smi; power cap comparison | Hardware/provider permissions and cost agreed before paid use; measured watts and accuracy vs assumptions; no invented GPU telemetry |

Phase 1 gets v0.1.1 because the supplied table did not assign it a tag; all other specified release numbers are preserved. Tags are immutable milestones, not created in advance. GitHub releases and public Pages publication require the correct repository/account, not merely an accessible account.

## UI delivery

- v0.2: Today, price only.
- v0.3: Forecast, P10–P90 and documented carbon estimates.
- v0.4: Grafana for operators.
- v0.5: Savings comparisons.
- v0.6: live Jobs timeline.
- v1.0: Calculator, public static demo, hero, mobile/accessibility polish.

## Current delivery status

The source implementation now spans Phases 0–8. The original phase-by-phase runtime release sequence could not be completed in this execution environment. Local implementation and reproducible checks proceeded under the user's subsequent instruction to deliver the whole project together. No blocked runtime milestone is represented as passed.

| Phase | Delivered | Verified here | Remaining gate |
|---|---|---|---|
| 0 | Repo, Makefile, isolated kind configuration | lifecycle unit tests | Actual cluster setup |
| 1 | Real prices, selected generation, carbon method, notebook, charts | 8,784 hourly 2024 prices; source provenance | Broad carbon coverage and vintage archives |
| 2 | Client, SQLite, Dockerfile, CronJob/PVC | Real source retrieval and idempotency tests | Docker build and scheduled cluster run |
| 3 | Baseline/LightGBM quantiles, API, Forecast Console | Chronological holdout and API tests | In-cluster serving and broader calibration |
| 4 | Prometheus metrics and Grafana provisioning | API metrics and YAML source checks | Live scrape, PromQL and genuine screenshot |
| 5 | 48-job replay and Savings Console | Reproduced 7.78% cost result | Capacity-aware/rolling-origin extension |
| 6 | Kueue controller, CPU worker, live-state adapter | Actual local checkpoint interruption/resume equality | Real Kueue acceptance and live Jobs demo |
| 7 | Five Console pages, GIF, README, badge, workflows, carousel, evidence video | Planner/DOM tests and production build | Browser visual QA, public deploy, full live demo and GitHub tags |
| 8 | nvidia-smi sampling, DCGM manifest, cap experiment | Source review only | Available GPU and measured same-work comparison |

See `reviews/final-review.md` for final evidence. The candidate is not a claim that every phase's live gate passed.
