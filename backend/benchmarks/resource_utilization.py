"""
V.E.N.U.S. Resource Utilization Profiler
==========================================
Collects a short-duration resource profile of the host and running Docker
containers and writes Markdown + JSON reports.

Usage (from the backend/ directory):
    python -m benchmarks.resource_utilization
    python -m benchmarks.resource_utilization --duration 15 --interval 1

Windows PowerShell:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python -m benchmarks.resource_utilization --duration 15 --interval 1

Optional dependency — psutil gives more accurate per-process metrics:
    pip install psutil

If psutil is not installed the script falls back to stdlib-only collection and
records a warning in the report.

Docker is optional.  If Docker CLI is unavailable or the daemon is not
running the script records a warning and continues without container stats.

Output files (default: ../benchmark_results relative to this script):
    resource_profile_YYYYMMDD_HHMMSS.md
    resource_profile_YYYYMMDD_HHMMSS.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Optional psutil import
# ---------------------------------------------------------------------------

try:
    import psutil  # type: ignore

    _PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore
    _PSUTIL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Container name/image keyword matching
# ---------------------------------------------------------------------------

_CONTAINER_KEYWORDS: dict[str, list[str]] = {
    "fastapi_backend": ["fastapi", "backend", "uvicorn", "venus"],
    "postgresql": ["postgres", "postgresql", "pg"],
    "kafka": ["kafka"],
    "zookeeper": ["zookeeper", "zk"],
    "mqtt_mosquitto": ["mosquitto", "mqtt", "emqx"],
    "frontend_nextjs": ["frontend", "nextjs", "next"],
}


def _matches_service(name: str, image: str) -> str | None:
    """Return the service label if the container name/image matches a known service."""
    combined = (name + " " + image).lower()
    for service, keywords in _CONTAINER_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return service
    return None


# ---------------------------------------------------------------------------
# Host resource collection
# ---------------------------------------------------------------------------


def _collect_host_psutil() -> dict[str, Any]:
    """Collect host CPU and memory stats using psutil."""
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    return {
        "cpu_percent": round(cpu, 2),
        "memory_total_mb": round(mem.total / 1024 / 1024, 1),
        "memory_used_mb": round(mem.used / 1024 / 1024, 1),
        "memory_available_mb": round(mem.available / 1024 / 1024, 1),
        "memory_percent": round(mem.percent, 2),
        "source": "psutil",
    }


def _collect_host_stdlib() -> dict[str, Any]:
    """
    Collect basic host info using stdlib only.
    CPU usage is not reliably available without psutil, so we report N/A.
    """
    result: dict[str, Any] = {
        "cpu_percent": "N/A (psutil not installed)",
        "memory_total_mb": "N/A",
        "memory_used_mb": "N/A",
        "memory_available_mb": "N/A",
        "memory_percent": "N/A",
        "source": "stdlib",
    }

    # Try /proc/meminfo on Linux
    meminfo_path = Path("/proc/meminfo")
    if meminfo_path.exists():
        try:
            raw = meminfo_path.read_text(encoding="utf-8")
            parsed: dict[str, int] = {}
            for line in raw.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    parsed[parts[0].rstrip(":")] = int(parts[1])
            total_kb = parsed.get("MemTotal", 0)
            avail_kb = parsed.get("MemAvailable", parsed.get("MemFree", 0))
            used_kb = total_kb - avail_kb
            if total_kb:
                result["memory_total_mb"] = round(total_kb / 1024, 1)
                result["memory_used_mb"] = round(used_kb / 1024, 1)
                result["memory_available_mb"] = round(avail_kb / 1024, 1)
                result["memory_percent"] = round(used_kb / total_kb * 100, 2)
        except Exception:
            pass

    return result


def collect_host_resources() -> dict[str, Any]:
    if _PSUTIL_AVAILABLE:
        return _collect_host_psutil()
    return _collect_host_stdlib()


# ---------------------------------------------------------------------------
# Process resource collection
# ---------------------------------------------------------------------------


def collect_process_resources() -> dict[str, Any]:
    """Collect CPU/memory of the current Python process (best-effort)."""
    result: dict[str, Any] = {"pid": os.getpid(), "source": "unknown"}
    if _PSUTIL_AVAILABLE:
        try:
            proc = psutil.Process()
            mem_info = proc.memory_info()
            result["cpu_percent"] = round(proc.cpu_percent(interval=0.2), 2)
            result["rss_mb"] = round(mem_info.rss / 1024 / 1024, 2)
            result["vms_mb"] = round(mem_info.vms / 1024 / 1024, 2)
            result["source"] = "psutil"
        except Exception as exc:
            result["error"] = str(exc)
    else:
        result["note"] = "psutil not available; process metrics skipped"
    return result


# ---------------------------------------------------------------------------
# Docker container stats
# ---------------------------------------------------------------------------


def _run_docker_ps() -> list[dict[str, str]]:
    """Return a list of running containers as {id, name, image}."""
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.ID}}\t{{.Names}}\t{{.Image}}"],
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        containers = []
        for line in out.decode("utf-8", errors="replace").strip().splitlines():
            parts = line.split("\t")
            if len(parts) == 3:
                containers.append(
                    {"id": parts[0], "name": parts[1], "image": parts[2]}
                )
        return containers
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []


def _run_docker_stats(container_id: str) -> dict[str, str]:
    """Return a single-sample docker stats dict for one container."""
    try:
        out = subprocess.check_output(
            [
                "docker",
                "stats",
                "--no-stream",
                "--format",
                "{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}",
                container_id,
            ],
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
        parts = out.decode("utf-8", errors="replace").strip().split("\t")
        if len(parts) == 5:
            return {
                "cpu_percent": parts[0],
                "mem_usage": parts[1],
                "mem_percent": parts[2],
                "net_io": parts[3],
                "block_io": parts[4],
            }
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    return {}


def collect_docker_stats(warnings: list[str]) -> dict[str, Any]:
    """
    Collect per-container resource stats for known V.E.N.U.S. services.
    Returns a dict of service_label -> stats (or {} if Docker is unavailable).
    Appends warning messages to the supplied list.
    """
    # Check Docker availability
    try:
        subprocess.check_output(
            ["docker", "info"],
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except FileNotFoundError:
        warnings.append(
            "Docker CLI not found. Container stats skipped. "
            "Install Docker Desktop or Docker Engine to enable container profiling."
        )
        return {}
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        warnings.append(
            "Docker daemon not responding (daemon may not be running). "
            "Container stats skipped."
        )
        return {}

    containers = _run_docker_ps()
    if not containers:
        warnings.append(
            "No running Docker containers found. "
            "Start the V.E.N.U.S. stack with docker-compose to collect container stats."
        )
        return {}

    result: dict[str, Any] = {}
    for c in containers:
        service = _matches_service(c["name"], c["image"])
        if service is None:
            continue
        stats = _run_docker_stats(c["id"])
        if stats:
            result[service] = {
                "container_name": c["name"],
                "image": c["image"],
                **stats,
            }

    if not result:
        warnings.append(
            "Docker is running but no containers matched V.E.N.U.S. service names. "
            "Ensure containers are named or imaged with keywords: "
            + ", ".join(
                kw
                for kwlist in _CONTAINER_KEYWORDS.values()
                for kw in kwlist
            )
            + "."
        )

    return result


# ---------------------------------------------------------------------------
# Backend health check
# ---------------------------------------------------------------------------


def check_backend_health(base_url: str) -> dict[str, Any]:
    """Perform a lightweight /health check.  Returns status dict."""
    url = f"{base_url.rstrip('/')}/health"
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            return {
                "reachable": True,
                "status_code": resp.status,
                "latency_ms": elapsed_ms,
            }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "reachable": False,
            "error": str(exc),
            "latency_ms": elapsed_ms,
        }


# ---------------------------------------------------------------------------
# Multi-sample collection loop
# ---------------------------------------------------------------------------


def collect_samples(
    duration_s: float,
    interval_s: float,
) -> list[dict[str, Any]]:
    """
    Collect host resource samples for *duration_s* seconds,
    sleeping *interval_s* between samples.
    Returns a list of per-sample dicts.
    """
    samples: list[dict[str, Any]] = []
    end_time = time.monotonic() + duration_s
    while time.monotonic() < end_time:
        ts = datetime.now(timezone.utc).isoformat()
        host = collect_host_resources()
        sample: dict[str, Any] = {"timestamp": ts, "host": host}
        samples.append(sample)
        remaining = end_time - time.monotonic()
        if remaining > 0:
            time.sleep(min(interval_s, remaining))
    return samples


def _summarise_float_series(values: list[float]) -> dict[str, float]:
    if not values:
        return {}
    return {
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "avg": round(sum(values) / len(values), 2),
    }


def summarise_samples(samples: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute min/max/avg of numeric host metrics across all samples."""
    if not samples:
        return {}

    cpu_vals: list[float] = []
    mem_pct_vals: list[float] = []
    mem_used_vals: list[float] = []

    for s in samples:
        host = s.get("host", {})
        cpu = host.get("cpu_percent")
        if isinstance(cpu, (int, float)):
            cpu_vals.append(float(cpu))
        mem_pct = host.get("memory_percent")
        if isinstance(mem_pct, (int, float)):
            mem_pct_vals.append(float(mem_pct))
        mem_used = host.get("memory_used_mb")
        if isinstance(mem_used, (int, float)):
            mem_used_vals.append(float(mem_used))

    summary: dict[str, Any] = {"sample_count": len(samples)}
    if cpu_vals:
        summary["cpu_percent"] = _summarise_float_series(cpu_vals)
    if mem_pct_vals:
        summary["memory_percent"] = _summarise_float_series(mem_pct_vals)
    if mem_used_vals:
        summary["memory_used_mb"] = _summarise_float_series(mem_used_vals)

    # Pass through memory_total_mb from first sample
    first_host = samples[0].get("host", {}) if samples else {}
    if isinstance(first_host.get("memory_total_mb"), (int, float)):
        summary["memory_total_mb"] = first_host["memory_total_mb"]

    return summary


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _fmt(val: Any) -> str:
    if val is None:
        return "N/A"
    return str(val)


