# V.E.N.U.S.
**Virtual Edge-Node Unified System — Real-Time Smart-Grid Monitoring and Load Management**

---

V.E.N.U.S. is a near-complete distributed edge-cloud platform for smart-grid monitoring, fault detection, AI-driven risk prediction, and autonomous load balancing. Simulated substations produce live telemetry that flows through MQTT and Kafka into a FastAPI/PostgreSQL backend, where an XGBoost model predicts fault risk and a load-balancing engine recommends or executes corrective actions. Operators interact with a Next.js dashboard that streams live updates via WebSocket.

---

## Capabilities

- **Real-time telemetry ingestion** — voltage, current, temperature, load, and frequency from multiple simulated substations
- **Edge anomaly detection** — Isolation Forest runs at each substation before data is forwarded, enriching telemetry with anomaly scores
- **Fault detection and alerts** — backend raises alerts when telemetry crosses thresholds; visible on the Alerts page
- **AI risk predictions** — XGBoost model scores each telemetry reading for fault probability
- **Load balancing workflow** — engine detects overloaded nodes, generates recommendations, supports operator approval, and logs every decision for audit
- **Live dashboard** — WebSocket-driven updates for telemetry, alerts, node status, analytics, predictions, and balancing history
- **Closed-loop outcome tracking** — balancing outcomes are validated and stored for post-hoc review

---

## Architecture

```
Substation simulators (Python)
  │  MQTT publish (venus/telemetry/#, venus/faults/#)
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
  ├── XGBoost prediction engine
  ├── Load balancing engine (recommend / approve / audit)
  └── WebSocket push to frontend
  ▼
Next.js dashboard (operator UI)
```

| Layer | Technology |
|---|---|
| Substation simulation | Python, Isolation Forest |
| Messaging | Mosquitto MQTT, Apache Kafka, Zookeeper |
| Backend | FastAPI, PostgreSQL |
| ML | Isolation Forest (edge), XGBoost (cloud) |
| Frontend | Next.js, Tailwind CSS |
| Infrastructure | Docker, Docker Compose |

---

## Project structure

```
VENUS/
├── backend/
│   ├── backend/
│   │   ├── api/            FastAPI app, routes, schemas
│   │   ├── kafka/          Kafka consumers (telemetry, faults)
│   │   ├── mqtt/           MQTT-to-Kafka bridge
│   │   ├── models/         XGBoost prediction model
│   │   └── load_balancing/ Balancing engine and audit logic
│   ├── simulator/          Substation A/B/C simulators (MQTT publishers)
│   ├── benchmarks/         Latency, throughput, and AI evaluation scripts
│   ├── tests/              Backend unit and integration tests
│   └── docker-compose.yml  Infrastructure services
├── frontend/
│   ├── app/                Next.js pages (dashboard, telemetry, alerts, …)
│   ├── components/         Shared UI components
│   └── services/           API client, settings, WebSocket helpers
└── docs/                   Validation, benchmarking, and testing guides
```

---

## Setup and run

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ with a virtual environment (`backend/venv`)
- Node.js 18+

### 1. Start infrastructure

```bash
cd backend
docker-compose up -d
```

This starts Zookeeper, Kafka (with topic init), Mosquitto MQTT, and PostgreSQL. Wait 30–60 seconds, then verify:

```bash
docker ps
# Expected containers: venus-zookeeper, venus-kafka, venus-kafka-init, venus-mosquitto, venus-postgres

docker exec venus-kafka kafka-topics --bootstrap-server venus-kafka:29092 --list
# Expected topics: venus.telemetry  venus.faults  venus.alerts  venus.load-balancing
```

### 2. Start the backend

```bash
cd backend
source venv/bin/activate          # macOS/Linux
# venv\Scripts\Activate.ps1       # Windows PowerShell

export ENABLE_KAFKA_TELEMETRY_CONSUMER=true
export ENABLE_KAFKA_FAULT_CONSUMER=true
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export MQTT_HOST=localhost
export MQTT_PORT=1883

python -m uvicorn backend.api.main:app --reload
```

Backend starts at `http://127.0.0.1:8000`. Swagger docs: `http://127.0.0.1:8000/docs`.

### 3. Start the MQTT-to-Kafka bridge

Open a new terminal:

```bash
cd backend
source venv/bin/activate

export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export MQTT_HOST=localhost
export MQTT_PORT=1883

python -m backend.mqtt.mqtt_to_kafka_bridge
```

