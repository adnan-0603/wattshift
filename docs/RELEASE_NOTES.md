# WattShift v1.0.0rc4 — independently reviewed preflight (not stable)

- Expired forecast start plans are recalculated if revised deadlines/runtimes make them infeasible.
- Saved plans are matched by Kueue Workload UID; stale Job-owner UID mismatches are not approved.
- Close SQLite connections explicitly during ingest instead of leaving file handles alive.
- Fix GitHub cluster CI to deploy the actual lite stack before running acceptance.
- Bind acceptance evidence to a commit so stable release script can verify the revision.
- Align Docker tags, manifests, Python and npm package metadata.
- Live Kubernetes, fresh frontend bundle, real GPU and performance claims remain unverified in this environment.

---

# WattShift v1.0.0rc3 — Kueue admission gate candidate (not stable)

- Replace post-hoc `Workload.spec.active` polling with a **Kueue AdmissionCheck**
  (`wattshift-forecast`) required by the ClusterQueue at creation time.
- AdmissionCheck controller reports an Active condition and only changes its
  own Pending state to Ready, via `/status` subresources and scoped RBAC.
- Prevent accidental reactivation of manually inactive Workloads. Preserve
  other admission checks; refuse invalid Job annotations and missing gate state.
- Add reduced RAM `make stack-lite` profile and separate CPU-only live Kueue
  admission/checkpoint acceptance script (requires a real cluster).
- 46 Python tests and 5 Node planner tests pass; **no live Docker/Kueue,
  browser build or GPU validation claimed.**
- Offline source race addressed in design; still blocked for final release on
  real cluster acceptance, fresh frontend build and workload validation.

See `docs/reviews/rc3-admission-audit.md` for test scope and next steps.

---

# WattShift v1.0.0rc2 — patched release candidate (not stable)

- Fix stale/incomplete readiness; separate strict live status and labelled stale demo.
- Introduce common pure hourly best-window selection for replay and forecast controller.
- Add forecast-based non-preemptive admission and sticky planned start across polls.
- Harden malformed job state/annotations and cap retrospective calculator horizon.
- Add targeted regression tests (36 backend passing versus 25 in rc1) while preserving rc1 simulated results.
- Align backend image tags and manifest generator for rc2.
- Still **not** fully cluster/GPU/browser verified; **Kueue first-admission race remains**.

See `docs/reviews/rc2-source-audit.md` for exact verification scope and unresolved gates.

---

# WattShift release candidate

Adds SMARD ingestion and provenance, production-weighted carbon estimates, chronological LightGBM quantile evaluation, FastAPI endpoints, three-policy simulation, a checkpoint-aware CPU worker, Kueue control source, Kubernetes infrastructure, monitoring provisioning, a five-page React Console, public refresh/deployment workflows and reproducible showcase assets.

Local tests and production frontend build are recorded in `docs/reviews/final-review.md`. Live Kubernetes acceptance, Docker builds, GPU measurement and remote deployment are not established by this candidate. Do not publish this text as a verified stable release without updating it with actual runtime evidence. No historical tags have been fabricated.
