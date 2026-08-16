# V.E.N.U.S.

**Virtual Edge-Node Unified System - Real-Time Smart-Grid Monitoring and Load Management**

V.E.N.U.S. is a full-stack smart-grid monitoring and decision-support prototype for real-time telemetry ingestion, simulated edge anomaly detection, cloud-side AI fault prediction, and operator-supervised load-balancing recommendations.

The system models a distributed edge-cloud utility workflow: simulated substations publish telemetry, the backend stores and analyzes operating data, and the frontend gives operators a live view of grid health, predictions, alerts, recommendations, and audit history.

> **Scope note:** V.E.N.U.S. is designed as a deployed smart-grid monitoring prototype and evidence platform. It demonstrates realistic data flow, operator workflows, anomaly detection, and decision support, but it is not a production SCADA/control system and does not actuate real electrical infrastructure.

---

## Live Demo

```text
https://venusnotplanet.vercel.app/
```

---

## Key Capabilities

- **Real-time telemetry ingestion** - voltage, current, temperature, load, and frequency from simulated substations A, B, and C.
- **Simulated edge anomaly detection** - Isolation Forest enriches telemetry with edge anomaly scores before cloud persistence.
- **Cloud-side AI fault prediction** - XGBoost classifies recent telemetry into normal or likely fault conditions.
- **Live operator dashboard** - WebSocket-triggered updates refresh telemetry, node health, analytics, predictions, alerts, and balancing data.
- **Node and grid health monitoring** - current health uses latest telemetry and a configurable recent active-fault window rather than treating all historical faults as active.
- **Load-balancing decision support** - engine recommends simulated load shifts and supports operator approval/rejection.
- **Decision audit trail** - records balancing triggers, decisions, operator workflow, status, and observed impact.
- **Benchmark evidence** - latency, throughput, AI evaluation, edge/cloud comparison, and resource-profile scripts support repeatable validation.
- **Deployment support** - production Docker Compose files for backend/infrastructure and Vercel-compatible frontend configuration.

---

## Architecture

```text
Substation simulators (Python)
  │  MQTT publish: venus/telemetry/#, venus/faults/#
  ▼
Mosquitto MQTT broker
  │
  ▼
MQTT-to-Kafka bridge
  │  Kafka topics: venus.telemetry, venus.faults, venus.alerts, venus.load-balancing
  ▼
FastAPI backend
  ├── Kafka telemetry consumer → PostgreSQL
  ├── Kafka fault consumer → PostgreSQL / alerts
  ├── Simulated edge anomaly detection metadata
  ├── XGBoost prediction engine
  ├── Load-balancing recommendation / approval / audit APIs
  └── WebSocket push to frontend
  ▼
Next.js dashboard (operator UI)
```

| Layer | Technology |
|---|---|
| Substation simulation | Python |
| Messaging | Mosquitto MQTT, Apache Kafka, Zookeeper |
| Backend | FastAPI, SQLAlchemy, PostgreSQL |
| ML / analytics | Isolation Forest, XGBoost, pandas, scikit-learn |
| Frontend | Next.js App Router, React, Tailwind CSS, Recharts |
| Deployment | Docker, Docker Compose, Vercel-compatible frontend |

---

## Project Structure

```text
VENUS/
├── backend/
│   ├── backend/
│   │   ├── api/            FastAPI app, routes, schemas, WebSocket manager
│   │   ├── ai/             XGBoost prediction and Isolation Forest model training
│   │   ├── edge/           simulated edge anomaly detector
│   │   ├── kafka/          telemetry/fault consumers and producer utilities
│   │   ├── mqtt/           MQTT-to-Kafka bridge
│   │   ├── optimization/   load-balancing decision engine
│   │   └── database/       schema initialization
│   ├── simulator/          substation telemetry/fault publishers
│   ├── benchmarks/         latency, throughput, AI, edge/cloud, resource reports
│   ├── tests/              backend unit/integration tests
│   └── docker-compose*.yml infrastructure and deployment profiles
├── frontend/
│   ├── app/                dashboard, telemetry, alerts, analytics, nodes, predictions, settings
│   ├── components/         charts, cards, navigation, live update components
│   └── services/           API client, WebSocket client, settings, timestamp helpers
└── docs/                   deployment, validation, benchmarking, reliability, evidence guides
```

