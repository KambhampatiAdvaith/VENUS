# V.E.N.U.S.
**Intelligent Edge-Cloud Platform for Real-Time Power Grid Fault Prediction and Autonomous Load Balancing**

---

V.E.N.U.S. is a distributed edge-cloud system for smart grid monitoring, fault prediction, and autonomous load balancing. It simulates multiple substations generating real-time telemetry, processes that data through a layered edge-cloud pipeline, and takes automated decisions to maintain grid stability.

---

## How It Works

Simulated substations generate telemetry (voltage, current, temperature, load, frequency). An Isolation Forest model runs locally at each substation and enriches the data with anomaly scores before forwarding it to the cloud. The enriched telemetry flows through MQTT into Kafka, gets stored in PostgreSQL, and is analyzed by XGBoost for fault prediction. When a fault risk is detected, the load balancing engine executes or recommends a corrective action, logs the outcome, and validates whether the intervention worked.

```
Substation -> Edge Isolation Forest -> MQTT -> Kafka -> PostgreSQL
-> XGBoost Prediction -> Load Balancing Engine -> Dashboard
```

---

## Stack

| Layer | Tech |
|---|---|
| Edge | Python, Isolation Forest, Mosquitto MQTT |
| Streaming | Apache Kafka, Zookeeper |
| Backend | FastAPI, PostgreSQL |
| ML | Isolation Forest, XGBoost |
| Frontend | Next.js |
| Deployment | Docker, Docker Compose |

---

## Features

- Anomaly detection runs at the substation before cloud ingestion
- MQTT and Kafka event pipeline for real-time data flow
- XGBoost fault prediction with risk scoring
- Autonomous load balancing with approval workflows, decision logging, and closed-loop outcome tracking
- Live dashboard with telemetry, alerts, predictions, and balancing controls
- Separate Docker deployments for edge and cloud layers

---

## Run

```bash
# Edge layer
docker-compose -f docker-compose.edge.yml up --build

# Cloud layer
docker-compose -f docker-compose.cloud.yml up --build
```

---

## Status

| Feature | Status |
|---|---|
| Substation simulation | Done |
| Edge anomaly detection | Done |
| MQTT + Kafka pipeline | Done |
| XGBoost fault prediction | Done |
| Autonomous load balancing | Done |
| Live dashboard | Done |
| Docker edge-cloud separation | Done |
| WebSocket live updates | In Progress |
| Latency and throughput benchmarks | In Progress |

---
