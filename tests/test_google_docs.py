"""Tests for Google Docs integration."""

from datetime import date
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx

from pkm_tool.config import CacheConfig
from pkm_tool.models import GoogleDoc
from pkm_tool.sources.google_docs import _build_provider, fetch_google_docs


@pytest.fixture
def google_docs_config() -> dict[str, str]:
    """Sample Google Docs configuration with access token."""
    return {"access_token": "test_google_token"}


@pytest.fixture
def google_drive_files_response() -> dict:
    """Mock Google Drive API response."""
    return {
        "files": [
            {
                "id": "doc1",
                "name": "Test Document",
                "webViewLink": "https://docs.google.com/document/d/doc1/edit",
                "modifiedTime": "2025-11-21T10:30:00Z",
                "mimeType": "application/vnd.google-apps.document",
            },
            {
                "id": "doc2",
                "name": "Test Spreadsheet",
                "webViewLink": "https://docs.google.com/spreadsheets/d/doc2/edit",
                "modifiedTime": "2025-11-21T14:45:00Z",
                "mimeType": "application/vnd.google-apps.spreadsheet",
            },
            {
                "id": "doc3",
                "name": "Test Presentation",
                "webViewLink": "https://docs.google.com/presentation/d/doc3/edit",
                "modifiedTime": "2025-11-21T16:00:00Z",
                "mimeType": "application/vnd.google-apps.presentation",
            },
        ]
    }


class TestFetchGoogleDocs:
    """Tests for fetch_google_docs function."""

    @respx.mock
    def test_fetch_docs_success(
        self, google_docs_config: dict[str, str], google_drive_files_response: dict
    ) -> None:
        """Test successful Google Docs fetch."""
        target_date = date(2025, 11, 21)

        respx.get("https://www.googleapis.com/drive/v3/files").mock(
            return_value=httpx.Response(200, json=google_drive_files_response)
        )

        result = fetch_google_docs(target_date, google_docs_config)

        assert len(result) == 3

        # Check document
        doc = result[0]
        assert isinstance(doc, GoogleDoc)
        assert doc.title == "Test Document"
        assert doc.doc_type == "document"

        # Check spreadsheet
        spreadsheet = result[1]
        assert spreadsheet.title == "Test Spreadsheet"
        assert spreadsheet.doc_type == "spreadsheet"

        # Check presentation
        presentation = result[2]
        assert presentation.title == "Test Presentation"
        assert presentation.doc_type == "presentation"

    @respx.mock
    def test_fetch_docs_no_token(self) -> None:
        """Test Google Docs fetch with no access token."""
        target_date = date(2025, 11, 21)
        config: dict = {}

        result = fetch_google_docs(target_date, config)

        assert result == []

    @respx.mock
    def test_fetch_docs_empty_response(self, google_docs_config: dict[str, str]) -> None:
        """Test Google Docs fetch with empty response."""
        target_date = date(2025, 11, 21)

        respx.get("https://www.googleapis.com/drive/v3/files").mock(
            return_value=httpx.Response(200, json={"files": []})
        )

        result = fetch_google_docs(target_date, google_docs_config)

        assert result == []

    @respx.mock
    def test_fetch_docs_http_error(self, google_docs_config: dict[str, str]) -> None:
        """Test Google Docs fetch with HTTP error."""
        target_date = date(2025, 11, 21)

        respx.get("https://www.googleapis.com/drive/v3/files").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        result = fetch_google_docs(target_date, google_docs_config)

        assert result == []

    @respx.mock
    def test_fetch_docs_with_cache(
        self, google_docs_config: dict[str, str], google_drive_files_response: dict, tmp_path
    ) -> None:
        """Test Google Docs fetch with caching enabled."""
        target_date = date(2025, 11, 21)
        cache_config = CacheConfig(
            enabled=True,
            directory=str(tmp_path / "cache"),
            ttl_hours=24,
        )

        respx.get("https://www.googleapis.com/drive/v3/files").mock(
            return_value=httpx.Response(200, json=google_drive_files_response)
        )

        result = fetch_google_docs(target_date, google_docs_config, cache_config)

        assert len(result) == 3

    @respx.mock
    def test_fetch_docs_from_env(
        self, google_drive_files_response: dict, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test Google Docs fetch with token from environment variable."""
        target_date = date(2025, 11, 21)
        monkeypatch.setenv("GOOGLE_ACCESS_TOKEN", "env_token")

        respx.get("https://www.googleapis.com/drive/v3/files").mock(
            return_value=httpx.Response(200, json=google_drive_files_response)
        )

        result = fetch_google_docs(target_date, {})

        assert len(result) == 3

    @respx.mock
    def test_fetch_docs_key_error(self, google_docs_config: dict[str, str]) -> None:
        """Test Google Docs fetch with malformed response."""
        target_date = date(2025, 11, 21)

        # Response missing required fields
        respx.get("https://www.googleapis.com/drive/v3/files").mock(
            return_value=httpx.Response(
                200,
                json={
                    "files": [
                        {
                            "id": "doc1",
                            # Missing 'name' and other required fields
                        }
                    ]
                },
            )
        )

        result = fetch_google_docs(target_date, google_docs_config)

        # Should return empty list due to KeyError being caught
        assert result == []


class TestBuildProvider:
    """Tests for _build_provider helper function."""

    def test_build_provider_with_client_id(self) -> None:
        """Test building provider with client ID in config."""
        config = {"client_id": "test_client_id", "client_secret": "test_secret"}

        provider = _build_provider(config)

        assert provider is not None
        assert provider.client_id == "test_client_id"
        assert provider.client_secret == "test_secret"

    def test_build_provider_no_client_id(self) -> None:
        """Test building provider without client ID returns None."""
        config: dict = {}

        provider = _build_provider(config)

        assert provider is None

    def test_build_provider_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test building provider with client ID from environment."""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "env_client_id")
        monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "env_secret")

        provider = _build_provider({})

        assert provider is not None
        assert provider.client_id == "env_client_id"
        assert provider.client_secret == "env_secret"

    def test_build_provider_with_custom_scopes(self) -> None:
        """Test building provider with custom scopes."""
        config = {
            "client_id": "test_client_id",
            "scopes": [
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/docs",
            ],
        }

        provider = _build_provider(config)

        assert provider is not None
        assert len(provider.scopes) == 2

    def test_build_provider_with_string_scope(self) -> None:
        """Test building provider with scope as string (not list)."""
        config = {
            "client_id": "test_client_id",
            "scopes": "https://www.googleapis.com/auth/drive.readonly",
        }

        provider = _build_provider(config)

        assert provider is not None
        assert provider.scopes == ["https://www.googleapis.com/auth/drive.readonly"]


