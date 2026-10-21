import pytest

from flight_intelligence.analytics.tiers import (
    classify_airport_tier,
    load_tier_config,
)


@pytest.mark.parametrize(
    ("movements", "expected"),
    [
        (None, "T0"),
        (0, "T0"),
        (999, "T0"),
        (1000, "T4"),
        (11999, "T4"),
        (12000, "T3"),
        (39999, "T3"),
        (40000, "T2"),
        (99999, "T2"),
        (100000, "T1"),
        (250000, "T1"),
    ],
)
def test_classifies_configured_movement_boundaries(movements, expected):
    assert classify_airport_tier(movements) == expected
@pytest.mark.parametrize("movements", [-1, 1.5, True, "40000"])
def test_rejects_invalid_movement_values(movements):
    if movements == -1:
        with pytest.raises(ValueError):
            classify_airport_tier(movements)
    else:
        with pytest.raises(TypeError):
            classify_airport_tier(movements)
def test_t5_and_t6_boundaries_remain_unresolved():
    config = load_tier_config()
    tiers = {tier["tier"]: tier for tier in config["tiers"]}
    for tier_name in ("T5", "T6"):
        tier = tiers[tier_name]
        assert tier["annual_movements_min_inclusive"] is None
        assert tier["annual_movements_max_inclusive"] is None
        assert tier["status"] == "unresolved_movement_boundary"
    # Values below the first resolved threshold must not be assigned T5/T6.
    assert classify_airport_tier(999, config) == "T0"
def test_t0_means_unknown_not_zero_traffic():
    config = load_tier_config()
    t0 = next(tier for tier in config["tiers"] if tier["tier"] == "T0")
    assert t0["status"] == "unclassified_or_reliable_traffic_data_unavailable"
    assert classify_airport_tier(None, config) == "T0"
