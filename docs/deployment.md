# V.E.N.U.S. Deployment Guide

This guide covers deploying the V.E.N.U.S. full-stack system in a production-oriented setup:
- **Frontend** hosted on [Vercel](https://vercel.com) (or any static/Next.js host)
- **Backend + infrastructure** running on a single Docker VPS/VM

---

## Recommended architecture

```
Internet
  │
  ├── Vercel (Next.js frontend)
  │     └── NEXT_PUBLIC_API_BASE_URL=https://<backend-domain>
  │
  └── VPS / VM (Ubuntu, Docker)
        ├── nginx / Caddy (optional HTTPS reverse proxy → :8000)
        ├── venus-backend        (FastAPI, port 8000)
        ├── venus-mqtt-bridge    (MQTT → Kafka bridge)
        ├── venus-kafka          (port 9092)
        ├── venus-zookeeper
        ├── venus-mosquitto      (MQTT, port 1883)
        ├── venus-postgres       (port 5432)
        └── venus-substation-a/b/c (optional demo simulators)
```

> **Mixed-content note:** If the frontend is served over HTTPS (e.g. on Vercel), the
> backend must also be reachable over HTTPS. A plain `http://` backend URL will be
> blocked by browsers as mixed content. Use a reverse proxy (nginx/Caddy) with a TLS
> certificate to terminate HTTPS in front of port 8000.

---

## Prerequisites

- Ubuntu 22.04 (or later) VPS/VM with at least 2 vCPU / 4 GB RAM
- [Docker Engine](https://docs.docker.com/engine/install/ubuntu/) + the Compose plugin (`docker compose`)
- Git
- *(Optional)* A domain name pointed at the server's IP and a reverse proxy (nginx/Caddy) for HTTPS

---

## Backend / infrastructure deployment

### 1. Clone the repository

```bash
git clone https://github.com/KambhampatiAdvaith/VENUS.git
cd VENUS
```

### 2. Configure environment variables

Create a `.env` file inside the `backend/` directory (it is git-ignored). At minimum set a strong database password and your frontend URL:

```bash
cat > backend/.env <<'EOF'
POSTGRES_USER=venus
POSTGRES_PASSWORD=change_me_in_prod
POSTGRES_DB=venus_db

FRONTEND_URL=https://<your-vercel-app>.vercel.app

# Kafka consumer toggles (defaults used by docker-compose.prod.yml)
ENABLE_KAFKA_TELEMETRY_CONSUMER=true
ENABLE_KAFKA_FAULT_CONSUMER=false
ACTIVE_FAULT_WINDOW_MINUTES=10
EOF
```

`ACTIVE_FAULT_WINDOW_MINUTES` controls how long a fault stays "active" for `/nodes`
and `/dashboard/metrics`. Historical fault rows remain stored and visible through
`/faults`, but node/grid health only reflects faults inside this recent window.

### 3. Start the production stack

```bash
cd backend
docker compose -f docker-compose.prod.yml up -d --build
```

This builds the backend image and starts all services. The first run takes a few minutes while Docker pulls images and builds the image.

### 4. Inspect running containers

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Expected containers (all `Up`):

| Name | Purpose |
|---|---|
| `venus-postgres` | PostgreSQL database |
| `venus-zookeeper` | Kafka coordination |
| `venus-kafka` | Kafka broker |
| `venus-kafka-init` | One-shot topic initializer (exits 0) |
| `venus-init-db` | One-shot DB schema initializer (exits 0) |
| `venus-mosquitto` | MQTT broker |
| `venus-backend` | FastAPI backend (port 8000) |
| `venus-mqtt-bridge` | MQTT-to-Kafka bridge |
| `venus-substation-a/b/c` | Demo simulators (optional) |

### 5. Verify Kafka topics

Wait ~30 seconds after start for `kafka-init` to finish, then:

```bash
docker exec venus-kafka kafka-topics \
  --bootstrap-server venus-kafka:29092 --list
```

Expected output:
```
venus.alerts
venus.faults
venus.load-balancing
venus.telemetry
```

### 6. Initialize / verify the database

On the first run, the `venus-init-db` one-shot service applies `backend/database/schema.sql` automatically before the backend starts. Verify the tables exist:

```bash
docker exec -it venus-postgres \
  psql -U venus -d venus_db -c "\dt"
```

If tables are missing, check the `venus-init-db` logs for errors:

```bash
docker compose -f docker-compose.prod.yml logs init-db
```

### 7. Test backend health and key endpoints

```bash
BASE=http://localhost:8000

curl $BASE/health
curl "$BASE/telemetry?limit=3"
curl "$BASE/nodes"
curl -X POST $BASE/predictions/run
curl "$BASE/load-balancing?limit=5"
```

> If you have a domain + HTTPS reverse proxy, replace `http://localhost:8000` with
> `https://<backend-domain>`.

### 8. View logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Single service
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f mqtt-bridge
docker compose -f docker-compose.prod.yml logs -f kafka
```

### 9. Stop the stack

```bash
docker compose -f docker-compose.prod.yml down
```

To also remove persistent volumes (⚠️ deletes all stored telemetry):

```bash
docker compose -f docker-compose.prod.yml down -v
```

### 10. Update / restart after code changes

```bash
git pull
cd backend
docker compose -f docker-compose.prod.yml up -d --build
```

Running containers are recreated only if their image or config changed.

---

## Frontend deployment (Vercel)

1. Import the repository into [Vercel](https://vercel.com/new).
2. Set the following in the Vercel project settings:

   | Setting | Value |
   |---|---|
   | **Root Directory** | `frontend` |
   | **Build Command** | `npm run build` |
   | **Install Command** | `npm install` |

3. Add the environment variable:

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://<backend-domain>` |

4. Deploy. Vercel automatically rebuilds on every push to `main`.

### CORS

Set `FRONTEND_URL` in `backend/.env` to the deployed Vercel URL so the backend allows cross-origin requests:

```
FRONTEND_URL=https://<your-vercel-app>.vercel.app
```

Then restart the backend container:

```bash
docker compose -f docker-compose.prod.yml restart backend
```

---

## Smoke tests

Run after every deployment to confirm the stack is healthy:

```bash
BASE=https://<backend-domain>   # or http://localhost:8000 on the server

curl $BASE/health
curl "$BASE/telemetry?limit=3"
curl $BASE/nodes
curl -X POST $BASE/predictions/run
curl "$BASE/load-balancing?limit=5"
```

All requests should return HTTP 200 with JSON bodies.

---

## Demo stability notes

The production compose file defaults to:

```
ENABLE_KAFKA_TELEMETRY_CONSUMER=true   # streams live telemetry into the DB
ENABLE_KAFKA_FAULT_CONSUMER=false      # reduces noise in demo/prod environments
```

To enable the fault consumer (full pipeline):

```bash
# In backend/.env
ENABLE_KAFKA_FAULT_CONSUMER=true
```

Then restart the backend:

```bash
docker compose -f docker-compose.prod.yml restart backend
```
