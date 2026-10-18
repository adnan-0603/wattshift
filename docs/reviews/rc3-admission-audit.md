# WattShift v1.0.0rc3 — Kueue Admission Gate & CPU Validation Audit

**Status:** Offline regression-tested release candidate, **NOT** independently verified in Kubernetes.\
**Date:** 18 October 2026\
**Source:** `WattShift_v1.0.0rc2_Source_Audit_Fixes.zip` was used as the unchanged baseline; rc3 is a new working copy.

## বাংলায় ফলাফল

**সংশোধন করা হয়েছে:** আগের controller `Workload.spec.active` পরিবর্তন করত। নতুন Job তৈরি হওয়ার পর Kueue controller-এর আগে Job admit করলে পূর্বের সিদ্ধান্ত আর কার্যকর থাকত না। rc3-তে ClusterQueue-এর জন্য একটি বাধ্যতামূলক `wattshift-forecast` Kueue AdmissionCheck যোগ হয়েছে। Kueue নিজেই প্রথমে সেটিকে `Pending` রাখে। আমাদের controller forecast অনুযায়ী উপযুক্ত সময় এলে সেই check-কে `Ready` করে; Job কখন unsuspend হবে, সেটির দায়িত্ব Kueue-এর। এটি Kueue-এর documented gate semantics অনুসারে আগের first-admission race-এর source-level সমাধান। **বাস্তব cluster-এ কাজ করেছে কি না এখনও যাচাই হয়নি।**

### নতুন পরিবর্তন

1. ClusterQueue `wattshift-cpu` এখন Kueue `wattshift-forecast` AdmissionCheck ছাড়া Workload admit করতে পারবে না।
2. WattShift controller custom AdmissionCheck `Active` condition ও per-Workload `Ready` state **status subresource**-এ লেখে; `Job.suspend` বা `Workload.spec.active` পরিবর্তন করে না।
3. RBAC-এ Workload `/status` ও AdmissionCheck `/status` patch-এর জন্য পৃথক সীমিত permission রাখা হয়েছে।
4. ভুল/অনুপস্থিত Job annotation, অনুপস্থিত check, অন্য controller-এর check, already-admitted ungated migration state, Workload inactive ও `Rejected` অবস্থাগুলো আলাদাভাবে সামলানো হচ্ছে।
5. একটি Job মুছে গেলে বা status update-এ Kubernetes HTTP 409 conflict হলে অন্য Job-এর processing চলতে থাকে।
6. `make stack-lite` যোগ হয়েছে—পূর্ণ monitoring বাদ দিয়ে CPU-only Kubernetes smoke test চেষ্টা করা যায়। কোনো GPU বা paid cloud প্রয়োজন নেই।
7. `scripts/cluster_acceptance.py --lite`-এ controller **বন্ধ রেখে** Job তৈরি করার মাধ্যমে first-admission race পরীক্ষা, তারপর controller চালু করে gated admission এবং checkpoint resume পরীক্ষা করার স্ক্রিপ্ট দেওয়া হয়েছে। এটি **চালানো হয়নি** কারণ বর্তমান audit runtime-এ Docker, kind ও kubectl নেই।

## চালানো পরীক্ষার প্রমাণ

| Test | Observed result |
|---|---|
| Python `pytest -q` | **50/50 PASS** |
| Node `npm test` (TypeScript planner) | **5/5 PASS** |
| Source Python syntax / import | **PASS** |
| Offline `scripts/validate.py` | **PASS: 32 Kubernetes objects, 16,264 intervals, 168 forecast hours, 48 jobs** |
| `scripts/review.py` | **PASS**, bundled legacy archive hash verified |
| Docker backend/frontend build | **NOT RUN** — Docker unavailable |
| Actual Kueue AdmissionCheck/Workload lifecycle | **NOT RUN** — kind/kubectl unavailable |
| Browser/UI test and production Vite build | **NOT RUN** — npm dependencies unavailable offline |
| NVIDIA GPU job in Kueue | **NOT RUN** — free Kaggle GPU is not a kind worker |

### How to run on the user's 8 GB Mac

First run the lightweight offline gates:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt pytest
python -m pytest -q
python scripts/validate.py
```

If Docker/kind/kubectl are available, sufficient free memory exists, and the Mac can host a cluster:

```bash
make doctor
make stack-lite
python scripts/cluster_acceptance.py --lite
```

**Important:** `cluster_acceptance.py` is designed for a *fresh isolated* `kind-wattshift` cluster with no existing `wattshift-checkpoint-demo` Job. It creates that Job and temporarily scales the WattShift controller to zero, restoring its replica count on exit. It does **not** delete users' other clusters or Kubernetes contexts. `make down` destroys the named kind cluster and its local data, so export valuable checkpoints first. Close other heavy applications; **8 GB of physical RAM is not a performance guarantee**.

## Remaining release blockers / limitations

- **Critical runtime gate:** actual Kueue admission check creation, check Active condition, Workload Pending→Ready, and Job suspension/resumption must pass `scripts/cluster_acceptance.py --lite` on the user's machine. It is not verified here.
- **API version/install compatibility:** rendered CRDs use Kueue `v1beta2`, reference installation `v0.20.1`; validate against the installed live API/CRDs.
- **No fresh npm install / full browser production build** in this offline runtime.
- **Forecast failure policy:** stale/unavailable forecast explicitly fails open and releases valid Jobs; it protects deadline progress, not price optimization. Bad Job annotations fail closed.
- **Quota reservation:** Kueue AdmissionCheck Pending can hold quota while a job waits; under contention this may obstruct other jobs. A resource-efficient requeue strategy is a follow-up design task.
- **Model and capacity:** forecast uncertainty calibration, capacity constraints, true checkpoint overhead and Kubernetes job deadline semantics are not fully integrated.
- **No measured GPU power or live price savings:** the prior 7.783353% saving is retrospective simulation only, not measured utility, cloud/GPU rental, or real-world emissions.
- **Kaggle limitation:** user has demonstrated Tesla T4 x2 GPU compute in a Kaggle notebook, but its session is neither a stable cluster worker nor a guaranteed repeatable free quota.

## Technical design references

- Kueue AdmissionCheck concept: https://kueue.sigs.k8s.io/docs/concepts/admission_check/
- Developing an AdmissionCheck Controller: https://kueue.sigs.k8s.io/docs/tasks/dev/develop-acc/
- Kueue Job integration: https://kueue.sigs.k8s.io/docs/tasks/run/jobs/
- Detailed Kueue v1beta2 API: https://kueue.sigs.k8s.io/docs/reference/kueue.v1beta2/

**Verdict:** A testable first-admission guard has been implemented with the documented Kueue AdmissionCheck API, and local regressions pass. Stable `v1.0.0` remains blocked by live Kueue cluster acceptance, frontend build and remaining correctness/measurement limitations. No actual GPU result, cloud spend, or final GitHub release has been claimed.
