# V.E.N.U.S. Week 8 — Resource Utilization Profile

This document explains how to collect host and container resource usage
evidence using the `benchmarks.resource_utilization` script added in Week 8.

For performance benchmark evidence (latency, throughput, AI evaluation) see
[Week 8 Benchmarking](week8_benchmarking.md).

---

## Overview

The resource utilization profiler collects a short-duration snapshot of:

- **Host CPU usage** (via psutil or stdlib fallback)
- **Host memory** — total / used / available / percent
- **Current Python process** — RSS, VMS, CPU (requires psutil)
- **Docker container stats** — per-service CPU %, memory usage, memory %
  for FastAPI/backend, PostgreSQL, Kafka, Zookeeper, MQTT/Mosquitto,
  and Next.js/frontend containers

Output: two timestamped files written to `benchmark_results/`

```
benchmark_results/resource_profile_YYYYMMDD_HHMMSS.json
benchmark_results/resource_profile_YYYYMMDD_HHMMSS.md
```

---

## Optional dependency — psutil

psutil is **not required** but gives richer per-process metrics (CPU %, RSS,
VMS).  Without it the script falls back to `/proc/meminfo` on Linux (or
reports N/A on Windows/macOS) and records a warning in the report.

To install (inside the backend venv):

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install psutil
```

The script will continue without psutil and note which metrics are unavailable.

---

## Running the profiler

**Basic run (15-second profile, 1-second samples):**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.resource_utilization
```

**Custom duration and interval:**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m benchmarks.resource_utilization `
  --duration 60 `
  --interval 2 `
  --base-url http://127.0.0.1:8000
```

**Custom output directory:**

```powershell
python -m benchmarks.resource_utilization `
  --duration 30 `
  --interval 1 `
  --output-dir benchmark_results
```

**CLI options:**

| Option | Default | Description |
|---|---|---|
| `--duration` | `15` | Profiling window in seconds |
| `--interval` | `1` | Seconds between host samples |
| `--base-url` | `http://127.0.0.1:8000` | URL for `/health` reachability check |
| `--output-dir` | `../benchmark_results` | Directory to write reports |

---

## Running as part of the combined benchmark suite

Add `--resource-profile` to `run_week7_benchmarks` to run the profiler after
all benchmark phases:

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
  --resource-profile-duration 30 `
  --resource-profile-interval 1
```

---

## Docker stats behavior

The script tries to detect running V.E.N.U.S. containers by matching
container names and image names against known keywords:

| Service label | Matching keywords |
|---|---|
| `fastapi_backend` | fastapi, backend, uvicorn, venus |
| `postgresql` | postgres, postgresql, pg |
| `kafka` | kafka |
| `zookeeper` | zookeeper, zk |
| `mqtt_mosquitto` | mosquitto, mqtt, emqx |
| `frontend_nextjs` | frontend, nextjs, next |

### When Docker is unavailable

| Scenario | Script behavior |
|---|---|
| Docker CLI not installed | Records a warning; continues without container stats |
| Docker daemon not running | Records a warning; continues without container stats |
| No containers match V.E.N.U.S. keywords | Records a warning; continues |
| All containers matched | Stats collected and written to report |

No exception is raised in any of these cases.  The Markdown and JSON reports
are always written, with a `warnings` section listing what was skipped.

---

## Documentation table template

Use the table below to record resource usage observed during the final
validation run.  Fill in values from the generated Markdown report.

| Resource | Metric | Observed value | Notes |
|---|---|---|---|
| Host CPU | Average % | | |
| Host CPU | Maximum % | | |
| Host memory | Average % | | |
| Host memory | Used (MB) | | |
| Host memory | Total (MB) | | |
| Docker — FastAPI/backend | CPU % | | |
| Docker — FastAPI/backend | Memory usage | | |
| Docker — PostgreSQL | CPU % | | |
| Docker — PostgreSQL | Memory usage | | |
| Docker — Kafka | CPU % | | |
| Docker — Kafka | Memory usage | | |
| Docker — Zookeeper | CPU % | | |
| Docker — Zookeeper | Memory usage | | |
| Docker — MQTT/Mosquitto | CPU % | | |
| Docker — MQTT/Mosquitto | Memory usage | | |
| Docker — Frontend/Next.js | CPU % | | |
| Docker — Frontend/Next.js | Memory usage | | |

Copy the table into your evidence folder (`evidence/week8/`) alongside a
screenshot of the Markdown report.

---

## Interpretation guidance

### CPU usage

- **< 30 %** average: healthy idle/light-load operation.
- **30–70 %**: normal under active benchmarking or simulation.
- **> 70 %** sustained: may indicate a bottleneck; note peak events.
- Compare CPU peaks during benchmark phases against idle baseline.

### Memory usage

- **< 60 %** host memory: comfortable headroom.
- **60–80 %**: system is loaded; watch for swapping.
- **> 80 %**: high pressure; OOM risk if traffic spikes further.
- PostgreSQL and Kafka typically consume the most memory in the stack.

### Docker container memory

- FastAPI/backend: typically 100–300 MB in development.
- PostgreSQL: 100–500 MB depending on cache size and row count.
- Kafka + Zookeeper combined: 500 MB–1 GB is common.
- MQTT/Mosquitto: lightweight, often < 50 MB.
- Next.js frontend: 100–200 MB at dev/build time.

### psutil not installed

If the report shows `N/A` for CPU and process metrics, install psutil and
re-run to get a richer profile for the final presentation:

```powershell
pip install psutil
python -m benchmarks.resource_utilization --duration 60
```

### Backend not reachable

The `/health` check is lightweight and non-blocking.  A failed health check
is recorded as a warning but does not stop the host/Docker collection.  Start
the backend stack before running the profiler to get a complete report.

---

## Related docs

- [Week 8 Benchmarking](week8_benchmarking.md)
- [Evidence Collection Checklist](week8_evidence_checklist.md)
- [End-to-End Validation Runbook](week8_validation.md)
- [Week 7 Evidence Pack](week7_evidence_pack.md)
