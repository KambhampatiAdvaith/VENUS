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


def normalize_utc_timestamp(value, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(normalized)
    else:
        raise ValueError(f"Invalid {field_name} value: {value!r}")

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)

    return timestamp.astimezone(UTC)


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
    payload_timestamp = normalize_utc_timestamp(
        data["timestamp"],
        field_name="timestamp",
    )

    # generated_at: prefer explicit field, fall back to payload timestamp
    generated_at_raw = data.get("generated_at") or payload_timestamp
    generated_at = normalize_utc_timestamp(
        generated_at_raw,
        field_name="generated_at",
    )
    kafka_received_at = (
        normalize_utc_timestamp(
            data["kafka_received_at"],
            field_name="kafka_received_at",
        )
        if data.get("kafka_received_at") is not None
        else None
    )
    edge_processed_at = (
        normalize_utc_timestamp(
            data["edge_processed_at"],
            field_name="edge_processed_at",
        )
        if data.get("edge_processed_at") is not None
        else None
    )

    values = (
        data["substation"],
        data["voltage"],
        data["current"],
        data["temperature"],
        data["load"],
        data["frequency"],
        payload_timestamp,
        data.get("edge_anomaly", False),
        data.get("edge_anomaly_score"),
        data.get("edge_model"),
        edge_processed_at,
        generated_at,
        kafka_received_at,
        now_utc,
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        connection.commit()
        logger.debug(
            "Telemetry inserted for substation=%s at %s | db_written_at=%s | edge_score=%s",
            data["substation"],
            payload_timestamp.isoformat(),
            now_utc.isoformat(),
            data.get("edge_anomaly_score"),
        )
        result = dict(data)
        result["timestamp"] = payload_timestamp
        result["generated_at"] = generated_at
        result["kafka_received_at"] = kafka_received_at
        result["edge_processed_at"] = edge_processed_at
        result["database_written_at"] = now_utc
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
        fault_timestamp,
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        inserted_fault = cursor.fetchone()
        connection.commit()
        logger.debug(
            "Fault inserted for substation=%s with fault_type=%s at %s",
            data["substation"],
            fault_type,
            fault_timestamp.isoformat(),
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
    fault_timestamp = normalize_utc_timestamp(
        data["timestamp"],
        field_name="timestamp",
    )
