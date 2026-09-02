from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.database.connection import get_connection


BASELINE_SUBSTATION_IDS = [str(index) for index in range(1, 21)]


def seed_baseline_telemetry(cursor) -> int:
    now_utc = datetime.now(UTC)
    inserted = 0

    for index, substation in enumerate(BASELINE_SUBSTATION_IDS, start=1):
        cursor.execute(
            """
            SELECT 1
            FROM telemetry
            WHERE substation = %s
            LIMIT 1
            """,
            (substation,),
        )

        if cursor.fetchone() is not None:
            continue

        offset = ((index % 5) - 2) * 0.5
        baseline_load = 50.0 + offset
        baseline_voltage = 229.5 - (offset * 0.4)
        baseline_temperature = 41.5 + (offset * 0.7)
        baseline_frequency = 50.0 - (offset * 0.002)
        baseline_current = 14.8 + (baseline_load * 0.27)
        baseline_timestamp = now_utc - timedelta(seconds=(20 - index))

        cursor.execute(
            """
            INSERT INTO telemetry (
                substation,
                voltage,
                "current",
                temperature,
                "load",
                frequency,
                timestamp,
                generated_at,
                kafka_received_at,
                database_written_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                substation,
                round(baseline_voltage, 2),
                round(baseline_current, 2),
                round(baseline_temperature, 2),
                round(baseline_load, 2),
                round(baseline_frequency, 4),
                baseline_timestamp,
                baseline_timestamp,
                baseline_timestamp,
                now_utc,
            ),
        )
        inserted += 1

    return inserted


def init_database() -> None:
    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as file:
        schema_sql = file.read()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(schema_sql)
        seeded_rows = seed_baseline_telemetry(cursor)
        connection.commit()
        print("[DATABASE] Schema created successfully")
        print(
            "[DATABASE] Baseline telemetry ensured for Substation 1..20"
            f" (inserted {seeded_rows} rows)."
        )

    except Exception as error:
        connection.rollback()
        print(f"[DATABASE] Failed to create schema: {error}")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    init_database()