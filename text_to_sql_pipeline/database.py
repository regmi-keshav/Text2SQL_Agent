import os
from pathlib import Path

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")


class DatabaseConfigError(EnvironmentError):
    pass


def get_db_settings() -> dict:
    settings = {
        "host": os.getenv("POSTGRES_HOST", "localhost").strip(),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("POSTGRES_DB", "").strip(),
        "user": os.getenv("POSTGRES_USER", "").strip(),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "sslmode": os.getenv("POSTGRES_SSLMODE", "prefer").strip(),
    }
    if not settings["dbname"] or not settings["user"]:
        raise DatabaseConfigError(
            "Missing PostgreSQL configuration in .env. "
            "Set POSTGRES_DB and POSTGRES_USER at minimum."
        )
    return settings


def get_connection():
    config = get_db_settings()
    return psycopg2.connect(
        host=config["host"],
        port=config["port"],
        dbname=config["dbname"],
        user=config["user"],
        password=config["password"],
        sslmode=config["sslmode"],
    )


def execute_sql(sql_text: str):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql_text)
            return cursor.fetchall()
