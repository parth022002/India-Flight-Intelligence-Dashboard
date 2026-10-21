from flight_intelligence.validation.records import validate_airport_record


def test_valid_airport_record_has_no_errors():
    record = {
        "airport_id": "example-1",
        "name": "Example Airport",
        "latitude": 19.0,
        "longitude": 72.0,
    }
    assert validate_airport_record(record) == []


def test_missing_and_invalid_coordinates_are_reported():
    record = {
        "airport_id": "example-2",
        "name": "Example",
        "latitude": 91,
        "longitude": "bad",
    }
    errors = validate_airport_record(record)
    assert "latitude_out_of_range" in errors
    assert "longitude_not_numeric" in errors


def test_missing_required_fields_are_reported():
    assert "missing_required_field:airport_id" in validate_airport_record({})
