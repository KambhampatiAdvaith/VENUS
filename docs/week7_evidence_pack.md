# V.E.N.U.S. Week 7 Evidence Pack

This document is the final Week 7 runbook for generating presentation evidence
without changing the production architecture. It consolidates the real-time
dashboard, latency, benchmark, AI evaluation, edge-vs-cloud, and reliability
deliverables added across Week 7 PRs #3-#8.

## Week 7 deliverables at a glance

| Area | What it proves | Implementation / docs |
|---|---|---|
| Real-time WebSocket dashboard updates | The dashboard can refresh from live backend events instead of only manual reloads | [`backend/backend/api/routes/websocket.py`](../backend/backend/api/routes/websocket.py), [`backend/backend/api/live_broadcast.py`](../backend/backend/api/live_broadcast.py), [`backend/backend/api/ws_manager.py`](../backend/backend/api/ws_manager.py), [`frontend/components/LiveUpdateBanner.tsx`](../frontend/components/LiveUpdateBanner.tsx), [`frontend/services/websocket.ts`](../frontend/services/websocket.ts) |
| Latency measurement and timestamp normalization | Telemetry freshness and latency are based on consistent timestamp handling and a dedicated latency endpoint | [`backend/backend/api/routes/telemetry.py`](../backend/backend/api/routes/telemetry.py), [`backend/backend/api/schemas.py`](../backend/backend/api/schemas.py), [`frontend/services/api.ts`](../frontend/services/api.ts), [`frontend/services/timestamps.ts`](../frontend/services/timestamps.ts), [`frontend/app/dashboard/page.tsx`](../frontend/app/dashboard/page.tsx) |
| Throughput / scalability benchmarks | The backend can produce repeatable API latency and telemetry throughput evidence | [`backend/benchmarks/api_latency_benchmark.py`](../backend/benchmarks/api_latency_benchmark.py), [`backend/benchmarks/telemetry_throughput_benchmark.py`](../backend/benchmarks/telemetry_throughput_benchmark.py), [`backend/benchmarks/run_week7_benchmarks.py`](../backend/benchmarks/run_week7_benchmarks.py), [`docs/benchmarks.md`](benchmarks.md) |
| AI evaluation metrics | Week 7 reports describe available AI metrics honestly and measure AI endpoint latency without changing models | [`backend/benchmarks/ai_evaluation_metrics.py`](../backend/benchmarks/ai_evaluation_metrics.py), [`docs/ai_evaluation.md`](ai_evaluation.md) |
| Edge vs Cloud comparison | The system can report operational agreement, coverage, and recency between edge telemetry and cloud predictions | [`backend/benchmarks/edge_cloud_comparison.py`](../backend/benchmarks/edge_cloud_comparison.py), [`docs/edge_cloud_comparison.md`](edge_cloud_comparison.md) |
| Reliability / retry / logging | Kafka, MQTT, simulator, prediction, and DB integrations log failures clearly and retry with bounded backoff | [`backend/backend/utils/logging.py`](../backend/backend/utils/logging.py), [`backend/backend/kafka/telemetry_consumer.py`](../backend/backend/kafka/telemetry_consumer.py), [`backend/backend/kafka/fault_consumer.py`](../backend/backend/kafka/fault_consumer.py), [`backend/backend/kafka/producer.py`](../backend/backend/kafka/producer.py), [`backend/backend/mqtt/mqtt_to_kafka_bridge.py`](../backend/backend/mqtt/mqtt_to_kafka_bridge.py), [`docs/reliability.md`](reliability.md) |

## Windows PowerShell runbook

### 1. Start the backend for a local Week 7 demo

This keeps Kafka and MQTT optional while still allowing local screenshots,
benchmarks, AI evaluation, and reliability-log capture.

```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:ENABLE_STARTUP_TELEMETRY_SIMULATOR="true"
$env:ENABLE_AI_PREDICTION_LOOP="true"
$env:ENABLE_KAFKA_TELEMETRY_CONSUMER="false"
$env:ENABLE_KAFKA_FAULT_CONSUMER="false"
python -m uvicorn backend.api.main:app --reload
```

If you want to capture structured logs to a file at the same time:

