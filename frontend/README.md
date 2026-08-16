# V.E.N.U.S. Frontend

The V.E.N.U.S. frontend is a Next.js operator dashboard for the Volt Edge Network Utility System. It visualizes live telemetry, node health, analytics, AI predictions, alerts, load-balancing recommendations, and decision audit trails from the FastAPI backend.

This README is specific to the frontend app. For full system architecture, backend setup, benchmarking, and deployment notes, see the root [`README.md`](../README.md).

---

## Stack

- Next.js App Router
- React
- TypeScript
- Tailwind CSS
- Recharts
- WebSocket-triggered live refresh

---

## Environment

Create `frontend/.env.local` for local development:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/live
```

For hosted deployment, use HTTPS/WSS URLs:

```env
NEXT_PUBLIC_API_BASE_URL=https://<backend-host>
NEXT_PUBLIC_WS_URL=wss://<backend-host>/ws/live
```

If `NEXT_PUBLIC_WS_URL` is omitted, the frontend attempts to derive it from `NEXT_PUBLIC_API_BASE_URL`.

---

## Run Locally

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

## Build and Lint

```bash
npm run lint
npm run build
```

---

## Main Pages

| Route | Purpose |
|---|---|
| `/dashboard` | Grid overview, metrics, AI risk, load balancing, load trend |
| `/telemetry` | Recent telemetry rows and timestamp evidence |
| `/nodes` | Current substation health from latest telemetry and active faults |
| `/analytics` | Load, node efficiency, and fault summaries |
| `/predictions` | Cloud-side AI prediction records and risk score |
| `/alerts` | Fault/alert history |
| `/load-balancing` | Load distribution and recommendation workflow |
| `/settings` | Refresh interval and alert threshold controls |

---

## Live Update Model

The frontend treats backend data as the source of truth. WebSocket events do not create telemetry directly; they trigger page refreshes so server-rendered pages refetch current backend data.

```text
Backend inserts/updates data -> WebSocket event -> frontend refresh -> latest API data displayed
```

Chart timestamps come from telemetry records, not from the browser clock or WebSocket receive time.
