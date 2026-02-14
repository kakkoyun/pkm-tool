"""Common utilities for data sources.

Error Handling Pattern
----------------------

All data sources follow a consistent error handling pattern:

1. **Handle errors once** - Errors are caught and handled at the top-level function only.
   Internal helper functions should raise exceptions rather than catching them.

2. **Consistent logging levels**:
   - Use `logger.error()` for actual failures (with exc_info=True for tracebacks)
   - Use `logger.warning()` for missing configuration/authentication
   - Use `logger.debug()` for normal flow information
   - Use `logger.info()` for successful operations

3. **Graceful degradation** - All fetch functions return empty results on error:
   - Return empty list `[]` for list-returning functions
   - Return `None` for single-object functions
   - Never raise exceptions to the caller (aggregator)

4. **Error isolation** - Errors in one source do not affect other sources.
   The aggregator catches exceptions from each source and stores error messages
   in the metadata dictionary.

Example Pattern:
    ```python
    def fetch_source_data(target_date: date, config: dict[str, Any]) -> list[Model]:
        logger.debug("source_fetch_started", date=str(target_date))

        # Check for required configuration
        token = get_source_token("source_name", config)
        if not token:
            logger.warning("source_no_token", message="No token configured")
            return []

        try:
            # Call internal implementation that may raise
            results = _fetch_source_internal(target_date, token)
            logger.info("source_fetch_completed", count=len(results))
            return results
        except SpecificError as e:
            # Handle specific errors with more context
            logger.error("source_fetch_failed", error=str(e), exc_info=True)
            return []
        except Exception as e:
            # Catch-all for unexpected errors
            logger.error("source_fetch_failed", error=str(e), exc_info=True)
            return []
    ```

Testing:
    Error handling is comprehensively tested in tests/test_error_handling.py:
    - Authentication failures
    - Network errors
    - API rate limits
    - Malformed responses
    - Missing configuration
    - Platform compatibility
    - Error isolation (one source failure doesn't affect others)
"""

import os
from typing import Any

import httpx
import structlog

from pkm_tool.auth import AuthManager
from pkm_tool.cache import get_cached_client
from pkm_tool.config import CacheConfig, RetryConfig
from pkm_tool.exceptions import (
    AuthenticationError,
    NetworkError,
    RateLimitError,
    SourceError,
)

logger = structlog.get_logger(__name__)


def get_source_token(
    source_name: str,
    config: dict[str, Any],
    config_key: str = "token",
    env_var: str | None = None,
) -> str | None:
    """
    Retrieve token for a source from token store, config, or environment.

    This centralizes the token retrieval pattern used across all sources.

    Args:
        source_name: Name of the source (e.g., "github", "wakatime")
        config: Configuration dictionary for the source
        config_key: Key to look for in config dict (default: "token")
        env_var: Environment variable name to check (optional)

    Returns:
        Token string or None if not found
    """
    auth_manager = AuthManager()
    stored = auth_manager.get_token(source_name)
    if stored:
        return stored.token

    # Check config
    token = config.get(config_key)
    if token:
        return token

    # Check environment variable if specified
    if env_var:
        return os.environ.get(env_var)

    return None


def create_http_client(
    headers: dict[str, str],
    cache_config: CacheConfig | None = None,
    timeout: float = 30.0,
    transport: httpx.BaseTransport | None = None,
    retry_config: RetryConfig | None = None,
    source: str = "unknown",
) -> httpx.Client:
    """
    Create an HTTP client with optional caching, retry, and transport injection.

    This centralizes the HTTP client creation pattern used across sources.

    Args:
        headers: HTTP headers to include in requests
        cache_config: Optional cache configuration for response caching
        timeout: Request timeout in seconds (default: 30.0)
        transport: Optional custom transport for testing (mock injection)
        retry_config: Optional retry configuration for failed requests
        source: Source name for logging (used by retry transport)

    Returns:
        Configured httpx.Client instance
    """
    from pkm_tool.retry import RetryTransport

    # Apply retry transport if configured
    actual_transport = transport
    if retry_config and retry_config.enabled and actual_transport is None:
        actual_transport = RetryTransport(
            max_retries=retry_config.max_retries,
            base_delay=retry_config.base_delay,
            max_delay=retry_config.max_delay,
            source=source,
        )

    if cache_config and actual_transport is None:
        # Caching is only used with the default transport
        return get_cached_client(cache_config, headers=headers, timeout=timeout)
    return httpx.Client(headers=headers, timeout=timeout, transport=actual_transport)


def classify_http_error(
    source: str,
    error: httpx.HTTPStatusError | httpx.ConnectError | httpx.TimeoutException | Exception,
) -> SourceError:
    """Classify an HTTP error into a domain exception.

    Maps HTTP status codes and connection errors to structured exception types.
    Used by sources to convert raw HTTP errors into domain exceptions.

    Args:
        source: Name of the source (e.g., "github", "wakatime")
        error: The original HTTP error

    Returns:
        Appropriate SourceError subclass
    """
    # Handle HTTP status errors
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        reason = error.response.reason_phrase

        # Authentication errors (401, 403)
        if status in (401, 403):
            return AuthenticationError(source, f"HTTP {status}: {reason}")

        # Rate limiting (429)
        if status == 429:
            # Parse Retry-After header if present
            retry_after_header = error.response.headers.get("Retry-After")
            retry_after: float | None = None
            if retry_after_header:
                try:
                    retry_after = float(retry_after_header)
                except ValueError:
                    # Retry-After can be an HTTP date, but we simplify to None
                    pass
            return RateLimitError(source, retry_after=retry_after)

        # Server errors (500, 502, 503, 504) - retriable
        if status in (500, 502, 503, 504):
            return SourceError(source, f"HTTP {status}: {reason}", retriable=True)

        # Other HTTP errors - non-retriable
        return SourceError(source, f"HTTP {status}: {reason}", retriable=False)

    # Handle connection errors
    if isinstance(error, httpx.ConnectError):
        return NetworkError(source, f"Connection failed: {error}")

    # Handle timeout errors
    if isinstance(error, httpx.TimeoutException):
        return NetworkError(source, f"Request timed out: {error}")

    # Fallback for unknown errors
    return SourceError(source, str(error), retriable=False)
