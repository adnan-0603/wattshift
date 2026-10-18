# Complete requirements register

This is the acceptance register. Implementation now spans Phases 0–8; use `reviews/final-review.md` and `ROADMAP.md` for delivered versus verified status. A listed requirement is not itself proof of completion.

| ID | Requirement | Phase / verification |
|---|---|---|
| S01 | Repository folders, Makefile, README skeleton | 0; source review |
| S02 | Local kind cluster via one `make up` | 0; real cluster check |
| S03 | Review and release history at each phase | All; review records + actual GitHub tags/releases |
| D01 | Real SMARD price data | 1; source and retrieval evidence |
| D02 | Generation mix and carbon estimate | 1; explicit emission factors, boundaries and assumptions |
| D03 | MW/MWh, day-ahead market, 15-min intervals, gCO2e/kWh | 1; notebook explanations and unit tests |
| D04 | First price and carbon charts | 1; real data with timestamps, source and estimate labels |
| I01 | Python ingest client and Docker image | 2; build/run and deterministic input tests |
| I02 | Kubernetes CronJob and persistent data | 2; retry/idempotency, restart and scheduled-run evidence |
| I03 | PVC or PostgreSQL, ConfigMap, Secret when needed | 2; choose PVC initially; do not add fake credentials |
| F01 | Baseline and LightGBM quantile models | 3; training and chronological validation |
| F02 | D+2 to D+7 forecasts, P10/P50/P90 | 3; leakage checks, quantile ordering, empirical coverage |
| F03 | FastAPI `/forecast`, Deployment/Service/probes | 3; endpoint + in-cluster checks |
| F04 | Regret measurement | 3/5; compare decision cost vs explicitly hindsight oracle |
| O01 | Prometheus gauges/counters and PromQL | 4; scrape and query verification |
| O02 | Grafana price/carbon/power/savings panels | 4 then expand 5/6/8; estimated vs measured distinguished |
| M01 | Job trace generator | 5; fixed seeds and documented arrivals/durations/deadlines |
| M02 | Immediate, cheapest, greenest policies | 5; identical jobs, forecasts known at issue time |
| M03 | Deadlines/slack and GPU energy model | 5; unit and boundary tests |
| M04 | EUR and carbon savings headline/comparison chart | 5; reproducible aggregate, absolute deltas, coverage and missed deadlines |
| C01 | Kueue installation and admission integration | 6; pinned compatible version + real cluster |
| C02 | CPU-emulated GPU job | 6; clearly labelled CPU workload |
| C03 | Price-aware stop/restart controller loop | 6; idempotency, retries, stale-signal policy |
| C04 | Checkpoint/resume correctness | 6; resumed output equals uninterrupted output |
| U01 | WattShift Console distinct from Grafana | 2–7; user workflows vs operational metrics |
| U02 | Today: current price/carbon, best window, today/tomorrow curves | 2/3; timestamp/timezone/freshness; carbon only when available |
| U03 | Forecast: seven days, published solid line and forecast bands | 3; D+1 solid ONLY after publication; missing/unpublished states |
| U04 | Jobs: price-overlay timeline, always-on inference, shifted training, paused batch | 6; actual state and checkpoints in cluster mode |
| U05 | Savings: cumulative EUR/kgCO2e and three policies | 5; distinguish simulated, estimated and measured |
| U06 | Calculator: GPU count, duration, deadline flexibility, season | 7; valid windows and comparable datasets; power/tariff assumptions visible |
| U07 | React + Vite + TypeScript | 2–7; production build |
| U08 | Apache ECharts + Tailwind | 2–7; responsive chart, band and timeline |
| U09 | Solar amber/evening slate, unified font, GPU/sun outline logo | 2/7; contrast and consistent semantics |
| U10 | Public GitHub Pages mode: static JSON, refreshed daily | 7; Today/Forecast/Calculator, no fake live jobs |
| U11 | Cluster mode: live APIs, all five pages | 6/7; nginx Deployment + Ingress |
| U12 | Same frontend code with interchangeable data adapters | 2–7; typed contract and mode parity checks |
| P01 | Real-data Duck & Job hero GIF | 7; feasible job times, labelled market-price curve |
| P02 | Daily GitHub Action and Today badge | 7; Europe/Berlin date, stale state, meaningful commits only |
| P03 | Three-act README: problem/platform/result | 7; chart, architecture and verified number |
| P04 | One-command full stack `make up` | 7; expand setup target after each component passes |
| P05 | How it works, design decisions, limits, MOBI attribution | All/7; preserved team provenance |
| P06 | Two-minute demo video | 7; actual recorded interaction, not a storyboard labelled video |
| P07 | Portfolio embed, LinkedIn 3-slide carousel, CV sentence, 60-second pitch | 7; prepare assets; publishing messages needs separate explicit send authorization |
| G01 | Optional paid GPU, DCGM, nvidia-smi, power-cap comparison | 8; cost/provider authorization, hardware evidence |

## Scientific and engineering constraints

1. Prices alone are not carbon intensity. Generation-weighted intensity is an estimate with explicit emission factors; identify operational versus lifecycle factors, imports/storage treatment, coverage and uncertainty. Ex-post generation mix is not an advance carbon forecast.
2. D+1 prices are only known after the auction/publication. The UI must not show unpublished tomorrow values as facts. Quantile coverage requires validation; P10–P90 is not automatically a calibrated 80% interval.
3. Native market resolution can vary over time. Preserve interval bounds; do not silently pretend hourly history is measured quarter-hour data. Normalize timezone/DST correctly.
4. “Duck curve” technically refers to net load. Retain the visual nickname but label price charts accurately. Do not move an evening-submitted job backward into the same afternoon.
5. Kubernetes suspension terminates Pods; checkpoints must be handled by the application. Kueue and the custom controller must not compete for ownership of suspend/admission fields. Retain pause/resume as a milestone only after checkpoint tests pass.
6. Negative wholesale prices do not prove negative total bills. Fixed cloud GPU rental normally does not track local spot electricity. Display energy-only assumptions and relevant tariff components.
7. Savings claims require a fixed workload suite and observation range, identical jobs, failures/deadlines included, and explicit perfect-hindsight benchmarks. No synthetic headline or fake Grafana evidence.
8. Public deployment, GitHub releases and posts cannot be claimed from local files. Every completion requires its actual evidence.
