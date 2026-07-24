# V.E.N.U.S. Week 8 — Evidence Collection Checklist

Use this checklist to collect and organize all evidence needed for the final
Week 8 sign-off.  Benchmark reports and reliability logs generated during
Week 7 can be reused where noted — there is no need to regenerate them unless
data has changed.

For the step-by-step procedures that produce each piece of evidence, see the
[End-to-End Validation Runbook](week8_validation.md).

---

## How to use this checklist

1. Work through the checklist in order.
2. Capture each item (screenshot, terminal output, or saved file).
3. Name screenshots clearly, for example `dashboard_live_update.png`.
4. Store all evidence in a local folder such as `evidence/week8/` (this folder
   is not committed to the repository).
5. Mark each item **Collected** when done, or note **Reused from Week 7** where
   applicable.

---

## 1. Dashboard

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 1.1 | Dashboard main page showing live telemetry rows | Screenshot of `http://localhost:3000` with data visible | |
| 1.2 | WebSocket live-update banner or indicator | Screenshot showing connection status (connected / active) | |
| 1.3 | Dashboard auto-refresh in action | Screenshot or screen recording showing new row appearing without manual reload | |
| 1.4 | Navigation between dashboard pages | Screenshot showing the page links and the active page | |

---

## 2. Telemetry

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 2.1 | `GET /telemetry/latest` API response | PowerShell: `(Invoke-WebRequest http://127.0.0.1:8000/telemetry/latest).Content` — screenshot or copy output | |
| 2.2 | Telemetry list page in dashboard | Screenshot of the Telemetry page showing multiple rows | |
| 2.3 | Latency endpoint output | PowerShell: `(Invoke-WebRequest http://127.0.0.1:8000/telemetry/latency).Content` — screenshot or copy output | |
| 2.4 | Freshness indicator showing recent timestamp | Screenshot of the dashboard Telemetry page with freshness/last-updated visible | |
| 2.5 | Simulator realism evidence | Capture `POST /telemetry/simulate/normal` and `POST /telemetry/simulate/fault` output showing lower off-peak load, higher evening load, and clear fault deviation; compare with [Simulator Realism Enhancement](simulator_realism.md) | |

---

## 3. Alerts

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 3.1 | Alerts page in dashboard with alert rows | Screenshot of `http://localhost:3000/alerts` (or equivalent) showing fault alerts | |
| 3.2 | `GET /faults` API response after fault injection | PowerShell: `(Invoke-WebRequest http://127.0.0.1:8000/faults?limit=5).Content` — screenshot or copy | |
| 3.3 | Fault injection command and result | Screenshot of the PowerShell terminal after `POST /telemetry/simulate/fault` | |

---

## 4. Node Status

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 4.1 | Node Status page in dashboard | Screenshot of the Nodes page showing node cards/rows with load values | |
| 4.2 | `GET /nodes` API response | PowerShell: `(Invoke-WebRequest http://127.0.0.1:8000/nodes).Content` — screenshot or copy | |

---

## 5. AI Predictions

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 5.1 | Predictions page in dashboard | Screenshot showing recent prediction rows | |
| 5.2 | `GET /predictions/metrics` API response | PowerShell: `(Invoke-WebRequest http://127.0.0.1:8000/predictions/metrics).Content` — screenshot or copy | |
| 5.3 | At least one prediction with `predicted_fault != "normal" or anomaly = true` | Screenshot or API output showing a high-risk prediction | |
| 5.4 | AI evaluation Markdown report | Reuse `benchmark_results/ai_evaluation_YYYYMMDD_HHMMSS.md` from Week 7, or regenerate — see note below | |

> **Week 7 reuse note:** The AI evaluation report from Week 7 benchmarks covers
> prediction counts, anomaly rates, and probability statistics.  Reuse the
> existing report file from `benchmark_results/` unless the prediction data has
> significantly changed.  To regenerate:
>
> ```powershell
> cd backend
> .\venv\Scripts\Activate.ps1
> python -m benchmarks.ai_evaluation_metrics --base-url http://127.0.0.1:8000
> ```

---

## 6. Recommendation Page

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 6.1 | Recommendations page showing pending items | Screenshot with at least one pending recommendation visible | |
| 6.2 | `GET /load-balancing` API response | PowerShell: `(Invoke-WebRequest http://127.0.0.1:8000/load-balancing?limit=5).Content` — screenshot or copy | |
| 6.3 | Recommendation details (`id`, `action_status`, `source_node`, `target_node`, `load_shifted`, `trigger_reason`) | Screenshot or API output showing all key fields | |

---

## 7. Operator Approval

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 7.1 | Dashboard before approval (pending status visible) | Screenshot of the pending recommendation | |
| 7.2 | Dashboard after approval (`action_status` updated) | Screenshot showing executed/approved workflow status | |
| 7.3 | Approval API response | PowerShell terminal screenshot showing `POST /load-balancing/approve/<id>` result | |
| 7.4 | Rejection API response | PowerShell terminal screenshot showing `POST /load-balancing/reject/<id>` result | |
| 7.5 | Dashboard after rejection (rejected status visible) | Screenshot showing `"Rejected"` status on the recommendation | |

---

