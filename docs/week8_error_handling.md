# V.E.N.U.S. Week 8 — Error Handling and UI/UX Polish

This document describes the error handling improvements and UI/UX polish added
in Week 8 PR #13. The goal is to make every dashboard page demo-ready under
empty data, backend unavailability, and API failure conditions.

---

## Overview

Changes cover three areas:

1. **Error state banners** — every server-rendered page now shows a clear red
   notice when the backend API cannot be reached, instead of silently falling
   back to blank data.

2. **Improved empty states** — empty tables and lists now include an actionable
   hint explaining what to do next (e.g. run the simulator or inject a fault).

3. **Client-side error feedback** — the AI Predictions page (a client component)
   now distinguishes between a *fetch* error (backend unreachable) and a
   *run* error (prediction cycle failed), and shows each as a separate banner.

---

## Pages and their states

### Dashboard (`/dashboard`)

| State | Behaviour |
|---|---|
| Loading | Next.js server render; page is blank until the server responds |
| Data available | Metrics, charts, node cards, load balancing summary |
| Empty (no telemetry) | Metric cards show zero values; load chart shows no bars |
| API error | Red banner: "Unable to load dashboard data — ensure backend is running" |

### Telemetry (`/telemetry`)

| State | Behaviour |
|---|---|
| Data available | Table of telemetry rows with freshness banner |
| Empty | "No telemetry records yet" with hint: `POST /telemetry/simulate/normal` |
| API error | Red banner above the table |

### Alerts (`/alerts`)

| State | Behaviour |
|---|---|
| Data available | List of fault cards with severity badge |
| Empty | "No fault alerts yet" with hint: `POST /telemetry/simulate/fault` |
| API error | Red banner above the list |

### Node Status (`/nodes`)

| State | Behaviour |
|---|---|
| Data available | Table of node rows with load, voltage, temperature, frequency |
| Empty | "No node status records yet" with hint: `POST /telemetry/simulate/normal` |
| API error | Red banner above the table |

### Load Balancing (`/load-balancing`)

| State | Behaviour |
|---|---|
| Data available | Node load cards, recommendation box, distribution table |
| Empty | "No load balancing data available" (within the status summary component) |
| API error | Red banner above the status summary |

### Analytics (`/analytics`)

| State | Behaviour |
|---|---|
| Data available | Metric cards, load and distribution charts |
| Empty | Charts render with zero values; metric cards show 0 |
| API error | Red banner above the metric cards |

### AI Predictions (`/predictions`)

This is a client component with client-side data fetching.

| State | Behaviour |
|---|---|
| Loading | "Loading AI prediction records..." in the table |
| Data available | Table of prediction rows |
| Empty | "No AI prediction records yet" with hint to run `POST /telemetry/simulate/normal` then click "Refresh Now" |
| Fetch error | Red banner: "Unable to load predictions" |
| Run error | Yellow banner: "Prediction cycle failed" |

---

## Backend defensive handling

The backend routes already return safe empty arrays and objects for most empty
dataset conditions. Key patterns already in place:

- `GET /faults` — returns `[]` when no faults exist (SQLAlchemy query returns empty list)
- `GET /nodes` — returns `[]` when no telemetry exists (raw SQL returns empty result set)
- `GET /telemetry` — returns `[]` when table is empty
- `GET /predictions` — returns `[]` when table is empty
- `GET /load-balancing/impact/summary` — returns `{"status": "empty", ...}` with zero counts when no executed actions exist
- `GET /load-balancing/decision-log` — returns `{"status": "success", "count": 0, "decision_log": []}` when empty
- `GET /telemetry/latency` — returns `{"sample_count": 0, ...}` with `null` latency fields when no samples

No unhandled exceptions were found in the critical dashboard routes. The
existing pattern of returning safe empty responses is consistent throughout.

---

## Design principles

- **Graceful fallback over crash**: all server components fall back to empty
  data on API failure; no unhandled exceptions propagate to the user.
- **Actionable messages**: empty states include a one-line hint of what to do
  next so the demo flow is clear without consulting separate documentation.
- **Consistent styling**: error banners use `border-red-500/40 bg-red-500/10
  text-red-300`; warning banners use `border-yellow-500/40 bg-yellow-500/10
  text-yellow-300` — matching the existing freshness indicator palette.
- **No schema or architecture changes**: no database schema, Kafka/MQTT
  architecture, AI model, or API route signatures were changed.

---

## Demo edge case playbook

| Scenario | What to do | Expected result |
|---|---|---|
| No telemetry data | Open `/telemetry` with empty DB | Empty state with `POST /telemetry/simulate/normal` hint |
| No fault alerts | Open `/alerts` with no faults | Empty state with `POST /telemetry/simulate/fault` hint |
| No predictions | Open `/predictions` with empty DB | Empty state with simulator and run hint |
| Backend down | Stop backend, open any page | Red error banner per page |
| Prediction cycle fails | Click "Refresh Now" when backend is down | Yellow warning banner on predictions page |
| Stale telemetry | Data older than 5 minutes | Yellow freshness banner on pages with freshness indicator |

---

## Related documents

- [End-to-End Validation Runbook](week8_validation.md)
- [Functional Testing Checklist](week8_functional_testing.md)
- [Evidence Collection Checklist](week8_evidence_checklist.md)
- [Final Performance Benchmarking](week8_benchmarking.md)
- [Resource Utilization Profile](week8_resource_profile.md)
- [Simulator Realism Enhancement](simulator_realism.md)
