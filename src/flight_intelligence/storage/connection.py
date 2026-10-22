"""PostgreSQL connection helpers."""
from __future__ import annotations

import os

import psycopg
from dotenv import load_dotenv


def connect_database(
    *,
    timeout_seconds: int = 10,
    url_env_var: str = "DATABASE_URL",
) -> psycopg.Connection:
    """Connect using an explicitly selected environment variable."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if not url_env_var or not url_env_var.strip():
        raise ValueError("url_env_var must not be empty")

    load_dotenv()
    database_url = os.getenv(url_env_var, "").strip()
    if not database_url:
        raise RuntimeError(
            f"{url_env_var} is missing. Configure it before connecting."
        )

    try:
        return psycopg.connect(
            database_url,
            connect_timeout=timeout_seconds,
        )
    except psycopg.Error as exc:
        # Never include connection details in error messages.
        raise RuntimeError(
            f"Could not connect to PostgreSQL ({type(exc).__name__})."
        ) from None