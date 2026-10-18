# WattShift v1.0.0rc2 — Source-level audit, fixes and evidence

**Status:** patched release candidate; NOT an accepted production/live-Kubernetes release.\
**Constraints:** €0 budget, Apple M1 / 8 GiB host RAM, no locally attached GPU. Free Kaggle Tesla T4 x2 was *separately* verified by the user, but is not a Kubernetes worker and not used by these code tests.

## Scope and method

Re-inspected the original, integrity-checked `wattshift-v1.0-rc1(1).zip` in a separate working directory. Reviewed Python services (`api`, `controller`, `policies`, `simulator`, `forecast`, `export`, `ingest`, `refresh`, `worker`, `gpu`), test code, TypeScript planner and Console data contract, container files, manifests, deployment/cluster helpers, CI workflows, research provenance and docs. New rc2 changes do **not** overwrite the original zip. Original archive, legacy ZIP and Git bundle were retained in the untouched user-supplied rc1 archive. This rc2 distribution excludes the historical Git bundle and binary font files; the bundle does *not* contain rc2 changes.

## Confirmed defects / material inconsistencies addressed

| Finding | Fix | Regression evidence |
|---|---|---|
| Stale or truncated live market snapshot responded `/ready=200` | `check_readiness` checks schema, 168 consecutive forecast hours, usable non-finite values, consecutive market tail, current coverage, issue and retrieval age; strict live mode 503 when stale | `test_fresh_ready_and_timestamp_validation`, `test_price_coverage_needed_not_only_retrieval_time`, `test_ready_endpoint_fails_stale_and_malformed` |
| Offline seed is necessarily stale on future replay, strict readiness would prevent local demo starting | Explicit `WATTSHIFT_ALLOW_STALE_DEMO=1` **only** in the generated local kind API Deployment; returns `stale-demo-ready` / `live_data_ready:false`; controller independently fails open on stale signal | API tests, manifests and standalone validation |
| Controller used only current-price threshold, while research replay optimized future forecast windows | Forecast-driven hourly **admission** selection uses the same pure `best_start` implementation as offline replay; defaults to `forecast`, legacy threshold policy opt-in | `test_shared_policy_earliest_tie_and_gap`, `test_forecast_selects_cheapest_not_current_threshold`, `test_controller_forecast_patches_only_inactive_not_running` |
| Controller could defer forever when polling across a previously chosen start boundary | Persist/reuse selected job start time in controller-state across 20-second polls; activate at due time, no re-optimizing after that boundary | `test_forecast_persisted_start_does_not_drift_after_boundary` |
| Stale, missing, invalid forecasts could mislead live admission | Fail open to enable progress; explicit deadline override, missing deadline fails open; no preemption after Job is already running/admitted | `test_forecast_nonpreemptive_deadline_stale_and_missing_data` |
| Malformed annotation could stop reconciliation of all managed jobs | Per-job error status, continue subsequent jobs | `test_invalid_managed_job_does_not_prevent_others` |
| Broken `controller-state.json` yielded unhandled server error | `/jobs` returns 503, future-invalid heartbeat not connected | API route regression |
| Unbounded client planning horizon allowed excessively expensive retrospective enumeration | `/plan` rejects >14 days | `test_invalid_plan_request_bounded` |
| Naïve floating sliding sums changed tie choices | Earliest selection on near-equal floating totals; 48 historical replay decisions and reported totals match rc1 exactly | Replay/export parity reproduced in scratch directory |
| Mismatched old rc1 backend image tags after code update | Updated project version, image tags in deploy, demo, CI and *generated* platform YAML | Offline manifest validation and source consistency scan |

## Reproducible offline verification

- Backend: `python -m pytest -q` → **36 passed**, previously 25. Uses synthetic/small mocked controller resources; not a real cluster.
- TypeScript planner: `node --experimental-strip-types --test apps/console/src/planner.test.ts` → **5 passed**.
- Offline `python scripts/validate.py` → **29 YAML objects parsed**, 16,264 market intervals, 168 forecast hours, 48 job records. YAML parsing is NOT K8s server-side API validation.
- `python -m compileall -q wattshift scripts` → syntax compiled.
- Independent export in scratch dir → simulated `jobs` and `totals` **identical** to original rc1; headline savings remain €2.169125 / 7.783353% **simulated energy cost**, not achieved Kubernetes/GPU savings.
- Outer archive and per-file sha256 manifest rechecked on packaged rc2; preserve immutable source.

`pip check` of this *shared review environment* reports an unrelated preinstalled `moviepy`/`Pillow` mismatch. It is not a dependency of WattShift's locked runtime requirements; it was not remediated or called a successful environment check.

## BLOCKERS / not fixed or not verifiable here

1. **Critical Kueue admission race:** A newly created `Workload` may become admitted by Kueue before this polling controller makes its first `spec.active` decision. Shared forecast policy and hourly decision tests do **not** eliminate that race. A fail-closed admission gate / admission webhook or supported Kueue integration, plus live acceptance tests, is required before claiming reliable forecast-controlled **first** admission.
2. **No real Docker/kind/kubectl cluster** here. No deployment, Pod restart, Kueue eviction/admission, PVC recovery, ingress, Prometheus/Grafana target, TLS or full resource-footprint claims were validated. CI `cluster.yml` exists but has not been executed on the intended repository.
3. **Frontend**: Node direct planner tests passed. Fresh `npm ci`, React DOM, Vite `build`, responsive browser and security scanning not independently rerun (offline npm dependency cache absent). Bundled rc1 logs/prebuilt preview are historic, not rc2 proof.
4. **No local NVIDIA GPU**; Kaggle GPU verification is *external user evidence*. rc2 does NOT yet ship a Kaggle-specific reproducible GPU training or checkpoint test; no DCGM/power measurements or GPU-on-K8s integration.
5. **Model limitations:** P10–P90 bands remain uncalibrated; source report found 52–99% week-to-week coverage. No capacity-constrained, multi-queue or preemption-overhead optimization, no verified carbon reduction claim. Live controller assumes one independent fixed-power job with hour-aligned planning; **not equivalent** to the full retrospective 48-job economics under real capacity and costs.
6. **CPU host memory:** 8 GB total memory cannot be assumed sufficient for the entire six-deployment observability stack. See `docs/LOW_RESOURCE.md` for a realistic staged approach. No paid cloud is required for current offline regression checks.
7. **No security-penetration test or up-to-date dependency vulnerability scan**, no public deployment. The audit is a structured engineering review, not mathematical proof of bug-free code.

## Acceptance before stable release

A future rc must close the first-admission race and demonstrate a clean run in a real CPU Kubernetes cluster; front-end install/build plus browser acceptance; source freshness cron recovery; explicit data/forecast provenance; alerting and security checks; then a separate no-fee Kaggle GPU experiment with model/optimizer/RNG checkpoint and interruption persistence. Only promote to stable `v1.0.0` after all mandatory gates are recorded with commands, versions, results, and failures.
