import os

import psycopg2
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "venus_db"),
        user=os.getenv("POSTGRES_USER", "venus"),
        password=os.getenv("POSTGRES_PASSWORD", "venus"),
    )