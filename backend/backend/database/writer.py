from backend.database.connection import get_connection


SEVERITY_MAP = {
    "temperature_spike": "high",
    "voltage_drop": "critical",
    "load_surge": "high",
    "frequency_deviation": "critical",
}


def insert_telemetry(data: dict) -> None:
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
            edge_processed_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """

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
    )

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(query, values)
        connection.commit()
        print(
            f"[DATABASE] Telemetry inserted for Substation {data['substation']} "
            f"| edge_score={data.get('edge_anomaly_score')}"
        )

    except Exception as error:
        connection.rollback()
        print(f"[DATABASE] Failed to insert telemetry: {error}")

    finally:
        cursor.close()
        connection.close()


def insert_fault(data: dict) -> None:
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
        VALUES (%s, %s, %s, %s);
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
        connection.commit()
        print(
            f"[DATABASE] Fault inserted for Substation {data['substation']} "
            f"with type {fault_type}"
        )

    except Exception as error:
        connection.rollback()
        print(f"[DATABASE] Failed to insert fault: {error}")

    finally:
        cursor.close()
        connection.close()