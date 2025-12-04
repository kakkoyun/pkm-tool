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
from pkm_tool.config import CacheConfig

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
) -> httpx.Client:
    """
    Create an HTTP client with optional caching support.

    This centralizes the HTTP client creation pattern used across sources.

    Args:
        headers: HTTP headers to include in requests
        cache_config: Optional cache configuration for response caching
        timeout: Request timeout in seconds (default: 30.0)

    Returns:
        Configured httpx.Client instance
    """
    if cache_config:
        return get_cached_client(cache_config, headers=headers, timeout=timeout)
    return httpx.Client(headers=headers, timeout=timeout)
