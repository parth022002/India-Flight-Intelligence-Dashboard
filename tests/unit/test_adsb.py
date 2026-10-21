
import pytest

from flight_intelligence.validation.adsb import validate_adsb_payload


def test_valid_aircraft_payload_has_no_errors():
    payload = {
        "aircraft": [
            {"hex": "800123", "lat": 19.0760, "lon": 72.8777}
        ]
    }
    assert validate_adsb_payload(payload) == []


def test_empty_aircraft_list_is_valid():
    assert validate_adsb_payload({"aircraft": []}) == []


@pytest.mark.parametrize("payload", [None, [], "invalid", 123])
def test_non_object_payload_is_rejected(payload):
    assert validate_adsb_payload(payload) == ["payload_not_object"]


def test_missing_aircraft_list_is_rejected():
    assert validate_adsb_payload({}) == ["aircraft_not_list"]


def test_missing_required_aircraft_fields_are_reported():
    errors = validate_adsb_payload({"aircraft": [{"hex": "800123"}]})
    assert "aircraft[0]_missing:lat" in errors
    assert "aircraft[0]_missing:lon" in errors


def test_invalid_coordinates_are_reported():
    errors = validate_adsb_payload(
        {"aircraft": [{"hex": "800123", "lat": 91, "lon": "bad"}]}
    )
    assert "aircraft[0]_lat_out_of_range" in errors
    assert "aircraft[0]_lon_not_numeric" in errors


def test_non_finite_coordinates_are_rejected():
    errors = validate_adsb_payload(
        {"aircraft": [{"hex": "800123", "lat": float("nan"), "lon": float("inf")}]}
    )
    assert "aircraft[0]_lat_not_finite" in errors
    assert "aircraft[0]_lon_not_finite" in errors


def test_non_object_aircraft_entry_is_rejected():
    assert validate_adsb_payload({"aircraft": [None]}) == [
        "aircraft[0]_not_object"
    ]