---

## Setup and Run Locally

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+

### 1. Start infrastructure

```bash
cd backend
docker-compose up -d
```

Verify Kafka topics:

```bash
docker exec venus-kafka kafka-topics --bootstrap-server venus-kafka:29092 --list
```

Expected topics include:

```text
venus.telemetry
venus.faults
venus.alerts
venus.load-balancing
```

### 2. Start backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\Activate.ps1      # Windows PowerShell

pip install -r requirements.txt
python -m backend.database.init_db

export ENABLE_KAFKA_TELEMETRY_CONSUMER=true
export ENABLE_KAFKA_FAULT_CONSUMER=true
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export MQTT_HOST=localhost
export MQTT_PORT=1883
export ACTIVE_FAULT_WINDOW_MINUTES=10

python -m uvicorn backend.api.main:app --reload
```

Backend docs:

```text
http://127.0.0.1:8000/docs
```

### 3. Start MQTT-to-Kafka bridge

```bash
cd backend
source venv/bin/activate

export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export MQTT_HOST=localhost
export MQTT_PORT=1883

python -m backend.mqtt.mqtt_to_kafka_bridge
```

### 4. Start substation simulators

Open one terminal per substation:

```bash
cd backend
source venv/bin/activate
export MQTT_HOST=localhost
export MQTT_PORT=1883

python -m simulator.substation_a
python -m simulator.substation_b
python -m simulator.substation_c
```

### 5. Start frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000/dashboard
```

---

## Environment Variables

### Backend

| Variable | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://venus:venus@localhost:5432/venus` |
| `FRONTEND_URL` | Allowed frontend origin for CORS | `https://venusnotplanet.vercel.app` |
| `ENABLE_STARTUP_TELEMETRY_SIMULATOR` | Starts backend demo telemetry loop | `true` |
| `TELEMETRY_SIMULATION_INTERVAL` | Backend simulator interval in seconds | `5` |
| `ENABLE_AI_PREDICTION_LOOP` | Runs periodic prediction cycles | `true` |
| `ENABLE_KAFKA_TELEMETRY_CONSUMER` | Starts Kafka telemetry consumer | `true` |
| `ENABLE_KAFKA_FAULT_CONSUMER` | Starts Kafka fault consumer | `true` |
| `ACTIVE_FAULT_WINDOW_MINUTES` | Recent window used for active node/grid health | `10` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker list | `localhost:9092` |
| `MQTT_HOST` / `MQTT_PORT` | MQTT broker location | `localhost` / `1883` |

### Frontend

| Variable | Purpose | Example |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API base URL | `https://your-backend.onrender.com` |
| `NEXT_PUBLIC_WS_URL` | Live WebSocket URL | `wss://your-backend.onrender.com/ws/live` |

If `NEXT_PUBLIC_WS_URL` is omitted, the frontend can derive the WebSocket URL from `NEXT_PUBLIC_API_BASE_URL`.

---

## Operational Workflows

### Generate normal telemetry

```bash
curl -X POST http://127.0.0.1:8000/telemetry/simulate/normal
curl http://127.0.0.1:8000/telemetry?limit=10
curl http://127.0.0.1:8000/nodes
```

### Inject a fault scenario

```bash
curl -X POST http://127.0.0.1:8000/telemetry/simulate/fault
curl http://127.0.0.1:8000/faults?limit=10
curl http://127.0.0.1:8000/dashboard/metrics
```

`/faults` preserves historical records. Current node/grid health uses recent faults inside `ACTIVE_FAULT_WINDOW_MINUTES` plus latest telemetry thresholds.

### Run cloud-side predictions

```bash
curl -X POST http://127.0.0.1:8000/predictions/run
curl http://127.0.0.1:8000/predictions?limit=10
curl http://127.0.0.1:8000/predictions/metrics
```

### Create and review load-balancing recommendations

```bash
curl -X POST http://127.0.0.1:8000/load-balancing/recommend
curl http://127.0.0.1:8000/load-balancing/pending?limit=10
curl -X POST http://127.0.0.1:8000/load-balancing/approve/1
curl -X POST http://127.0.0.1:8000/load-balancing/reject/1
curl http://127.0.0.1:8000/load-balancing/decision-log?limit=10
```