def build_markdown(
    run_ts: str,
    base_url: str,
    duration_s: float,
    interval_s: float,
    host_summary: dict[str, Any],
    process_info: dict[str, Any],
    docker_stats: dict[str, Any],
    health_check: dict[str, Any],
    warnings: list[str],
    psutil_available: bool,
) -> str:
    lines: list[str] = [
        "# V.E.N.U.S. Resource Utilization Profile",
        "",
        f"**Run:** {run_ts}  ",
        f"**Target:** {base_url}  ",
        f"**Duration:** {duration_s}s  |  **Interval:** {interval_s}s  ",
        f"**psutil available:** {'Yes' if psutil_available else 'No (stdlib fallback)'}  ",
        "",
    ]

    # Warnings
    if warnings:
        lines += ["## Warnings", ""]
        for w in warnings:
            lines.append(f"> ⚠️  {w}")
        lines += [""]

    # Backend health
    lines += [
        "## Backend Health Check",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| URL | {base_url}/health |",
        f"| Reachable | {health_check.get('reachable', 'N/A')} |",
        f"| Status code | {_fmt(health_check.get('status_code'))} |",
        f"| Latency (ms) | {_fmt(health_check.get('latency_ms'))} |",
    ]
    if not health_check.get("reachable"):
        lines.append(
            f"| Error | {_fmt(health_check.get('error'))} |"
        )
    lines += [""]

    # Host summary
    cpu = host_summary.get("cpu_percent") or {}
    mem_pct = host_summary.get("memory_percent") or {}
    mem_used = host_summary.get("memory_used_mb") or {}
    total_mb = host_summary.get("memory_total_mb", "N/A")
    sample_count = host_summary.get("sample_count", "N/A")

    lines += [
        "## Host Resource Summary",
        "",
        f"*{sample_count} samples collected over {duration_s}s*",
        "",
        "| Metric | Min | Avg | Max |",
        "|---|---|---|---|",
        (
            f"| CPU usage (%) "
            f"| {_fmt(cpu.get('min'))} "
            f"| {_fmt(cpu.get('avg'))} "
            f"| {_fmt(cpu.get('max'))} |"
        ),
        (
            f"| Memory usage (%) "
            f"| {_fmt(mem_pct.get('min'))} "
            f"| {_fmt(mem_pct.get('avg'))} "
            f"| {_fmt(mem_pct.get('max'))} |"
        ),
        (
            f"| Memory used (MB) "
            f"| {_fmt(mem_used.get('min'))} "
            f"| {_fmt(mem_used.get('avg'))} "
            f"| {_fmt(mem_used.get('max'))} |"
        ),
        f"| Memory total (MB) | — | {_fmt(total_mb)} | — |",
        "",
    ]

    # Process info
    lines += [
        "## Python Process",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| PID | {_fmt(process_info.get('pid'))} |",
        f"| CPU (%) | {_fmt(process_info.get('cpu_percent'))} |",
        f"| RSS (MB) | {_fmt(process_info.get('rss_mb'))} |",
        f"| VMS (MB) | {_fmt(process_info.get('vms_mb'))} |",
        f"| Source | {_fmt(process_info.get('source'))} |",
        "",
    ]

    # Docker container stats
    if docker_stats:
        lines += [
            "## Docker Container Stats",
            "",
            "| Service | Container | CPU (%) | Memory Usage | Memory (%) |",
            "|---|---|---|---|---|",
        ]
        for svc, s in docker_stats.items():
            lines.append(
                f"| {svc} "
                f"| {s.get('container_name', 'N/A')} "
                f"| {s.get('cpu_percent', 'N/A')} "
                f"| {s.get('mem_usage', 'N/A')} "
                f"| {s.get('mem_percent', 'N/A')} |"
            )
        lines += [""]
    else:
        lines += [
            "## Docker Container Stats",
            "",
            "*No container stats available — see Warnings above.*",
            "",
        ]

    # Footer
    lines += [
        "---",
        "",
        "> Generated by `benchmarks.resource_utilization`.",
        "> Install psutil (`pip install psutil`) for richer process metrics.",
    ]

    return "\n".join(lines)


