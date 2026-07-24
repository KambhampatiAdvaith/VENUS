# V.E.N.U.S. Week 8 — Final Performance Benchmarking

This document explains how to produce final Week 8 performance benchmark
evidence by running the existing Week 7 benchmark scripts.  No new benchmark
infrastructure is needed — the scripts added in Week 7 are re-run (or their
saved reports are reused) for final sign-off.

For resource utilization evidence (CPU, memory, Docker containers) see
[Week 8 Resource Profile](week8_resource_profile.md).

---

## Overview

| Script | Evidence it produces |
|---|---|
| `benchmarks.api_latency_benchmark` | API endpoint latency (min / avg / median / P95 / max) |
| `benchmarks.telemetry_throughput_benchmark` | Telemetry simulate throughput and DB row growth |
| `benchmarks.ai_evaluation_metrics` | AI prediction counts, anomaly rate, probability stats |
| `benchmarks.edge_cloud_comparison` | Edge vs cloud coverage, recency gap, agreement rate |
| `benchmarks.run_week7_benchmarks` | Combined report running all four phases above |

All reports are written to `benchmark_results/` (already in `.gitignore`).

---

## Prerequisites

1. Backend running:

   ```powershell
   cd backend
   .\venv\Scripts\Activate.ps1
   python -m uvicorn backend.api.main:app --reload
   ```

2. PostgreSQL accessible (required for the backend to start).

3. Kafka / MQTT are optional — benchmarks degrade gracefully if unavailable.

---

## Running individual benchmark scripts

### API Latency Benchmark

Measures HTTP response latency across all dashboard-critical endpoints.

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.api_latency_benchmark --base-url http://127.0.0.1:8000 --requests 50
```

**Output files:**

```
benchmark_results/api_latency_YYYYMMDD_HHMMSS.json
benchmark_results/api_latency_YYYYMMDD_HHMMSS.md
```

**Success criteria:**

| Metric | Target |
|---|---|
| Average latency | < 200 ms for read endpoints |
| P95 latency | < 500 ms |
| Success rate | ≥ 95 % |
| Errors | 0 for critical paths (`/telemetry/latest`, `/dashboard/metrics`) |

---

### Telemetry Throughput Benchmark

Sends telemetry simulation requests at a target rate and measures observed
throughput and database row growth.

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.telemetry_throughput_benchmark `
  --base-url http://127.0.0.1:8000 `
  --duration 30 `
  --rate 10
```

**Output files:**

```
benchmark_results/telemetry_throughput_YYYYMMDD_HHMMSS.json
benchmark_results/telemetry_throughput_YYYYMMDD_HHMMSS.md
```

**Success criteria:**

| Metric | Target |
|---|---|
| Observed rate | ≥ 80 % of target rate |
| Average simulate latency | < 300 ms |
| DB rows inserted | > 0 (confirms end-to-end write path) |
| Success rate | ≥ 90 % |

---

### AI Evaluation Report

Evaluates AI prediction quality from the stored database predictions.

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.ai_evaluation_metrics `
  --base-url http://127.0.0.1:8000 `
  --requests 20
```

**Output files:**

```
benchmark_results/ai_evaluation_YYYYMMDD_HHMMSS.json
benchmark_results/ai_evaluation_YYYYMMDD_HHMMSS.md
```

**Success criteria:**

| Metric | Target |
|---|---|
| Total predictions evaluated | > 0 |
| Anomaly rate | Plausible range 5–40 % depending on simulation scenario |
| Avg probability | > 0 (model is producing scores) |
| High-confidence count | > 0 |

---

### Edge vs Cloud Comparison Report

Compares edge anomaly detection outputs against cloud XGBoost predictions.

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.edge_cloud_comparison `
  --base-url http://127.0.0.1:8000 `
  --requests 20
```

**Output files:**

```
benchmark_results/edge_cloud_comparison_YYYYMMDD_HHMMSS.json
benchmark_results/edge_cloud_comparison_YYYYMMDD_HHMMSS.md
```

**Success criteria:**

| Metric | Target |
|---|---|
| DB available | True |
| Edge substations covered | > 0 |
| Cloud substations covered | > 0 |
| Operational agreement rate | ≥ 50 % (both models agree on normal/fault direction) |
| Latest edge age (s) | < 120 (recent data present) |

---

## Running the combined Week 7 benchmark suite

The combined runner executes all phases in sequence and writes a single
summary report.

**Minimal run (API latency + throughput only):**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.run_week7_benchmarks `
  --base-url http://127.0.0.1:8000 `
  --requests 30 `
  --duration 30
```

**Full run including AI evaluation and edge/cloud comparison:**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.run_week7_benchmarks `
  --base-url http://127.0.0.1:8000 `
  --requests 30 `
  --duration 30 `
  --ai-eval `
  --ai-eval-requests 20 `
  --edge-cloud `
  --edge-cloud-requests 20
```

**Full run including resource utilization profiling (Week 8):**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.run_week7_benchmarks `
  --base-url http://127.0.0.1:8000 `
  --requests 30 `
  --duration 30 `
  --ai-eval `
  --edge-cloud `
  --resource-profile `
  --resource-profile-duration 15 `
  --resource-profile-interval 1
```

**Output files:**

```
benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.json
benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.md
```

---

## Expected report files under `benchmark_results/`

After running the full suite the following files will be present:

```
benchmark_results/
  api_latency_YYYYMMDD_HHMMSS.json
  api_latency_YYYYMMDD_HHMMSS.md
  telemetry_throughput_YYYYMMDD_HHMMSS.json
  telemetry_throughput_YYYYMMDD_HHMMSS.md
  ai_evaluation_YYYYMMDD_HHMMSS.json
  ai_evaluation_YYYYMMDD_HHMMSS.md
  edge_cloud_comparison_YYYYMMDD_HHMMSS.json
  edge_cloud_comparison_YYYYMMDD_HHMMSS.md
  week7_benchmark_YYYYMMDD_HHMMSS.json
  week7_benchmark_YYYYMMDD_HHMMSS.md
  resource_profile_YYYYMMDD_HHMMSS.json    ← Week 8 addition
  resource_profile_YYYYMMDD_HHMMSS.md      ← Week 8 addition
```

All files are git-ignored; they exist only on the developer's machine.

---

## Reusing Week 7 reports for Week 8 evidence

If you already ran the Week 7 benchmarks and the data has not changed you can
reuse the existing report files directly as Week 8 evidence.  No re-run is
required unless:

- The backend API or data model changed since the reports were generated.
- The reports are missing from `benchmark_results/`.
- Significantly more data has been ingested and a fresh evaluation is desired.

---

## Related docs

- [Week 8 Resource Profile](week8_resource_profile.md)
- [Evidence Collection Checklist](week8_evidence_checklist.md)
- [End-to-End Validation Runbook](week8_validation.md)
- [Week 7 Evidence Pack](week7_evidence_pack.md)
