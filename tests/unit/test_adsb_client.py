
import httpx
import pytest

from flight_intelligence.collectors.adsb_client import (
    AdsbClient,
    AdsbClientConfig,
    AdsbClientError,
)


def make_http_client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_disabled_client_makes_no_request():
    def handler(request):
        pytest.fail("Disabled client must not make an HTTP request")

    with AdsbClient(
        AdsbClientConfig(enabled=False),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="disabled"):
            client.fetch_aircraft("/v0/lat/19.0/lon/72.0/dist/10")

        assert client.requests_used == 0


def test_valid_response_is_returned():
    payload = {"aircraft": [{"hex": "800123", "lat": 19.0, "lon": 72.0}]}

    def handler(request):
        assert request.url.scheme == "https"
        assert request.url.path == "/v0/test"
        return httpx.Response(200, json=payload)

    with AdsbClient(
        AdsbClientConfig(enabled=True, max_retries=0),
        client=make_http_client(handler),
    ) as client:
        assert client.fetch_aircraft("/v0/test") == payload
        assert client.requests_used == 1


def test_invalid_json_is_rejected():
    def handler(request):
        return httpx.Response(200, content=b"not-json")

    with AdsbClient(
        AdsbClientConfig(enabled=True, max_retries=0),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="valid JSON"):
            client.fetch_aircraft("/v0/test")


def test_invalid_payload_is_rejected():
    def handler(request):
        return httpx.Response(200, json={"aircraft": [{"hex": "800123"}]})

    with AdsbClient(
        AdsbClientConfig(enabled=True, max_retries=0),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="failed validation"):
            client.fetch_aircraft("/v0/test")


def test_request_budget_is_enforced():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=2,
            retry_backoff_seconds=0,
            max_requests_per_run=2,
        ),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError):
            client.fetch_aircraft("/v0/test")

        assert calls == 2
        assert client.requests_used == 2

        with pytest.raises(AdsbClientError, match="budget exhausted"):
            client.fetch_aircraft("/v0/test")


def test_oversized_response_is_rejected():
    payload = {"aircraft": []}

    def handler(request):
        return httpx.Response(200, json=payload)

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=0,
            max_payload_bytes_per_run=2,
        ),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="payload budget exceeded"):
            client.fetch_aircraft("/v0/test")


def test_absolute_url_is_rejected():
    with AdsbClient(
        AdsbClientConfig(enabled=True),
        client=make_http_client(lambda request: pytest.fail("No request expected")),
    ) as client:
        with pytest.raises(ValueError, match="relative API path"):
            client.fetch_aircraft("https://example.com/data")


def test_http_404_is_not_retried():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=2,
            retry_backoff_seconds=0,
        ),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="HTTP 404"):
            client.fetch_aircraft("/v0/test")

        assert calls == 1



@pytest.mark.parametrize("endpoint", [
    "../private",
    "/v0/../private",
    "//example.com/data",
    "/v0/test?debug=true",
    "/v0/test#fragment",
])
def test_unsafe_relative_endpoints_are_rejected(endpoint):
    with AdsbClient(
        AdsbClientConfig(enabled=True),
        client=make_http_client(
            lambda request: pytest.fail("Unsafe endpoint must not make a request")
        ),
    ) as client:
        with pytest.raises(ValueError, match="safe relative API path"):
            client.fetch_aircraft(endpoint)

        assert client.requests_used == 0


def test_transient_server_error_is_retried():
    calls = 0
    payload = {"aircraft": []}

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, json=payload)

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=1,
            retry_backoff_seconds=0,
            max_requests_per_run=2,
        ),
        client=make_http_client(handler),
    ) as client:
        assert client.fetch_aircraft("/v0/test") == payload
        assert calls == 2
        assert client.requests_used == 2


def test_payload_budget_is_cumulative_across_responses():
    payload = {"aircraft": []}
    response_size = len(httpx.Response(200, json=payload).content)

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=0,
            max_requests_per_run=2,
            max_payload_bytes_per_run=response_size + 1,
        ),
        client=make_http_client(
            lambda request: httpx.Response(200, json=payload)
        ),
    ) as client:
        client.fetch_aircraft("/v0/first")
        assert client.payload_bytes_used == response_size

        with pytest.raises(AdsbClientError, match="payload budget exceeded"):
            client.fetch_aircraft("/v0/second")

        assert client.requests_used == 2


def test_retry_does_not_exceed_request_budget():
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=5,
            retry_backoff_seconds=0,
            max_requests_per_run=2,
        ),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError):
            client.fetch_aircraft("/v0/test")

        assert calls == 2
        assert client.requests_used == 2


def test_oversized_response_counts_bytes_consumed_before_rejection():
    response_body = b"x" * 20

    def handler(request):
        return httpx.Response(200, content=response_body)

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=0,
            max_payload_bytes_per_run=10,
        ),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="payload budget exceeded"):
            client.fetch_aircraft("/v0/test")

        # The client consumed bytes before detecting that the budget was exceeded.
        assert client.payload_bytes_used > 0
        assert client.payload_bytes_used <= 10
