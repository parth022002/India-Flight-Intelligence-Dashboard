import json

import pytest

from flight_intelligence.analytics.tiers import classify_airport_tier
from flight_intelligence.config import load_json_config


def test_example_settings_load_as_object():
    config = load_json_config("config/settings.example.json")
    assert config["app"]["name"] == "India Flight Intelligence"
    assert config["collection"]["enabled"] is False


def test_invalid_top_level_config_raises(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_json_config(path)


@pytest.mark.parametrize(
    ("movements", "expected"),
    [(None, "T0"), (0, "T0"), (999, "T0"), (1000, "T4"),
     (11999, "T4"), (12000, "T3"), (40000, "T2"), (100000, "T1")],
)
def test_tier_classification(movements, expected):
    assert classify_airport_tier(movements) == expected


def test_negative_movements_rejected():
    with pytest.raises(ValueError):
        classify_airport_tier(-1)
