# WattShift v1.0-rc1 — সম্পূর্ণ প্রজেক্টের নিরপেক্ষ টেকনিক্যাল রিভিউ

**তারিখ: ১৮ অক্টোবর ২০২৬ | ফাইল: `wattshift-v1.0-rc1(1).zip`**

## সহজ বাংলায় চূড়ান্ত সিদ্ধান্ত

**এটি একটি ভালোভাবে সাজানো এবং যথেষ্ট বাস্তবায়িত Research/Portfolio Release Candidate। কিন্তু এখনই একে পুরোপুরি পরীক্ষিত, production-ready সফটওয়্যার বলা যাবে না।** প্রজেক্টে আসল জার্মান বিদ্যুৎবাজারের ডেটা, price forecasting, API, React Console, simulated scheduling, Kubernetes configuration, monitoring setup এবং checkpoint-recovery worker আছে। বিভিন্ন ফাইল একসঙ্গে কাজ করার জন্য তৈরি করা হয়েছে; কিন্তু বাস্তব Kubernetes cluster-এ পুরো ব্যবস্থা চালিয়ে সফলতার প্রমাণ এই পর্যালোচনায় পাওয়া যায়নি।

### আমার নিজের চালানো পরীক্ষায় যা পাস করেছে

| কী পরীক্ষা করেছি | ফলাফল |
|---|---|
| মূল ZIP ফাইল এবং ভেতরের আগের প্রজেক্টের ZIP নষ্ট কি না | পাস |
| সংরক্ষিত ১৩২টি ফাইলের SHA-256 checksum | সবগুলো মিলেছে |
| Git history bundle | যাচাই সফল |
| Python backend test | ২৫/২৫ পাস |
| TypeScript scheduling logic test | ৫/৫ পাস |
| Data ও Kubernetes YAML-এর প্রাথমিক validation | পাস — তবে cluster-এ চালানোর পরীক্ষা নয় |
| CPU worker থামিয়ে আবার চালালে আগের কাজ ঠিক থাকে কি না | পাস; শেষ ফলাফল অপরিবর্তিত |
| Notebook-এর code cell | ৩টি সফল |
| আগের হিসাব নতুন করে চালালে একই forecast/simulation আসে কি না | পাস |
| বাস্তব Docker, Kubernetes, Grafana, GPU, browser rendering | এখানে পুনরায় পরীক্ষা করা যায়নি |

### সবচেয়ে জরুরি সমস্যাগুলো

**১. Simulation আর Kubernetes controller-এর কাজ এক নয় — সবচেয়ে গুরুত্বপূর্ণ ফাঁক।** Simulation-এ মডেল ভবিষ্যতের কোন সময়ে বিদ্যুতের দাম কম হবে তা অনুমান করে কাজ সরানোর চেষ্টা করে। অথচ আসল Kubernetes controller বর্তমান দাম নির্দিষ্ট সীমার ওপরে বা নিচে কি না, শুধু সেটি দেখে কাজ pause/resume করে। অর্থাৎ যে পদ্ধতিতে **৭.৭৮% সাশ্রয়** দেখানো হয়েছে, সেই একই পদ্ধতি বাস্তব controller চালায় না। তাই ৭.৭৮% সাশ্রয়কে Kubernetes-এর বাস্তব অর্জন বলা যাবে না। `wattshift/controller.py`, `wattshift/forecast.py` ও `wattshift/policies.py`-তে বিষয়টি দেখা যায়।

**২. পুরোনো ডেটা থাকলেও API নিজেকে ready বলে — পরীক্ষায় নিশ্চিত bug।** `wattshift/api.py`-এর `/ready` endpoint-এ আমি একটি পরীক্ষামূলক snapshot-এর retrieval date **১ জানুয়ারি ২০০০** করে দিয়েছি। তারপরও endpoint **HTTP 200** দিয়েছে। ডেটা আছে কি না, তার পাশাপাশি সেটি কতটা পুরোনো এবং যথেষ্ট সম্পূর্ণ কি না, সেটিও যাচাই করা দরকার।

