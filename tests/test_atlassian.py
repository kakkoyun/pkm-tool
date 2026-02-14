"""Tests for Atlassian source module."""

from datetime import date
from unittest.mock import Mock

from pkm_tool.sources.atlassian import (
    _get_atlassian_credentials,
    fetch_atlassian_items,
)

TARGET_DATE = date(2025, 11, 21)


class TestFetchAtlassianItems:
    """Test main fetch function."""

    def test_fetch_jira_and_confluence(self, mock_jira_client, mock_confluence_client, mocker):
        """Fetches items from both Jira and Confluence."""
        mocker.patch(
            "pkm_tool.sources.atlassian._get_atlassian_credentials",
            return_value=("https://test.atlassian.net", "user@test.com", "token"),
        )
        items = fetch_atlassian_items(TARGET_DATE, {})
        assert len(items) == 4  # 2 Jira + 2 Confluence
        jira_items = [i for i in items if i.type == "jira_issue"]
        conf_items = [i for i in items if i.type == "confluence_page"]
        assert len(jira_items) == 2
        assert len(conf_items) == 2

    def test_returns_empty_on_missing_credentials(self, mocker):
        """Returns empty when credentials missing."""
        mocker.patch(
            "pkm_tool.sources.atlassian._get_atlassian_credentials",
            return_value=(None, None, None),
        )
        items = fetch_atlassian_items(TARGET_DATE, {})
        assert items == []

    def test_returns_empty_on_partial_credentials(self, mocker):
        """Returns empty when only some credentials are present."""
        mocker.patch(
            "pkm_tool.sources.atlassian._get_atlassian_credentials",
            return_value=("https://test.atlassian.net", None, None),
        )
        items = fetch_atlassian_items(TARGET_DATE, {})
        assert items == []

    def test_returns_empty_on_exception(self, mocker):
        """Returns empty list on API exceptions."""
        mocker.patch(
            "pkm_tool.sources.atlassian._get_atlassian_credentials",
            return_value=("https://test.atlassian.net", "user@test.com", "token"),
        )
        mocker.patch(
            "pkm_tool.sources.atlassian.Jira",
        ).return_value.jql.side_effect = Exception("API error")
        items = fetch_atlassian_items(TARGET_DATE, {})
        assert items == []

    def test_jira_items_have_correct_structure(
        self, mock_jira_client, mock_confluence_client, mocker
    ):
        """Jira items have all expected fields."""
        mocker.patch(
            "pkm_tool.sources.atlassian._get_atlassian_credentials",
            return_value=("https://test.atlassian.net", "user@test.com", "token"),
        )
        items = fetch_atlassian_items(TARGET_DATE, {})
        jira_items = [i for i in items if i.type == "jira_issue"]
        assert jira_items[0].key == "PROJ-123"
        assert jira_items[0].status == "In Progress"
        assert "test.atlassian.net" in jira_items[0].url

    def test_confluence_items_have_correct_structure(
        self, mock_jira_client, mock_confluence_client, mocker
    ):
        """Confluence items have all expected fields."""
        mocker.patch(
            "pkm_tool.sources.atlassian._get_atlassian_credentials",
            return_value=("https://test.atlassian.net", "user@test.com", "token"),
        )
        items = fetch_atlassian_items(TARGET_DATE, {})
        conf_items = [i for i in items if i.type == "confluence_page"]
        assert conf_items[0].title == "API Documentation"
        assert conf_items[0].status is None  # Confluence pages don't have status

    def test_jira_empty_results(self, mocker):
        """Handles empty Jira results."""
        mocker.patch(
            "pkm_tool.sources.atlassian._get_atlassian_credentials",
            return_value=("https://test.atlassian.net", "user@test.com", "token"),
        )
        mock_jira = mocker.patch("pkm_tool.sources.atlassian.Jira")
        mock_jira.return_value.jql.return_value = None
        mock_confluence = mocker.patch("pkm_tool.sources.atlassian.Confluence")
        mock_confluence.return_value.cql.return_value = {"results": []}
        items = fetch_atlassian_items(TARGET_DATE, {})
        assert items == []

    def test_malformed_jira_issue_skipped(self, mocker):
        """Malformed Jira issues are skipped without crashing."""
        mocker.patch(
            "pkm_tool.sources.atlassian._get_atlassian_credentials",
            return_value=("https://test.atlassian.net", "user@test.com", "token"),
        )
        mock_jira = mocker.patch("pkm_tool.sources.atlassian.Jira")
        mock_jira.return_value.jql.return_value = {
            "issues": [{"key": "BAD-1", "fields": {}}]  # Missing summary/status
        }
        mock_confluence = mocker.patch("pkm_tool.sources.atlassian.Confluence")
        mock_confluence.return_value.cql.return_value = {"results": []}
        items = fetch_atlassian_items(TARGET_DATE, {})
        assert items == []  # Malformed issue skipped


class TestGetAtlassianCredentials:
    """Test credential retrieval."""

    def test_credentials_from_token_store(self, mocker):
        """Gets credentials from encrypted token store."""
        import json

        stored_data = json.dumps(
            {
                "base_url": "https://stored.atlassian.net",
                "username": "stored@test.com",
                "api_token": "stored-token",
            }
        )
        mock_token = Mock()
        mock_token.token = stored_data
        mocker.patch.object(
            __import__("pkm_tool.sources.atlassian", fromlist=["_AUTH_MANAGER"]),
            "_AUTH_MANAGER",
        )
        mocker.patch(
            "pkm_tool.sources.atlassian._AUTH_MANAGER.get_token",
            return_value=mock_token,
        )
        base_url, username, api_token = _get_atlassian_credentials({})
        assert base_url == "https://stored.atlassian.net"
        assert username == "stored@test.com"
        assert api_token == "stored-token"

    def test_credentials_from_config(self, mocker):
        """Falls back to config when token store is empty."""
        mocker.patch(
            "pkm_tool.sources.atlassian._AUTH_MANAGER.get_token",
            return_value=None,
        )
        config = {
            "base_url": "https://config.atlassian.net",
            "username": "config@test.com",
            "api_token": "config-token",
        }
        base_url, _username, _api_token = _get_atlassian_credentials(config)
        assert base_url == "https://config.atlassian.net"

    def test_credentials_from_env(self, mocker):
        """Falls back to environment variables."""
        mocker.patch(
            "pkm_tool.sources.atlassian._AUTH_MANAGER.get_token",
            return_value=None,
        )
        mocker.patch.dict(
            "os.environ",
            {
                "ATLASSIAN_BASE_URL": "https://env.atlassian.net",
                "ATLASSIAN_USERNAME": "env@test.com",
                "ATLASSIAN_API_TOKEN": "env-token",
            },
        )
        base_url, _username, _api_token = _get_atlassian_credentials({})
        assert base_url == "https://env.atlassian.net"

    def test_corrupted_token_falls_through(self, mocker):
        """Corrupted JSON token falls through to config."""
        mock_token = Mock()
        mock_token.token = "not-valid-json"
        mocker.patch(
            "pkm_tool.sources.atlassian._AUTH_MANAGER.get_token",
            return_value=mock_token,
        )
        config = {"base_url": "https://fallback.atlassian.net", "username": "u", "api_token": "t"}
        base_url, _, _ = _get_atlassian_credentials(config)
        assert base_url == "https://fallback.atlassian.net"
