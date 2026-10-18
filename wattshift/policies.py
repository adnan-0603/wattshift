"""Reproducible independent-job replay; forecast decisions vs realized costs."""
import numpy as np
import pandas as pd
from .scheduling import best_start


def replay(prices,predicted,carbon=None,predicted_carbon=None,seed=42,count=48):
    prices=np.asarray(prices,dtype=float);predicted=np.asarray(predicted,dtype=float)
    if len(prices)!=len(predicted):raise ValueError('Signals must align')
    n=len(prices)
    if n<24:raise ValueError('At least 24 hourly intervals required')
    rng=np.random.default_rng(seed);jobs=[]
    for j in range(count):
        duration=int(rng.choice([1,2,4,6]));release=int(rng.integers(0,n-24+1));slack=int(rng.choice([0,4,8,12,18]))
        deadline=min(n,release+duration+slack);gpus=int(rng.choice([1,2,4,8]))
        kw=(gpus*.3+.1)*1.2
        schedules={'immediate':release,'cheapest':best_start(predicted,release,deadline,duration),
                   'greenest':best_start(predicted_carbon,release,deadline,duration) if predicted_carbon is not None else None,
                   'oracle':best_start(prices,release,deadline,duration)}
        outcomes={}
        for name,start in schedules.items():
            if start is None:outcomes[name]=None;continue
            real=prices[start:start+duration]
            if not np.isfinite(real).all():outcomes[name]=None;continue
            co=None
            if carbon is not None:
                vals=np.asarray(carbon[start:start+duration],dtype=float)
                if np.isfinite(vals).all():co=float(vals.sum()*kw/1000)
            outcomes[name]={'start_slot':start,'end_slot':start+duration,'cost_eur':float(real.sum()*kw/1000),'carbon_kg':co}
        jobs.append({'id':f'batch-{j+1:03d}','release_slot':release,'deadline_slot':deadline,'duration_hours':duration,'gpus':gpus,'assumed_kw':kw,'policies':outcomes})
    totals={}
    for name in ('immediate','cheapest','greenest','oracle'):
        matched=[j for j in jobs if j['policies'][name] and j['policies']['immediate']]
        base=sum(j['policies']['immediate']['cost_eur'] for j in matched)
        cost=sum(j['policies'][name]['cost_eur'] for j in matched)
        co=[j['policies'][name]['carbon_kg'] for j in matched]
        baseco=[j['policies']['immediate']['carbon_kg'] for j in matched]
        totals[name]={'jobs':len(matched),'unavailable_jobs':count-len(matched),'cost_eur':cost if matched else None,
                      'baseline_cost_eur':base if matched else None,'saving_eur':base-cost if matched else None,
                      'saving_pct':100*(base-cost)/base if base>0 else None,
                      'carbon_kg':sum(co) if matched and all(x is not None for x in co) else None,
                      'carbon_saving_kg':sum(baseco)-sum(co) if matched and all(x is not None for x in co+baseco) else None}
    matched=[j for j in jobs if j['policies']['cheapest'] and j['policies']['oracle']]
    regret=sum(j['policies']['cheapest']['cost_eur']-j['policies']['oracle']['cost_eur'] for j in matched)
    return {'mode':'retrospective simulation','seed':seed,'requested_jobs':count,'totals':totals,'jobs':jobs,
            'regret_eur_vs_hindsight':regret,'assumptions':'Independent jobs, unlimited capacity, constant GPU/host watts, no rental/idle/checkpoint fees; 1-hour evaluation slots. Predicted price decisions evaluated against actual holdout prices. Oracle is hindsight only.'}
