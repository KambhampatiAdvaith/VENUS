# V.E.N.U.S. Week 7 Benchmark Guide

Lightweight benchmark scripts that measure the V.E.N.U.S. telemetry pipeline
**throughput** and **API responsiveness** without modifying production code.

For AI evaluation metrics (prediction/anomaly/confidence distributions and AI
endpoint latency), see [`docs/ai_evaluation.md`](ai_evaluation.md).

For Edge vs Cloud comparison evidence, see
[`docs/edge_cloud_comparison.md`](edge_cloud_comparison.md).

For the final Week 7 demo order, screenshot checklist, and consolidated
PowerShell runbook, see [`docs/week7_evidence_pack.md`](week7_evidence_pack.md).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10+ | `python --version` |
| Backend running | `python -m uvicorn backend.api.main:app --reload` |
| PostgreSQL accessible | Required for the backend to start |
| Kafka / MQTT | **Optional** — benchmarks skip gracefully when unavailable |
| Frontend | **Not required** for benchmarks |

---

## Setup (Windows PowerShell)

```powershell
# From the repository root
cd backend
.\venv\Scripts\Activate.ps1
```

If you don't have a venv yet:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## Running benchmarks

### All Week 7 benchmarks (recommended)

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --duration 30
```

This runs both the API latency benchmark and the telemetry throughput benchmark,
then writes a combined summary to `benchmark_results/`.

Optional Week 7 evidence modules can be enabled explicitly:

```powershell
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --ai-eval
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --edge-cloud
```

#### Full option list

```powershell
python -m benchmarks.run_week7_benchmarks `
  --base-url http://127.0.0.1:8000 `
  --requests 50 `
  --duration 30 `
  --rate 10 `
  --output-dir ..\benchmark_results
```

| Flag | Default | Description |
|---|---|---|
| `--base-url` | `http://127.0.0.1:8000` | Backend URL |
| `--requests` | `30` | Requests per API endpoint |
| `--duration` | `30` | Throughput benchmark duration (seconds) |
| `--rate` | `10` | Target simulate req/s (keep ≤ 20 on local machines) |
| `--output-dir` | `../benchmark_results` | Where report files are written |
| `--ai-eval` | disabled | Add AI evaluation evidence |
| `--ai-eval-requests` | `10` | Requests per AI endpoint when `--ai-eval` is used |
| `--edge-cloud` | disabled | Add Edge vs Cloud comparison evidence |
| `--edge-cloud-requests` | `10` | Requests per endpoint when `--edge-cloud` is used |

---

### API latency only

```powershell
python -m benchmarks.api_latency_benchmark --base-url http://127.0.0.1:8000 --requests 50
```

Measures latency (min / avg / median / p95 / max) for each dashboard-critical endpoint:

- `/dashboard/metrics`
- `/telemetry?limit=25`
- `/telemetry/latest`
- `/telemetry/latency`
- `/nodes`
- `/load-balancing?limit=8`

---

### Telemetry throughput only

```powershell
python -m benchmarks.telemetry_throughput_benchmark --duration 30 --rate 20
```

Measures:
- Simulated telemetry publish rate (via `/telemetry/simulate/normal`)
- Database row growth (rows/sec) when a `/telemetry/count` endpoint is available

---

## Output

Reports are written to `benchmark_results/` at the repository root.

| File | Description |
|---|---|
| `api_latency_YYYYMMDD_HHMMSS.json` | Full API latency data in JSON |
| `api_latency_YYYYMMDD_HHMMSS.md` | Markdown summary table |
| `telemetry_throughput_YYYYMMDD_HHMMSS.json` | Throughput data in JSON |
| `telemetry_throughput_YYYYMMDD_HHMMSS.md` | Throughput Markdown summary |
| `week7_benchmark_YYYYMMDD_HHMMSS.json` | Combined Week 7 report (JSON) |
| `week7_benchmark_YYYYMMDD_HHMMSS.md` | Combined Week 7 report (Markdown) |
| `ai_evaluation_YYYYMMDD_HHMMSS.json` | AI evaluation metrics report (JSON) |
| `ai_evaluation_YYYYMMDD_HHMMSS.md` | AI evaluation metrics report (Markdown) |
| `edge_cloud_comparison_YYYYMMDD_HHMMSS.json` | Edge vs Cloud comparison report (JSON) |
| `edge_cloud_comparison_YYYYMMDD_HHMMSS.md` | Edge vs Cloud comparison report (Markdown) |

> **Note:** `benchmark_results/*.json` and `benchmark_results/*.md` are excluded
> from Git (see `.gitignore`).

---

## AI evaluation metrics (Week 7 PR #6)

```powershell
python -m benchmarks.ai_evaluation_metrics --base-url http://127.0.0.1:8000
```

Or include in the combined suite:

```powershell
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --ai-eval
```

See [`docs/ai_evaluation.md`](ai_evaluation.md) for full documentation.

---

## Edge vs Cloud comparison evidence (Week 7 PR #7)

```powershell
python -m benchmarks.edge_cloud_comparison --base-url http://127.0.0.1:8000
```

Or include in the combined suite:

```powershell
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --edge-cloud
```

See [`docs/edge_cloud_comparison.md`](edge_cloud_comparison.md) for full
documentation and caveats about operational agreement vs supervised accuracy.

---

## macOS / Linux

Replace the PowerShell activation with:

```bash
cd backend
source venv/bin/activate
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --duration 30
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ERROR: Cannot reach .../health` | Start the backend first (see Prerequisites) |
| `ModuleNotFoundError: benchmarks` | Run from the `backend/` directory, not the repo root |
| All requests fail on `/nodes` | First request may be slow while indexes are created after a fresh DB migration — wait a moment and retry |
| High latency on `/nodes` (>1 s) | Ensure Postgres has the `idx_telemetry_substation_database_written_at` index (created automatically on startup) |
