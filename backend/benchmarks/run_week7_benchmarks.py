"""
V.E.N.U.S. Week 7 Benchmark Runner
=====================================
Orchestrates all Week 7 benchmarks and produces a combined JSON + Markdown
summary report.

Usage (from the backend/ directory):
    python -m benchmarks.run_week7_benchmarks
    python -m benchmarks.run_week7_benchmarks --base-url http://127.0.0.1:8000 --duration 30

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
) -> None:
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    print("=" * 60)
    print("  V.E.N.U.S. Week 7 Benchmark Suite")
    print(f"  {run_ts}")
    print("=" * 60)
    print(f"  Target URL : {base_url}")
    print(f"  API requests per endpoint : {n_requests}")
    print(f"  Throughput duration : {duration_s}s")
    print(f"  Throughput target rate : {target_rate} req/s")
    print()

    _check_reachability(base_url)

    # --- Phase 1: API latency ---
    print("\n[1/2] Running API latency benchmark …")
    api_results = run_api_latency(
        base_url=base_url,
        n_requests=n_requests,
        output_dir=output_dir,
        timeout=api_timeout,
    )

    # --- Phase 2: Throughput ---
    print("\n[2/2] Running telemetry throughput benchmark …")
    throughput_results = run_throughput(
        base_url=base_url,
        duration_s=duration_s,
        target_rate=target_rate,
        output_dir=output_dir,
        timeout=throughput_timeout,
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
    )


if __name__ == "__main__":
    main()
