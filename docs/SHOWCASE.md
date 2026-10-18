# Showcase kit

## Recruiter story

WattShift explores whether flexible AI batch work can run in cheaper electricity windows. It combines real German market data, probabilistic forecasting, a scheduling simulation and a Kubernetes implementation with an application checkpoint worker. A React Console explains the trade-offs, while Prometheus and Grafana are prepared for operations. The measured local evidence is a 48-job historical simulation and CPU checkpoint/resume correctness; live cluster and GPU validation are still outstanding.

## CV sentence

Built WattShift, an energy-aware workload scheduling prototype using German SMARD data, LightGBM, FastAPI, React and Kubernetes/Kueue manifests; a 48-job held-out simulation reduced wholesale energy cost by 7.78%, with checkpoint/resume correctness verified locally on CPU.

## 60-second pitch

GPU workloads often have deadlines without needing to start immediately. WattShift asks what happens if we use that flexibility. I ingested real German prices and generation, built a quantile price forecast, and compared immediate, cheap-hour and carbon-aware scheduling on exactly the same jobs. The forecast policy saved 7.78% of simulated energy cost in one held-out week. Carbon savings were much smaller, and the simple green policy actually worsened carbon, so I show that limitation rather than hide it. The Console lets people inspect prices, forecasts, jobs, savings and a retrospective calculator. The infrastructure includes Kubernetes, Kueue, Prometheus and Grafana. A real CPU process survived interruption and resumed to exactly the same final result. Live cluster acceptance and actual GPU watts remain the next validation gates.

## Three-image carousel

Use `docs/assets/price-carbon.png`, `architecture.png`, `comparison.png` in that order. They are original plots/diagrams from this project, not screenshots of a deployed system. Caption: “Same compute, flexible timing. Actual German prices; a transparent forecast-based simulation; honest carbon trade-offs.” Include the one-week/48-job scope next to the result. No posts were published.

## Portfolio embed

After Pages has actually deployed, replace YOUR_PAGES_URL below with the resulting URL. Do not present a placeholder as a live link.

```html
<iframe src="YOUR_PAGES_URL" title="WattShift Console" style="width:100%;height:900px;border:0" loading="lazy"></iframe>
```

A standalone link is preferable on a narrow mobile screen. The same static build works under a GitHub repository subpath because its base is relative.

## Video

`docs/assets/evidence-walkthrough.mp4` is a two-minute captioned walkthrough of source data, model results and actual local checkpoint evidence. It is not a recording of Console interactions or a live cluster. The full live demonstration required by the original plan remains pending until the cluster acceptance gate passes. Suggested live recording: 20s Today, 20s Forecast, 25s calculator, 20s Savings, 25s real Kueue pause/resume, 10s Grafana and limitations.
