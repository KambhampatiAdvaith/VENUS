import asyncio
import os
import random
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text

from backend.api.database import get_engine
from backend.edge.edge_anomaly_detector import edge_detector


router = APIRouter()

_simulator_started = False


def build_normal_telemetry() -> list[dict[str, Any]]:
    return [
        {
            "substation": "A",
            "voltage": round(random.uniform(224, 232), 2),
            "current": round(random.uniform(24, 34), 2),
            "temperature": round(random.uniform(35, 45), 2),
            "load": round(random.uniform(42, 63), 2),
            "frequency": round(random.uniform(49.8, 50.2), 2),
        },
        {
            "substation": "B",
            "voltage": round(random.uniform(222, 231), 2),
            "current": round(random.uniform(25, 36), 2),
            "temperature": round(random.uniform(36, 48), 2),
            "load": round(random.uniform(45, 68), 2),
            "frequency": round(random.uniform(49.8, 50.2), 2),
        },
        {
            "substation": "C",
            "voltage": round(random.uniform(225, 233), 2),
            "current": round(random.uniform(22, 33), 2),
            "temperature": round(random.uniform(34, 44), 2),
            "load": round(random.uniform(38, 60), 2),
            "frequency": round(random.uniform(49.8, 50.2), 2),
        },
    ]


def build_overload_telemetry(source_node: str) -> list[dict[str, Any]]:
    readings = build_normal_telemetry()

    for reading in readings:
        if reading["substation"] == source_node:
            reading["load"] = round(random.uniform(88, 98), 2)
            reading["temperature"] = round(random.uniform(72, 86), 2)
            reading["current"] = round(random.uniform(45, 56), 2)
            reading["voltage"] = round(random.uniform(205, 216), 2)
            reading["frequency"] = round(random.uniform(49.2, 49.7), 2)

        else:
            reading["load"] = round(random.uniform(35, 58), 2)
            reading["temperature"] = round(random.uniform(33, 45), 2)
            reading["current"] = round(random.uniform(20, 32), 2)
            reading["voltage"] = round(random.uniform(224, 234), 2)
            reading["frequency"] = round(random.uniform(49.8, 50.2), 2)

    return readings


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
            edge_processed_at
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
            :edge_processed_at
        )
    """

    timestamp = datetime.now(UTC)
    rows = apply_edge_anomaly_detection(readings, timestamp)

    with engine.begin() as connection:
        connection.execute(text(query), rows)

    return rows


async def telemetry_simulation_loop() -> None:
    interval_seconds = int(os.getenv("TELEMETRY_SIMULATION_INTERVAL", "15"))

    while True:
        try:
            scenario, readings = generate_telemetry_cycle()
            inserted_rows = insert_telemetry(readings)

            anomaly_count = sum(
                1 for row in inserted_rows if row.get("edge_anomaly") is True
            )

            print(
                f"[telemetry-simulator] Inserted {scenario} telemetry cycle "
                f"for {len(inserted_rows)} substations. "
                f"Edge anomalies detected: {anomaly_count}."
            )

        except Exception as error:
            print(f"[telemetry-simulator] Error: {error}")

        await asyncio.sleep(interval_seconds)


def start_telemetry_simulator() -> None:
    global _simulator_started

    if _simulator_started:
        return

    _simulator_started = True

    asyncio.create_task(telemetry_simulation_loop())

    print("[telemetry-simulator] Started.")


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