**৩. Kubernetes/Grafana বাস্তবে চলেছে, এমন প্রমাণ এখনো নেই।** Docker image build, kind cluster, Kueue eviction ও readmission, pod-এর মধ্যে checkpoint থেকে resume, Prometheus scrape এবং Grafana dashboard বাস্তবে দেখতে হবে। YAML ঠিকভাবে parse হলেই deployment কাজ করবে—এমন নয়।

**৪. Forecast-এর অনিশ্চয়তার পরিসর সব সপ্তাহে সমান নির্ভরযোগ্য নয়।** আমি ২০২৪ সালের আরও ছয়টি সপ্তাহের শুরুতে forecast চালিয়েছি। প্রতিটি নির্বাচিত সপ্তাহে মডেলের গড় ভুল (MAE) সাধারণ seasonal baseline-এর চেয়ে কম। কিন্তু P10–P90 interval-এর বাস্তব coverage ছিল **৫২.৩৮% থেকে ৯৮.৮১%**। অর্থাৎ মাঝামাঝি ৮০% coverage লক্ষ্য থাকলেও সেই মান বিভিন্ন সময়ে অনেক বদলে যাচ্ছে; এটি calibrate করতে হবে।

**৫. CPU checkpoint আর GPU training এক জিনিস নয়।** Worker সত্যিই CPU-তে কাজ মাঝপথে থামিয়ে আবার চালাতে পারে, এটি একটি প্রমাণিত ভালো দিক। কিন্তু বাস্তব GPU training job, GPU power measurement, capacity-constrained cluster optimization ও live event-history dashboard এখনো সম্পূর্ণ নয়।

**৬. Frontend-এর আগের build-এর log আছে, কিন্তু আমি এখানে নতুন করে full build করতে পারিনি।** Node-এর সরাসরি scheduling tests পাস করেছে। কিন্তু `npm ci --offline` নির্ভরতা না পাওয়ায় থেমেছে, তাই ECharts rendering, React DOM test, visual/mobile browser test এবং Vite production build নতুন করে সফল হয়েছে—এমন দাবি করছি না।

### ৭.৭৮% সংখ্যাটির সঠিক অর্থ

২৫–৩১ ডিসেম্বর ২০২৪-এ ৪৮টি বানানো batch job ধরে, স্থির GPU power অনুমানে: সঙ্গে সঙ্গে চালালে আনুমানিক বিদ্যুৎ খরচ **€২৭.৮৬৯**, forecast দেখে সময় বাছলে **€২৫.৭০০**, পার্থক্য **€২.১৬৯ = ৭.৭৮%**। এটি **বিদ্যুতের energy component-এর simulation**, cloud GPU rental bill-এর সাশ্রয় নয়। Carbon-এর সুবিধাও খুব সামান্য ছিল; `greenest` নামের অন্য নীতিটি উল্টো carbon estimate বাড়িয়েছে। এক সপ্তাহের ফল দিয়ে সব সপ্তাহের সাশ্রয় নিশ্চিত করা যাবে না।

### এখন কী কী কাজ করতে হবে — অগ্রাধিকার অনুযায়ী

১. `/ready` endpoint-এ stale data এবং incomplete data শনাক্ত করার ব্যবস্থা ও test যোগ করতে হবে।

২. Kubernetes controller-কে সত্যিকারের forecast-driven scheduler বানাতে হবে; না হলে স্পষ্টভাবে **current-price threshold controller** বলতে হবে।

৩. `make up` এবং `scripts/cluster_acceptance.py` বাস্তব Docker-enabled মেশিনে চালিয়ে পুরো stack-এর প্রমাণ সংগ্রহ করতে হবে। Grafana, CronJob ও PVC restart-ও দেখতে হবে।

৪. Frontend dependency install, build, UI interaction, responsive browser এবং chart rendering নতুন করে পরীক্ষা করতে হবে।

৫. Forecast-এর rolling backtest/calibration এবং realistic capacity/energy-cost model উন্নত করতে হবে।

৬. তারপর GitHub Actions, public Pages এবং প্রমাণসহ release করতে হবে। Hardware থাকলে optional GPU পরিমাপ যোগ করতে হবে।