def save_reports(
    run_ts: str,
    base_url: str,
    duration_s: float,
    interval_s: float,
    samples: list[dict[str, Any]],
    host_summary: dict[str, Any],
    process_info: dict[str, Any],
    docker_stats: dict[str, Any],
    health_check: dict[str, Any],
    warnings: list[str],
    output_dir: Path,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "benchmark": "resource_profile",
        "timestamp": run_ts,
        "target_url": base_url,
        "configuration": {
            "duration_s": duration_s,
            "interval_s": interval_s,
            "psutil_available": _PSUTIL_AVAILABLE,
            "platform": platform.system(),
            "python_version": platform.python_version(),
        },
        "host_summary": host_summary,
        "process_info": process_info,
        "docker_container_stats": docker_stats,
        "backend_health_check": health_check,
        "warnings": warnings,
        "samples": samples,
    }

    stem = f"resource_profile_{run_ts}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_content = build_markdown(
        run_ts=run_ts,
        base_url=base_url,
        duration_s=duration_s,
        interval_s=interval_s,
        host_summary=host_summary,
        process_info=process_info,
        docker_stats=docker_stats,
        health_check=health_check,
        warnings=warnings,
        psutil_available=_PSUTIL_AVAILABLE,
    )
    md_path.write_text(md_content, encoding="utf-8")

    return json_path, md_path


