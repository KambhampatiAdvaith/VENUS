# Backend

## Required environment

Set either `DATABASE_URL` or the individual `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB` variables.

Common optional variables:

- `FRONTEND_URL` for a non-default frontend origin
- `ENABLE_STARTUP_TELEMETRY_SIMULATOR=false` to keep the simulator disabled by default
- `ENABLE_AI_PREDICTION_LOOP=false` to keep the prediction loop manual by default
- `TELEMETRY_SIMULATION_INTERVAL=15`
- `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`

## Fresh-start setup

```bash
cd /home/runner/work/VENUS/VENUS/backend
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

## Existing database migration note

If your local database predates the current backend, rerun `python -m backend.database.init_db` or apply the updated `backend/database/schema.sql` statements manually so `predictions`, `faults`, `load_balancing_actions`, and the telemetry edge columns all exist before starting the API.
