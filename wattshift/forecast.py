"""Calendar + lagged-price quantiles. All feature values >=14 days behind target."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_pinball_loss


def load_prices(path):
    frame=pd.read_csv(path)
    frame.index=pd.to_datetime(frame.pop('start_utc'),utc=True,format='mixed')
    if frame.index.has_duplicates:raise ValueError('Duplicate prices')
    frame['price_eur_mwh']=pd.to_numeric(frame['price_eur_mwh'],errors='raise')
    return frame.sort_index()


def features(series,targets):
    local=targets.tz_convert('Europe/Berlin')
    X=pd.DataFrame(index=targets)
    X['hour_sin']=np.sin(2*np.pi*local.hour/24);X['hour_cos']=np.cos(2*np.pi*local.hour/24)
    X['weekday']=local.dayofweek;X['month']=local.month;X['weekend']=(local.dayofweek>=5).astype(int)
    for days in (14,21,28):
        X[f'lag_{days}d']=series.reindex(targets-pd.Timedelta(days=days)).to_numpy()
    return X


def predict(history,origin,days=7,n_estimators=100):
    origin=pd.Timestamp(origin);origin=origin.tz_localize('UTC') if origin.tzinfo is None else origin.tz_convert('UTC')
    if not 1<=days<=7:raise ValueError('Horizon must be 1 to 7 days')
    # Never train on or use values at/after issue time, even if passed by caller.
    series=history.loc[history.index<origin,'price_eur_mwh'].resample('h').mean()
    targets=pd.date_range(origin,periods=days*24,freq='h')
    X=features(series,series.index);valid=X.notna().all(axis=1)&series.notna()
    future=features(series,targets)
    baseline=series.reindex(targets-pd.Timedelta(days=7)).to_numpy()
    result=pd.DataFrame({'baseline':baseline},index=targets)
    if valid.sum()<168 or future.isna().any().any():
        result['p10']=np.nan;result['p50']=baseline;result['p90']=np.nan
        return result,{'model':'seasonal_baseline','issue_time':origin.isoformat(),'training_rows':int(valid.sum()),'reason':'insufficient complete lag history for quantile model'}
    for q in (.1,.5,.9):
        model=LGBMRegressor(objective='quantile',alpha=q,n_estimators=n_estimators,num_leaves=15,
                           learning_rate=.05,min_child_samples=24,verbosity=-1,n_jobs=2,random_state=42)
        model.fit(X.loc[valid],series.loc[valid])
        result[f'p{int(q*100)}']=model.predict(future)
    # Rearrangement prevents crossing but does not establish interval calibration.
    result[['p10','p50','p90']]=np.sort(result[['p10','p50','p90']].to_numpy(),axis=1)
    return result,{'model':'LightGBM quantile','issue_time':origin.isoformat(),'training_rows':int(valid.sum()),'features':list(X),'quantiles':[.1,.5,.9],'interval':'uncalibrated P10–P90; empirical coverage reported separately'}


def backtest(history,days=7):
    end=history.index.max().floor('D')+pd.Timedelta(days=1)
    origin=end-pd.Timedelta(days=days)
    predictions,meta=predict(history,origin,days)
    actual=history.price_eur_mwh.resample('h').mean().reindex(predictions.index)
    valid=actual.notna()&predictions.p50.notna()&predictions.baseline.notna()
    if not valid.any():raise ValueError('No aligned holdout rows')
    y=actual[valid];p=predictions.loc[valid]
    metrics={'origin':origin.isoformat(),'holdout_end':end.isoformat(),'rows':int(valid.sum()),
             'model_mae_eur_mwh':float(mean_absolute_error(y,p.p50)),
             'baseline_mae_eur_mwh':float(mean_absolute_error(y,p.baseline)),
             'p10_p90_coverage':None if p.p10.isna().any() else float(((y>=p.p10)&(y<=p.p90)).mean()),
             'pinball':{str(q):float(mean_pinball_loss(y,p[f'p{int(q*100)}'],alpha=q)) for q in (.1,.5,.9)} if not p.p10.isna().any() else {},
             'limitation':'One final seven-day holdout; not exhaustive rolling-origin validation or tuned production accuracy',**meta}
    predictions['actual']=actual
    return predictions,metrics
