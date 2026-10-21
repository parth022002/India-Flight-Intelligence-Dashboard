"""Standard console logging configuration."""
from __future__ import annotations

import logging
import os


def configure_logging(level: str | None = None) -> None:
    """Configure concise logging; callers must not log credentials or raw payloads."""
    resolved = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    numeric = getattr(logging, resolved, logging.INFO)
    logging.basicConfig(level=numeric, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
