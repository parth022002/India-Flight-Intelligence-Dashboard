"""PostgreSQL connection helpers."""
from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv


def connect_database(
    *,
    timeout_seconds: int = 10,
) -> psycopg.Connection:
    """Connect to PostgreSQL using DATABASE_URL from the environment."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Configure it in your local .env file."
        )
    try:
        return psycopg.connect(
            database_url,
            connect_timeout=timeout_seconds,
        )
    except psycopg.Error as exc:
        # Do not include the exception text: it may expose connection details.
        raise RuntimeError(
            f"Could not connect to PostgreSQL ({type(exc).__name__})."
        ) from None