## 8. Balancing History

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 8.1 | Balancing History page in dashboard | Screenshot showing executed actions after an approval | |
| 8.2 | `GET /load-balancing/impact` API response | PowerShell: `(Invoke-WebRequest http://127.0.0.1:8000/load-balancing/impact?limit=5).Content` | |
| 8.3 | Confirmation that rejected recommendations are not executed successes | Compare `/load-balancing/impact` before/after rejection; rejected entry should show `feedback_status: "rejected"` or `action_status: "rejected"` | |

---

## 9. Decision Audit Trail

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 9.1 | Decision Audit Trail page in dashboard | Screenshot showing audit records with decision details and timestamps | |
| 9.2 | Audit record for an approved recommendation | Screenshot or API output from `/load-balancing/decision-log?limit=5` showing approved/executed workflow | |
| 9.3 | Audit record for a rejected recommendation | Screenshot or API output from `/load-balancing/decision-log?limit=5` showing `action_status: "rejected"` and no action executed | |

---

## 10. Benchmark Results

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 10.1 | Combined Week 7 benchmark Markdown report | Reuse `benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.md` — see note below | |
| 10.2 | API latency benchmark results | Reuse `benchmark_results/api_latency_YYYYMMDD_HHMMSS.md` | |
| 10.3 | Telemetry throughput benchmark results | Reuse `benchmark_results/telemetry_throughput_YYYYMMDD_HHMMSS.md` | |
| 10.4 | Edge vs Cloud comparison report | Reuse `benchmark_results/edge_cloud_comparison_YYYYMMDD_HHMMSS.md` | |
| 10.5 | Resource utilization profile (Week 8) | Run `python -m benchmarks.resource_utilization` — see [Week 8 Resource Profile](week8_resource_profile.md) | |

> **Week 7 reuse note:** All benchmark reports were generated as part of
> Week 7 PR #9.  These cover API latency, telemetry throughput, AI evaluation,
> and edge-vs-cloud comparison.  Reuse the existing files from
> `benchmark_results/` for Week 8 evidence.  The full procedure for generating
> or regenerating them is in the
> [Week 7 Evidence Pack](week7_evidence_pack.md#windows-powershell-runbook).
>
> To regenerate all benchmarks plus resource utilization in one command see
> [Week 8 Benchmarking](week8_benchmarking.md).

---

## 11. Reliability Logs

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 11.1 | Structured backend log showing normal operation | PowerShell: start backend with `Tee-Object -FilePath .\backend.log`; capture a log snippet | |
| 11.2 | Log lines showing retry/backoff behavior (if triggered) | PowerShell: `Select-String -Path .\backend.log -Pattern "WARNING","ERROR","retry","backoff"` | |
| 11.3 | Log showing `timestamp \| component \| level \| message` format | Screenshot of log lines matching the structured format | |

> **Week 7 reuse note:** Reliability logging was implemented in Week 7 PR #8.
> If you captured structured log screenshots during Week 7, reuse them here
> unless you want fresh logs from a new validation run.

---

## 12. Error Handling and UI/UX Polish

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 12.1 | Telemetry empty state | Open `http://localhost:3000/telemetry` with an empty database; screenshot showing "No telemetry records yet" message and simulator hint | |
| 12.2 | Alerts empty state | Open `http://localhost:3000/alerts` with no faults; screenshot showing "No fault alerts yet" message and fault injection hint | |
| 12.3 | Node Status empty state | Open `http://localhost:3000/nodes` with an empty database; screenshot showing "No node status records yet" message | |
| 12.4 | Predictions empty state | Open `http://localhost:3000/predictions` with no prediction records; screenshot showing "No AI prediction records yet" message | |
| 12.5 | API error banner — any page | Stop the backend, open any page (e.g. `/telemetry`); screenshot showing the red "Unable to load" banner | |
| 12.6 | Prediction cycle failure | With backend down, click "Refresh Now" on `/predictions`; screenshot showing the yellow "Prediction cycle failed" banner | |

> **How to create an empty-database state:** Stop the backend, clear the
> database tables (or point to a fresh DB), then restart the backend and open
> the pages listed above.
>
> **How to trigger a backend-down error:** Stop the backend service while the
> frontend is running, then navigate to any dashboard page and screenshot the
> red error banner.

---

## Evidence summary

After collecting all items, record the final status here:

| Section | Items collected | Items reused from Week 7 | Outstanding |
|---|---|---|---|
| Dashboard | | | |
| Telemetry | | | |
| Alerts | | | |
| Node Status | | | |
| AI Predictions | | | |
| Recommendation Page | | | |
| Operator Approval | | | |
| Balancing History | | | |
| Decision Audit Trail | | | |
| Benchmark Results | | | |
| Reliability Logs | | | |
| Error Handling / UI Polish | | | |
| **Total** | | | |

---

## Related Week 8 docs

- [End-to-End Validation Runbook](week8_validation.md)
- [Functional Testing Checklist](week8_functional_testing.md)
- [Final Performance Benchmarking](week8_benchmarking.md)
- [Resource Utilization Profile](week8_resource_profile.md)
- [Simulator Realism Enhancement](simulator_realism.md)
- [Error Handling and UI/UX Polish](week8_error_handling.md)
- [Week 7 Evidence Pack](week7_evidence_pack.md)