**সিদ্ধান্ত:** এখনই `v1.0.0rc1` হিসেবে রাখা যুক্তিসঙ্গত। প্রয়োজনীয় সংশোধন ও বাস্তব end-to-end পরীক্ষা ছাড়া এটিকে পূর্ণাঙ্গ `v1.0.0` বলা ঠিক হবে না। নিচে বিস্তারিত ইংরেজি রিপোর্টে প্রতিটি ফাইলের অবস্থান, পরীক্ষার ফল এবং আরও ছয়টি সপ্তাহের সংখ্যাসহ দেওয়া আছে।

---

# WattShift v1.0-rc1 — Independent Expert Audit

**Audit date:** 18 October 2026\
**Reviewed archive:** `wattshift-v1.0-rc1(1).zip` (133 ZIP members, ~26 MB)\
**Scope:** packaged source, data, manifests, archived evidence, preview assets, Git bundle, nested legacy archives, direct local tests, reproducibility and additional chronological forecasting experiments.

## Executive decision

**Verdict: credible, substantially implemented portfolio/research release candidate; NOT fully end-to-end verified and NOT production-ready.** Keep the `rc1` designation. The research result and the checkpoint worker were independently reproduced. Important operational and functional gates remain unverified; the live controller does not implement the forecast-optimization policy used in the savings simulation.

## 1. Independently executed checks

| Check | Result | Evidence / scope |
|---|---|---|
| Outer ZIP CRC | PASS | All 133 members decoded without an error |
| PACKAGE_SHA256.json | PASS | All 132 included recorded file hashes matched |
| Original prototype ZIP and nested academic ZIP | PASS (integrity) | Both readable, no corruption; legacy code not individually integration-tested |
| Git bundle | PASS | Verified from a temporary Git repository; complete history recorded, refs `main` and `HEAD` |
| Snapshot consistency | PASS | `data/processed`, public Console and preview snapshots SHA-256 identical |
| Dataset provenance | PASS (internal) | Five CSV SHA-256 hashes equal their provenance entries; independent historical source re-fetch not done |
| Backend suite | PASS | `python -m pytest -q`: **25 passed** |
| TypeScript planner tests | PASS | Node direct `--experimental-strip-types --test`: **5 passed** |
| Source-level data/YAML validation | PASS | `scripts/validate.py`: 29 objects, 16,264 price intervals, 168 forecast hours, 48 jobs |
| CPU worker checkpoint | PASS | Controlled termination (exit 75), resume through step 100, final digest matched uninterrupted run |
| Notebook code | PASS | 3 code cells executed in-process |
| Archived MP4 metadata | PASS | ~119.93 seconds; this is a local showcase recording, NOT proof of live cluster |
| Forecast/export replay | PASS | Fresh `python -m wattshift.export --out /tmp/...` matched all packaged `backtest`, `forecast`, `simulation` values |
| Real Kubernetes/Docker builds and Grafana | NOT RUN | `docker`, `kind`, `kubectl` not installed in inspection environment |
| UI DOM/visual test, current Vite build | NOT RUN | No cached npm packages and outbound registry unavailable; archive contains earlier build/DOM evidence, not an independent rerun |
| Physical GPU/DCGM metrics | NOT RUN | No NVIDIA hardware/tooling |
| Actual public Pages/GitHub Actions | NOT RUN | No target GitHub repository connected for deployment |

**Important distinction:** `scripts/validate.py` parses manifest syntax and checks basic structure, not API-server admission, Docker image correctness, pod scheduling or Helm/Kueue execution.

## 2. Findings in priority order

### P1 — System/product acceptance blocker: forecast-to-controller gap

**Evidence:** `wattshift/controller.py` lines 13–19 and 63–71; `wattshift/forecast.py` and `wattshift/policies.py`. The cluster controller requests `/prices`, extracts the **current** interval, and controls Kueue `Workload.spec.active` using a fixed `max-price` plus hysteresis. It neither requests `/forecast` nor chooses future forecast-optimal start windows. The 7.78% simulation is an offline forecast-based **different policy** and is not evidence of savings achieved by the deployed controller.

**Action:** Implement a forecast-driven admission/deferral policy with decision time, release/deadline constraints, capacity awareness, re-planning, controller event/audit history, and common policy tests. Compare the actual controller trace to the same forecast policy used in `replay`. Label the current behavior `real-time threshold-based controller` until this is built.

### P1 — End-to-end runtime unverified

