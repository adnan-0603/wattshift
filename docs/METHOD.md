# Data, modeling and reproducibility

## Source and units

SMARD/Bundesnetzagentur observations are retrieved through `https://www.smard.de/app/chart_data`. Price filter 4169; generation mappings are in `wattshift/ingest.py`. A retrieved dataset includes CSV, generation when requested, provenance timestamps, requested/actual coverage, resolution and SHA-256. CC BY 4.0 attribution remains visible. There is no ENTSO-E token/integration in this candidate: SMARD provides the German price and generation inputs. ENTSO-E is a potential independent validation source, not a claimed active integration.

2024 history has 8,784 hourly observations (leap year); recent observations retain quarter-hour bounds. UTC timestamps are canonical; display uses Europe/Berlin including DST. Generation values are MWh per interval, not MW. kWh = kW × hours; € = kWh × €/MWh / 1,000. No hourly data is silently described as measured quarter-hour data. The saved 2024 series is retrospective: publication timestamps and revisions are not archived by this adapter.

Regenerate using `python -m wattshift.ingest --start 2024-01-01 --end 2025-01-01 --resolution hour --out data/historical`; add `--generation` for selected weeks. The bundled summer and winter windows provide carbon coverage. `make export` trains/evaluates and rebuilds the Console contract. `python scripts/assets.py` regenerates scientific figures and GIF (install matplotlib/Pillow for showcase generation).

## Carbon

The proxy is sum(generation × factor)/sum(included generation), in gCO₂e/kWh. Factors and explicit approximations are versioned in `config/emissions.json`, based on IPCC AR5 WGIII Annex III lifecycle medians. Lignite uses coal's median; other conventional and other renewable categories use explicit assumed factors. Imports and pumped storage are excluded. Unknown categories remain unknown; nuclear absence after 2023-04-16 is treated as structural zero. This is neither consumption-based intensity nor marginal avoided emissions. Ex-post carbon is never sold as a known future signal.

## Forecast and decision experiment

LightGBM fits quantiles 0.1, 0.5, 0.9 using calendar terms and 14/21/28-day price lags. Training data end before issue time. A seasonal baseline is retained for comparison and short-history fallback. Quantiles are sorted to avoid crossing; sorting is not calibration. Seven days are served, but D+1 is marked published only when real source intervals cover the full hour. Source availability and model issue time are visible. The Forecast page carbon overlay uses a separate prior-14-day hourly carbon profile (UTC hour), trained strictly before issue time; it is an unvalidated baseline, and missing coverage stays N/A. It is not the lag-week proxy used in the held-out simulation.

A single chronological holdout spans 2024-12-25 00:00 UTC to 2025-01-01 00:00 UTC. The simulator uses the same 48 jobs (seed42) across policies, with 1/2/4/6-hour durations, GPU counts1/2/4/8 and slack0/4/8/12/18h. All compared starts satisfy release/deadline and all required intervals. Cheapest uses forecast prices; greenest uses previous-week carbon as a deliberately simple forecast proxy. Oracle uses actual future prices and is explicitly hindsight. Jobs are independent with unlimited capacity; queuing, checkpoint overhead, actual GPU utilization, cloud rental and idle power are omitted. No causal emissions claim is justified.

The calculator is a different, retrospective experiment: it chooses the cheapest/lowest-carbon feasible window using actual 2024 observations. It must not be confused with forecast-policy performance. Spring/autumn lack bundled carbon and display N/A. Winter and summer include selected generation windows. Facility watts are assumed, not sampled.

## Honest limitations and next experiments

Use rolling-origin backtests across seasons before generalizing the headline. Add publication-vintage archives, tariff/rental models, capacity-constrained scheduling and checkpoint overhead before a production claim. Validate consumption-based carbon and uncertainty separately. The API is intended for a local demo; external production hosting needs authentication, resource hardening, backups and operational ownership. Sources are official SMARD data, [IPCC factors](https://www.ipcc.ch/site/assets/uploads/2018/02/ipcc_wg3_ar5_annex-iii.pdf), [Kueue Workload lifecycle](https://kueue.sigs.k8s.io/docs/concepts/workload/), and [NVIDIA DCGM exporter](https://github.com/NVIDIA/dcgm-exporter).
