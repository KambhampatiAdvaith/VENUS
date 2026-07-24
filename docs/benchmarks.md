# V.E.N.U.S. Week 7 Benchmark Guide

Lightweight benchmark scripts that measure the V.E.N.U.S. telemetry pipeline
**throughput** and **API responsiveness** without modifying production code.

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

> **Note:** `benchmark_results/*.json` and `benchmark_results/*.md` are excluded
> from Git (see `.gitignore`).

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