**Evidence:** `docs/reviews/final-review.md`, `scripts/deploy.py`, `scripts/cluster_acceptance.py`. All deployment manifests and a CI workflow are included, but neither real image builds, kind/Kueue lifecycle, PVC persistence after a restart, ingress reachability nor genuine Grafana scrape/queries has been verified here. A Python integration smoke script is provided, not executed.

**Action:** On a Docker-capable machine run `make doctor && make up`, then `python scripts/cluster_acceptance.py`. Capture checked logs, actual Grafana target and panels, controller pause/resume and full completion digest. Run the GitHub workflow `cluster.yml` on the intended repository. Failure at any gate blocks stable v1.0.

### P2 — Confirmed defect: readiness passes stale datasets

**Evidence:** `wattshift/api.py` lines 35–37. Direct reproduction with a snapshot whose `retrieved_at` was `2000-01-01T00:00:00+00:00` returned **HTTP 200** with `status='ready'`. The frontend labels snapshots stale after 36 hours and the controller has a 36-hour freshness check, but `/ready` verifies existence only, not recency or required interval coverage.

**Action:** Separate data freshness from liveness; return **503 readiness** if the required latest market coverage, retrieval age or schema is inadequate. Add tests for stale, malformed, future-timestamped and partial snapshots. Keep historical replay mode explicitly separate from a live-data readiness contract.

### P2 — Forecast uncertainty is not calibrated

**Evidence:** `wattshift/forecast.py` lines 41–48: quantiles are fitted independently and sorted; sorting prevents crossings, not calibration. Six additional seven-day holdouts below gave empirical P10–P90 coverage from **52.38% to 98.81%**. A nominal P10–P90 interval targets 80% coverage, which is not stable across these examples.

**Action:** Add rolling-origin validation over multiple seasons/years, calibration/error breakdown by hour/horizon, interval calibration on a separate validation period, and drift/data-vintage monitoring. Do not promise calibrated 80% probability intervals.

### P2 — Full live Jobs/GPU story absent

**Evidence:** `wattshift/worker.py` explicitly executes CPU digest hashing, not ML/GPU compute. Jobs screen (`apps/console/src/main.tsx`, Jobs function) shows the first 10 simulated jobs plus a small live controller status table, not an operational event history or Gantt of observed pause/resume. `wattshift/gpu.py` provides a sampler but no actual measurements are supplied. These limitations are fairly disclosed in the README/review.

**Action:** Store controller transitions and Kueue events with timestamps; expose observed event history, start/stop/resume counts and checkpoint data; run on actual hardware only if Phase 8 is pursued.

### P2 — Public hosting/security is still demo-oriented

**Evidence:** `wattshift/api.py` exposes an unauthenticated POST `/plan` with permissive timestamp horizons and processing over snapshots, plus read-only endpoints. K8s manifests use local ingress and transient application snapshots; no Internet production security review or abuse/rate controls. Current architecture and documentation correctly identify it as a local/public demonstration.

**Action:** If exposing API externally, add authentication or intended public rate-limiting, request bounds/cost controls, security headers, TLS, resource policy/network controls, monitoring and backup/restore evidence. This is not automatically a blocker for local kind mode.

### P3 — Maintainability and browser performance

**Evidence:** Five-page UI is concentrated in a handful of enormous one-line TSX/CSS declarations. `Chart.tsx` has an effect depending on a newly built `option` object; parent rerenders can recreate/dispose entire ECharts instances. This is source-level performance/maintainability risk; it has not been user-profiled in a real browser.

**Action:** Split into components/pages, memoize chart options or update charts in place, and perform actual desktop/mobile/browser responsiveness and accessibility tests.

### P3 — Cost, carbon and causality model restrictions

**Evidence:** `wattshift/policies.py` and `docs/METHOD.md`: unlimited capacity, independent generated jobs, constant GPU/host power, no electricity network tariff, cloud rental, idle, failure or checkpoint overhead, and lifecycle production-mix carbon rather than marginal avoided emissions. Price data uses retrospective retrieval without publication-vintage archives.

**Action:** Add capacity-constrained scheduling, matched realistic workloads/measurement, energy tariffs and deployment-specific marginal carbon modeling before claiming savings for a real platform/customer.

## 3. Extra independent rolling-origin analysis

