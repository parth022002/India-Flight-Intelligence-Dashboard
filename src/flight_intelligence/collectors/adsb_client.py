"""Bounded HTTP client for ADS-B API responses.

Live requests must remain disabled until provider terms and access limits
have been reviewed.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from flight_intelligence.validation.adsb import validate_adsb_payload

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {408, 429}


class AdsbClientError(RuntimeError):
    """Raised when an ADS-B request fails or its response is invalid."""


@dataclass(frozen=True)
class AdsbClientConfig:
    base_url: str = "https://api.adsb.lol"
    timeout_seconds: float = 20.0
    max_retries: int = 2
    retry_backoff_seconds: float = 2.0
    max_requests_per_run: int = 2
    max_payload_bytes_per_run: int = 5 * 1024 * 1024
    enabled: bool = False

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("base_url must be a clean HTTPS base URL")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds cannot be negative")
        if self.max_requests_per_run < 1:
            raise ValueError("max_requests_per_run must be at least 1")
        if self.max_payload_bytes_per_run < 1:
            raise ValueError("max_payload_bytes_per_run must be at least 1")


class AdsbClient:
    """Request and validate ADS-B JSON without logging raw aircraft data."""

    def __init__(
        self,
        config: AdsbClientConfig | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config or AdsbClientConfig()
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            follow_redirects=False,
        )
        self._owns_client = client is None
        self._requests_used = 0
        self._payload_bytes_used = 0

    @property
    def requests_used(self) -> int:
        """Return HTTP attempts made during this client run."""
        return self._requests_used

    @property
    def payload_bytes_used(self) -> int:
        """Return response bytes consumed during this client run."""
        return self._payload_bytes_used

    def close(self) -> None:
        """Close the HTTP session if this client created it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> AdsbClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _validate_endpoint(self, endpoint: str) -> str:
        """Accept only a valid ADS-B API v2 geographic search path."""
        import math
        import re

        if not isinstance(endpoint, str) or not endpoint.strip():
            raise ValueError("endpoint must be a non-empty relative API path")

        endpoint = endpoint.strip()
        parsed = urlparse(endpoint)

        if (
            parsed.scheme
            or parsed.netloc
            or parsed.query
            or parsed.fragment
            or "\\" in endpoint
            or any(part in {".", ".."} for part in endpoint.split("/"))
        ):
            raise ValueError("endpoint must be a safe relative API path")

        path = endpoint.lstrip("/")
        match = re.fullmatch(
            r"v2/lat/([^/]+)/lon/([^/]+)/dist/([^/]+)",
            path,
        )
        if not match:
            raise ValueError("endpoint must match the supported ADS-B API v2 route")

        try:
            latitude, longitude, radius = map(float, match.groups())
        except ValueError as exc:
            raise ValueError("endpoint coordinates and radius must be numeric") from exc

        if not all(map(math.isfinite, (latitude, longitude, radius))):
            raise ValueError("endpoint coordinates and radius must be finite")
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        if not 0 < radius <= 250:
            raise ValueError("radius must be greater than 0 and at most 250")

        return path

    def fetch_aircraft(self, endpoint: str) -> dict[str, Any]:
        """Fetch one JSON endpoint and return its validated payload.

        Every HTTP attempt counts against the request budget. Response bytes
        are counted as they arrive, including unsuccessful HTTP responses.
        """
        if not self.config.enabled:
            raise AdsbClientError("ADS-B collection is disabled by configuration")

        path = self._validate_endpoint(endpoint)
        url = f"{self.config.base_url.rstrip('/')}/{path}"
        last_error: Exception | None = None

        for attempt in range(self.config.max_retries + 1):
            if self._requests_used >= self.config.max_requests_per_run:
                raise AdsbClientError("per-run HTTP request budget exhausted")

            self._requests_used += 1
            try:
                with self._client.stream("GET", url) as response:
                    content = bytearray()

                    for chunk in response.iter_bytes():
                        remaining = (
                            self.config.max_payload_bytes_per_run
                            - self._payload_bytes_used
                            - len(content)
                        )

                        if len(chunk) > remaining:
                            # Count only bytes within the configured budget.
                            # Do not retain the oversized remainder.
                            if remaining > 0:
                                content.extend(chunk[:remaining])
                            self._payload_bytes_used += len(content)
                            raise AdsbClientError("per-run response payload budget exceeded")

                        content.extend(chunk)

                    # Count the response body, even if its HTTP status is unsuccessful.
                    self._payload_bytes_used += len(content)

                    if response.status_code in RETRYABLE_STATUS_CODES or (
                        response.status_code >= 500
                    ):
                        last_error = AdsbClientError(
                            f"retryable HTTP status: {response.status_code}"
                        )
                    else:
                        response.raise_for_status()
                        try:
                            payload = httpx.Response(
                                status_code=response.status_code,
                                content=bytes(content),
                                headers={"content-type": "application/json"},
                            ).json()
                        except ValueError as exc:
                            raise AdsbClientError("API response was not valid JSON") from exc

                        errors = validate_adsb_payload(payload)
                        if errors:
                            logger.warning(
                                "ADS-B response validation failed: error_count=%d",
                                len(errors),
                            )
                            raise AdsbClientError(
                                f"API response failed validation ({len(errors)} errors)"
                            )

                        logger.info(
                            "ADS-B response accepted: aircraft_count=%d",
                            len(payload["aircraft"]),
                        )
                        return dict(payload)

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status not in RETRYABLE_STATUS_CODES and status < 500:
                    raise AdsbClientError(f"API returned HTTP {status}") from exc
                last_error = exc
            except AdsbClientError:
                raise

            if attempt < self.config.max_retries:
                delay = self.config.retry_backoff_seconds * (2**attempt)
                if delay:
                    time.sleep(delay)

        logger.warning(
            "ADS-B request failed after bounded attempts: attempts=%d",
            min(self.config.max_retries + 1, self._requests_used),
        )
        raise AdsbClientError("ADS-B request failed after bounded retries") from last_error
