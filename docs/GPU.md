# Phase 8: real GPU measurement

Measurement tooling is implemented; **no GPU was available and no cloud GPU was rented**. There are no measured watts or power-cap savings in the headline. GPU sampling requires an NVIDIA driver and `nvidia-smi`; DCGM additionally needs a GPU-capable Kubernetes node and the NVIDIA device plugin. A CPU-only kind cluster is insufficient.

1. Run one repeatable representative training workload, with its dataset/checkpoint fixed. Record device model, batch size, precision, completed work and wall time.
2. Run `python -m wattshift.gpu --seconds 60 --output reports/gpu.csv`. Raw samples and a JSON trapezoidal energy integral are written. It measures GPU energy only; host and cooling energy are excluded.
3. For an explicitly chosen device cap, run `python scripts/power_cap_compare.py --gpu 0 --cap-watts VALUE --seconds 60`, replacing VALUE with a supported limit for your device. This command changes the cap and restores the original in `finally`; it requires device permissions. Use matched completed work, not merely matched sampling duration, to compare efficiency. A killed host cannot guarantee restoration: verify the device cap after an interrupted experiment.
4. On a GPU cluster, apply `infra/kubernetes/dcgm-optional.yaml` only after configuring drivers/device plugin and the `nvidia.com/gpu.present=true` node label. The pinned official exporter is optional; validate its compatibility with your driver before deployment.
5. Add the following scrape job to the Prometheus ConfigMap, restart Prometheus, and verify `up{job="dcgm"}` before adding a measured panel:

```yaml
- job_name: dcgm
  static_configs:
    - targets: ['wattshift-dcgm:9400']
```

Use `DCGM_FI_DEV_POWER_USAGE` for measured GPU watts. Keep it separate from `wattshift_assumed_job_power_watts`, which is simulated facility power. Record energy per completed job and throughput under both caps before changing the simulator's 300 W assumption. Rental charges and minimum billing intervals must be measured separately from electricity estimates.
