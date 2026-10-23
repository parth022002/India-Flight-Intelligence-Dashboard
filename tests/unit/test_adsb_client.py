import httpx
import pytest

from flight_intelligence.collectors.adsb_client import (
    AdsbClient,
    AdsbClientConfig,
    AdsbClientError,
)

VALID_ENDPOINT = "/v2/lat/19.0760/lon/72.8777/dist/50"


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
            client.fetch_aircraft(VALID_ENDPOINT)

        assert client.requests_used == 0
        assert client.payload_bytes_used == 0


def test_valid_response_is_returned():
    payload = {"aircraft": [{"hex": "800123", "lat": 19.0, "lon": 72.0}]}

    def handler(request):
        assert request.url.scheme == "https"
        assert request.url.host == "api.adsb.lol"
        assert request.url.path == VALID_ENDPOINT
        return httpx.Response(200, json=payload)

    with AdsbClient(
        AdsbClientConfig(enabled=True, max_retries=0),
        client=make_http_client(handler),
    ) as client:
        assert client.fetch_aircraft(VALID_ENDPOINT) == payload
        assert client.requests_used == 1
        assert client.payload_bytes_used == len(httpx.Response(200, json=payload).content)


def test_invalid_json_is_rejected():
    def handler(request):
        return httpx.Response(200, content=b"not-json")

    with AdsbClient(
        AdsbClientConfig(enabled=True, max_retries=0),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="valid JSON"):
            client.fetch_aircraft(VALID_ENDPOINT)


def test_invalid_payload_is_rejected():
    def handler(request):
        return httpx.Response(200, json={"aircraft": [{"hex": "800123"}]})

    with AdsbClient(
        AdsbClientConfig(enabled=True, max_retries=0),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="failed validation"):
            client.fetch_aircraft(VALID_ENDPOINT)


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
            client.fetch_aircraft(VALID_ENDPOINT)

        assert calls == 2
        assert client.requests_used == 2

        with pytest.raises(AdsbClientError, match="budget exhausted"):
            client.fetch_aircraft(VALID_ENDPOINT)

        assert calls == 2


def test_oversized_response_is_rejected():
    def handler(request):
        return httpx.Response(200, json={"aircraft": []})

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=0,
            max_payload_bytes_per_run=2,
        ),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="payload budget exceeded"):
            client.fetch_aircraft(VALID_ENDPOINT)

        assert client.payload_bytes_used == 2


def test_oversized_response_without_content_length_is_rejected():
    response_body = b"x" * 20

    def handler(request):
        return httpx.Response(
            200,
            stream=httpx.ByteStream(response_body),
            headers={"content-type": "application/octet-stream"},
        )

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=0,
            max_payload_bytes_per_run=10,
        ),
        client=make_http_client(handler),
    ) as client:
        with pytest.raises(AdsbClientError, match="payload budget exceeded"):
            client.fetch_aircraft(VALID_ENDPOINT)

        assert client.payload_bytes_used == 10
        assert client.requests_used == 1


def test_absolute_url_is_rejected_without_request():
    with AdsbClient(
        AdsbClientConfig(enabled=True),
        client=make_http_client(lambda request: pytest.fail("No request expected")),
    ) as client:
        with pytest.raises(ValueError, match="relative API path"):
            client.fetch_aircraft("https://example.com/data")

        assert client.requests_used == 0


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
            client.fetch_aircraft(VALID_ENDPOINT)

        assert calls == 1
        assert client.requests_used == 1


@pytest.mark.parametrize(
    "endpoint",
    [
        # Path traversal, host override, and URL components.
        "../private",
        "/v2/lat/19/lon/72/dist/50/../private",
        "//example.com/data",
        "https://example.com/data",
        "/v2/lat/19/lon/72/dist/50?debug=true",
        "/v2/lat/19/lon/72/dist/50#fragment",
        r"/v2\lat\19\lon\72\dist\50",
        "",
        "   ",
        # Legacy or unrelated paths must be rejected.
        "/v0/test",
        "/v0/lat/19/lon/72/dist/50",
        "/private",
        "/health",
        "/v3/lat/19/lon/72/dist/50",
        # Malformed API v2 routes.
        "/v2/lat/not-a-number/lon/72.8777/dist/50",
        "/v2/lat/91/lon/72.8777/dist/50",
        "/v2/lat/19.0760/lon/181/dist/50",
        "/v2/lat/19.0760/lon/72.8777/dist/0",
        "/v2/lat/19.0760/lon/72.8777/dist/251",
        "/v2/lat/19.0760/dist/50",
        "/v2/lat/19.0760/lon/72.8777/dist/50/extra",
    ],
)
def test_unsafe_or_unapproved_endpoints_are_rejected_without_request(endpoint):
    with AdsbClient(
        AdsbClientConfig(enabled=True),
        client=make_http_client(
            lambda request: pytest.fail("Invalid endpoint must not make an HTTP request")
        ),
    ) as client:
        with pytest.raises(ValueError):
            client.fetch_aircraft(endpoint)

        assert client.requests_used == 0
        assert client.payload_bytes_used == 0


def test_valid_endpoint_without_leading_slash_is_accepted():
    payload = {"aircraft": []}
    endpoint = VALID_ENDPOINT.lstrip("/")

    def handler(request):
        assert request.url.path == VALID_ENDPOINT
        return httpx.Response(200, json=payload)

    with AdsbClient(
        AdsbClientConfig(enabled=True, max_retries=0),
        client=make_http_client(handler),
    ) as client:
        assert client.fetch_aircraft(endpoint) == payload


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
        assert client.fetch_aircraft(VALID_ENDPOINT) == payload
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
        client=make_http_client(lambda request: httpx.Response(200, json=payload)),
    ) as client:
        client.fetch_aircraft(VALID_ENDPOINT)
        assert client.payload_bytes_used == response_size

        with pytest.raises(AdsbClientError, match="payload budget exceeded"):
            client.fetch_aircraft(VALID_ENDPOINT)

        assert client.requests_used == 2
        assert client.payload_bytes_used == response_size + 1


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
            client.fetch_aircraft(VALID_ENDPOINT)

        assert calls == 2
        assert client.requests_used == 2


def test_oversized_response_counts_only_bytes_within_budget():
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
            client.fetch_aircraft(VALID_ENDPOINT)

        assert client.payload_bytes_used == 10
        assert client.payload_bytes_used <= 10
        assert client.requests_used == 1


def test_payload_budget_exhausted_before_next_request():
    payload = {"aircraft": []}
    response_size = len(httpx.Response(200, json=payload).content)

    with AdsbClient(
        AdsbClientConfig(
            enabled=True,
            max_retries=0,
            max_requests_per_run=2,
            max_payload_bytes_per_run=response_size,
        ),
        client=make_http_client(lambda request: httpx.Response(200, json=payload)),
    ) as client:
        client.fetch_aircraft(VALID_ENDPOINT)

        with pytest.raises(AdsbClientError, match="payload budget exceeded"):
            client.fetch_aircraft(VALID_ENDPOINT)

        assert client.requests_used == 2
        assert client.payload_bytes_used == response_size
