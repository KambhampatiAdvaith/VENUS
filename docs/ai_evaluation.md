# V.E.N.U.S. AI Evaluation Metrics Guide

Lightweight, repeatable tooling for evaluating the V.E.N.U.S. predictive
fault/anomaly intelligence layer.  Produces Week 7 evidence without changing
the core model, production UI, or database schema.

---

## Overview

The AI evaluation script queries the existing `predictions` table and measures
latency for the three AI endpoints (`/predictions/metrics`, `/predictions`,
and optionally `/predictions/run`).

### Honest metric scope

| Category | Available | Notes |
|---|---|---|
| Operational / descriptive | ✅ | Derived directly from model prediction outputs |
| Supervised (accuracy, precision, recall, F1, confusion matrix) | ❌ | No ground-truth fault labels exist in the schema |

Because V.E.N.U.S. does not store verified fault labels alongside predictions,
all supervised classification metrics are **unavailable by design**.  The
script reports this clearly rather than fabricating accuracy numbers.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python --version` |
| Backend running | `python -m uvicorn backend.api.main:app --reload` |
| PostgreSQL accessible | Required for DB evaluation; script degrades gracefully when unavailable |
| Kafka / MQTT | **Not required** for evaluation |
| Frontend | **Not required** for evaluation |

---

## Setup (Windows PowerShell)

```powershell
# From the repository root
cd backend
.\venv\Scripts\Activate.ps1
```

If you do not have a venv yet:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Running the evaluation

### Standalone AI evaluation (recommended for Week 7 PR #6)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.ai_evaluation_metrics --base-url http://127.0.0.1:8000
```

#### Full option list

```powershell
python -m benchmarks.ai_evaluation_metrics `
  --base-url http://127.0.0.1:8000 `
  --requests 10 `
  --output-dir ..\benchmark_results `
  --timeout 15
```

| Flag | Default | Description |
|---|---|---|
| `--base-url` | `http://127.0.0.1:8000` | Backend URL |
| `--requests` | `10` | Requests per AI endpoint for latency timing |
| `--output-dir` | `../benchmark_results` | Where report files are written |
| `--run-prediction` | off | Trigger `POST /predictions/run` once before timing (writes to DB — use sparingly) |
| `--timeout` | `15` | Per-request HTTP timeout in seconds |

### Combined Week 7 suite including AI evaluation

```powershell
python -m benchmarks.run_week7_benchmarks `
  --base-url http://127.0.0.1:8000 `
  --ai-eval
```

With all options:

```powershell
python -m benchmarks.run_week7_benchmarks `
  --base-url http://127.0.0.1:8000 `
  --requests 30 `
  --duration 30 `
  --rate 10 `
  --ai-eval `
  --ai-eval-requests 10
```

---

## macOS / Linux

Replace the PowerShell activation with:

```bash
cd backend
source venv/bin/activate
python -m benchmarks.ai_evaluation_metrics --base-url http://127.0.0.1:8000
```

---

## Metrics explained

### Prediction coverage

| Metric | Meaning |
|---|---|
| `total_predictions` | Total rows in the `predictions` table |
| `distinct_substations` | Number of unique substations that have at least one prediction |
| `earliest_prediction_timestamp` | Timestamp of the oldest prediction in the table |
| `latest_prediction_timestamp` | Timestamp of the most recent prediction |

### Anomaly detection

| Metric | Meaning |
|---|---|
| `anomaly_true_count` | Number of predictions where `anomaly = TRUE` |
| `anomaly_rate_percent` | `anomaly_true_count / total_predictions × 100` |

### Fault distribution

The `predicted_fault_distribution` field shows how many predictions were
assigned each fault class (e.g. `voltage_drop`, `overload`, `normal`).  A
healthy system with a working simulation pipeline will usually show a mix of
fault types and a significant portion of `normal` readings.

### Confidence / probability distribution

| Metric | Meaning |
|---|---|
| `avg_probability` | Mean of the model's output probability across all predictions |
| `min_probability` | Lowest output probability seen |
| `max_probability` | Highest output probability seen |
| `median_probability` | 50th-percentile probability |
| `p95_probability` | 95th-percentile probability — most predictions fall below this value |
| `high_confidence_count` | Predictions with `probability ≥ 0.8` |
| `medium_confidence_count` | Predictions with `0.5 ≤ probability < 0.8` |
| `low_confidence_count` | Predictions with `probability < 0.5` |

A well-calibrated model for binary fault detection should show most predictions
clustered near 0 (confident normal) or near 1 (confident fault), with few
values near 0.5 (uncertain).

### Anomaly score statistics

The `anomaly_score_stats` field reports descriptive statistics for the raw
Isolation Forest / XGBoost anomaly score before it is thresholded into the
boolean `anomaly` flag.

### Supervised metrics

```
supervised_metrics_available: false
reason: "No ground-truth fault labels found in repository/database schema."
```

This is the honest and expected output.  V.E.N.U.S. generates synthetic
telemetry via its simulator and does not store verified fault labels alongside
predictions.  To unlock supervised metrics in a future iteration, an operator
would need to:

1. Add a `ground_truth_fault` column to the `predictions` table (or a
   separate `labeled_predictions` table).
2. Populate it with verified fault labels for a representative sample.
3. Re-run the evaluation script — it will detect the labels and automatically
   compute accuracy, precision, recall, F1, and a confusion matrix.

---

## Output

Reports are written to `benchmark_results/` at the repository root.

| File | Description |
|---|---|
| `ai_evaluation_YYYYMMDD_HHMMSS.json` | Full evaluation data in JSON |
| `ai_evaluation_YYYYMMDD_HHMMSS.md` | Markdown summary |
| `week7_benchmark_YYYYMMDD_HHMMSS.json` | Combined report (when run via `run_week7_benchmarks --ai-eval`) |
| `week7_benchmark_YYYYMMDD_HHMMSS.md` | Combined Markdown report |

> **Note:** `benchmark_results/*.json` and `benchmark_results/*.md` are
> excluded from Git (see `.gitignore`).

---

## Compile check

```powershell
cd backend
python -m compileall benchmarks
```

Expected output:

```
Listing 'benchmarks'...
Compiling 'benchmarks/__init__.py'...
Compiling 'benchmarks/ai_evaluation_metrics.py'...
Compiling 'benchmarks/api_latency_benchmark.py'...
Compiling 'benchmarks/run_week7_benchmarks.py'...
Compiling 'benchmarks/telemetry_throughput_benchmark.py'...
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `DB unavailable: ...` | Start PostgreSQL and/or the backend; evaluation will still run endpoint latency |
| `Predictions table is empty` | Run `POST /predictions/run` once, or start the AI prediction loop with `ENABLE_AI_PREDICTION_LOOP=true` |
| `WARNING: Backend is not reachable` | Start the backend: `python -m uvicorn backend.api.main:app --reload` |
| `ModuleNotFoundError: benchmarks` | Run from the `backend/` directory, not the repo root |
| High AI endpoint latency | Expected on first call if prediction models are loading; subsequent calls should be faster |
