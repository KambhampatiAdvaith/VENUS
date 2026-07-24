import asyncio
import os
import random
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from backend.api.database import get_engine
from backend.api.ws_manager import manager
from backend.edge.edge_anomaly_detector import edge_detector
from backend.utils.logging import get_logger
from simulator.realism import build_normal_grid_telemetry, build_overload_grid_telemetry


router = APIRouter()

_simulator_started = False
logger = get_logger("backend.api.telemetry_simulator")


def build_normal_telemetry() -> list[dict[str, Any]]:
    return [dict(reading) for reading in build_normal_grid_telemetry()]


def build_overload_telemetry(source_node: str) -> list[dict[str, Any]]:
    return [dict(reading) for reading in build_overload_grid_telemetry(source_node)]


def generate_telemetry_cycle() -> tuple[str, list[dict[str, Any]]]:
    scenario = random.choice(
        [
            "normal",
            "normal",
            "normal",
            "overload_b",
            "overload_c",
        ]
    )

    if scenario == "overload_b":
        return "overload_b", build_overload_telemetry("B")

    if scenario == "overload_c":
        return "overload_c", build_overload_telemetry("C")

    return "normal", build_normal_telemetry()


def apply_edge_anomaly_detection(
    readings: list[dict[str, Any]],
    timestamp: datetime,
) -> list[dict[str, Any]]:
    """
    Applies simulated edge-side Isolation Forest anomaly detection
    before telemetry is stored in the cloud database.

    This adds:
    - edge_anomaly
    - edge_anomaly_score
    - edge_model
    - edge_processed_at
    """
    rows: list[dict[str, Any]] = []

    for reading in readings:
        payload = {
            **reading,
            "timestamp": timestamp.isoformat(),
        }

        payload = edge_detector.analyze(payload)

        rows.append(
            {
                **payload,
                "timestamp": timestamp,
                "generated_at": timestamp,
            }
        )

    return rows


def insert_telemetry(readings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    engine = get_engine()

    query = """
        INSERT INTO telemetry (
            substation,
            voltage,
            current,
            temperature,
            load,
            frequency,
            timestamp,
            edge_anomaly,
            edge_anomaly_score,
            edge_model,
            edge_processed_at,
            generated_at,
            database_written_at
        )
        VALUES (
            :substation,
            :voltage,
            :current,
            :temperature,
            :load,
            :frequency,
            :timestamp,
            :edge_anomaly,
            :edge_anomaly_score,
            :edge_model,
            :edge_processed_at,
            :generated_at,
            :database_written_at
        )
    """

    now_utc = datetime.now(UTC)
    rows = apply_edge_anomaly_detection(readings, now_utc)

    # Attach database_written_at to each row for the insert
    rows_with_written_at = [
        {**row, "database_written_at": now_utc}
        for row in rows
    ]

    with engine.begin() as connection:
        connection.execute(text(query), rows_with_written_at)

    return rows_with_written_at


async def telemetry_simulation_loop() -> None:
    interval_seconds = int(os.getenv("TELEMETRY_SIMULATION_INTERVAL", "15"))

    while True:
        try:
            scenario, readings = generate_telemetry_cycle()
            inserted_rows = insert_telemetry(readings)

            anomaly_count = sum(
                1 for row in inserted_rows if row.get("edge_anomaly") is True
            )

            logger.info(
                "Inserted %s telemetry cycle for %s substations. Edge anomalies detected: %s.",
                scenario,
                len(inserted_rows),
                anomaly_count,
            )

            await manager.broadcast(
                "telemetry",
                {
                    "scenario": scenario,
                    "count": len(inserted_rows),
                    "edge_anomaly_count": anomaly_count,
                },
            )

        except Exception:
            logger.exception("Telemetry simulator cycle failed.")

        await asyncio.sleep(interval_seconds)


def start_telemetry_simulator() -> None:
    global _simulator_started

    if _simulator_started:
        return

    _simulator_started = True

    asyncio.create_task(telemetry_simulation_loop())

    logger.info("Telemetry simulator started.")


@router.post("/telemetry/simulate")
def simulate_single_telemetry_cycle():
    scenario, readings = generate_telemetry_cycle()
    inserted_rows = insert_telemetry(readings)

    return {
        "status": "success",
        "scenario": scenario,
        "count": len(inserted_rows),
        "readings": inserted_rows,
    }


@router.post("/telemetry/simulate/normal")
def simulate_normal_telemetry():
    readings = build_normal_telemetry()
    inserted_rows = insert_telemetry(readings)

    return {
        "status": "success",
        "scenario": "normal",
        "count": len(inserted_rows),
        "readings": inserted_rows,
    }


@router.post("/telemetry/simulate/overload-b")
def simulate_overload_b_telemetry():
    readings = build_overload_telemetry("B")
    inserted_rows = insert_telemetry(readings)

    return {
        "status": "success",
        "scenario": "overload_b",
        "count": len(inserted_rows),
        "readings": inserted_rows,
    }


@router.post("/telemetry/simulate/overload-c")
def simulate_overload_c_telemetry():
    readings = build_overload_telemetry("C")
    inserted_rows = insert_telemetry(readings)

    return {
        "status": "success",
        "scenario": "overload_c",
        "count": len(inserted_rows),
        "readings": inserted_rows,
    }


@router.post("/telemetry/simulate/fault")
def simulate_fault_telemetry():
    source_node = random.choice(["A", "B", "C"])
    readings = build_overload_telemetry(source_node)
    inserted_rows = insert_telemetry(readings)

    return {
        "status": "success",
        "scenario": "fault",
        "count": len(inserted_rows),
        "readings": inserted_rows,
    }