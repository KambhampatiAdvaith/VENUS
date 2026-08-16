# Backend

## Required environment

Set either `DATABASE_URL` or the individual `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` variables.

Common optional variables:

- `FRONTEND_URL` for a non-default frontend origin
- `ENABLE_STARTUP_TELEMETRY_SIMULATOR=false` to keep the simulator disabled by default
- `ENABLE_AI_PREDICTION_LOOP=false` to keep the prediction loop manual by default
- `ENABLE_KAFKA_TELEMETRY_CONSUMER=true` starts the real Kafka telemetry consumer inside FastAPI and broadcasts telemetry WebSocket events after database writes.
- `ENABLE_KAFKA_FAULT_CONSUMER=true` starts the real Kafka fault consumer inside FastAPI and broadcasts fault WebSocket events after database writes.
- `ACTIVE_FAULT_WINDOW_MINUTES=10` limits node/grid health to faults seen in the most recent window while keeping all historical fault records stored for `/faults` and history views.
- `TELEMETRY_SIMULATION_INTERVAL=15`
- `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`

## Fresh-start setup

```bash
cd backend
python -m pip install -r requirements.txt
python -m backend.database.init_db
python -m uvicorn backend.api.main:app --reload
```

## Smoke-test endpoints

- `GET /docs`
- `GET /health`
- `GET /telemetry?limit=10`
- `GET /nodes`
- `GET /load-balancing?limit=5`
- `POST /load-balancing/recommend`
- `GET /load-balancing/pending?limit=10`

## Reliability notes

See [Reliability, Retry, and Logging](../docs/reliability.md) for the current backend logging format, retry/backoff behavior, tolerated failures, and Windows PowerShell-friendly log inspection commands.

For the consolidated Week 7 demo/runbook and evidence checklist, see [Week 7 Evidence Pack](../docs/week7_evidence_pack.md).

## Existing database migration note

If your local database predates the current backend, rerun `python -m backend.database.init_db` or apply the updated `backend/database/schema.sql` statements manually so `predictions`, `faults`, `load_balancing_actions`, and the telemetry edge columns all exist before starting the API.
