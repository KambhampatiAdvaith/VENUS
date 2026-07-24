"""
V.E.N.U.S. Edge vs Cloud Comparison Evidence
============================================
Produces lightweight Week 7 evidence comparing available edge-side telemetry
signals against cloud/backend prediction signals already stored by V.E.N.U.S.

This script does **not** invent supervised accuracy. When paired ground-truth
labels are unavailable, it reports only operational/descriptive comparison.

Usage (from the ``backend/`` directory):
    python -m benchmarks.edge_cloud_comparison
    python -m benchmarks.edge_cloud_comparison --base-url http://127.0.0.1:8000

Windows PowerShell:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python -m benchmarks.edge_cloud_comparison --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import statistics
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.api_latency_benchmark import benchmark_endpoint

EDGE_CLOUD_ENDPOINTS: list[dict[str, str]] = [
    {"name": "telemetry_list", "path": "/telemetry?limit=25"},
    {"name": "telemetry_latest", "path": "/telemetry/latest"},
    {"name": "nodes", "path": "/nodes"},
    {"name": "predictions_metrics", "path": "/predictions/metrics"},
    {"name": "predictions_list", "path": "/predictions"},
]


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * pct / 100.0
    lo = int(k)
    hi = lo + 1
    if hi >= len(sorted_values):
        return sorted_values[-1]
    frac = k - lo
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


def _stats(values: list[float], ndigits: int = 4) -> dict[str, float] | None:
    if not values:
        return None
    sorted_values = sorted(values)
    return {
        "avg": round(statistics.mean(values), ndigits),
        "min": round(min(values), ndigits),
        "max": round(max(values), ndigits),
        "median": round(statistics.median(values), ndigits),
        "p95": round(_percentile(sorted_values, 95), ndigits),
    }


def _normalize_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _isoformat(value: Any) -> str | None:
    normalized = _normalize_datetime(value)
    return normalized.isoformat() if normalized else None


def _age_seconds(value: Any, now: datetime) -> float | None:
    normalized = _normalize_datetime(value)
    if normalized is None:
        return None
    return round((now - normalized).total_seconds(), 4)


def _round_or_none(value: Any, ndigits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), ndigits)


def _display(value: Any, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{value}{suffix}"


def _backend_reachable(base_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/health", timeout=5) as response:
            _ = response.read()
        return True
    except Exception:
        return False


def _query_db() -> dict[str, Any]:
    try:
        from backend.api.database import get_engine  # noqa: PLC0415
        from sqlalchemy import text as sa_text  # noqa: PLC0415
    except ImportError as exc:
        return {
            "db_available": False,
            "db_error": f"Import failed: {exc}",
            "telemetry_table_available": False,
            "predictions_table_available": False,
        }

    try:
        engine = get_engine()
        with engine.begin() as connection:
            existence = connection.execute(
                sa_text(
                    """
                    SELECT
                        to_regclass('public.telemetry') IS NOT NULL AS telemetry_exists,
                        to_regclass('public.predictions') IS NOT NULL AS predictions_exists
                    """
                )
            ).mappings().first()

            telemetry_exists = bool(existence["telemetry_exists"])
            predictions_exists = bool(existence["predictions_exists"])

            result: dict[str, Any] = {
                "db_available": True,
                "telemetry_table_available": telemetry_exists,
                "predictions_table_available": predictions_exists,
            }

            if telemetry_exists:
                edge_coverage_row = connection.execute(
                    sa_text(
                        """
                        SELECT
                            COUNT(*) AS total_telemetry_rows,
                            COUNT(DISTINCT substation) AS telemetry_distinct_substations,
                            COUNT(*) FILTER (
                                WHERE edge_processed_at IS NOT NULL
                                   OR edge_model IS NOT NULL
                                   OR edge_anomaly_score IS NOT NULL
                                   OR edge_anomaly IS NOT NULL
                            ) AS telemetry_rows_with_edge_outputs,
                            COUNT(DISTINCT substation) FILTER (
                                WHERE edge_processed_at IS NOT NULL
                                   OR edge_model IS NOT NULL
                                   OR edge_anomaly_score IS NOT NULL
                                   OR edge_anomaly IS NOT NULL
                            ) AS distinct_substations_with_edge_outputs,
                            MAX(edge_processed_at) AS latest_edge_processed_at
                        FROM telemetry
                        """
                    )
                ).mappings().first()

                edge_score_row = connection.execute(
                    sa_text(
                        """
                        SELECT
                            AVG(edge_anomaly_score) AS avg_edge_anomaly_score,
                            MIN(edge_anomaly_score) AS min_edge_anomaly_score,
                            MAX(edge_anomaly_score) AS max_edge_anomaly_score,
                            PERCENTILE_CONT(0.5) WITHIN GROUP (
                                ORDER BY edge_anomaly_score
                            ) AS median_edge_anomaly_score,
                            PERCENTILE_CONT(0.95) WITHIN GROUP (
                                ORDER BY edge_anomaly_score
                            ) AS p95_edge_anomaly_score
                        FROM telemetry
                        WHERE edge_anomaly_score IS NOT NULL
                        """
                    )
                ).mappings().first()

                latest_edge_rows = connection.execute(
                    sa_text(
                        """
                        SELECT DISTINCT ON (substation)
                            substation,
                            edge_anomaly,
                            edge_anomaly_score,
                            edge_model,
                            edge_processed_at,
                            timestamp AS telemetry_timestamp
                        FROM telemetry
                        WHERE substation IS NOT NULL
                          AND (
                                edge_processed_at IS NOT NULL
                             OR edge_model IS NOT NULL
                             OR edge_anomaly_score IS NOT NULL
                             OR edge_anomaly IS NOT NULL
                          )
                        ORDER BY
                            substation,
                            COALESCE(edge_processed_at, database_written_at, timestamp) DESC,
                            id DESC
                        """
                    )
                ).mappings().all()

                total_rows = int(edge_coverage_row["total_telemetry_rows"] or 0)
                rows_with_edge = int(edge_coverage_row["telemetry_rows_with_edge_outputs"] or 0)
                result["edge_coverage"] = {
                    "total_telemetry_rows": total_rows,
                    "telemetry_rows_with_edge_outputs": rows_with_edge,
                    "edge_output_coverage_percent": (
                        round(rows_with_edge / total_rows * 100, 2) if total_rows else 0.0
                    ),
                    "telemetry_distinct_substations": int(
                        edge_coverage_row["telemetry_distinct_substations"] or 0
                    ),
                    "distinct_substations_with_edge_outputs": int(
                        edge_coverage_row["distinct_substations_with_edge_outputs"] or 0
                    ),
                    "latest_edge_processed_at": _isoformat(
                        edge_coverage_row["latest_edge_processed_at"]
                    ),
                    "edge_anomaly_score_stats": {
                        "avg": _round_or_none(edge_score_row["avg_edge_anomaly_score"]),
                        "min": _round_or_none(edge_score_row["min_edge_anomaly_score"]),
                        "max": _round_or_none(edge_score_row["max_edge_anomaly_score"]),
                        "median": _round_or_none(edge_score_row["median_edge_anomaly_score"]),
                        "p95": _round_or_none(edge_score_row["p95_edge_anomaly_score"]),
                    },
                    "latest_per_substation": [
                        {
                            "substation": row["substation"],
                            "edge_anomaly": (
                                None if row["edge_anomaly"] is None else bool(row["edge_anomaly"])
                            ),
                            "edge_anomaly_score": _round_or_none(row["edge_anomaly_score"]),
                            "edge_model": row["edge_model"],
                            "edge_processed_at": _isoformat(row["edge_processed_at"]),
                            "telemetry_timestamp": _isoformat(row["telemetry_timestamp"]),
                        }
                        for row in latest_edge_rows
                    ],
                }

            if predictions_exists:
                prediction_coverage_row = connection.execute(
                    sa_text(
                        """
                        SELECT
                            COUNT(*) AS total_prediction_rows,
                            COUNT(DISTINCT substation) AS prediction_distinct_substations,
                            MAX(timestamp) AS latest_prediction_timestamp
                        FROM predictions
                        """
                    )
                ).mappings().first()

                probability_row = connection.execute(
                    sa_text(
                        """
                        SELECT
                            AVG(probability) AS avg_probability,
                            MIN(probability) AS min_probability,
                            MAX(probability) AS max_probability,
                            PERCENTILE_CONT(0.5) WITHIN GROUP (
                                ORDER BY probability
                            ) AS median_probability,
                            PERCENTILE_CONT(0.95) WITHIN GROUP (
                                ORDER BY probability
                            ) AS p95_probability
                        FROM predictions
                        WHERE probability IS NOT NULL
                        """
                    )
                ).mappings().first()

                anomaly_score_row = connection.execute(
                    sa_text(
                        """
                        SELECT
                            AVG(anomaly_score) AS avg_anomaly_score,
                            MIN(anomaly_score) AS min_anomaly_score,
                            MAX(anomaly_score) AS max_anomaly_score,
                            PERCENTILE_CONT(0.5) WITHIN GROUP (
                                ORDER BY anomaly_score
                            ) AS median_anomaly_score,
                            PERCENTILE_CONT(0.95) WITHIN GROUP (
                                ORDER BY anomaly_score
                            ) AS p95_anomaly_score
                        FROM predictions
                        WHERE anomaly_score IS NOT NULL
                        """
                    )
                ).mappings().first()

                latest_prediction_rows = connection.execute(
                    sa_text(
                        """
                        SELECT DISTINCT ON (substation)
                            substation,
                            predicted_fault,
                            probability,
                            anomaly,
                            anomaly_score,
                            timestamp
                        FROM predictions
                        WHERE substation IS NOT NULL
                        ORDER BY substation, timestamp DESC, id DESC
                        """
                    )
                ).mappings().all()

                result["cloud_coverage"] = {
                    "total_prediction_rows": int(
                        prediction_coverage_row["total_prediction_rows"] or 0
                    ),
                    "prediction_distinct_substations": int(
                        prediction_coverage_row["prediction_distinct_substations"] or 0
                    ),
                    "latest_prediction_timestamp": _isoformat(
                        prediction_coverage_row["latest_prediction_timestamp"]
                    ),
                    "probability_stats": {
                        "avg": _round_or_none(probability_row["avg_probability"]),
                        "min": _round_or_none(probability_row["min_probability"]),
                        "max": _round_or_none(probability_row["max_probability"]),
                        "median": _round_or_none(probability_row["median_probability"]),
                        "p95": _round_or_none(probability_row["p95_probability"]),
                    },
                    "anomaly_score_stats": {
                        "avg": _round_or_none(anomaly_score_row["avg_anomaly_score"]),
                        "min": _round_or_none(anomaly_score_row["min_anomaly_score"]),
                        "max": _round_or_none(anomaly_score_row["max_anomaly_score"]),
                        "median": _round_or_none(anomaly_score_row["median_anomaly_score"]),
                        "p95": _round_or_none(anomaly_score_row["p95_anomaly_score"]),
                    },
                    "latest_per_substation": [
                        {
                            "substation": row["substation"],
                            "predicted_fault": row["predicted_fault"],
                            "probability": _round_or_none(row["probability"]),
                            "anomaly": (
                                None if row["anomaly"] is None else bool(row["anomaly"])
                            ),
                            "anomaly_score": _round_or_none(row["anomaly_score"]),
                            "timestamp": _isoformat(row["timestamp"]),
                        }
                        for row in latest_prediction_rows
                    ],
                }

            return result
    except Exception as exc:  # noqa: BLE001
        return {
            "db_available": False,
            "db_error": str(exc),
            "telemetry_table_available": False,
            "predictions_table_available": False,
        }


def _build_comparison_sections(db_result: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    now = datetime.now(timezone.utc)
    edge_rows = {
        row["substation"]: row
        for row in (db_result.get("edge_coverage", {}).get("latest_per_substation") or [])
        if row.get("substation")
    }
    cloud_rows = {
        row["substation"]: row
        for row in (db_result.get("cloud_coverage", {}).get("latest_per_substation") or [])
        if row.get("substation")
    }

    paired_substations = sorted(set(edge_rows) & set(cloud_rows))
    edge_only_substations = sorted(set(edge_rows) - set(cloud_rows))
    cloud_only_substations = sorted(set(cloud_rows) - set(edge_rows))

    comparison_rows: list[dict[str, Any]] = []
    agreement_count = 0
    disagreement_count = 0
    comparable_count = 0
    edge_age_values: list[float] = []
    cloud_age_values: list[float] = []
    cloud_minus_edge_values: list[float] = []

    for substation in paired_substations:
        edge_row = edge_rows[substation]
        cloud_row = cloud_rows[substation]

        edge_processed_at = edge_row.get("edge_processed_at")
        cloud_timestamp = cloud_row.get("timestamp")
        edge_age_seconds = _age_seconds(edge_processed_at, now)
        cloud_age_seconds = _age_seconds(cloud_timestamp, now)
        cloud_minus_edge_seconds = None

        edge_dt = _normalize_datetime(edge_processed_at)
        cloud_dt = _normalize_datetime(cloud_timestamp)
        if edge_age_seconds is not None:
            edge_age_values.append(edge_age_seconds)
        if cloud_age_seconds is not None:
            cloud_age_values.append(cloud_age_seconds)
        if edge_dt is not None and cloud_dt is not None:
            cloud_minus_edge_seconds = round((cloud_dt - edge_dt).total_seconds(), 4)
            cloud_minus_edge_values.append(cloud_minus_edge_seconds)

        edge_anomaly = edge_row.get("edge_anomaly")
        cloud_anomaly = cloud_row.get("anomaly")
        agreement = None
        if edge_anomaly is not None and cloud_anomaly is not None:
            comparable_count += 1
            agreement = bool(edge_anomaly) == bool(cloud_anomaly)
            if agreement:
                agreement_count += 1
            else:
                disagreement_count += 1

        comparison_rows.append(
            {
                "substation": substation,
                "edge_anomaly": edge_anomaly,
                "edge_anomaly_score": edge_row.get("edge_anomaly_score"),
                "edge_model": edge_row.get("edge_model"),
                "edge_processed_at": edge_processed_at,
                "edge_age_seconds": edge_age_seconds,
                "cloud_predicted_fault": cloud_row.get("predicted_fault"),
                "cloud_probability": cloud_row.get("probability"),
                "cloud_anomaly": cloud_anomaly,
                "cloud_anomaly_score": cloud_row.get("anomaly_score"),
                "cloud_timestamp": cloud_timestamp,
                "cloud_age_seconds": cloud_age_seconds,
                "cloud_minus_edge_seconds": cloud_minus_edge_seconds,
                "operational_agreement": agreement,
            }
        )

    edge_latest = db_result.get("edge_coverage", {}).get("latest_edge_processed_at")
    cloud_latest = db_result.get("cloud_coverage", {}).get("latest_prediction_timestamp")

    agreement_summary = {
        "paired_substations": len(paired_substations),
        "edge_only_substations": edge_only_substations,
        "cloud_only_substations": cloud_only_substations,
        "comparable_substations": comparable_count,
        "agreement_count": agreement_count,
        "disagreement_count": disagreement_count,
        "agreement_rate_percent": (
            round(agreement_count / comparable_count * 100, 2) if comparable_count else None
        ),
        "comparison_rows": comparison_rows,
        "note": (
            "Operational agreement compares latest edge anomaly booleans and latest "
            "cloud anomaly booleans per substation. It is not supervised accuracy."
        ),
    }

    recency_summary = {
        "latest_edge_processed_at": edge_latest,
        "latest_edge_age_seconds": _age_seconds(edge_latest, now),
        "latest_cloud_prediction_timestamp": cloud_latest,
        "latest_cloud_age_seconds": _age_seconds(cloud_latest, now),
        "paired_edge_age_seconds": _stats(edge_age_values),
        "paired_cloud_age_seconds": _stats(cloud_age_values),
        "cloud_minus_edge_seconds": _stats(cloud_minus_edge_values),
        "note": (
            "Positive cloud_minus_edge_seconds means the latest cloud prediction is newer "
            "than the latest edge output for that substation."
        ),
    }

    return agreement_summary, recency_summary


def benchmark_endpoints(
    base_url: str,
    n_requests: int,
    timeout: float,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for endpoint in EDGE_CLOUD_ENDPOINTS:
        results.append(benchmark_endpoint(base_url, endpoint, n_requests, timeout=timeout))
    return results


def _print_db_summary(result: dict[str, Any]) -> None:
    print("\n--- DB Coverage ---")
    if not result.get("db_available"):
        print(f"  DB unavailable: {result.get('db_error', 'unknown error')}")
        return

    if result.get("telemetry_table_available"):
        edge = result.get("edge_coverage", {})
        print(
            f"  Edge rows with outputs    : {edge.get('telemetry_rows_with_edge_outputs', 0)}"
            f" / {edge.get('total_telemetry_rows', 0)}"
        )
        print(
            f"  Edge substations covered  : "
            f"{edge.get('distinct_substations_with_edge_outputs', 0)}"
        )
        print(f"  Latest edge processed at  : {edge.get('latest_edge_processed_at', 'N/A')}")
    else:
        print("  Telemetry table unavailable.")

    if result.get("predictions_table_available"):
        cloud = result.get("cloud_coverage", {})
        print(f"  Cloud prediction rows     : {cloud.get('total_prediction_rows', 0)}")
        print(
            f"  Cloud substations covered : {cloud.get('prediction_distinct_substations', 0)}"
        )
        print(f"  Latest cloud prediction   : {cloud.get('latest_prediction_timestamp', 'N/A')}")
    else:
        print("  Predictions table unavailable.")


def _print_agreement_summary(agreement: dict[str, Any], recency: dict[str, Any]) -> None:
    print("\n--- Operational Agreement ---")
    print(f"  Paired substations        : {agreement.get('paired_substations', 0)}")
    print(f"  Comparable substations    : {agreement.get('comparable_substations', 0)}")
    print(f"  Agreement count           : {agreement.get('agreement_count', 0)}")
    print(f"  Disagreement count        : {agreement.get('disagreement_count', 0)}")
    print(
        f"  Agreement rate            : "
        f"{_display(agreement.get('agreement_rate_percent'), '%')}"
    )
    print("  Note                      : agreement is operational, not supervised accuracy")

    print("\n--- Recency Summary ---")
    print(
        f"  Latest edge age (s)       : "
        f"{_display(recency.get('latest_edge_age_seconds'))}"
    )
    print(
        f"  Latest cloud age (s)      : "
        f"{_display(recency.get('latest_cloud_age_seconds'))}"
    )
    gap = recency.get("cloud_minus_edge_seconds") or {}
    if gap:
        print(
            f"  Cloud-edge gap (avg/med)  : "
            f"{gap.get('avg', 'N/A')} / {gap.get('median', 'N/A')} seconds"
        )


def _latency_md_table(results: list[dict[str, Any]]) -> str:
    header = (
        "| Endpoint | Requests | OK | Errors | Min (ms) | Avg (ms) | Median (ms) | "
        "P95 (ms) | Max (ms) |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    rows = []
    for result in results:
        latency = result.get("latency_ms") or {}
        rows.append(
            f"| {result['endpoint']} | {result['requests']} | {result['successes']} | "
            f"{result['failures']} | {latency.get('min', 'N/A')} | "
            f"{latency.get('avg', 'N/A')} | {latency.get('median', 'N/A')} | "
            f"{latency.get('p95', 'N/A')} | {latency.get('max', 'N/A')} |"
        )
    return header + "\n".join(rows)


def save_reports(
    base_url: str,
    n_requests: int,
    db_result: dict[str, Any],
    agreement: dict[str, Any],
    recency: dict[str, Any],
    endpoint_results: list[dict[str, Any]],
    output_dir: Path,
    run_ts: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    caveats = [
        "Operational agreement compares latest edge and latest cloud anomaly booleans per substation.",
        "Agreement is not supervised accuracy because no ground-truth labels are joined in this report.",
        "Timestamp gaps are descriptive recency differences, not a full end-to-end latency SLA.",
    ]
    if not endpoint_results:
        caveats.append("Backend endpoint timing was skipped because the API was unreachable.")
    if not db_result.get("db_available"):
        caveats.append("Database-derived metrics were unavailable because the DB connection failed.")

    payload: dict[str, Any] = {
        "benchmark": "edge_cloud_comparison",
        "timestamp": run_ts,
        "target_url": base_url,
        "configuration": {"endpoint_requests": n_requests},
        "database": db_result,
        "agreement_summary": agreement,
        "recency_summary": recency,
        "endpoint_timing": endpoint_results,
        "caveats": caveats,
    }

    stem = f"edge_cloud_comparison_{run_ts}"
    json_path = output_dir / f"{stem}.json"
    md_path = output_dir / f"{stem}.md"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    edge = db_result.get("edge_coverage", {})
    cloud = db_result.get("cloud_coverage", {})
    edge_stats = edge.get("edge_anomaly_score_stats", {})
    cloud_prob = cloud.get("probability_stats", {})
    gap = recency.get("cloud_minus_edge_seconds") or {}

    md_lines = [
        "# V.E.N.U.S. Edge vs Cloud Comparison Evidence",
        "",
        f"**Run:** {run_ts}  ",
        f"**Target:** {base_url}  ",
        f"**Requests per timed endpoint:** {n_requests}",
        "",
        "> **Important:** Agreement in this report is **operational agreement only**.",
        "> It is **not supervised accuracy** unless future work adds paired ground-truth labels.",
        "",
        "## Caveats",
        "",
    ]
    md_lines.extend(f"- {caveat}" for caveat in caveats)
    md_lines += [
        "",
        "## Database Availability",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| DB available | {db_result.get('db_available', False)} |",
        f"| Telemetry table available | {db_result.get('telemetry_table_available', False)} |",
        f"| Predictions table available | {db_result.get('predictions_table_available', False)} |",
        f"| DB error | {db_result.get('db_error', 'N/A')} |",
        "",
    ]

    if db_result.get("telemetry_table_available"):
        md_lines += [
            "## Edge Coverage",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total telemetry rows | {edge.get('total_telemetry_rows', 'N/A')} |",
            f"| Telemetry rows with edge outputs | {edge.get('telemetry_rows_with_edge_outputs', 'N/A')} |",
            f"| Edge output coverage | {edge.get('edge_output_coverage_percent', 'N/A')}% |",
            f"| Distinct telemetry substations | {edge.get('telemetry_distinct_substations', 'N/A')} |",
            f"| Distinct substations with edge outputs | {edge.get('distinct_substations_with_edge_outputs', 'N/A')} |",
            f"| Latest edge processed at | {edge.get('latest_edge_processed_at', 'N/A')} |",
            f"| Edge anomaly score avg/min/max | {edge_stats.get('avg', 'N/A')} / {edge_stats.get('min', 'N/A')} / {edge_stats.get('max', 'N/A')} |",
            f"| Edge anomaly score median/p95 | {edge_stats.get('median', 'N/A')} / {edge_stats.get('p95', 'N/A')} |",
            "",
        ]

    if db_result.get("predictions_table_available"):
        cloud_anomaly = cloud.get("anomaly_score_stats", {})
        md_lines += [
            "## Cloud Coverage",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total prediction rows | {cloud.get('total_prediction_rows', 'N/A')} |",
            f"| Distinct substations with predictions | {cloud.get('prediction_distinct_substations', 'N/A')} |",
            f"| Latest cloud prediction timestamp | {cloud.get('latest_prediction_timestamp', 'N/A')} |",
            f"| Cloud probability avg/min/max | {cloud_prob.get('avg', 'N/A')} / {cloud_prob.get('min', 'N/A')} / {cloud_prob.get('max', 'N/A')} |",
            f"| Cloud probability median/p95 | {cloud_prob.get('median', 'N/A')} / {cloud_prob.get('p95', 'N/A')} |",
            f"| Cloud anomaly score avg/min/max | {cloud_anomaly.get('avg', 'N/A')} / {cloud_anomaly.get('min', 'N/A')} / {cloud_anomaly.get('max', 'N/A')} |",
            f"| Cloud anomaly score median/p95 | {cloud_anomaly.get('median', 'N/A')} / {cloud_anomaly.get('p95', 'N/A')} |",
            "",
        ]

    md_lines += [
        "## Operational Agreement Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Paired substations | {agreement.get('paired_substations', 0)} |",
        f"| Comparable substations | {agreement.get('comparable_substations', 0)} |",
        f"| Agreement count | {agreement.get('agreement_count', 0)} |",
        f"| Disagreement count | {agreement.get('disagreement_count', 0)} |",
        f"| Agreement rate | {_display(agreement.get('agreement_rate_percent'), '%')} |",
        f"| Edge-only substations | {', '.join(agreement.get('edge_only_substations', [])) or 'None'} |",
        f"| Cloud-only substations | {', '.join(agreement.get('cloud_only_substations', [])) or 'None'} |",
        "",
    ]

    comparison_rows = agreement.get("comparison_rows", [])
    if comparison_rows:
        md_lines += [
            "### Latest Paired Edge vs Cloud Rows",
            "",
            "| Substation | Edge anomaly | Cloud anomaly | Agreement | Edge score | Cloud probability | Cloud minus edge (s) |",
            "|---|---|---|---|---|---|---|",
        ]
        for row in comparison_rows:
            md_lines.append(
                f"| {row['substation']} | {row.get('edge_anomaly', 'N/A')} | "
                f"{row.get('cloud_anomaly', 'N/A')} | {row.get('operational_agreement', 'N/A')} | "
                f"{row.get('edge_anomaly_score', 'N/A')} | {row.get('cloud_probability', 'N/A')} | "
                f"{row.get('cloud_minus_edge_seconds', 'N/A')} |"
            )
        md_lines += [""]
    else:
        md_lines += ["No paired edge/cloud latest-per-substation rows were available.", ""]

    md_lines += [
        "## Recency Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Latest edge age (s) | {_display(recency.get('latest_edge_age_seconds'))} |",
        f"| Latest cloud age (s) | {_display(recency.get('latest_cloud_age_seconds'))} |",
        f"| Cloud minus edge avg/min/max (s) | {gap.get('avg', 'N/A')} / {gap.get('min', 'N/A')} / {gap.get('max', 'N/A')} |",
        f"| Cloud minus edge median/p95 (s) | {gap.get('median', 'N/A')} / {gap.get('p95', 'N/A')} |",
        "",
        "## Endpoint Timing",
        "",
    ]

    if endpoint_results:
        md_lines += [_latency_md_table(endpoint_results), ""]
    else:
        md_lines += ["Backend unavailable; endpoint timing was skipped.", ""]

    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    return json_path, md_path


def run(
    base_url: str,
    n_requests: int,
    output_dir: Path,
    timeout: float = 10.0,
) -> dict[str, Any]:
    run_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    print(f"\n=== V.E.N.U.S. Edge vs Cloud Comparison  [{run_ts}] ===")
    print(f"Target : {base_url}")
    print(f"Requests per timed endpoint : {n_requests}")

    db_result = _query_db()
    _print_db_summary(db_result)

    agreement, recency = _build_comparison_sections(db_result)
    _print_agreement_summary(agreement, recency)

    print("\n--- Endpoint Timing ---")
    if _backend_reachable(base_url):
        endpoint_results = benchmark_endpoints(
            base_url=base_url,
            n_requests=n_requests,
            timeout=timeout,
        )
    else:
        endpoint_results = []
        print(
            "  Backend unavailable. DB-only comparison completed; endpoint timing skipped."
        )

    json_path, md_path = save_reports(
        base_url=base_url,
        n_requests=n_requests,
        db_result=db_result,
        agreement=agreement,
        recency=recency,
        endpoint_results=endpoint_results,
        output_dir=output_dir,
        run_ts=run_ts,
    )

    print("\nReports saved:")
    print(f"  JSON     : {json_path}")
    print(f"  Markdown : {md_path}")

    return {
        "run_ts": run_ts,
        "database": db_result,
        "agreement_summary": agreement,
        "recency_summary": recency,
        "endpoint_timing": endpoint_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate operational edge-vs-cloud comparison evidence for V.E.N.U.S."
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
        help="Requests per endpoint for optional timing (default: 10)",
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
        help="Per-request endpoint timing timeout in seconds (default: 10)",
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
