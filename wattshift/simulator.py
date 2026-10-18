"""Standard-library-only simulator. Costs are energy-only estimates, not GPU rental bills."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import csv
import math


def timestamp(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamps must include UTC offset or Z')
    return result.astimezone(timezone.utc)


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime
    available_at: datetime
    price_eur_mwh: float
    carbon_g_kwh: float | None = None


def load_csv(path):
    with open(path, newline='') as handle:
        rows = [Interval(timestamp(r['start_utc']), timestamp(r['end_utc']),
                         timestamp(r['available_at_utc']), float(r['price_eur_mwh']),
                         float(r['carbon_g_kwh']) if r.get('carbon_g_kwh', '').strip() else None)
                for r in csv.DictReader(handle)]
    return rows


def plan(rows, *, decision_at, release, deadline, duration_minutes,
         gpu_count=1, gpu_watts=300, host_watts=100, pue=1.2,
         tariff_adder_eur_kwh=0, objective='cost'):
    """Enumerate all interval-aligned contiguous windows; choose earliest on ties.

    Baseline = earliest feasible start with the same job, power and data.
    One job, unlimited assumed capacity, constant power; no preemption or queueing.
    Input prices/carbon must be available at decision time. Does not invent forecasts.
    """
    if objective not in ('cost', 'carbon'):
        raise ValueError('objective must be cost or carbon')
    for dt in (decision_at, release, deadline):
        if dt.tzinfo is None:
            raise ValueError('All job timestamps must be timezone-aware')
    decision_at, release, deadline = [dt.astimezone(timezone.utc) for dt in (decision_at, release, deadline)]
    if not decision_at <= release < deadline:
        raise ValueError('Require decision_at <= release < deadline')
    values = (duration_minutes, gpu_count, gpu_watts, host_watts, pue, tariff_adder_eur_kwh)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('Job parameters must be finite')
    if duration_minutes <= 0 or gpu_count < 1 or int(gpu_count) != gpu_count or gpu_watts <= 0 or host_watts < 0 or pue < 1:
        raise ValueError('Invalid duration, GPU count, power or PUE')
    rows = sorted(rows, key=lambda r: r.start)
    if not rows:
        raise ValueError('No intervals')
    for i, row in enumerate(rows):
        if any(t.tzinfo is None for t in (row.start, row.end, row.available_at)):
            raise ValueError('Interval timestamps must be timezone-aware')
        if row.end <= row.start or not math.isfinite(row.price_eur_mwh):
            raise ValueError('Invalid interval or price')
        if row.carbon_g_kwh is not None and (not math.isfinite(row.carbon_g_kwh) or row.carbon_g_kwh < 0):
            raise ValueError('Invalid carbon intensity')
        if i and row.start < rows[i-1].end:
            raise ValueError('Overlapping or duplicate intervals')
    eligible = [r for r in rows if r.available_at <= decision_at and r.start >= release and r.end <= deadline]
    duration = timedelta(minutes=duration_minutes)
    power_kw = (gpu_count * gpu_watts + host_watts) * pue / 1000
    candidates = []
    for i, first in enumerate(eligible):
        window = []
        for row in eligible[i:]:
            if window and window[-1].end != row.start:
                break
            window.append(row)
            elapsed = row.end - first.start
            if elapsed > duration:
                break
            if elapsed == duration:
                energies = [power_kw * (r.end-r.start).total_seconds()/3600 for r in window]
                carbon = None if any(r.carbon_g_kwh is None for r in window) else sum(e*r.carbon_g_kwh/1000 for e,r in zip(energies,window))
                candidates.append({'start_utc': first.start.isoformat(), 'end_utc': row.end.isoformat(),
                    'energy_kwh': sum(energies),
                    'energy_cost_eur': sum(e*(r.price_eur_mwh/1000+tariff_adder_eur_kwh) for e,r in zip(energies,window)),
                    'estimated_carbon_kg': carbon})
                break
    if not candidates:
        raise ValueError('No contiguous feasible window; check coverage, publication times, deadline and interval alignment')
    if objective == 'carbon' and any(c['estimated_carbon_kg'] is None for c in candidates):
        raise ValueError('Carbon objective requires complete carbon data for all feasible windows')
    key = 'energy_cost_eur' if objective == 'cost' else 'estimated_carbon_kg'
    baseline = candidates[0]
    selected = min(candidates, key=lambda c: c[key])
    savings = baseline['energy_cost_eur']-selected['energy_cost_eur']
    carbon_delta = None if baseline['estimated_carbon_kg'] is None or selected['estimated_carbon_kg'] is None else baseline['estimated_carbon_kg']-selected['estimated_carbon_kg']
    return {'mode':'simulation', 'objective':objective, 'feasible_windows':len(candidates),
        'baseline':baseline, 'selected':selected, 'energy_cost_saving_eur':savings,
        'energy_cost_saving_pct':100*savings/baseline['energy_cost_eur'] if baseline['energy_cost_eur']>0 else None,
        'estimated_carbon_saving_kg':carbon_delta,
        'assumptions':{'gpu_count':gpu_count,'gpu_watts_assumed':gpu_watts,'host_watts_assumed':host_watts,
                       'pue_assumed':pue,'tariff_adder_eur_kwh':tariff_adder_eur_kwh,
                       'capacity':'unlimited for a single job','baseline':'earliest feasible start',
                       'billing':'energy component only; excludes GPU rental, fixed fees and taxes unless in adder'}}
