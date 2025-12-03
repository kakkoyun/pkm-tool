"""Common utilities for data sources."""

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