### 4. Start substation simulators

Open three terminals (one per substation):

```bash
cd backend && source venv/bin/activate
export MQTT_HOST=localhost && export MQTT_PORT=1883

python -m simulator.substation_a   # Terminal A
python -m simulator.substation_b   # Terminal B
python -m simulator.substation_c   # Terminal C
```

Each simulator publishes telemetry and fault events to the MQTT broker. Data flows: MQTT → Kafka → backend → PostgreSQL → dashboard.

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000/dashboard`.

---

## Operational guidelines

### Generate normal telemetry

Run all three substation simulators (step 4 above). After 10–20 seconds:

```bash
curl http://127.0.0.1:8000/telemetry?limit=10
curl http://127.0.0.1:8000/telemetry/latency
```

### Inject a fault

The simulators periodically inject fault conditions automatically. To observe fault detection:

1. Watch the **Alerts** page (`/alerts`) in the dashboard.
2. Check the backend logs for fault consumer activity.
3. Query the faults endpoint: `curl http://127.0.0.1:8000/faults?limit=10`

### Run AI predictions

With the backend running and telemetry flowing:

```bash
curl http://127.0.0.1:8000/predictions?limit=10
```

The **AI Predictions** page (`/predictions`) shows risk scores in real time.

### Trigger load balancing

1. Open the **Load Balancing** page (`/load-balancing`).
2. When nodes are flagged as overloaded (load > alert threshold), the engine generates recommendations.
3. Approve or reject recommendations using the operator controls.
4. Review the audit trail on the **Balancing History** page.

Or via API:

```bash
curl -X POST http://127.0.0.1:8000/load-balancing/rebalance
curl http://127.0.0.1:8000/load-balancing/history
```

### Inspect latency and throughput

```bash
cd backend
source venv/bin/activate
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000
```

Reports are written to `benchmark_results/`. See [Benchmarking Guide](docs/benchmarks.md) for options.

### Resource utilization profile

```bash
python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --resource-profile
```

### Recommended demo flow

1. Start Docker services → wait for Kafka topics
2. Start backend with Kafka consumers enabled
3. Start MQTT-to-Kafka bridge
4. Start substation simulators (A, B, C)
5. Open dashboard → confirm live data age < 30 s
6. Check Alerts page for detected faults
7. Open Predictions page for XGBoost risk scores
8. Open Load Balancing page → approve a recommendation
9. Check Balancing History for the audit record
10. Adjust Settings (refresh interval, alert threshold) to tune the operator view

---

## Validation and testing

| Guide | Purpose |
|---|---|
| [End-to-End Validation Runbook](docs/week8_validation.md) | Full system walk-through and acceptance criteria |
| [Functional Testing Checklist](docs/week8_functional_testing.md) | Per-page and per-flow pass/fail checklist |
| [Evidence Collection Checklist](docs/week8_evidence_checklist.md) | Screenshots, logs, and metrics to capture |
| [Benchmarking Guide](docs/benchmarks.md) | Latency, throughput, and AI evaluation scripts |
| [Performance Benchmarking](docs/week8_benchmarking.md) | Benchmark run instructions and result interpretation |
| [Resource Utilization Profile](docs/week8_resource_profile.md) | CPU, memory, and I/O profiling |
| [Simulator Realism](docs/simulator_realism.md) | Fault injection patterns and realism settings |
| [Error Handling](docs/week8_error_handling.md) | UI error states and backend resilience |
| [Reliability](docs/reliability.md) | Retry logic, circuit breakers, and logging |
| [AI Evaluation Metrics](docs/ai_evaluation.md) | XGBoost precision, recall, and F1 results |
| [Edge vs Cloud Comparison](docs/edge_cloud_comparison.md) | Latency and accuracy trade-offs |

---

## Feature status

| Feature | Status |
|---|---|
| Substation simulation (A, B, C) | ✅ Complete |
| Edge anomaly detection (Isolation Forest) | ✅ Complete |
| MQTT + Kafka pipeline | ✅ Complete |
| XGBoost fault prediction | ✅ Complete |
| Autonomous load balancing | ✅ Complete |
| Operator approval and audit trail | ✅ Complete |
| Live dashboard with WebSocket updates | ✅ Complete |
| Docker infrastructure | ✅ Complete |
| Latency and throughput benchmarks | ✅ Complete |
| AI evaluation metrics | ✅ Complete |

---
