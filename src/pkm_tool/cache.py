"""HTTP response caching for data sources.

This module provides a caching layer for HTTP-based data sources using hishel,
a standards-compliant HTTP caching library that works with httpx.

The cache:
- Stores responses in a local SQLite database (easy to clean)
- Respects HTTP caching headers including ETag
- Expires cached entries after configurable TTL (default: 24 hours)
"""

from pathlib import Path
from typing import Any

import httpx
import structlog
from hishel import SyncSqliteStorage
from hishel._core._spec import CacheOptions
from hishel._policies import SpecificationPolicy
from hishel.httpx import SyncCacheClient

from pkm_tool.config import CacheConfig

logger = structlog.get_logger(__name__)


def get_cache_storage(cache_config: CacheConfig) -> SyncSqliteStorage:
    """
    Create a SQLite-based cache storage.

    Args:
        cache_config: Cache configuration

    Returns:
        SyncSqliteStorage instance configured with the cache database and TTL
    """
    # Ensure cache directory exists
    cache_dir = Path(cache_config.directory)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Create database path inside the cache directory
    db_path = cache_dir / "cache.db"

    logger.debug(
        "cache_storage_initialized",
        directory=str(cache_dir),
        database=str(db_path),
        ttl_hours=cache_config.ttl_hours,
    )

    # TTL in seconds
    ttl_seconds = cache_config.ttl_hours * 3600.0

    return SyncSqliteStorage(
        database_path=str(db_path),
        default_ttl=ttl_seconds,
    )


def get_cache_policy() -> SpecificationPolicy:
    """
    Create a cache policy following HTTP specification.

    The policy is configured to:
    - Act as a private cache (not shared/proxy)
    - Allow stale responses when fresh ones aren't available

    Returns:
        SpecificationPolicy instance
    """
    return SpecificationPolicy(
        cache_options=CacheOptions(
            # Act as a private cache (single user)
            shared=False,
            # Allow serving stale responses
            allow_stale=True,
        )
    )


def get_cached_client(
    cache_config: CacheConfig,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> httpx.Client:
    """
    Create an httpx Client with caching enabled.

    This is the main entry point for sources that want to use caching.
    When caching is disabled, returns a regular httpx.Client.

    Args:
        cache_config: Cache configuration
        headers: Optional headers to include in all requests
        timeout: Request timeout in seconds

    Returns:
        httpx.Client or SyncCacheClient depending on cache_config.enabled
    """
    if not cache_config.enabled:
        logger.debug("cache_disabled", message="Using regular httpx.Client")
        return httpx.Client(headers=headers, timeout=timeout)

    storage = get_cache_storage(cache_config)
    policy = get_cache_policy()

    logger.debug(
        "cache_client_created",
        directory=str(cache_config.directory),
        ttl_hours=cache_config.ttl_hours,
    )

    return SyncCacheClient(
        storage=storage,
        policy=policy,
        headers=headers,
        timeout=httpx.Timeout(timeout),
    )


def clear_cache(cache_config: CacheConfig) -> int:
    """
    Clear all cached responses.

    Args:
        cache_config: Cache configuration

    Returns:
        Number of files deleted
    """
    cache_dir = Path(cache_config.directory)
    if not cache_dir.exists():
        logger.info("cache_clear_skipped", reason="Cache directory does not exist")
        return 0

    count = 0
    for file_path in cache_dir.rglob("*"):
        if file_path.is_file():
            try:
                file_path.unlink()
                count += 1
            except OSError as e:
                logger.warning("cache_file_delete_failed", path=str(file_path), error=str(e))

    # Also remove empty directories
    for dir_path in sorted(cache_dir.rglob("*"), reverse=True):
        if dir_path.is_dir():
            try:
                dir_path.rmdir()
            except OSError:
                # Directory not empty or other error
                pass

    logger.info("cache_cleared", files_deleted=count)
    return count


def get_cache_stats(cache_config: CacheConfig) -> dict[str, Any]:
    """
    Get statistics about the cache.

    Args:
        cache_config: Cache configuration

    Returns:
        Dictionary with cache statistics
    """
    cache_dir = Path(cache_config.directory)
    if not cache_dir.exists():
        return {
            "exists": False,
            "file_count": 0,
            "total_size_bytes": 0,
            "directory": str(cache_dir),
        }

    file_count = 0
    total_size = 0
    for file_path in cache_dir.rglob("*"):
        if file_path.is_file():
            file_count += 1
            total_size += file_path.stat().st_size

    return {
        "exists": True,
        "file_count": file_count,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "directory": str(cache_dir),
        "ttl_hours": cache_config.ttl_hours,
    }

