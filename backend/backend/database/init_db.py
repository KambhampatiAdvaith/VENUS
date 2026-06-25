from pathlib import Path

from backend.database.connection import get_connection


def init_database() -> None:
    schema_path = Path(__file__).parent / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as file:
        schema_sql = file.read()

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(schema_sql)
        connection.commit()
        print("[DATABASE] Schema created successfully")

    except Exception as error:
        connection.rollback()
        print(f"[DATABASE] Failed to create schema: {error}")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    init_database()