---

## Performance and Validation Results

The following benchmark values were captured from the project benchmark suite and are included as representative evidence for the completed prototype.

### API Latency

| Endpoint | Requests | OK | Errors | Avg Latency |
|---|---:|---:|---:|---:|
| Dashboard Metrics | 10 | 10 | 0 | 30.15 ms |
| Telemetry List | 10 | 10 | 0 | 42.60 ms |
| Latest Telemetry | 10 | 10 | 0 | 29.45 ms |
| Telemetry Latency | 10 | 10 | 0 | 18.17 ms |
| Nodes | 10 | 10 | 0 | 19.96 ms |
| Load Balancing | 10 | 10 | 0 | 21.31 ms |

### Telemetry Throughput

| Metric | Value |
|---|---:|
| Total simulate requests | 51 |
| Successes | 51 |
| Failures | 0 |
| Observed rate | 5.07 req/s |
| Avg simulate latency | 90.29 ms |
| Rows inserted | 153 |
| Rows per second | 15.2 |

### Latency Measurements

| Metric | Value |
|---|---:|
| Average Latency | 18.17 ms |
| Minimum Latency | 5.07 ms |
| Maximum Latency | 35.85 ms |
| Median Latency | 17.44 ms |

### Edge vs Cloud Comparison

| Metric | Value |
|---|---:|
| Edge substations covered | 3 |
| Cloud substations covered | 3 |
| Paired substations | 3 |
| Operational agreement rate | 100.0% |

### Processing Mode Comparison

| Processing Mode | Latency |
|---|---:|
| Cloud-only | 17.84 ms |
| Edge-assisted | 29.62 ms |

> Edge/cloud values are prototype benchmark evidence over simulated telemetry. Operational agreement is not supervised real-world accuracy.

---

## Deployment

See [`docs/deployment.md`](docs/deployment.md) for the full deployment guide covering backend infrastructure and Vercel frontend setup.

Minimum hosted frontend configuration:

```text
NEXT_PUBLIC_API_BASE_URL=https://<backend-host>
NEXT_PUBLIC_WS_URL=wss://<backend-host>/ws/live
```

Minimum hosted backend configuration:

```text
FRONTEND_URL=https://venusnotplanet.vercel.app
ENABLE_STARTUP_TELEMETRY_SIMULATOR=true
TELEMETRY_SIMULATION_INTERVAL=5
ENABLE_AI_PREDICTION_LOOP=true
ACTIVE_FAULT_WINDOW_MINUTES=10
```

---

## Validation and Evidence Guides

| Guide | Purpose |
|---|---|
| [`docs/week8_validation.md`](docs/week8_validation.md) | End-to-end validation runbook |
| [`docs/week8_functional_testing.md`](docs/week8_functional_testing.md) | Per-page functional testing checklist |
| [`docs/week8_evidence_checklist.md`](docs/week8_evidence_checklist.md) | Screenshot, log, and metric evidence checklist |
| [`docs/benchmarks.md`](docs/benchmarks.md) | Latency, throughput, AI, and edge/cloud benchmark instructions |
| [`docs/week8_benchmarking.md`](docs/week8_benchmarking.md) | Benchmark interpretation and success criteria |
| [`docs/simulator_realism.md`](docs/simulator_realism.md) | Simulator realism design notes |
| [`docs/reliability.md`](docs/reliability.md) | Retry, logging, and tolerated failure behavior |

---

## Real-World Scope and Limitations

V.E.N.U.S. is intended to demonstrate a realistic monitoring and decision-support workflow. To avoid overclaiming:

- The substations are simulated, not physical devices.
- Edge anomaly detection is simulated edge-side processing, not deployed hardware inference.
- AI predictions are trained and evaluated over simulated/rule-labeled telemetry, not utility outage ground truth.
- Load balancing stores simulated recommendations and outcomes; it does not actuate real switching equipment.
- The dashboard has operator controls, but production authentication/authorization and SCADA-grade safety controls are outside the current scope.
- The system is best described as a smart-grid monitoring and decision-support prototype, not a production grid control platform.

These limitations are intentional for a safe, repeatable prototype while preserving a realistic edge-cloud architecture and operator workflow.
