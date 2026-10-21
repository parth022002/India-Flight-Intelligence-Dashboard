"""Configuration loading helpers with safe defaults."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path("config/settings.example.json")


def load_json_config(path: str | Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load JSON configuration and require an object at the top level."""
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Configuration must be a JSON object: {path}")
    return data


def get_log_level(default: str = "INFO") -> str:
    """Get a normalized log level from the environment."""
    return os.getenv("LOG_LEVEL", default).strip().upper()
