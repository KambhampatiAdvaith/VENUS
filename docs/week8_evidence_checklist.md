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
| 5.3 | At least one prediction with `predicted_fault: true` | Screenshot or API output showing a high-risk prediction | |
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
| 6.3 | Recommendation details (id, action, substation) | Screenshot or API output showing all key fields | |

---

## 7. Operator Approval

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 7.1 | Dashboard before approval (pending status visible) | Screenshot of the pending recommendation | |
| 7.2 | Dashboard after approval (status updated) | Screenshot showing `"approved"` or `"executed"` status | |
| 7.3 | Approval API response | PowerShell terminal screenshot showing `POST /load-balancing/<id>/approve` result | |
| 7.4 | Rejection API response | PowerShell terminal screenshot showing `POST /load-balancing/<id>/reject` result | |
| 7.5 | Dashboard after rejection (rejected status visible) | Screenshot showing `"Rejected"` status on the recommendation | |

---

## 8. Balancing History

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 8.1 | Balancing History page in dashboard | Screenshot showing executed actions after an approval | |
| 8.2 | `GET /load-balancing/history` API response | PowerShell: `(Invoke-WebRequest http://127.0.0.1:8000/load-balancing/history?limit=5).Content` | |
| 8.3 | Confirmation that rejected recommendations have no history entry | Compare history before/after rejection; no new executed entry | |

---

## 9. Decision Audit Trail

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 9.1 | Decision Audit Trail page in dashboard | Screenshot showing audit records with actions and timestamps | |
| 9.2 | Audit record for an approved recommendation | Screenshot or API output showing `action: "approved"` with timestamp | |
| 9.3 | Audit record for a rejected recommendation | Screenshot or API output showing `action: "rejected"` with no execution timestamp | |

---

## 10. Benchmark Results

| # | Evidence item | How to capture | Status |
|---|---|---|---|
| 10.1 | Combined Week 7 benchmark Markdown report | Reuse `benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.md` — see note below | |
| 10.2 | API latency benchmark results | Reuse `benchmark_results/api_latency_YYYYMMDD_HHMMSS.md` | |
| 10.3 | Telemetry throughput benchmark results | Reuse `benchmark_results/telemetry_throughput_YYYYMMDD_HHMMSS.md` | |
| 10.4 | Edge vs Cloud comparison report | Reuse `benchmark_results/edge_cloud_comparison_YYYYMMDD_HHMMSS.md` | |

> **Week 7 reuse note:** All benchmark reports were generated as part of
> Week 7 PR #9.  These cover API latency, telemetry throughput, AI evaluation,
> and edge-vs-cloud comparison.  Reuse the existing files from
> `benchmark_results/` for Week 8 evidence.  The full procedure for generating
> or regenerating them is in the
> [Week 7 Evidence Pack](week7_evidence_pack.md#windows-powershell-runbook).

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
| **Total** | | | |

---

## Related Week 8 docs

- [End-to-End Validation Runbook](week8_validation.md)
- [Functional Testing Checklist](week8_functional_testing.md)
- [Week 7 Evidence Pack](week7_evidence_pack.md)
