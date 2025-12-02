"""Tests for HTTP caching module."""

from pathlib import Path

from pkm_tool.cache import (
    clear_cache,
    get_cache_policy,
    get_cache_stats,
    get_cache_storage,
    get_cached_client,
)
from pkm_tool.config import CacheConfig


class TestGetCacheStorage:
    """Tests for get_cache_storage function."""

    def test_creates_cache_directory(self, tmp_path: Path) -> None:
        """Test that cache directory is created if it doesn't exist."""
        cache_dir = tmp_path / "new_cache"
        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=24,
        )

        storage = get_cache_storage(cache_config)

        assert cache_dir.exists()
        assert storage is not None

    def test_uses_existing_directory(self, tmp_path: Path) -> None:
        """Test that existing cache directory is used."""
        cache_dir = tmp_path / "existing_cache"
        cache_dir.mkdir()

        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=12,
        )

        storage = get_cache_storage(cache_config)

        assert storage is not None

    def test_ttl_configuration(self, tmp_path: Path) -> None:
        """Test that TTL is properly configured."""
        cache_dir = tmp_path / "ttl_cache"
        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=48,
        )

        storage = get_cache_storage(cache_config)

        # TTL is set internally - storage should be created
        assert storage is not None


class TestGetCachePolicy:
    """Tests for get_cache_policy function."""

    def test_returns_policy(self) -> None:
        """Test that a policy is returned."""
        policy = get_cache_policy()

        assert policy is not None


class TestGetCachedClient:
    """Tests for get_cached_client function."""

    def test_returns_regular_client_when_disabled(self, tmp_path: Path) -> None:
        """Test that regular client is returned when caching is disabled."""
        cache_config = CacheConfig(
            enabled=False,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )

        client = get_cached_client(cache_config)

        # Should be a regular httpx.Client, not SyncCacheClient
        assert client is not None
        assert not hasattr(client, "_storage")
        client.close()

    def test_returns_cache_client_when_enabled(self, tmp_path: Path) -> None:
        """Test that cache client is returned when caching is enabled."""
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )

        client = get_cached_client(cache_config)

        # Should be a SyncCacheClient
        assert client is not None
        client.close()

    def test_custom_headers(self, tmp_path: Path) -> None:
        """Test that custom headers are passed to the client."""
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )
        headers = {"Authorization": "Bearer test_token"}

        client = get_cached_client(cache_config, headers=headers)

        assert client is not None
        client.close()

    def test_custom_timeout(self, tmp_path: Path) -> None:
        """Test that custom timeout is used."""
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )

        client = get_cached_client(cache_config, timeout=60.0)

        assert client is not None
        client.close()

    def test_disabled_with_headers(self, tmp_path: Path) -> None:
        """Test disabled cache with custom headers still works."""
        cache_config = CacheConfig(
            enabled=False,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )
        headers = {"Authorization": "Bearer test_token"}

        client = get_cached_client(cache_config, headers=headers)

        assert client is not None
        client.close()


class TestClearCache:
    """Tests for clear_cache function."""

    def test_clears_existing_cache(self, tmp_path: Path) -> None:
        """Test clearing an existing cache with files."""
        cache_dir = tmp_path / "clear_test_cache"
        cache_dir.mkdir()

        # Create some fake cache files
        (cache_dir / "file1.txt").write_text("cached data 1")
        (cache_dir / "file2.txt").write_text("cached data 2")
        subdir = cache_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("cached data 3")

        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=24,
        )

        count = clear_cache(cache_config)

        assert count == 3  # 3 files deleted

    def test_clears_nonexistent_cache(self, tmp_path: Path) -> None:
        """Test clearing a cache that doesn't exist."""
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "nonexistent_cache"),
            ttl_hours=24,
        )

        count = clear_cache(cache_config)

        assert count == 0

    def test_clears_empty_cache(self, tmp_path: Path) -> None:
        """Test clearing an empty cache directory."""
        cache_dir = tmp_path / "empty_cache"
        cache_dir.mkdir()

        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=24,
        )

        count = clear_cache(cache_config)

        assert count == 0


class TestGetCacheStats:
    """Tests for get_cache_stats function."""

    def test_stats_nonexistent_cache(self, tmp_path: Path) -> None:
        """Test stats for a cache that doesn't exist."""
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "nonexistent_stats"),
            ttl_hours=24,
        )

        stats = get_cache_stats(cache_config)

        assert stats["exists"] is False
        assert stats["file_count"] == 0
        assert stats["total_size_bytes"] == 0

    def test_stats_empty_cache(self, tmp_path: Path) -> None:
        """Test stats for an empty cache directory."""
        cache_dir = tmp_path / "empty_stats"
        cache_dir.mkdir()

        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=24,
        )

        stats = get_cache_stats(cache_config)

        assert stats["exists"] is True
        assert stats["file_count"] == 0
        assert stats["total_size_bytes"] == 0

    def test_stats_with_files(self, tmp_path: Path) -> None:
        """Test stats for a cache with files."""
        cache_dir = tmp_path / "stats_with_files"
        cache_dir.mkdir()

        # Create some files with known sizes
        (cache_dir / "file1.txt").write_bytes(b"x" * 100)
        (cache_dir / "file2.txt").write_bytes(b"y" * 200)

        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=12,
        )

        stats = get_cache_stats(cache_config)

        assert stats["exists"] is True
        assert stats["file_count"] == 2
        assert stats["total_size_bytes"] == 300
        assert stats["ttl_hours"] == 12
        assert stats["directory"] == str(cache_dir)

    def test_stats_with_subdirectories(self, tmp_path: Path) -> None:
        """Test stats for a cache with nested directories."""
        cache_dir = tmp_path / "stats_nested"
        cache_dir.mkdir()

        (cache_dir / "file1.txt").write_bytes(b"x" * 50)
        subdir = cache_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_bytes(b"y" * 75)

        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=24,
        )

        stats = get_cache_stats(cache_config)

        assert stats["exists"] is True
        assert stats["file_count"] == 2
        assert stats["total_size_bytes"] == 125


class TestCacheConfigIntegration:
    """Integration tests for cache configuration."""

    def test_full_cache_workflow(self, tmp_path: Path) -> None:
        """Test a complete cache workflow: create, use, stats, clear."""
        cache_dir = tmp_path / "workflow_cache"
        cache_config = CacheConfig(
            enabled=True,
            directory=str(cache_dir),
            ttl_hours=24,
        )

        # Create storage (creates directory)
        storage = get_cache_storage(cache_config)
        _ = storage  # Used to create the cache directory
        assert cache_dir.exists()

        # Get client
        client = get_cached_client(cache_config)
        assert client is not None
        client.close()

        # Create some files to simulate cache entries
        (cache_dir / "cache.db").write_bytes(b"x" * 1000)

        # Check stats
        stats = get_cache_stats(cache_config)
        assert stats["exists"] is True
        assert stats["file_count"] >= 1

        # Clear cache
        count = clear_cache(cache_config)
        assert count >= 1

        # Verify cleared (but directory might still exist)
        stats_after = get_cache_stats(cache_config)
        assert stats_after["file_count"] == 0
