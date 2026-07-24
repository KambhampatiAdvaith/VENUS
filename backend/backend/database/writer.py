from datetime import UTC, datetime

from backend.database.connection import get_connection
from backend.utils.logging import get_logger


SEVERITY_MAP = {
    "temperature_spike": "high",
    "voltage_drop": "critical",
    "load_surge": "high",
    "frequency_deviation": "critical",
}

logger = get_logger("backend.database.writer")


def insert_telemetry(data: dict) -> dict | None:
    query = """
        INSERT INTO telemetry (
            substation,
            voltage,
            "current",
            temperature,
            "load",
            frequency,
            timestamp,
            edge_anomaly,
            edge_anomaly_score,
            edge_model,
            edge_processed_at,
            generated_at,
            kafka_received_at,
            database_written_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

    now_utc = datetime.now(UTC)

    # generated_at: prefer explicit field, fall back to payload timestamp
    generated_at = data.get("generated_at") or data.get("timestamp")

    values = (
        data["substation"],
        data["voltage"],
        data["current"],
        data["temperature"],
        data["load"],
        data["frequency"],
        data["timestamp"],
        data.get("edge_anomaly", False),
        data.get("edge_anomaly_score"),
        data.get("edge_model"),
        data.get("edge_processed_at"),
        generated_at,
        data.get("kafka_received_at"),
        now_utc,
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        connection.commit()
        logger.debug(
            "Telemetry inserted for substation=%s | edge_score=%s",
            data["substation"],
            data.get("edge_anomaly_score"),
        )
        result = dict(data)
        result["database_written_at"] = now_utc
        if "generated_at" not in result:
            result["generated_at"] = generated_at
        return result

    except Exception:
        connection.rollback()
        logger.exception(
            "Failed to insert telemetry for substation=%s.",
            data.get("substation"),
        )
        return None

    finally:
        cursor.close()
        connection.close()


def insert_fault(data: dict) -> dict | None:
    fault_type = data.get("fault_type")

    severity = data.get("severity")
    if not severity:
        severity = SEVERITY_MAP.get(fault_type, "medium")

    query = """
        INSERT INTO faults (
            substation,
            fault_type,
            severity,
            timestamp
        )
        VALUES (%s, %s, %s, %s)
        RETURNING id, substation, fault_type, severity, timestamp;
    """

    values = (
        data["substation"],
        fault_type,
        severity,
        data["timestamp"],
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        inserted_fault = cursor.fetchone()
        connection.commit()
        logger.debug(
            "Fault inserted for substation=%s with fault_type=%s",
            data["substation"],
            fault_type,
        )
        return {
            "id": inserted_fault[0],
            "substation": inserted_fault[1],
            "fault_type": inserted_fault[2],
            "severity": inserted_fault[3],
            "timestamp": inserted_fault[4],
        }

    except Exception:
        connection.rollback()
        logger.exception(
            "Failed to insert fault for substation=%s with fault_type=%s.",
            data.get("substation"),
            fault_type,
        )
        return None

    finally:
        cursor.close()
        connection.close()