Using the project’s own `predict()` and `replay()` with different strictly earlier training cutoffs, seven-day forward windows and the same simulation seed and 48 generated jobs:

| Forecast origin (UTC) | Model MAE (€/MWh) | Seasonal MAE (€/MWh) | P10–P90 coverage | Simulated cost saving |
|---|---:|---:|---:|---:|
| 2024-03-15 | 10.81 | 15.69 | 52.38% | 11.50% |
| 2024-05-15 | 16.80 | 33.52 | 98.81% | 48.46% |
| 2024-07-15 | 22.40 | 23.77 | 72.02% | 35.77% |
| 2024-09-15 | 17.63 | 23.14 | 91.67% | 20.62% |
| 2024-11-15 | 23.54 | 27.41 | 58.33% | 8.86% |
| 2024-12-25 | 27.07 | 58.45 | 80.36% | 7.78% |

Model MAE beat the seasonal comparator in all six *selected* windows, but uncertainty coverage and modeled savings varied greatly. These windows are **additional retrospective spot checks**, not a complete walk-forward hyperparameter-selection-controlled scientific validation. Large percentage savings in individual weeks should not become marketing claims without the euro denominators, job assumptions, zero/negative price context and confidence intervals.

The packaged headline was reproduced exactly on its own week: immediate **€27.868770**, cheapest forecast **€25.699645**, saving **€2.169125 / 7.783353%**, with simulated carbon reduction only **0.222627 kgCO₂e**. The `greenest` proxy actually **increased** its estimated carbon by **0.324635 kgCO₂e**. These are **simulated energy-only** euros—not cloud rental costs or measured GPU power.

## 4. Positive technical evidence

- Source archive and research replay have strong reproducibility properties: ZIP CRC, file checksums, data-provenance hashes, Git bundle and deterministic LightGBM/replay metrics all checked.
- SMARD generation filter mappings are consistent with the documented public SMARD chart-data API; carbon missing values are treated conservatively, and methods explain the approximation.
- Unit/deadline/time-window logic is covered by tests; no simple future-price leakage was observed in the backtest test suite.
- The CPU worker actually survived process interruption via checkpoint and matched the uninterrupted digest.
- The controller edits `Workload.spec.active` rather than competing with Kueue for Job suspension fields; this is directionally aligned with documented Kueue APIs, but still requires real runtime acceptance.
- Honest documentation explicitly separates modeled savings and forecast from real cloud bills and real cluster execution.

## 5. Recommended release gates

1. **Fix proven readiness bug**, add freshness, schema and source-coverage checks with automated tests.
2. **Decide product semantics**: either clearly call the running controller a price-threshold demonstration, or implement a real forecast-driven job scheduling policy and measure its results on trace and cluster.
3. **Complete clean frontend build/DOM/browser checks** with `npm ci`, `npm test`, `npm run test:ui`, `npm run build`, then verify graphs and responsive UI in an actual browser.
4. **Run full container and cluster gate**, recording `make up` and `cluster_acceptance.py` outcomes, real ingress, CronJob/PVC, Kueue interactions and Grafana metrics.
5. **Expand walk-forward backtesting** and calibration; add realistic capacity and workload costs before broad efficacy claims.
6. **Finish GitHub repo, Pages, CI/CD release milestones and evidence video** without backdating tags or claiming work that did not execute. Optional: measured GPU/DCGM comparison.

**Release recommendation:** retain **`v1.0.0rc1`**, treat as a strong research/portfolio demo candidate, but **do not tag or describe it as fully end-to-end verified `v1.0.0`** until the runtime acceptance gates are completed.

### External technical cross-checks

- Kueue v0.20 `Workload.active`: https://kueue.sigs.k8s.io/v0.20/docs/concepts/workload/
- Kueue v0.20 `ClusterQueue`: https://kueue.sigs.k8s.io/v0.20/docs/concepts/cluster_queue/
- SMARD chart-data filter mapping: https://github.com/bundesAPI/smard-api

**Limits of this audit:** No actual downloaded upstream SMARD data re-fetch from the container; no Docker/kubectl/kind, GPU, complete UI dependency cache or browser environment. Previous packaged build logs were reviewed as supplied evidence, not presented as independent execution. Source review is not a substitute for a live cluster or formal security assessment.
