"""
V.E.N.U.S. AI Evaluation Metrics
==================================
Evaluates the V.E.N.U.S. predictive fault/anomaly intelligence layer by
querying the existing ``predictions`` table and measuring AI endpoint latency.

No ground-truth fault labels are stored in the repository/database, so
**supervised** metrics (accuracy, precision, recall, F1, confusion matrix) are
honestly reported as unavailable.  The script produces an *operational /
descriptive* evaluation that is still useful as Week 7 evidence.

Usage (from the ``backend/`` directory):
    python -m benchmarks.ai_evaluation_metrics
    python -m benchmarks.ai_evaluation_metrics --base-url http://127.0.0.1:8000

Windows PowerShell:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python -m benchmarks.ai_evaluation_metrics --base-url http://127.0.0.1:8000

Run with optional live prediction trigger (writes to DB — use sparingly):
    python -m benchmarks.ai_evaluation_metrics --run-prediction

Options:
    --base-url URL       Backend base URL (default: http://127.0.0.1:8000)
    --requests N         Requests per AI endpoint for latency timing (default: 10)
    --output-dir PATH    Directory for report files (default: ../benchmark_results)
    --run-prediction     Trigger /predictions/run once and include in latency stats
    --timeout SECONDS    Per-request HTTP timeout (default: 15)
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# AI endpoints to measure
# ---------------------------------------------------------------------------

AI_ENDPOINTS: list[dict[str, str]] = [
    {"name": "predictions_metrics", "path": "/predictions/metrics"},
    {"name": "predictions_list", "path": "/predictions?limit=50"},
]

# /predictions/run is POST and potentially expensive; only included when
# --run-prediction is explicitly requested.
RUN_PREDICTION_ENDPOINT: dict[str, str] = {
    "name": "predictions_run",
    "path": "/predictions/run",
}


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only — no extra dependencies)
# ---------------------------------------------------------------------------


def _get_once(url: str, timeout: float = 15.0) -> tuple[bool, float, int, bytes]:
    """GET *url*; return (success, elapsed_ms, status_code, body)."""
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return True, elapsed_ms, resp.status, body
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return False, elapsed_ms, exc.code, b""
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return False, elapsed_ms, 0, b""


def _post_once(url: str, timeout: float = 30.0) -> tuple[bool, float, int, bytes]:
    """POST *url* with empty body; return (success, elapsed_ms, status_code, body)."""
    start = time.perf_counter()
    req = urllib.request.Request(url, data=b"{}", method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return True, elapsed_ms, resp.status, body
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return False, elapsed_ms, exc.code, b""
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return False, elapsed_ms, 0, b""


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Return the *pct*-th percentile (0–100) from a pre-sorted list."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * pct / 100.0
    lo = int(k)
    hi = lo + 1
    if hi >= len(sorted_values):
        return sorted_values[-1]
    frac = k - lo
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


def _latency_stats(latencies: list[float]) -> dict[str, Any]:
    if not latencies:
        return None  # type: ignore[return-value]
    s = sorted(latencies)
    return {
        "min": round(min(latencies), 2),
        "max": round(max(latencies), 2),
        "avg": round(statistics.mean(latencies), 2),
        "median": round(statistics.median(latencies), 2),
        "p95": round(_percentile(s, 95), 2),
        "stdev": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0.0,
    }


# ---------------------------------------------------------------------------
# AI endpoint latency benchmark
# ---------------------------------------------------------------------------


def benchmark_ai_endpoints(
    base_url: str,
    n_requests: int,
    run_prediction: bool,
    timeout: float,
) -> list[dict[str, Any]]:
    """Time each AI endpoint and return a list of per-endpoint result dicts."""
    endpoints = list(AI_ENDPOINTS)
    if run_prediction:
        endpoints.append(RUN_PREDICTION_ENDPOINT)

    results: list[dict[str, Any]] = []

    for ep in endpoints:
        url = f"{base_url.rstrip('/')}{ep['path']}"
        name = ep["name"]
        is_post = name == "predictions_run"
        repeat = 1 if is_post else n_requests

        latencies: list[float] = []
        successes = 0
        failures = 0

        print(
            f"  [{name}] {url} — {repeat} request(s) …",
            end="",
            flush=True,
        )

        for _ in range(repeat):
            if is_post:
                ok, ms, _code, _body = _post_once(url, timeout=timeout)
            else:
                ok, ms, _code, _body = _get_once(url, timeout=timeout)
            if ok:
                successes += 1
                latencies.append(ms)
            else:
                failures += 1

        stats = _latency_stats(latencies)

        if stats:
            print(
                f" done  min={stats['min']:.1f}ms"
                f"  avg={stats['avg']:.1f}ms"
                f"  p95={stats['p95']:.1f}ms"
                f"  max={stats['max']:.1f}ms"
                f"  errors={failures}"
            )
        else:
            print(f" ALL FAILED (errors={failures})")

        results.append(
            {
                "endpoint": name,
                "url": url,
                "requests": repeat,
                "successes": successes,
                "failures": failures,
                "latency_ms": stats,
            }
        )

    return results


# ---------------------------------------------------------------------------
# DB-level prediction evaluation
# ---------------------------------------------------------------------------


def _try_db_evaluation() -> dict[str, Any]:
    """
    Query the ``predictions`` table via SQLAlchemy and return descriptive stats.
    Returns a partial dict with ``db_available: False`` when DB is unreachable.
    """
    try:
        # Import lazily so the script still *loads* when the DB is unavailable.
        from backend.api.database import get_engine  # noqa: PLC0415
        from sqlalchemy import text as sa_text  # noqa: PLC0415
    except ImportError as exc:
        return {
            "db_available": False,
            "db_error": f"Import failed: {exc}",
            "supervised_metrics_available": False,
            "supervised_metrics_reason": (
                "No ground-truth fault labels found in repository/database schema."
            ),
        }

    try:
        engine = get_engine()

        # ── Basic count and coverage ─────────────────────────────────────────
        count_sql = sa_text(
            """
            SELECT
                COUNT(*)                         AS total_predictions,
                COUNT(DISTINCT substation)        AS distinct_substations,
                COUNT(*) FILTER (WHERE anomaly)   AS anomaly_true_count,
                MIN(timestamp)                    AS earliest_prediction,
                MAX(timestamp)                    AS latest_prediction
            FROM predictions
            """
        )

        # ── Probability distribution ─────────────────────────────────────────
        prob_sql = sa_text(
            """
            SELECT
                AVG(probability)                AS avg_probability,
                MIN(probability)                AS min_probability,
                MAX(probability)                AS max_probability,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY probability)
                                                AS median_probability,
                PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY probability)
                                                AS p95_probability,
                COUNT(*) FILTER (WHERE probability >= 0.8)  AS high_confidence_count,
                COUNT(*) FILTER (
                    WHERE probability >= 0.5 AND probability < 0.8
                )                               AS medium_confidence_count,
                COUNT(*) FILTER (WHERE probability < 0.5)   AS low_confidence_count
            FROM predictions
            """
        )

        # ── Fault distribution ───────────────────────────────────────────────
        fault_dist_sql = sa_text(
            """
            SELECT predicted_fault, COUNT(*) AS count
            FROM predictions
            GROUP BY predicted_fault
            ORDER BY count DESC
            """
        )

        # ── Anomaly score distribution ───────────────────────────────────────
        anomaly_sql = sa_text(
            """
            SELECT
                AVG(anomaly_score)    AS avg_anomaly_score,
                MIN(anomaly_score)    AS min_anomaly_score,
                MAX(anomaly_score)    AS max_anomaly_score
            FROM predictions
            """
        )

        with engine.begin() as conn:
            count_row = conn.execute(count_sql).mappings().first()
            prob_row = conn.execute(prob_sql).mappings().first()
            fault_rows = conn.execute(fault_dist_sql).mappings().all()
            anomaly_row = conn.execute(anomaly_sql).mappings().first()

        total = int(count_row["total_predictions"] or 0)

        if total == 0:
            return {
                "db_available": True,
                "predictions_table_available": True,
                "total_predictions": 0,
                "note": (
                    "Predictions table is empty. "
                    "Run a prediction cycle first: POST /predictions/run"
                ),
                "supervised_metrics_available": False,
                "supervised_metrics_reason": (
                    "No ground-truth fault labels found in repository/database schema."
                ),
            }

        anomaly_count = int(count_row["anomaly_true_count"] or 0)
        anomaly_rate = round(anomaly_count / total * 100, 2) if total else 0.0

        fault_distribution = {
            str(r["predicted_fault"]): int(r["count"]) for r in fault_rows
        }

        def _round_or_none(val: Any, ndigits: int = 4) -> Any:
            return round(float(val), ndigits) if val is not None else None

        # Format timestamps as ISO strings
        def _ts(val: Any) -> Any:
            if val is None:
                return None
            if isinstance(val, datetime):
                return val.isoformat()
            return str(val)

        return {
            "db_available": True,
            "predictions_table_available": True,
            "total_predictions": total,
            "distinct_substations": int(count_row["distinct_substations"] or 0),
            "earliest_prediction_timestamp": _ts(count_row["earliest_prediction"]),
            "latest_prediction_timestamp": _ts(count_row["latest_prediction"]),
            "predicted_fault_distribution": fault_distribution,
            "anomaly_true_count": anomaly_count,
            "anomaly_rate_percent": anomaly_rate,
            "probability_stats": {
                "avg": _round_or_none(prob_row["avg_probability"]),
                "min": _round_or_none(prob_row["min_probability"]),
                "max": _round_or_none(prob_row["max_probability"]),
                "median": _round_or_none(prob_row["median_probability"]),
                "p95": _round_or_none(prob_row["p95_probability"]),
            },
            "confidence_distribution": {
                "high_count": int(prob_row["high_confidence_count"] or 0),
                "medium_count": int(prob_row["medium_confidence_count"] or 0),
                "low_count": int(prob_row["low_confidence_count"] or 0),
            },
            "anomaly_score_stats": {
                "avg": _round_or_none(anomaly_row["avg_anomaly_score"]),
                "min": _round_or_none(anomaly_row["min_anomaly_score"]),
                "max": _round_or_none(anomaly_row["max_anomaly_score"]),
            },
            "supervised_metrics_available": False,
            "supervised_metrics_reason": (
                "No ground-truth fault labels found in repository/database schema."
            ),
        }

    except Exception as exc:  # noqa: BLE001
        return {
            "db_available": False,
            "db_error": str(exc),
            "supervised_metrics_available": False,
            "supervised_metrics_reason": (
                "No ground-truth fault labels found in repository/database schema."
            ),
        }


# ---------------------------------------------------------------------------
# Console summary printer
# ---------------------------------------------------------------------------


def _print_db_summary(db: dict[str, Any]) -> None:
    print("\n--- DB Prediction Evaluation ---")

    if not db.get("db_available"):
        print(f"  DB unavailable: {db.get('db_error', 'unknown error')}")
        print(
            "  To fix: ensure PostgreSQL is running and the backend can reach it.\n"
            "  Start the backend: python -m uvicorn backend.api.main:app --reload"
        )
        return

    if not db.get("predictions_table_available"):
        print("  Predictions table not accessible.")
        return

    total = db.get("total_predictions", 0)
    if total == 0:
        print(f"  {db.get('note', 'No predictions found.')}")
        print("  Supervised metrics: unavailable (no ground-truth labels)")
        return

    print(f"  Total predictions        : {total}")
    print(f"  Distinct substations     : {db.get('distinct_substations', 'N/A')}")
    print(f"  Latest prediction        : {db.get('latest_prediction_timestamp', 'N/A')}")

    fd = db.get("predicted_fault_distribution", {})
    if fd:
        print("  Fault distribution       :")
        for fault, cnt in fd.items():
            pct = round(cnt / total * 100, 1) if total else 0
            print(f"    {fault:<30} {cnt:>6}  ({pct:.1f}%)")

    print(f"  Anomaly count            : {db.get('anomaly_true_count', 'N/A')}")
    print(f"  Anomaly rate             : {db.get('anomaly_rate_percent', 'N/A')}%")

    ps = db.get("probability_stats", {})
    print(
        f"  Probability (avg/med/p95): "
        f"{ps.get('avg', 'N/A')} / {ps.get('median', 'N/A')} / {ps.get('p95', 'N/A')}"
    )

    cd = db.get("confidence_distribution", {})
    print(
        f"  Confidence distribution  : "
        f"high={cd.get('high_count', 'N/A')}  "
        f"medium={cd.get('medium_count', 'N/A')}  "
        f"low={cd.get('low_count', 'N/A')}"
    )

    print(
        f"  Supervised metrics       : unavailable — "
        f"{db.get('supervised_metrics_reason', '')}"
    )


def _print_endpoint_summary(results: list[dict[str, Any]]) -> None:
    print("\n--- AI Endpoint Latency ---")
    for r in results:
        lat = r.get("latency_ms")
        if lat:
            print(
                f"  [{r['endpoint']}]  "
                f"min={lat['min']:.1f}ms  avg={lat['avg']:.1f}ms  "
                f"p95={lat['p95']:.1f}ms  max={lat['max']:.1f}ms  "
                f"ok={r['successes']}  err={r['failures']}"
            )
        else:
            print(f"  [{r['endpoint']}]  ALL FAILED (errors={r['failures']})")


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------


def _latency_md_table(results: list[dict[str, Any]]) -> str:
    header = (
        "| Endpoint | Requests | OK | Errors | "
        "Min (ms) | Avg (ms) | Median (ms) | P95 (ms) | Max (ms) |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for r in results:
        lat = r.get("latency_ms") or {}
        rows.append(
            f"| {r['endpoint']} "
            f"| {r['requests']} "
            f"| {r['successes']} "
            f"| {r['failures']} "
            f"| {lat.get('min', 'N/A')} "
            f"| {lat.get('avg', 'N/A')} "
            f"| {lat.get('median', 'N/A')} "
            f"| {lat.get('p95', 'N/A')} "
            f"| {lat.get('max', 'N/A')} |"
        )
    return header + "\n".join(rows)


def _fault_dist_md_table(fd: dict[str, int], total: int) -> str:
    header = "| Predicted Fault | Count | % of total |\n|---|---|---|\n"
    rows = []
    for fault, cnt in fd.items():
        pct = round(cnt / total * 100, 1) if total else 0.0
        rows.append(f"| {fault} | {cnt} | {pct}% |")
    return header + "\n".join(rows)


def save_reports(
    base_url: str,
    n_requests: int,
    run_prediction: bool,
    db_eval: dict[str, Any],
    endpoint_results: list[dict[str, Any]],
    output_dir: Path,
    run_ts: str,
) -> tuple[Path, Path]:
    """Write JSON and Markdown report files; return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "benchmark": "ai_evaluation_metrics",
        "timestamp": run_ts,
        "target_url": base_url,
        "configuration": {
            "ai_endpoint_requests": n_requests,
            "run_prediction_triggered": run_prediction,
        },
        "db_prediction_evaluation": db_eval,
        "ai_endpoint_latency": endpoint_results,
    }

    stem = f"ai_evaluation_{run_ts}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    total = db_eval.get("total_predictions", 0)
    db_ok = db_eval.get("db_available", False)
    table_ok = db_eval.get("predictions_table_available", False)

    md_lines: list[str] = [
        "# V.E.N.U.S. AI Evaluation Metrics",
        "",
        f"**Run:** {run_ts}  ",
        f"**Target:** {base_url}  ",
        f"**AI endpoint requests:** {n_requests}  ",
        f"**Prediction cycle triggered:** {'Yes' if run_prediction else 'No'}",
        "",
        "---",
        "",
        "## Operational / Descriptive Evaluation",
        "",
        "> **Note:** No ground-truth fault labels exist in the database schema.",
        "> Supervised metrics (accuracy, precision, recall, F1, confusion matrix)",
        "> are therefore **unavailable**.",
        "> The metrics below are derived from the model's own prediction outputs.",
        "",
    ]

    if not db_ok:
        md_lines += [
            f"**DB unavailable:** {db_eval.get('db_error', 'unknown')}",
            "",
        ]
    elif not table_ok:
        md_lines += ["**Predictions table not accessible.**", ""]
    elif total == 0:
        md_lines += [
            f"**{db_eval.get('note', 'No predictions found.')}**",
            "",
        ]
    else:
        ps = db_eval.get("probability_stats", {})
        cd = db_eval.get("confidence_distribution", {})
        fd = db_eval.get("predicted_fault_distribution", {})

        md_lines += [
            "### Prediction Coverage",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total predictions | {total} |",
            f"| Distinct substations | {db_eval.get('distinct_substations', 'N/A')} |",
            f"| Earliest prediction | {db_eval.get('earliest_prediction_timestamp', 'N/A')} |",
            f"| Latest prediction | {db_eval.get('latest_prediction_timestamp', 'N/A')} |",
            "",
            "### Anomaly Detection",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Anomaly count | {db_eval.get('anomaly_true_count', 'N/A')} |",
            f"| Anomaly rate | {db_eval.get('anomaly_rate_percent', 'N/A')}% |",
            "",
            "### Confidence / Probability Distribution",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Average probability | {ps.get('avg', 'N/A')} |",
            f"| Min probability | {ps.get('min', 'N/A')} |",
            f"| Max probability | {ps.get('max', 'N/A')} |",
            f"| Median probability | {ps.get('median', 'N/A')} |",
            f"| P95 probability | {ps.get('p95', 'N/A')} |",
            f"| High confidence (≥0.8) | {cd.get('high_count', 'N/A')} |",
            f"| Medium confidence (0.5–0.8) | {cd.get('medium_count', 'N/A')} |",
            f"| Low confidence (<0.5) | {cd.get('low_count', 'N/A')} |",
            "",
        ]

        if fd:
            md_lines += [
                "### Predicted Fault Distribution",
                "",
                _fault_dist_md_table(fd, total),
                "",
            ]

    md_lines += [
        "### Supervised Metrics",
        "",
        f"| Available | {db_eval.get('supervised_metrics_available', False)} |",
        f"| Reason | {db_eval.get('supervised_metrics_reason', 'N/A')} |",
        "",
        "---",
        "",
        "## AI Endpoint Latency",
        "",
        _latency_md_table(endpoint_results),
        "",
    ]

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path, md_path


