"""Kueue AdmissionCheck controller for checkpointable CPU jobs.

Forecast mode defers *not-yet-running* jobs to a cheaper contiguous hourly
window, then leaves running jobs alone (non-preemptive).  This is not a GPU
cluster and does not claim measured energy savings.  An explicit legacy
price-threshold policy remains available for demonstration.
"""
from datetime import datetime, timezone, timedelta
import json
import math
import os
from pathlib import Path
import ssl
import time
import httpx
from .scheduling import best_start

FRESHNESS_SECONDS = 36 * 3600
CHECK_NAME = "wattshift-forecast"
CHECK_CONTROLLER = "wattshift.dev/forecast-admission"
KUEUE_API = "/apis/kueue.x-k8s.io/v1beta2"


def _utc(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('All controller signal timestamps require a timezone')
    return result.astimezone(timezone.utc)


def _recent(value, now):
    age = (now - _utc(value)).total_seconds()
    return -300 <= age <= FRESHNESS_SECONDS


def decision(price, max_price, active, now, deadline=None, remaining_seconds=0, hysteresis=5):
    """Legacy price-threshold policy, not forecast-based optimization."""
    if deadline and now + timedelta(seconds=remaining_seconds+60) >= deadline:
        return True, 'deadline override'
    if price is None:
        return True, 'price unavailable: fail open to preserve progress'
    if active and price > max_price + hysteresis:
        return False, 'price above stop threshold'
    if not active and price <= max_price:
        return True, 'price below resume threshold'
    return active, 'hysteresis hold'


def forecast_decision(signal, now, deadline, remaining_seconds, running=False, planned_start=None):
    """Return (admit, reason, chosen_start) based on an issued hourly signal.

    A running job is never interrupted to chase a revised forecast. Slots are
    hourly like the offline replay; estimated runtime is rounded up. No claim
    is made that an hour-aligned window predicts exact execution or capacity.
    """
    if running:
        return True, 'running/admitted job: no forecast preemption', None
    if deadline is None:
        return True, 'no job deadline: fail open', None
    if now + timedelta(seconds=remaining_seconds+60) >= deadline:
        return True, 'deadline override', None
    if not signal or signal.get('data_mode') != 'market snapshot':
        return True, 'forecast unavailable: fail open', None
    try:
        if not _recent(signal['retrieved_at'], now) or not _recent(signal['issue_time'], now):
            return True, 'forecast stale: fail open', None
        horizon = signal['intervals']
        if not isinstance(horizon, list) or not horizon:
            return True, 'forecast empty: fail open', None
        starts = [_utc(v['start']) for v in horizon]
        if len(set(starts)) != len(starts) or any(b-a != timedelta(hours=1) for a, b in zip(starts, starts[1:])):
            return True, 'forecast intervals discontinuous: fail open', None
        if planned_start:
            try:
                remembered = _utc(planned_start)
                if (now-timedelta(hours=1) <= remembered <= now+timedelta(days=7)
                        and remembered + timedelta(seconds=remaining_seconds+60) <= deadline):
                    if now >= remembered:
                        return True, 'previous planned start reached', remembered.isoformat()
                    return False, 'awaiting previous planned start', remembered.isoformat()
            except (ValueError, AttributeError, TypeError):
                pass
        values = [v.get('published') if v.get('published') is not None else v.get('p50') for v in horizon]
        # Begin no earlier than the next full hour. Otherwise, scheduling a
        # one-hour job at 12:45 against a 12:00–13:00 slot is optimistic.
        earliest = now.replace(minute=0, second=0, microsecond=0)
        if now > earliest:
            earliest += timedelta(hours=1)
        first = next((i for i, t in enumerate(starts) if t >= earliest), len(starts))
        last = len(starts) if deadline is None else next((i for i, t in enumerate(starts) if t >= deadline), len(starts))
        # A deadline inside an hour must not be rounded up.
        if deadline is not None:
            while last and starts[last-1] + timedelta(hours=1) > deadline:
                last -= 1
        hours = max(1, math.ceil(remaining_seconds/3600))
        if first >= last or last-first < hours:
            return True, 'insufficient forecast window: fail open', None
        chosen = best_start(values, first, last, hours)
        if chosen is None:
            return True, 'incomplete forecast window: fail open', None
        selected = starts[chosen]
        return (now >= selected, 'forecast-optimal window' if now >= selected else 'deferred to forecast-optimal window', selected.isoformat())
    except (ValueError, TypeError, KeyError, OverflowError):
        return True, 'invalid forecast: fail open', None


class Kubernetes:
    def __init__(self):
        token = Path('/var/run/secrets/kubernetes.io/serviceaccount/token').read_text()
        ca = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
        self.client = httpx.Client(base_url='https://' + os.environ['KUBERNETES_SERVICE_HOST'] + ':' + os.getenv('KUBERNETES_SERVICE_PORT', '443'),
                                   headers={'Authorization': 'Bearer ' + token}, verify=ssl.create_default_context(cafile=ca), timeout=15)

    def get(self, path):
        response = self.client.get(path)
        response.raise_for_status()
        return response.json()

    def patch_status(self, path, body):
        """Status subresource only: never mutate Kueue Job suspension or Workload.active."""
        response = self.client.patch(path + '/status', json=body,
                                     headers={'Content-Type': 'application/merge-patch+json'})
        response.raise_for_status()
        return response.json()


def activate_admission_check(kube, now=None):
    """Mark this ACC healthy so Kueue can use its fail-closed admission gate.

    A missing or incorrectly owned AdmissionCheck is a hard configuration error.
    A stopped controller cannot mark fresh Workloads Ready: the ClusterQueue's
    gate still blocks them, even if this Active condition remains True.
    """
    now = now or datetime.now(timezone.utc)
    path = f'{KUEUE_API}/admissionchecks/{CHECK_NAME}'
    check = kube.get(path)
    if check.get('spec', {}).get('controllerName') != CHECK_CONTROLLER:
        raise ValueError('AdmissionCheck missing expected controllerName')
    conditions = list(check.get('status', {}).get('conditions', []))
    if any(c.get('type') == 'Active' and c.get('status') == 'True' and
           c.get('observedGeneration') == check['metadata'].get('generation', 1)
           for c in conditions):
        return False
    conditions = [c for c in conditions if c.get('type') != 'Active']
    conditions.append({'type': 'Active', 'status': 'True',
                       'observedGeneration': check['metadata'].get('generation', 1),
                       'lastTransitionTime': now.isoformat(),
                       'reason': 'ControllerReady',
                       'message': 'WattShift admission controller is active'})
    kube.patch_status(path, {'metadata': {'resourceVersion': check['metadata']['resourceVersion']},
                             'status': {'conditions': conditions}})
    return True


def reconcile(kube, price=None, namespace='wattshift', now=None, forecast=None, previous_plans=None):
    """Only approve Pending admission checks; Kueue alone starts Jobs.

    Kueue adds a Pending check when it creates each Workload. This is atomic
    with its admission process: until this controller changes Pending to Ready,
    Kueue cannot admit a newly created Workload, even before the first poll.
    """
    now = now or datetime.now(timezone.utc)
    base = f'{KUEUE_API}/namespaces/{namespace}/workloads'
    work = kube.get(base)['items']
    states = []
    previous_plans = previous_plans or {}
    for item in work:
        conditions = item.get('status', {}).get('conditions', [])
        if any(c.get('type') == 'Finished' and c.get('status') == 'True' for c in conditions):
            continue
        owner = next((r for r in item.get('metadata', {}).get('ownerReferences', []) if r.get('kind') == 'Job'), None)
        if not owner:
            continue
        try:
            job = kube.get(f'/apis/batch/v1/namespaces/{namespace}/jobs/{owner["name"]}')
        except httpx.HTTPStatusError as exc:
            # An owner can be deleted between Workload list and Job GET.
            states.append({'id': owner['name'], 'status': 'job-unavailable',
                           'reason': str(exc), 'updated_at': now.isoformat()})
            continue
        owner_uid = owner.get('uid')
        job_uid = job.get('metadata', {}).get('uid')
        if owner_uid and job_uid and owner_uid != job_uid:
            states.append({'id': owner['name'], 'status': 'owner-uid-mismatch',
                           'reason': 'Workload belongs to an earlier Job with the same name',
                           'updated_at': now.isoformat()})
            continue
        if job.get('metadata', {}).get('labels', {}).get('wattshift.dev/managed') != 'true':
            continue
        ann = job.get('metadata', {}).get('annotations', {})
        if ann.get('wattshift.dev/checkpoint-enabled') != 'true':
            continue
        checks = item.get('status', {}).get('admissionChecks', [])
        gate = next((c for c in checks if c.get('name') == CHECK_NAME), None)
        admitted = any(c.get('type') == 'Admitted' and c.get('status') == 'True' for c in conditions)
        # A missing gate on an existing Workload is NOT a pass: that Workload
        # could have been created before the ClusterQueue became gated.
        if gate is None:
            states.append({'id': owner['name'], 'status': 'gate-missing',
                           'reason': 'Kueue has not installed the required AdmissionCheck state',
                           'updated_at': now.isoformat()})
            continue
        if item.get('spec', {}).get('active') is False:
            states.append({'id': owner['name'], 'status': 'inactive', 'updated_at': now.isoformat()})
            continue
        if admitted and gate.get('state') != 'Ready':
            # Migration from an ungated ClusterQueue: report the unsafe state.
            # Do not rewrite the status of an already running Workload.
            states.append({'id': owner['name'], 'status': 'already-admitted-ungated',
                           'reason': 'Admitted before WattShift gate was Ready',
                           'updated_at': now.isoformat()})
            continue
        try:
            deadline = _utc(ann['wattshift.dev/deadline']) if ann.get('wattshift.dev/deadline') else None
            remaining = int(ann.get('wattshift.dev/estimated-seconds', '300'))
            if not 1 <= remaining <= 7*24*3600:
                raise ValueError('estimated-seconds outside supported range')
            policy = ann.get('wattshift.dev/policy', 'forecast')
            if policy == 'forecast':
                # Once approved, never revoke a Workload that could be running.
                running = admitted or gate.get('state') == 'Ready' or bool(job.get('status', {}).get('active', 0))
                desired, reason, planned = forecast_decision(forecast, now, deadline, remaining,
                                                             running, previous_plans.get((owner['name'], item['metadata'].get('uid'))))
            elif policy == 'price-threshold':
                max_price = float(ann.get('wattshift.dev/max-price', '80'))
                if not math.isfinite(max_price):
                    raise ValueError('Invalid max-price')
                already_started = admitted or gate.get('state') == 'Ready' or bool(job.get('status', {}).get('active', 0))
                # For new workloads, threshold decides first admission only;
                # do not preempt running jobs using a quota-admission check.
                desired, reason = (True, 'already released to Kueue') if already_started else decision(
                    price, max_price, False, now, deadline, remaining)
                planned = None
            else:
                raise ValueError('Unknown controller policy')
        except (ValueError, TypeError, KeyError) as exc:
            states.append({'id': owner['name'], 'status': 'error', 'reason': str(exc),
                           'updated_at': now.isoformat()})
            continue
        if desired and gate.get('state') not in ('Ready', 'Rejected'):
            # Preserve other admission checks and their podSetUpdates. Include
            # resourceVersion so concurrent Kueue updates fail with HTTP 409;
            # the next poll reads the latest state and retries.
            new_checks = [dict(c) for c in checks]
            updated = next(c for c in new_checks if c.get('name') == CHECK_NAME)
            updated.update({'state': 'Ready', 'lastTransitionTime': now.isoformat(),
                            'message': reason})
            try:
                kube.patch_status(base+'/'+item['metadata']['name'],
                                  {'metadata': {'resourceVersion': item['metadata']['resourceVersion']},
                                   'status': {'admissionChecks': new_checks}})
            except httpx.HTTPStatusError as exc:
                # Most commonly HTTP 409: reconcile from a fresh RV next poll,
                # and keep processing other independent Workloads now.
                states.append({'id': owner['name'], 'status': 'status-conflict',
                               'reason': str(exc), 'updated_at': now.isoformat()})
                continue
        states.append({'id': owner['name'], 'active': item.get('spec', {}).get('active', True),
                       'status': ('rejected' if gate.get('state') == 'Rejected' else
                                  ('admitted' if admitted else 'awaiting-kueue') if desired else 'deferred'),
                       'admission_check': CHECK_NAME,
                       'workload_uid': item['metadata'].get('uid'),
                       'check_state': 'Ready' if desired else gate.get('state'),
                       'policy': policy, 'planned_start_utc': planned, 'reason': reason,
                       'deadline': deadline.isoformat() if deadline else None,
                       'cpu_emulation': True, 'updated_at': now.isoformat()})
    return states


def main():
    kube = Kubernetes()
    data = Path(os.getenv('WATTSHIFT_DATA', 'data/processed'))
    data.mkdir(parents=True, exist_ok=True)
    api = os.getenv('WATTSHIFT_API', 'http://wattshift-api:8000').rstrip('/')
    while True:
        now = datetime.now(timezone.utc)
        try:
            forecast = None
            price = None
            try:
                with httpx.Client(timeout=10) as client:
                    r = client.get(api+'/forecast')
                    r.raise_for_status()
                    forecast = r.json()
                    if forecast.get('data_mode') != 'market snapshot' or not _recent(forecast['retrieved_at'], now):
                        forecast = None
                    p = client.get(api+'/prices')
                    p.raise_for_status()
                    prices = p.json()
                    if prices.get('mode') == 'market snapshot' and _recent(prices['retrieved_at'], now):
                        current = [x for x in prices['intervals'] if _utc(x['start']) <= now < _utc(x['end'])]
                        if current:
                            price = current[0]['price']
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
                print(json.dumps({'event': 'signal_unavailable', 'error': str(exc)}), flush=True)
            try:
                previous = json.loads((data/'controller-state.json').read_text())
                previous_plans = {(j['id'], j['workload_uid']): j.get('planned_start_utc')
                                  for j in previous.get('jobs',[])
                                  if isinstance(j, dict) and j.get('policy') == 'forecast'
                                  and j.get('workload_uid') and j.get('planned_start_utc')}
            except (OSError,ValueError,TypeError,KeyError):
                previous_plans = {}
            activate_admission_check(kube, now)
            jobs = reconcile(kube, price, os.getenv('POD_NAMESPACE', 'wattshift'), now,
                             forecast=forecast, previous_plans=previous_plans)
            state = {'updated_at': now.isoformat(), 'mode': 'cluster', 'price_eur_mwh': price,
                     'forecast_available': forecast is not None, 'jobs': jobs}
            tmp = data/'controller-state.tmp'
            tmp.write_text(json.dumps(state))
            tmp.replace(data/'controller-state.json')
            print(json.dumps(state), flush=True)
        except Exception as exc:
            print(json.dumps({'event': 'reconcile_failed', 'error': str(exc)}), flush=True)
        time.sleep(20)


if __name__ == '__main__':
    main()