class TestGoogleDocsWithOAuth:
    """Tests for Google Docs with OAuth integration."""

    @respx.mock
    def test_fetch_docs_with_oauth_provider(self, google_drive_files_response: dict) -> None:
        """Test Google Docs fetch with OAuth provider configured."""
        target_date = date(2025, 11, 21)
        config = {
            "client_id": "test_client_id",
            "client_secret": "test_secret",
        }

        # Mock the auth manager to return no stored token
        with patch("pkm_tool.sources.google_docs._AUTH_MANAGER") as mock_auth:
            mock_auth.ensure_oauth_token.return_value = None

            respx.get("https://www.googleapis.com/drive/v3/files").mock(
                return_value=httpx.Response(200, json=google_drive_files_response)
            )

            # Without a token, should return empty
            result = fetch_google_docs(target_date, config)

            assert result == []

    @respx.mock
    def test_fetch_docs_with_stored_oauth_token(self, google_drive_files_response: dict) -> None:
        """Test Google Docs fetch with stored OAuth token."""
        target_date = date(2025, 11, 21)
        config = {
            "client_id": "test_client_id",
            "client_secret": "test_secret",
        }

        # Mock the auth manager to return a stored token
        mock_token = MagicMock()
        mock_token.token = "stored_oauth_token"

        with patch("pkm_tool.sources.google_docs._AUTH_MANAGER") as mock_auth:
            mock_auth.ensure_oauth_token.return_value = mock_token

            respx.get("https://www.googleapis.com/drive/v3/files").mock(
                return_value=httpx.Response(200, json=google_drive_files_response)
            )

            result = fetch_google_docs(target_date, config)

            assert len(result) == 3