# ---------------------------------------------------------------------------
# Main run function (importable by run_week7_benchmarks)
# ---------------------------------------------------------------------------


def run(
    base_url: str,
    n_requests: int,
    output_dir: Path,
    run_prediction: bool = False,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """
    Run the AI evaluation benchmark and return a results dict.

    This function is designed to be called standalone **or** from
    ``run_week7_benchmarks``.
    """
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print(f"\n=== V.E.N.U.S. AI Evaluation Metrics  [{run_ts}] ===")
    print(f"Target : {base_url}")
    print(f"AI endpoint requests : {n_requests}")
    if run_prediction:
        print("Prediction trigger : enabled (POST /predictions/run × 1)")
    print()

    # ── Phase 1: DB evaluation ────────────────────────────────────────────
    print("--- Querying predictions table …")
    db_eval = _try_db_evaluation()
    _print_db_summary(db_eval)

    # ── Phase 2: Endpoint latency ─────────────────────────────────────────
    print("\n--- Timing AI endpoints …")
    try:
        with urllib.request.urlopen(
            f"{base_url.rstrip('/')}/health", timeout=5
        ) as _r:
            pass
        backend_reachable = True
    except Exception:
        backend_reachable = False

    if not backend_reachable:
        print(
            "  WARNING: Backend is not reachable. Endpoint latency stats will be empty.\n"
            "  Start the backend:\n"
            "    cd backend\n"
            "    .\\venv\\Scripts\\Activate.ps1\n"
            "    python -m uvicorn backend.api.main:app --reload"
        )
        endpoint_results: list[dict[str, Any]] = []
    else:
        endpoint_results = benchmark_ai_endpoints(
            base_url=base_url,
            n_requests=n_requests,
            run_prediction=run_prediction,
            timeout=timeout,
        )
        _print_endpoint_summary(endpoint_results)

    # ── Phase 3: Save reports ─────────────────────────────────────────────
    json_path, md_path = save_reports(
        base_url=base_url,
        n_requests=n_requests,
        run_prediction=run_prediction,
        db_eval=db_eval,
        endpoint_results=endpoint_results,
        output_dir=output_dir,
        run_ts=run_ts,
    )

    print(f"\nReports saved:")
    print(f"  JSON     : {json_path}")
    print(f"  Markdown : {md_path}")

    return {
        "run_ts": run_ts,
        "db_prediction_evaluation": db_eval,
        "ai_endpoint_latency": endpoint_results,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate V.E.N.U.S. AI prediction outputs and measure AI endpoint latency."
        )
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=10,
        help="Requests per AI endpoint for latency timing (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "Directory for report files "
            "(default: ../benchmark_results relative to this script)"
        ),
    )
    parser.add_argument(
        "--run-prediction",
        action="store_true",
        default=False,
        help=(
            "Trigger POST /predictions/run once before endpoint timing. "
            "This writes to the DB — use sparingly."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Per-request HTTP timeout in seconds (default: 15)",
    )
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent.parent.parent / "benchmark_results"

    run(
        base_url=args.base_url,
        n_requests=args.requests,
        output_dir=output_dir,
        run_prediction=args.run_prediction,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