# ---------------------------------------------------------------------------
# Public run() function (importable by run_week7_benchmarks.py)
# ---------------------------------------------------------------------------


def run(
    base_url: str,
    duration_s: float,
    interval_s: float,
    output_dir: Path,
) -> dict[str, Any]:
    """
    Execute the resource utilization profile and write reports.
    Returns the JSON-serialisable payload dict.
    """
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    warnings: list[str] = []

    if not _PSUTIL_AVAILABLE:
        warnings.append(
            "psutil is not installed.  Some host and process metrics are unavailable.  "
            "Install with: pip install psutil"
        )

    print(f"\n=== V.E.N.U.S. Resource Utilization Profiler  [{run_ts}] ===")
    print(f"Target  : {base_url}")
    print(f"Duration: {duration_s}s  |  Interval: {interval_s}s")
    print(f"psutil  : {'available' if _PSUTIL_AVAILABLE else 'NOT installed (stdlib fallback)'}")

    # Backend health check (non-blocking)
    print("\nChecking backend health …")
    health_check = check_backend_health(base_url)
    if health_check["reachable"]:
        print(f"  Backend reachable: HTTP {health_check['status_code']} "
              f"in {health_check['latency_ms']} ms")
    else:
        print(f"  Backend not reachable: {health_check.get('error')}")
        warnings.append(
            f"Backend at {base_url}/health is not reachable: "
            f"{health_check.get('error', 'unknown error')}.  "
            "Start the backend before running a full evidence collection."
        )

    # Process info (snapshot before sampling loop)
    process_info = collect_process_resources()

    # Docker container stats
    print("\nCollecting Docker container stats …")
    docker_stats = collect_docker_stats(warnings)
    if docker_stats:
        print(f"  Found {len(docker_stats)} matching container(s): "
              + ", ".join(docker_stats.keys()))
    else:
        print("  No matching container stats collected.")

    # Host resource sampling loop
    print(f"\nSampling host resources for {duration_s}s …")
    samples = collect_samples(duration_s=duration_s, interval_s=interval_s)
    host_summary = summarise_samples(samples)
    print(f"  {len(samples)} sample(s) collected.")

    if host_summary.get("cpu_percent"):
        cpu = host_summary["cpu_percent"]
        print(
            f"  CPU  : min={cpu['min']}%  avg={cpu['avg']}%  max={cpu['max']}%"
        )
    if host_summary.get("memory_percent"):
        mem = host_summary["memory_percent"]
        print(
            f"  Mem  : min={mem['min']}%  avg={mem['avg']}%  max={mem['max']}%"
        )

    # Save reports
    json_path, md_path = save_reports(
        run_ts=run_ts,
        base_url=base_url,
        duration_s=duration_s,
        interval_s=interval_s,
        samples=samples,
        host_summary=host_summary,
        process_info=process_info,
        docker_stats=docker_stats,
        health_check=health_check,
        warnings=warnings,
        output_dir=output_dir,
    )

    print(f"\nReports saved:")
    print(f"  JSON : {json_path}")
    print(f"  MD   : {md_path}")

    return {
        "host_summary": host_summary,
        "process_info": process_info,
        "docker_container_stats": docker_stats,
        "backend_health_check": health_check,
        "warnings": warnings,
        "sample_count": len(samples),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="V.E.N.U.S. resource utilization profiler — collects host CPU/memory "
        "and Docker container stats."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL for /health availability check (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=15.0,
        help="Profiling duration in seconds (default: 15)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between samples (default: 1)",
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
        duration_s=args.duration,
        interval_s=args.interval,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
