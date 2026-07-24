"""
V.E.N.U.S. Week 7 Benchmark Runner
=====================================
Orchestrates all Week 7 benchmarks and produces a combined JSON + Markdown
summary report.

Usage (from the backend/ directory):
    python -m benchmarks.run_week7_benchmarks
    python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --duration 30

Include AI evaluation metrics (Week 7 PR #6):
    python -m benchmarks.run_week7_benchmarks --ai-eval

Include Edge vs Cloud comparison evidence (Week 7 PR #7):
    python -m benchmarks.run_week7_benchmarks --edge-cloud

Windows PowerShell:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --duration 30

Prerequisites:
  - Backend running: python -m uvicorn backend.api.main:app --reload
  - PostgreSQL accessible (required for the backend to start).
  - Kafka/MQTT optional; skipped gracefully.

Output:
  benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.json
  benchmark_results/week7_benchmark_YYYYMMDD_HHMMSS.md
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.api_latency_benchmark import run as run_api_latency
from benchmarks.ai_evaluation_metrics import run as run_ai_eval
from benchmarks.edge_cloud_comparison import run as run_edge_cloud
from benchmarks.telemetry_throughput_benchmark import run as run_throughput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_reachability(base_url: str) -> None:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/health", timeout=5) as r:
            _ = r.read()
    except Exception as exc:
        print(
            f"ERROR: Cannot reach {base_url}/health — {exc}\n"
            "\nPlease start the backend first:\n"
            "  cd backend\n"
            "  .\\venv\\Scripts\\Activate.ps1          # Windows\n"
            "  source venv/bin/activate               # macOS/Linux\n"
            "  python -m uvicorn backend.api.main:app --reload",
            file=sys.stderr,
        )
        sys.exit(1)


def _md_section(title: str, rows: list[tuple[str, Any]]) -> str:
    header = f"## {title}\n\n| Metric | Value |\n|---|---|\n"
    return header + "\n".join(f"| {k} | {v} |" for k, v in rows) + "\n"


# ---------------------------------------------------------------------------
# Combined report
# ---------------------------------------------------------------------------


def save_combined_report(
    base_url: str,
    duration_s: float,
    n_requests: int,
    target_rate: float,
    api_results: list[dict[str, Any]],
    throughput_results: dict[str, Any],
    output_dir: Path,
    run_ts: str,
    ai_eval_results: dict[str, Any] | None = None,
    edge_cloud_results: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "benchmark": "week7_full",
        "timestamp": run_ts,
        "target_url": base_url,
        "configuration": {
            "api_requests_per_endpoint": n_requests,
            "throughput_duration_s": duration_s,
            "throughput_target_rate_per_s": target_rate,
        },
        "api_latency": api_results,
        "telemetry_throughput": throughput_results.get("simulate_throughput"),
        "db_row_growth": throughput_results.get("db_row_growth"),
    }

    if ai_eval_results is not None:
        payload["ai_evaluation"] = ai_eval_results
    if edge_cloud_results is not None:
        payload["edge_cloud_comparison"] = edge_cloud_results

    stem = f"week7_benchmark_{run_ts}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # --- Markdown summary ---
    lines: list[str] = [
        "# V.E.N.U.S. Week 7 Benchmark Summary",
        "",
        f"**Run:** {run_ts}  ",
        f"**Target:** {base_url}  ",
        f"**API requests per endpoint:** {n_requests}  ",
        f"**Throughput duration:** {duration_s}s  ",
        f"**Throughput target rate:** {target_rate} req/s",
        "",
    ]

    # API latency table
    lines += [
        "## API Latency",
        "",
        "| Endpoint | Requests | OK | Errors | Min (ms) | Avg (ms) | Median (ms) | P95 (ms) | Max (ms) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in api_results:
        lat = r.get("latency_ms") or {}
        lines.append(
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

    lines += [""]

    # Throughput
    tp = throughput_results.get("simulate_throughput") or {}
    db = throughput_results.get("db_row_growth") or {}
    lines += [
        "## Telemetry Throughput",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Total simulate requests | {tp.get('total_requests', 'N/A')} |",
        f"| Successes | {tp.get('successes', 'N/A')} |",
        f"| Failures | {tp.get('failures', 'N/A')} |",
        f"| Observed rate (req/s) | {tp.get('observed_rate_per_s', 'N/A')} |",
        f"| Avg simulate latency (ms) | {tp.get('avg_latency_ms', 'N/A')} |",
        "",
        "## Database Row Growth",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Rows before benchmark | {db.get('row_count_before', 'N/A')} |",
        f"| Rows after benchmark | {db.get('row_count_after', 'N/A')} |",
        f"| Rows inserted | {db.get('rows_inserted', 'N/A')} |",
        f"| Rows per second | {db.get('rows_per_sec', 'N/A')} |",
        "",
    ]

    # AI evaluation summary (optional)
    if ai_eval_results is not None:
        db_eval = ai_eval_results.get("db_prediction_evaluation", {})
        total = db_eval.get("total_predictions", "N/A")
        anomaly_rate = db_eval.get("anomaly_rate_percent", "N/A")
        ps = db_eval.get("probability_stats") or {}
        cd = db_eval.get("confidence_distribution") or {}
        supervised = db_eval.get("supervised_metrics_available", False)

        lines += [
            "## AI Prediction Evaluation",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total predictions evaluated | {total} |",
            f"| Anomaly rate | {anomaly_rate}% |",
            f"| Avg probability | {ps.get('avg', 'N/A')} |",
            f"| Median probability | {ps.get('median', 'N/A')} |",
            f"| P95 probability | {ps.get('p95', 'N/A')} |",
            f"| High-confidence count (≥0.8) | {cd.get('high_count', 'N/A')} |",
            f"| Medium-confidence count (0.5–0.8) | {cd.get('medium_count', 'N/A')} |",
            f"| Low-confidence count (<0.5) | {cd.get('low_count', 'N/A')} |",
            f"| Supervised metrics available | {supervised} |",
            "",
        ]

        # AI endpoint latency
        ep_results = ai_eval_results.get("ai_endpoint_latency", [])
        if ep_results:
            lines += [
                "## AI Endpoint Latency",
                "",
                "| Endpoint | Requests | OK | Errors | Min (ms) | Avg (ms) | P95 (ms) | Max (ms) |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for r in ep_results:
                lat = r.get("latency_ms") or {}
                lines.append(
                    f"| {r['endpoint']} "
                    f"| {r['requests']} "
                    f"| {r['successes']} "
                    f"| {r['failures']} "
                    f"| {lat.get('min', 'N/A')} "
                    f"| {lat.get('avg', 'N/A')} "
                    f"| {lat.get('p95', 'N/A')} "
                    f"| {lat.get('max', 'N/A')} |"
                )
            lines += [""]

    if edge_cloud_results is not None:
        db_result = edge_cloud_results.get("database", {})
        edge = db_result.get("edge_coverage", {})
        cloud = db_result.get("cloud_coverage", {})
        agreement = edge_cloud_results.get("agreement_summary", {})
        recency = edge_cloud_results.get("recency_summary", {})
        gap = recency.get("cloud_minus_edge_seconds") or {}
        agreement_rate = agreement.get("agreement_rate_percent")

        lines += [
            "## Edge vs Cloud Comparison",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| DB available | {db_result.get('db_available', False)} |",
            f"| Telemetry rows with edge outputs | {edge.get('telemetry_rows_with_edge_outputs', 'N/A')} |",
            f"| Total prediction rows | {cloud.get('total_prediction_rows', 'N/A')} |",
            f"| Edge substations covered | {edge.get('distinct_substations_with_edge_outputs', 'N/A')} |",
            f"| Cloud substations covered | {cloud.get('prediction_distinct_substations', 'N/A')} |",
            f"| Paired substations | {agreement.get('paired_substations', 0)} |",
            f"| Operational agreement rate | {f'{agreement_rate}%' if agreement_rate is not None else 'N/A'} |",
            f"| Latest edge age (s) | {recency.get('latest_edge_age_seconds', 'N/A')} |",
            f"| Latest cloud age (s) | {recency.get('latest_cloud_age_seconds', 'N/A')} |",
            f"| Cloud minus edge median (s) | {gap.get('median', 'N/A')} |",
            "",
        ]

        endpoint_results = edge_cloud_results.get("endpoint_timing", [])
        if endpoint_results:
            lines += [
                "## Edge/Cloud Endpoint Timing",
                "",
                "| Endpoint | Requests | OK | Errors | Min (ms) | Avg (ms) | P95 (ms) | Max (ms) |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for r in endpoint_results:
                lat = r.get("latency_ms") or {}
                lines.append(
                    f"| {r['endpoint']} "
                    f"| {r['requests']} "
                    f"| {r['successes']} "
                    f"| {r['failures']} "
                    f"| {lat.get('min', 'N/A')} "
                    f"| {lat.get('avg', 'N/A')} "
                    f"| {lat.get('p95', 'N/A')} "
                    f"| {lat.get('max', 'N/A')} |"
                )
            lines += [""]

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(
    base_url: str,
    n_requests: int,
    duration_s: float,
    target_rate: float,
    output_dir: Path,
    api_timeout: float = 10.0,
    throughput_timeout: float = 15.0,
    ai_eval: bool = False,
    ai_eval_requests: int = 10,
    edge_cloud: bool = False,
    edge_cloud_requests: int = 10,
) -> None:
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    total_phases = 2 + int(ai_eval) + int(edge_cloud)

    print("=" * 60)
    print("  V.E.N.U.S. Week 7 Benchmark Suite")
    print(f"  {run_ts}")
    print("=" * 60)
    print(f"  Target URL : {base_url}")
    print(f"  API requests per endpoint : {n_requests}")
    print(f"  Throughput duration : {duration_s}s")
    print(f"  Throughput target rate : {target_rate} req/s")
    if ai_eval:
        print(f"  AI evaluation : enabled ({ai_eval_requests} req/endpoint)")
    if edge_cloud:
        print(f"  Edge vs cloud : enabled ({edge_cloud_requests} req/endpoint)")
    print()

    _check_reachability(base_url)

    # --- Phase 1: API latency ---
    phase = 1

    print(f"\n[{phase}/{total_phases}] Running API latency benchmark …")
    api_results = run_api_latency(
        base_url=base_url,
        n_requests=n_requests,
        output_dir=output_dir,
        timeout=api_timeout,
    )
    phase += 1

    # --- Phase 2: Throughput ---
    print(f"\n[{phase}/{total_phases}] Running telemetry throughput benchmark …")
    throughput_results = run_throughput(
        base_url=base_url,
        duration_s=duration_s,
        target_rate=target_rate,
        output_dir=output_dir,
        timeout=throughput_timeout,
    )
    phase += 1

    # --- Phase 3: AI evaluation (optional) ---
    ai_eval_results: dict[str, Any] | None = None
    if ai_eval:
        print(f"\n[{phase}/{total_phases}] Running AI evaluation metrics …")
        ai_eval_results = run_ai_eval(
            base_url=base_url,
            n_requests=ai_eval_requests,
            output_dir=output_dir,
        )
        phase += 1

    edge_cloud_results: dict[str, Any] | None = None
    if edge_cloud:
        print(f"\n[{phase}/{total_phases}] Running edge vs cloud comparison …")
        edge_cloud_results = run_edge_cloud(
            base_url=base_url,
            n_requests=edge_cloud_requests,
            output_dir=output_dir,
        )

    # --- Combined report ---
    json_path, md_path = save_combined_report(
        base_url=base_url,
        duration_s=duration_s,
        n_requests=n_requests,
        target_rate=target_rate,
        api_results=api_results,
        throughput_results=throughput_results,
        output_dir=output_dir,
        run_ts=run_ts,
        ai_eval_results=ai_eval_results,
        edge_cloud_results=edge_cloud_results,
    )

    print("\n" + "=" * 60)
    print("  Week 7 benchmark complete!")
    print(f"  JSON report  : {json_path}")
    print(f"  MD report    : {md_path}")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run all V.E.N.U.S. Week 7 benchmarks and produce a combined report."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=30,
        help="Number of requests per API endpoint (default: 30)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Throughput benchmark duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=10.0,
        help="Target simulate requests per second (default: 10)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for report files (default: ../benchmark_results relative to this script)",
    )
    parser.add_argument(
        "--ai-eval",
        action="store_true",
        default=False,
        help="Also run AI evaluation metrics (Week 7 PR #6 evidence)",
    )
    parser.add_argument(
        "--ai-eval-requests",
        type=int,
        default=10,
        help="Requests per AI endpoint for latency timing (default: 10, only used with --ai-eval)",
    )
    parser.add_argument(
        "--edge-cloud",
        action="store_true",
        default=False,
        help="Also run Edge vs Cloud comparison evidence (Week 7 PR #7)",
    )
    parser.add_argument(
        "--edge-cloud-requests",
        type=int,
        default=10,
        help="Requests per edge/cloud endpoint for timing (default: 10, only used with --edge-cloud)",
    )
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent.parent.parent / "benchmark_results"

    run(
        base_url=args.base_url,
        n_requests=args.requests,
        duration_s=args.duration,
        target_rate=args.rate,
        output_dir=output_dir,
        ai_eval=args.ai_eval,
        ai_eval_requests=args.ai_eval_requests,
        edge_cloud=args.edge_cloud,
        edge_cloud_requests=args.edge_cloud_requests,
    )


if __name__ == "__main__":
    main()
