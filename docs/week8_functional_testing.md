# V.E.N.U.S. Week 8 — Functional Testing Checklist

Use this checklist to verify that all major V.E.N.U.S. modules are working
correctly before final sign-off.  Mark each item **Pass** or **Fail** and add
notes where useful.

For the full validation procedure of each workflow, see the
[End-to-End Validation Runbook](week8_validation.md).

---

## How to use this checklist

1. Start the backend and frontend as described in the
   [Validation Runbook — System prerequisites](week8_validation.md#1-system-prerequisites).
2. Work through each module section below.
3. Record `Pass`, `Fail`, or `N/A` in the **Result** column.
4. For any `Fail`, note the symptom and cross-reference the runbook
   Troubleshooting notes.

---

## 1. Dashboard

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 1.1 | Open `http://localhost:3000` | Dashboard loads without JS errors | | |
| 1.2 | WebSocket connection indicator | Live-update banner shows "connected" or similar | | |
| 1.3 | Dashboard auto-refreshes after backend event | New data appears without manual browser refresh | | |
| 1.4 | Dashboard loads within 3 s on local network | No loading spinners stuck indefinitely | | |
| 1.5 | Navigation links to all pages are present | Telemetry, Alerts, Nodes, Predictions, Recommendations, History, Audit Trail links work | | |

---

## 2. Telemetry

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 2.1 | `GET /telemetry/latest` returns a row | JSON object with `substation_id`, `voltage`, `current`, `temperature`, `load`, `frequency` | | |
| 2.2 | `GET /telemetry?limit=10` returns multiple rows | JSON array with 1–10 telemetry rows | | |
| 2.3 | `GET /telemetry/latency` returns stats | `avg_latency_ms`, `min_latency_ms`, `max_latency_ms`, `median_latency_ms`, `sample_count > 0` | | |
| 2.4 | `POST /telemetry/simulate/normal` succeeds | HTTP 200; new row appears in subsequent `GET /telemetry/latest` | | |
| 2.5 | Telemetry page in dashboard shows rows | Table is populated with recent data | | |
| 2.6 | Freshness indicator shows recent timestamp | Timestamp is within the last few minutes | | |
| 2.7 | `edge_anomaly` and `edge_anomaly_score` fields present | Rows include edge-layer enrichment fields | | |

---

## 3. Alerts

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 3.1 | `GET /faults?limit=5` returns rows after fault injection | JSON array with fault records | | |
| 3.2 | Alerts page in dashboard shows fault alerts | Alert rows present with substation ID, type, timestamp | | |
| 3.3 | Fault injection via `POST /telemetry/simulate/fault` creates an alert | New fault row visible in `/faults` after call | | |
| 3.4 | Alert timestamps match injection time | Timestamp within ±60 s of the POST request time | | |
| 3.5 | Dashboard alerts update without page reload | New alert appears after WebSocket broadcast | | |

---

## 4. Node Status

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 4.1 | `GET /nodes` returns node list | JSON array with at least one node object | | |
| 4.2 | Node objects include `status`, `load`, `last_updated` | Fields are present and non-null | | |
| 4.3 | Node Status page in dashboard shows nodes | Node cards or rows visible with load values | | |
| 4.4 | Node load values are within realistic range (0–100 %) | No negative or >100 load percentages | | |

---

## 5. AI Prediction

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 5.1 | `GET /predictions?limit=5` returns rows | JSON array with prediction objects | | |
| 5.2 | Prediction row includes `predicted_fault`, `probability`, `anomaly`, `anomaly_score` | All fields present | | |
| 5.3 | `POST /predictions/run` succeeds | HTTP 200; new prediction row created | | |
| 5.4 | `GET /predictions/metrics` returns evaluation summary | JSON object with prediction counts and probability stats | | |
| 5.5 | Predictions page in dashboard shows results | Prediction table populated with recent rows | | |
| 5.6 | High-anomaly rows have `probability > 0.5` | Risk probability correlates with anomaly flag | | |

---

## 6. Recommendation Engine

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 6.1 | `GET /load-balancing?limit=5` returns rows | JSON array with recommendation objects | | |
| 6.2 | Recommendation object includes `id`, `status`, `action`, `substation_id` | Fields present | | |
| 6.3 | Recommendations page in dashboard shows pending items | At least one recommendation visible | | |
| 6.4 | New recommendations are created after fault injection + prediction run | `/load-balancing` count increases | | |

---

## 7. Load Balancing

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 7.1 | `POST /load-balancing/<id>/approve` succeeds | HTTP 200; recommendation status changes to `"approved"` or `"executed"` | | |
| 7.2 | Approved recommendation no longer shows as `"pending"` | Status updated in `/load-balancing/<id>` response | | |
| 7.3 | Load Balancing page in dashboard updates after approval | Approved item moves from pending to completed/approved | | |
| 7.4 | Node load changes after execution (if simulated) | Node load values reflect rebalancing | | |

---

## 8. Operator Approval

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 8.1 | Operator can approve a recommendation via the dashboard UI | Click Approve on a pending recommendation; status updates | | |
| 8.2 | Operator can reject a recommendation via the dashboard UI | Click Reject on a pending recommendation; status updates to `"rejected"` | | |
| 8.3 | `POST /load-balancing/<id>/approve` API call works | Status changes to `"approved"` or `"executed"` | | |
| 8.4 | `POST /load-balancing/<id>/reject` API call works | Status changes to `"rejected"` | | |
| 8.5 | Rejected recommendation shows `"Rejected"` on the dashboard | UI reflects the rejected status without page reload | | |

---

## 9. Decision Audit Trail

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 9.1 | `GET /load-balancing/history?limit=5` returns records | JSON array with audit/history records | | |
| 9.2 | Audit record for approved recommendation shows `action: "approved"` | Correct action label in history | | |
| 9.3 | Audit record for rejected recommendation shows `action: "rejected"` | No execution timestamp for rejections | | |
| 9.4 | Decision Audit Trail page in dashboard shows records | Audit table populated | | |
| 9.5 | Each audit record includes a timestamp | `created_at` or `timestamp` field is non-null | | |

---

## 10. Balancing History

| # | Test | Expected result | Result | Notes |
|---|---|---|---|---|
| 10.1 | Balancing History page in dashboard shows executed actions | History table is populated after an approval | | |
| 10.2 | `GET /load-balancing/history` returns executed balancing records | At least one record after approval workflow | | |
| 10.3 | Rejected recommendations do **not** appear in execution history | No execution entry for rejected IDs | | |
| 10.4 | History records include `action`, `substation_id`, and `timestamp` | Required fields present | | |
| 10.5 | Oldest records are preserved (no truncation without pagination) | Use `?limit=50` to confirm older records persist | | |

---

## Summary scorecard

After completing the checklist, tally results here:

| Module | Pass | Fail | N/A | Notes |
|---|---|---|---|---|
| Dashboard | | | | |
| Telemetry | | | | |
| Alerts | | | | |
| Node Status | | | | |
| AI Prediction | | | | |
| Recommendation Engine | | | | |
| Load Balancing | | | | |
| Operator Approval | | | | |
| Decision Audit Trail | | | | |
| Balancing History | | | | |
| **Total** | | | | |

---

## Related Week 8 docs

- [End-to-End Validation Runbook](week8_validation.md)
- [Evidence Collection Checklist](week8_evidence_checklist.md)
- [Week 7 Evidence Pack](week7_evidence_pack.md)
