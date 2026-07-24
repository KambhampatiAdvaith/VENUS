"""
V.E.N.U.S. Telemetry Throughput Benchmark
==========================================
Measures:
  1. Synthetic telemetry generation/publish rate using the simulator endpoint.
  2. Database row-growth rate (telemetry rows inserted per second).
  3. Optional: API ingestion throughput via the simulate endpoint.

Usage (from the backend/ directory):
    python -m benchmarks.telemetry_throughput_benchmark
    python -m benchmarks.telemetry_throughput_benchmark --duration 30 --rate 20

Windows PowerShell:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python -m benchmarks.telemetry_throughput_benchmark --duration 30 --rate 20

Prerequisites:
  - Backend running: python -m uvicorn backend.api.main:app --reload
  - PostgreSQL accessible (for DB row-growth measurement).
  - Kafka/MQTT services optional; skipped gracefully when unavailable.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Simulator endpoints that insert rows into the DB
# ---------------------------------------------------------------------------

SIMULATE_ENDPOINTS: list[dict[str, str]] = [
    {"name": "simulate_normal", "path": "/telemetry/simulate/normal", "method": "POST"},
    {"name": "simulate_overload_a", "path": "/telemetry/simulate/overload-a", "method": "POST"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_once(url: str, timeout: float = 15.0) -> tuple[bool, float, int]:
    """POST to *url* and return (success, elapsed_ms, status_code)."""
    start = time.perf_counter()
    req = urllib.request.Request(url, data=b"", method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _ = resp.read()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return True, elapsed_ms, resp.status
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return False, elapsed_ms, exc.code
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return False, elapsed_ms, 0


def _get_telemetry_row_count(base_url: str, timeout: float = 10.0) -> int | None:
    """
    Fetch the current telemetry row count via the /dashboard/metrics endpoint.
    Returns None when unavailable.
    """
    url = f"{base_url.rstrip('/')}/dashboard/metrics"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = json.loads(resp.read())
            # dashboard/metrics returns total_nodes but not row count;
            # use /telemetry?limit=1 and then rely on row-count from a separate call
            return body.get("telemetry_count") or body.get("total_telemetry")
    except Exception:
        return None


def _get_row_count_via_health(base_url: str, timeout: float = 10.0) -> int | None:
    """
    Use GET /telemetry?limit=1 as a proxy for DB reachability and fall back
    to a dedicated row-count endpoint if one exists.
    """
    url = f"{base_url.rstrip('/')}/telemetry/count"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = json.loads(resp.read())
            return int(body.get("count", 0))
    except Exception:
        pass

    # No dedicated endpoint: approximate by fetching a large page and counting
    url2 = f"{base_url.rstrip('/')}/telemetry?limit=1"
    try:
        with urllib.request.urlopen(url2, timeout=timeout) as resp:
            _ = resp.read()
            # We cannot get the true total count from a limited list endpoint,
            # so return None to signal "unavailable" rather than a wrong number.
    except Exception:
        pass
    return None


def _check_reachability(base_url: str) -> None:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/health", timeout=5) as r:
            _ = r.read()
    except Exception as exc:
        print(
            f"ERROR: Cannot reach {base_url}/health — {exc}\n"
            "Make sure the backend is running:\n"
            "  cd backend\n"
            "  .\\venv\\Scripts\\Activate.ps1\n"
            "  python -m uvicorn backend.api.main:app --reload",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Core benchmark
# ---------------------------------------------------------------------------


def benchmark_simulate_throughput(
    base_url: str,
    duration_s: float,
    target_rate: float,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """
    Send simulate requests at *target_rate* req/s for *duration_s* seconds.
    Returns a dict with throughput stats.
    """
    print(
        f"\n--- Simulate Throughput ---\n"
        f"  Duration : {duration_s}s\n"
        f"  Target rate : {target_rate} req/s\n"
        f"  Endpoint : {SIMULATE_ENDPOINTS[0]['path']}\n"
    )
    interval = 1.0 / target_rate if target_rate > 0 else 0.0
    endpoint = SIMULATE_ENDPOINTS[0]
    url = f"{base_url.rstrip('/')}{endpoint['path']}"

    successes = 0
    failures = 0
    latencies: list[float] = []
    start_wall = time.perf_counter()
    deadline = start_wall + duration_s
    next_tick = start_wall

    while time.perf_counter() < deadline:
        now = time.perf_counter()
        if now < next_tick:
            time.sleep(next_tick - now)
        ok, ms, _ = _post_once(url, timeout=timeout)
        if ok:
            successes += 1
            latencies.append(ms)
        else:
            failures += 1
        next_tick += interval

    elapsed = time.perf_counter() - start_wall
    total = successes + failures
    observed_rate = total / elapsed if elapsed > 0 else 0.0

    result: dict[str, Any] = {
        "endpoint": endpoint["name"],
        "url": url,
        "target_rate_per_s": target_rate,
        "duration_s": round(elapsed, 2),
        "total_requests": total,
        "successes": successes,
        "failures": failures,
        "observed_rate_per_s": round(observed_rate, 2),
    }
    if latencies:
        result["avg_latency_ms"] = round(sum(latencies) / len(latencies), 2)

    print(
        f"  Sent {total} requests in {elapsed:.1f}s "
        f"({observed_rate:.1f} req/s, {failures} errors)"
    )
    return result


def benchmark_db_row_growth(
    base_url: str,
    duration_s: float,
    target_rate: float,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """
    Measure telemetry row growth before/after sending simulate requests.
    Uses the /dashboard/metrics or /telemetry/count endpoint when available.
    """
    print("\n--- DB Row Growth ---")

    row_count_before: int | None = None
    row_count_after: int | None = None

    # Try to read row count before
    row_count_before = _get_row_count_via_health(base_url, timeout)
    if row_count_before is None:
        row_count_before = _get_telemetry_row_count(base_url, timeout)
    print(f"  Row count before : {row_count_before if row_count_before is not None else 'unavailable'}")

    # Send burst of simulate calls and measure time
    interval = 1.0 / target_rate if target_rate > 0 else 0.0
    endpoint = SIMULATE_ENDPOINTS[0]
    url = f"{base_url.rstrip('/')}{endpoint['path']}"
    successes = 0
    failures = 0
    start_wall = time.perf_counter()
    deadline = start_wall + duration_s
    next_tick = start_wall

    while time.perf_counter() < deadline:
        now = time.perf_counter()
        if now < next_tick:
            time.sleep(next_tick - now)
        ok, _, _ = _post_once(url, timeout=timeout)
        if ok:
            successes += 1
        else:
            failures += 1
        next_tick += interval

    elapsed = time.perf_counter() - start_wall

    # Brief pause to allow DB writes to flush
    time.sleep(0.5)

    # Try to read row count after
    row_count_after = _get_row_count_via_health(base_url, timeout)
    if row_count_after is None:
        row_count_after = _get_telemetry_row_count(base_url, timeout)
    print(f"  Row count after  : {row_count_after if row_count_after is not None else 'unavailable'}")

    rows_inserted: int | None = None
    rows_per_sec: float | None = None
    if row_count_before is not None and row_count_after is not None:
        rows_inserted = row_count_after - row_count_before
        rows_per_sec = round(rows_inserted / elapsed, 2) if elapsed > 0 else 0.0
        print(f"  Rows inserted    : {rows_inserted} ({rows_per_sec} rows/s)")
    else:
        print("  Row count unavailable — no dedicated /telemetry/count endpoint.")

    return {
        "row_count_before": row_count_before,
        "row_count_after": row_count_after,
        "rows_inserted": rows_inserted,
        "elapsed_s": round(elapsed, 2),
        "rows_per_sec": rows_per_sec,
        "simulate_successes": successes,
        "simulate_failures": failures,
    }


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------


def save_reports(
    base_url: str,
    duration_s: float,
    target_rate: float,
    throughput_result: dict[str, Any],
    db_result: dict[str, Any],
    output_dir: Path,
    run_ts: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "benchmark": "telemetry_throughput",
        "timestamp": run_ts,
        "target_url": base_url,
        "duration_s": duration_s,
        "target_rate_per_s": target_rate,
        "simulate_throughput": throughput_result,
        "db_row_growth": db_result,
    }

    stem = f"telemetry_throughput_{run_ts}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows_per_sec = db_result.get("rows_per_sec")
    rows_inserted = db_result.get("rows_inserted")

    md_lines = [
        "# V.E.N.U.S. Telemetry Throughput Benchmark",
        "",
        f"**Run:** {run_ts}  ",
        f"**Target:** {base_url}  ",
        f"**Duration:** {duration_s}s  ",
        f"**Target rate:** {target_rate} req/s",
        "",
        "## Simulate Throughput",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total requests | {throughput_result.get('total_requests', 'N/A')} |",
        f"| Successes | {throughput_result.get('successes', 'N/A')} |",
        f"| Failures | {throughput_result.get('failures', 'N/A')} |",
        f"| Observed rate (req/s) | {throughput_result.get('observed_rate_per_s', 'N/A')} |",
        f"| Avg latency (ms) | {throughput_result.get('avg_latency_ms', 'N/A')} |",
        "",
        "## DB Row Growth",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Rows before | {db_result.get('row_count_before', 'N/A')} |",
        f"| Rows after | {db_result.get('row_count_after', 'N/A')} |",
        f"| Rows inserted | {rows_inserted if rows_inserted is not None else 'N/A'} |",
        f"| Rows/sec | {rows_per_sec if rows_per_sec is not None else 'N/A'} |",
        "",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return json_path, md_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(
    base_url: str,
    duration_s: float,
    target_rate: float,
    output_dir: Path,
    timeout: float = 15.0,
) -> dict[str, Any]:
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"\n=== V.E.N.U.S. Telemetry Throughput Benchmark  [{run_ts}] ===")
    print(f"Target : {base_url}")
    print(f"Duration : {duration_s}s  |  Target rate : {target_rate} req/s")

    _check_reachability(base_url)

    throughput_result = benchmark_simulate_throughput(base_url, duration_s, target_rate, timeout)
    db_result = benchmark_db_row_growth(base_url, duration_s, target_rate, timeout)

    json_path, md_path = save_reports(
        base_url, duration_s, target_rate, throughput_result, db_result, output_dir, run_ts
    )
    print(f"\nReports saved:")
    print(f"  JSON : {json_path}")
    print(f"  Markdown : {md_path}")

    return {
        "simulate_throughput": throughput_result,
        "db_row_growth": db_result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark V.E.N.U.S. telemetry throughput."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=30.0,
        help="Benchmark duration in seconds (default: 30)",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=10.0,
        help="Target simulate requests per second (default: 10, keep modest on local machines)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for report files (default: ../benchmark_results relative to this script)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Per-request timeout in seconds (default: 15)",
    )
    args = parser.parse_args()

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(__file__).parent.parent.parent / "benchmark_results"

    run(
        base_url=args.base_url,
        duration_s=args.duration,
        target_rate=args.rate,
        output_dir=output_dir,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
