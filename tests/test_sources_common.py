"""Tests for common source utilities."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from pkm_tool.config import CacheConfig
from pkm_tool.sources.common import create_http_client, get_source_token


class TestGetSourceToken:
    """Tests for get_source_token utility function."""

    def test_get_token_from_stored(self) -> None:
        """Test getting token from token store."""
        mock_token = MagicMock()
        mock_token.token = "stored_token"

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = mock_token
            mock_auth_class.return_value = mock_auth

            result = get_source_token("test_source", {})

        assert result == "stored_token"

    def test_get_token_from_config(self) -> None:
        """Test getting token from config."""
        config = {"token": "config_token"}

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = get_source_token("test_source", config)

        assert result == "config_token"

    def test_get_token_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test getting token from environment variable."""
        monkeypatch.setenv("TEST_TOKEN", "env_token")

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = get_source_token("test_source", {}, env_var="TEST_TOKEN")

        assert result == "env_token"

    def test_get_token_custom_config_key(self) -> None:
        """Test getting token with custom config key."""
        config = {"api_key": "custom_token"}

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = get_source_token("test_source", config, config_key="api_key")

        assert result == "custom_token"

    def test_get_token_priority(self) -> None:
        """Test token retrieval priority: stored > config > env."""
        mock_token = MagicMock()
        mock_token.token = "stored_token"
        config = {"token": "config_token"}

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = mock_token
            mock_auth_class.return_value = mock_auth

            result = get_source_token("test_source", config, env_var="TEST_TOKEN")

        assert result == "stored_token"

    def test_get_token_not_found(self) -> None:
        """Test when no token is found."""
        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = get_source_token("test_source", {})

        assert result is None


class TestCreateHttpClient:
    """Tests for create_http_client utility function."""

    def test_create_regular_client(self) -> None:
        """Test creating a regular HTTP client without cache."""
        headers = {"Authorization": "Bearer token"}

        client = create_http_client(headers, cache_config=None, timeout=30.0)

        assert isinstance(client, httpx.Client)
        assert client.headers.get("Authorization") == "Bearer token"
        assert client.timeout.read == 30.0
        client.close()

    def test_create_cached_client(self) -> None:
        """Test creating a cached HTTP client."""
        headers = {"Authorization": "Bearer token"}
        cache_config = CacheConfig(enabled=True, directory=".test-cache")

        with patch("pkm_tool.sources.common.get_cached_client") as mock_get_cached:
            mock_client = MagicMock(spec=httpx.Client)
            mock_get_cached.return_value = mock_client

            client = create_http_client(headers, cache_config=cache_config, timeout=20.0)

            assert client == mock_client
            mock_get_cached.assert_called_once_with(
                cache_config, headers=headers, timeout=20.0
            )

    def test_create_client_custom_timeout(self) -> None:
        """Test creating client with custom timeout."""
        headers = {"Content-Type": "application/json"}

        client = create_http_client(headers, timeout=60.0)

        assert isinstance(client, httpx.Client)
        assert client.timeout.read == 60.0
        client.close()
