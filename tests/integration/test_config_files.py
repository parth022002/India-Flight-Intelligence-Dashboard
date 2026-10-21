import json
from pathlib import Path


def test_project_json_configs_are_valid():
    for path in (
        "config/settings.example.json",
        "config/thresholds.json",
        "config/weather_thresholds.json",
    ):
        with Path(path).open(encoding="utf-8") as handle:
            assert isinstance(json.load(handle), dict)
