"""Retry transport with exponential backoff for HTTP sources."""

import random
import time

import httpx
import structlog

from pkm_tool.exceptions import SourceError

logger = structlog.get_logger(__name__)

# HTTP status codes that should trigger a retry
RETRIABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Non-retriable status codes (fail immediately)
NON_RETRIABLE_STATUS_CODES = {401, 403, 404}


class RetryTransport(httpx.BaseTransport):
    """HTTP transport wrapper that retries failed requests with exponential backoff.

    Retries on:
    - Connection errors (httpx.ConnectError)
    - Timeout errors (httpx.TimeoutException)
    - HTTP 429 (rate limit) - respects Retry-After header
    - HTTP 500, 502, 503, 504 (server errors)

    Does NOT retry on:
    - HTTP 401, 403 (authentication errors)
    - HTTP 404 (not found)
    - Other client errors (4xx)
    """

    def __init__(
        self,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        source: str = "unknown",
    ) -> None:
        self._transport = transport or httpx.HTTPTransport()
        self._max_retries = max_retries
        self._base_delay = base_delay
        self._max_delay = max_delay
        self._source = source

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = self._transport.handle_request(request)

                # Non-retriable HTTP errors — fail immediately
                if response.status_code in NON_RETRIABLE_STATUS_CODES:
                    return response

                # Retriable HTTP errors — retry with backoff
                if response.status_code in RETRIABLE_STATUS_CODES:
                    if attempt < self._max_retries:
                        delay = self._get_delay(attempt, response)
                        logger.warning(
                            "http_retry",
                            source=self._source,
                            attempt=attempt + 1,
                            max_retries=self._max_retries,
                            status_code=response.status_code,
                            delay_seconds=f"{delay:.2f}",
                        )
                        time.sleep(delay)
                        continue
                    # Exhausted retries — return the response as-is
                    # (caller will handle via raise_for_status or classify_http_error)

                return response

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self._max_retries:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        "http_retry",
                        source=self._source,
                        attempt=attempt + 1,
                        max_retries=self._max_retries,
                        error=str(e),
                        error_type=type(e).__name__,
                        delay_seconds=f"{delay:.2f}",
                    )
                    time.sleep(delay)
                    continue
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise SourceError(self._source, "Retry exhausted without response", retriable=False)

    def _get_delay(self, attempt: int, response: httpx.Response) -> float:
        """Calculate delay, respecting Retry-After header for 429."""
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    return min(float(retry_after), self._max_delay)
                except ValueError:
                    pass
        return self._calculate_backoff(attempt)

    def _calculate_backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter."""
        delay = min(self._base_delay * (2**attempt) + random.uniform(0, 1), self._max_delay)
        return delay

    def close(self) -> None:
        self._transport.close()
