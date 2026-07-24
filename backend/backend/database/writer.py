from backend.database.connection import get_connection


SEVERITY_MAP = {
    "temperature_spike": "high",
    "voltage_drop": "critical",
    "load_surge": "high",
    "frequency_deviation": "critical",
}


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
        return data

    except Exception as error:
        connection.rollback()
        print(f"[DATABASE] Failed to insert telemetry: {error}")
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
        print(
            f"[DATABASE] Fault inserted for Substation {data['substation']} "
            f"with type {fault_type}"
        )
        return {
            "id": inserted_fault[0],
            "substation": inserted_fault[1],
            "fault_type": inserted_fault[2],
            "severity": inserted_fault[3],
            "timestamp": inserted_fault[4],
        }

    except Exception as error:
        connection.rollback()
        print(f"[DATABASE] Failed to insert fault: {error}")
        return None

    finally:
        cursor.close()
        connection.close()