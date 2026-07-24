"""
V.E.N.U.S. API Latency Benchmark
=================================
Measures HTTP response latency for the dashboard-critical API endpoints.

Usage (from the backend/ directory):
    python -m benchmarks.api_latency_benchmark
    python -m benchmarks.api_latency_benchmark --base-url http://127.0.0.1:8000 --requests 50

Windows PowerShell:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python -m benchmarks.api_latency_benchmark --base-url http://127.0.0.1:8000 --requests 50
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
# Endpoints to benchmark
# ---------------------------------------------------------------------------

DEFAULT_ENDPOINTS: list[dict[str, str]] = [
    {"name": "dashboard_metrics", "path": "/dashboard/metrics"},
    {"name": "telemetry_list", "path": "/telemetry?limit=25"},
    {"name": "telemetry_latest", "path": "/telemetry/latest"},
    {"name": "telemetry_latency", "path": "/telemetry/latency"},
    {"name": "nodes", "path": "/nodes"},
    {"name": "load_balancing", "path": "/load-balancing?limit=8"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request_once(url: str, timeout: float = 10.0) -> tuple[bool, float, int]:
    """
    Perform a single GET request and return (success, elapsed_ms, status_code).
    """
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            _ = resp.read()
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return True, elapsed_ms, resp.status
    except urllib.error.HTTPError as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return False, elapsed_ms, exc.code
    except Exception:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return False, elapsed_ms, 0


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


def benchmark_endpoint(
    base_url: str,
    endpoint: dict[str, str],
    n_requests: int,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """Run *n_requests* sequential requests against one endpoint and return stats."""
    url = f"{base_url.rstrip('/')}{endpoint['path']}"
    name = endpoint["name"]
    latencies: list[float] = []
    successes = 0
    failures = 0
    status_codes: dict[str, int] = {}

    print(f"  [{name}] {url} — {n_requests} requests …", end="", flush=True)

    for _ in range(n_requests):
        ok, ms, code = _request_once(url, timeout=timeout)
        if ok:
            successes += 1
            latencies.append(ms)
        else:
            failures += 1
        code_key = str(code)
        status_codes[code_key] = status_codes.get(code_key, 0) + 1

    sorted_lat = sorted(latencies)

    if latencies:
        result: dict[str, Any] = {
            "endpoint": name,
            "url": url,
            "requests": n_requests,
            "successes": successes,
            "failures": failures,
            "status_codes": status_codes,
            "latency_ms": {
                "min": round(min(latencies), 2),
                "max": round(max(latencies), 2),
                "avg": round(statistics.mean(latencies), 2),
                "median": round(statistics.median(latencies), 2),
                "p95": round(_percentile(sorted_lat, 95), 2),
                "stdev": round(statistics.stdev(latencies), 2) if len(latencies) > 1 else 0.0,
            },
        }
        print(
            f" done  min={result['latency_ms']['min']:.1f}ms"
            f"  avg={result['latency_ms']['avg']:.1f}ms"
            f"  p95={result['latency_ms']['p95']:.1f}ms"
            f"  max={result['latency_ms']['max']:.1f}ms"
            f"  errors={failures}"
        )
    else:
        result = {
            "endpoint": name,
            "url": url,
            "requests": n_requests,
            "successes": 0,
            "failures": failures,
            "status_codes": status_codes,
            "latency_ms": None,
        }
        print(f" ALL FAILED (status_codes={status_codes})")

    return result


# ---------------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------------


def _summary_table(results: list[dict[str, Any]]) -> str:
    """Return a Markdown table summarising the latency results."""
    header = (
        "| Endpoint | Requests | Successes | Failures | "
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


def save_reports(
    base_url: str,
    n_requests: int,
    results: list[dict[str, Any]],
    output_dir: Path,
    run_ts: str,
) -> tuple[Path, Path]:
    """Write JSON and Markdown report files; return their paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "benchmark": "api_latency",
        "timestamp": run_ts,
        "target_url": base_url,
        "requests_per_endpoint": n_requests,
        "endpoints": results,
    }

    stem = f"api_latency_{run_ts}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = [
        "# V.E.N.U.S. API Latency Benchmark",
        "",
        f"**Run:** {run_ts}  ",
        f"**Target:** {base_url}  ",
        f"**Requests per endpoint:** {n_requests}",
        "",
        "## Results",
        "",
        _summary_table(results),
        "",
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    return json_path, md_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(
    base_url: str,
    n_requests: int,
    output_dir: Path,
    timeout: float = 10.0,
) -> list[dict[str, Any]]:
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"\n=== V.E.N.U.S. API Latency Benchmark  [{run_ts}] ===")
    print(f"Target : {base_url}")
    print(f"Requests per endpoint : {n_requests}")
    print()

    # Quick reachability check
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

    results: list[dict[str, Any]] = []
    for ep in DEFAULT_ENDPOINTS:
        results.append(benchmark_endpoint(base_url, ep, n_requests, timeout=timeout))

    json_path, md_path = save_reports(base_url, n_requests, results, output_dir, run_ts)
    print(f"\nReports saved:")
    print(f"  JSON : {json_path}")
    print(f"  Markdown : {md_path}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark V.E.N.U.S. API endpoint latency."
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
        help="Number of requests per endpoint (default: 30)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for report files (default: ../benchmark_results relative to this script)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Per-request timeout in seconds (default: 10)",
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
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
