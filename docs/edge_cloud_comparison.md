# V.E.N.U.S. Edge vs Cloud Comparison Evidence

This Week 7 benchmark produces lightweight, repeatable evidence comparing
available **edge-side telemetry outputs** against **cloud/backend prediction
outputs** already stored by V.E.N.U.S.

It does **not** change the Docker Compose setup, Kafka/MQTT architecture,
frontend UI, or core training/prediction pipeline. It only measures and reports
what is already present.

## What it measures

- Edge telemetry coverage from `telemetry` rows:
  - `edge_anomaly`
  - `edge_anomaly_score`
  - `edge_model`
  - `edge_processed_at`
- Cloud prediction coverage from `predictions` rows:
  - `predicted_fault`
  - `probability`
  - `anomaly`
  - `anomaly_score`
  - `timestamp`
- Latest-per-substation operational comparison
- Edge/cloud recency summaries
- Optional endpoint timing for:
  - `/telemetry?limit=25`
  - `/telemetry/latest`
  - `/nodes`
  - `/predictions/metrics`
  - `/predictions`

## Important caveat

> **Agreement is not supervised accuracy.**
>
> This benchmark compares the latest edge anomaly boolean and latest cloud
> anomaly boolean for each substation where both exist. That yields
> **operational agreement/disagreement**, but it is **not** accuracy, precision,
> recall, or F1 unless paired ground-truth labels are added later.

## Windows PowerShell

Standalone report:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.edge_cloud_comparison --base-url http://127.0.0.1:8000
```

Combined Week 7 suite with optional edge/cloud evidence:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --edge-cloud
```

## Output

Reports are written to the existing ignored `benchmark_results/` directory:

- `benchmark_results/edge_cloud_comparison_YYYYMMDD_HHMMSS.json`
- `benchmark_results/edge_cloud_comparison_YYYYMMDD_HHMMSS.md`

The combined runner also writes:

- `benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.json`
- `benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.md`

## Behavior when services/data are missing

- **Backend unavailable**: DB-only evaluation still runs; endpoint timing is
  skipped with a clear note.
- **DB unavailable**: the script still writes a report explaining DB metrics are
  unavailable.
- **Empty telemetry/predictions tables**: the script writes coverage output and
  clearly states that paired comparison is unavailable.