```powershell
python -m uvicorn backend.api.main:app --reload 2>&1 | Tee-Object -FilePath .\backend.log
```

Optional: enable real Kafka-backed live ingestion only when your brokers are
already available.

```powershell
$env:ENABLE_KAFKA_TELEMETRY_CONSUMER="true"
$env:ENABLE_KAFKA_FAULT_CONSUMER="true"
```

### 2. Verify the backend is reachable

```powershell
(Invoke-WebRequest http://127.0.0.1:8000/health).Content
```

Expected healthy response:

```json
{"status":"healthy","database":"connected"}
```

### 3. Optional simulator and data warm-up

If the dashboard tables are empty, or benchmark scripts report no telemetry yet,
either leave the startup simulator enabled for a minute or trigger one manual
cycle:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/telemetry/simulate/normal
```

If predictions are empty, trigger a manual prediction pass once:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/predictions/run
```

### 4. Run the combined Week 7 benchmark suite

```powershell
python -m benchmarks.run_week7_benchmarks `
  --base-url http://127.0.0.1:8000 `
  --duration 30 `
  --ai-eval `
  --edge-cloud
```

This is the fastest way to produce one combined Week 7 benchmark report plus the
optional AI-evaluation and edge/cloud sections.

### 5. Run standalone evidence scripts when needed

AI evaluation only:

```powershell
python -m benchmarks.ai_evaluation_metrics --base-url http://127.0.0.1:8000
```

Edge vs Cloud comparison only:

```powershell
python -m benchmarks.edge_cloud_comparison --base-url http://127.0.0.1:8000
```

### 6. Inspect reliability logs

Follow the log file live:

```powershell
Get-Content .\backend.log -Wait
```

Filter for structured reliability-related lines:

```powershell
Select-String -Path .\backend.log -Pattern "backend.kafka","backend.mqtt","backend.api.telemetry_simulator","backend.ai.predict","WARNING","ERROR"
```

## Suggested report files to capture from `benchmark_results/`

- `benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.md`
- `benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.json`
- `benchmark_results/ai_evaluation_YYYYMMDD_HHMMSS.md`
- `benchmark_results/edge_cloud_comparison_YYYYMMDD_HHMMSS.md`
- `benchmark_results/api_latency_YYYYMMDD_HHMMSS.md`
- `benchmark_results/telemetry_throughput_YYYYMMDD_HHMMSS.md`

The most presentation-friendly files are usually the `*.md` summaries, with the
matching `*.json` files kept as raw evidence.

## Screenshot / evidence checklist

- [ ] Dashboard screenshot showing live updates active and recent telemetry rows
- [ ] `/health` screenshot or captured PowerShell output
- [ ] Combined Week 7 benchmark Markdown report screenshot or file
- [ ] AI evaluation Markdown report screenshot or file
- [ ] Edge vs Cloud Markdown report screenshot or file
- [ ] Reliability log screenshot showing structured `timestamp | component | level | message` output

## Final demo flow

1. Open a PowerShell terminal in `backend/` and start the API with the startup
   simulator enabled.
2. Confirm the backend is healthy with `Invoke-WebRequest` against `/health`.
3. Open the dashboard and wait for recent telemetry rows to appear.
4. Capture a screenshot showing the live-update indicator and fresh telemetry.
5. If the dashboard is empty, trigger `POST /telemetry/simulate/normal` and
   refresh once after a few seconds.
6. If prediction panels are empty, trigger `POST /predictions/run` once or
   restart with `$env:ENABLE_AI_PREDICTION_LOOP="true"`.
7. Run `python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --duration 30 --ai-eval --edge-cloud`.
8. Open the generated Markdown files in `benchmark_results/` and capture the
   combined benchmark, AI evaluation, and edge/cloud evidence.
9. Restart the backend with `Tee-Object` if needed, then capture structured
   reliability logs from `backend.log`.

## Related Week 7 docs

- [Week 7 Benchmark Guide](benchmarks.md)
- [AI Evaluation Metrics Guide](ai_evaluation.md)
- [Edge vs Cloud Comparison Evidence](edge_cloud_comparison.md)
- [Reliability, Retry, and Logging](reliability.md)
