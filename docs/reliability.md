# Reliability, Retry, and Logging

V.E.N.U.S. backend reliability-sensitive integrations now use shared Python logging and lightweight retry/backoff helpers instead of raw `print(...)` statements in the main Kafka, MQTT, simulator, and prediction loops.

## Logging behavior

- Log format: `timestamp | component | level | message`
- Component names identify the backend area, such as:
  - `backend.api.main`
  - `backend.api.telemetry_simulator`
  - `backend.kafka.telemetry_consumer`
  - `backend.kafka.fault_consumer`
  - `backend.kafka.producer`
  - `backend.mqtt.bridge`
  - `backend.database.writer`
- High-volume per-message success logs were moved to `DEBUG` where practical.
- Loop failures and service-boundary failures log at `WARNING` or `ERROR`, with stack traces on unexpected exceptions.

## Retry and backoff behavior

- Kafka consumer startup retries with exponential backoff and small jitter until a broker connection succeeds.
- Kafka consumer outer loops restart after unexpected crashes with bounded backoff.
- The MQTT-to-Kafka bridge retries MQTT broker connection/reconnection with exponential backoff and logs reconnect delays clearly.
- Kafka producer connection setup retries with backoff; publish failures are logged clearly and trigger a producer reconnect for future sends without blindly resending the failed message.
- Telemetry simulator and AI prediction loops continue running after logged exceptions instead of stopping silently.
- Database writes keep their current success/failure behavior (`None` on caught write failure) but now log failures with clearer component context.

## What failures are tolerated

Tolerated and retried automatically:

- Kafka broker unavailable during consumer or producer startup
- MQTT broker unavailable or dropped connection
- Unexpected exceptions inside background telemetry consumer, fault consumer, simulator, and AI prediction loops

Still fatal or operator-visible:

- Persistent external service outages (the process keeps retrying and logs each retry)
- Unhandled process termination signals
- Request-level failures that bubble out of API handlers

## Local log inspection

### PowerShell

Start the backend:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn backend.api.main:app --reload
```

Save logs to a file while still viewing them:

```powershell
python -m uvicorn backend.api.main:app --reload 2>&1 | Tee-Object -FilePath .\backend.log
```

Follow a saved log file:

```powershell
Get-Content .\backend.log -Wait
```

### Shell

```bash
cd backend
python -m uvicorn backend.api.main:app --reload 2>&1 | tee backend.log
tail -f backend.log
```
