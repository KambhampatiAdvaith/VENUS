import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()


POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "venus")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "venus")
POSTGRES_DB = os.getenv("POSTGRES_DB", "venus_db")


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return database_url

    return (
        f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )


DATABASE_URL = get_database_url()


engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


TELEMETRY_TIMESTAMP_COLUMNS_MIGRATION = """
    ALTER TABLE telemetry
      ADD COLUMN IF NOT EXISTS generated_at TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS kafka_received_at TIMESTAMPTZ,
      ADD COLUMN IF NOT EXISTS database_written_at TIMESTAMPTZ DEFAULT NOW();
"""


TELEMETRY_INDEXES_MIGRATION = """
    DROP INDEX IF EXISTS idx_telemetry_substation_effective_time;

    CREATE INDEX IF NOT EXISTS idx_telemetry_substation_database_written_at
      ON telemetry (substation, database_written_at DESC, id DESC);

    CREATE INDEX IF NOT EXISTS idx_telemetry_substation_timestamp
      ON telemetry (substation, "timestamp" DESC, id DESC);

    CREATE INDEX IF NOT EXISTS idx_telemetry_database_written_at
      ON telemetry (database_written_at DESC);
"""


def get_engine():
    return engine


def ensure_telemetry_timestamp_columns() -> None:
    with engine.begin() as connection:
        connection.execute(text(TELEMETRY_TIMESTAMP_COLUMNS_MIGRATION))
        connection.execute(text(TELEMETRY_INDEXES_MIGRATION))


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()