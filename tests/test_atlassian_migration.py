"""Tests for Atlassian library migration."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from pkm_tool.models import AtlassianItem
from pkm_tool.sources.atlassian import fetch_atlassian_items


@pytest.fixture
def mock_jira_response():
    """Mock Jira JQL response."""
    return {
        "issues": [
            {
                "key": "PROJ-123",
                "fields": {
                    "summary": "Test Issue",
                    "status": {"name": "In Progress"},
                    "updated": "2023-11-21T10:30:00.000+0000",
                },
            },
            {
                "key": "PROJ-456",
                "fields": {
                    "summary": "Another Issue",
                    "status": {"name": "Done"},
                    "updated": "2023-11-21T14:15:00.000+0000",
                },
            },
        ]
    }


@pytest.fixture
def mock_confluence_response():
    """Mock Confluence CQL response."""
    return {
        "results": [
            {
                "id": "123456",
                "title": "Test Page",
                "_links": {"webui": "/spaces/TEST/pages/123456"},
                "history": {"lastUpdated": {"when": "2023-11-21T09:00:00.000+0000"}},
            }
        ]
    }


def test_fetch_atlassian_items_no_config():
    """Test that empty list is returned when config is missing."""
    result = fetch_atlassian_items(date(2023, 11, 21), {})
    assert result == []


def test_fetch_atlassian_items_partial_config():
    """Test that empty list is returned when config is incomplete."""
    config = {
        "base_url": "https://example.atlassian.net",
        "username": "user@example.com",
        # Missing api_token
    }
    result = fetch_atlassian_items(date(2023, 11, 21), config)
    assert result == []


@patch("pkm_tool.sources.atlassian.Jira")
@patch("pkm_tool.sources.atlassian.Confluence")
def test_fetch_atlassian_items_with_jira_and_confluence(
    mock_confluence_cls, mock_jira_cls, mock_jira_response, mock_confluence_response
):
    """Test successful fetch of both Jira and Confluence items."""
    # Setup mocks
    mock_jira = MagicMock()
    mock_jira.jql.return_value = mock_jira_response
    mock_jira_cls.return_value = mock_jira

    mock_confluence = MagicMock()
    mock_confluence.cql.return_value = mock_confluence_response
    mock_confluence_cls.return_value = mock_confluence

    config = {
        "base_url": "https://example.atlassian.net",
        "username": "user@example.com",
        "api_token": "fake-token",
    }

    result = fetch_atlassian_items(date(2023, 11, 21), config)

    # Should return 2 Jira issues + 1 Confluence page = 3 items
    assert len(result) == 3

    # Check Jira items
    jira_items = [item for item in result if item.type == "jira_issue"]
    assert len(jira_items) == 2
    assert jira_items[0].key == "PROJ-123"
    assert jira_items[0].title == "Test Issue"
    assert jira_items[0].status == "In Progress"
    assert "PROJ-123" in jira_items[0].url

    # Check Confluence item
    confluence_items = [item for item in result if item.type == "confluence_page"]
    assert len(confluence_items) == 1
    assert confluence_items[0].key == "123456"
    assert confluence_items[0].title == "Test Page"
    assert confluence_items[0].status is None


@patch("pkm_tool.sources.atlassian.Jira")
@patch("pkm_tool.sources.atlassian.Confluence")
def test_fetch_atlassian_items_jira_error(mock_confluence_cls, mock_jira_cls):
    """Test graceful handling when Jira fails."""
    # Jira raises exception
    mock_jira_cls.side_effect = Exception("Connection error")

    # Confluence works
    mock_confluence = MagicMock()
    mock_confluence.cql.return_value = {"results": []}
    mock_confluence_cls.return_value = mock_confluence

    config = {
        "base_url": "https://example.atlassian.net",
        "username": "user@example.com",
        "api_token": "fake-token",
    }

    # Should not crash, should return empty list
    result = fetch_atlassian_items(date(2023, 11, 21), config)
    assert isinstance(result, list)
    assert len(result) == 0


@patch("pkm_tool.sources.atlassian.Jira")
@patch("pkm_tool.sources.atlassian.Confluence")
def test_fetch_atlassian_items_confluence_error(
    mock_confluence_cls, mock_jira_cls, mock_jira_response
):
    """Test graceful handling when Confluence fails but Jira succeeds."""
    # Jira works
    mock_jira = MagicMock()
    mock_jira.jql.return_value = mock_jira_response
    mock_jira_cls.return_value = mock_jira

    # Confluence raises exception
    mock_confluence_cls.side_effect = Exception("Connection error")

    config = {
        "base_url": "https://example.atlassian.net",
        "username": "user@example.com",
        "api_token": "fake-token",
    }

    # Should not crash, should return Jira items (graceful degradation)
    result = fetch_atlassian_items(date(2023, 11, 21), config)
    assert isinstance(result, list)
    # Should have 2 Jira items even though Confluence failed
    assert len(result) == 2
    assert all(item.type == "jira_issue" for item in result)


@patch("pkm_tool.sources.atlassian.Jira")
@patch("pkm_tool.sources.atlassian.Confluence")
def test_fetch_atlassian_items_empty_results(mock_confluence_cls, mock_jira_cls):
    """Test handling of empty results."""
    # Both return empty results
    mock_jira = MagicMock()
    mock_jira.jql.return_value = {"issues": []}
    mock_jira_cls.return_value = mock_jira

    mock_confluence = MagicMock()
    mock_confluence.cql.return_value = {"results": []}
    mock_confluence_cls.return_value = mock_confluence

    config = {
        "base_url": "https://example.atlassian.net",
        "username": "user@example.com",
        "api_token": "fake-token",
    }

    result = fetch_atlassian_items(date(2023, 11, 21), config)
    assert result == []


@patch("pkm_tool.sources.atlassian.Jira")
def test_jql_query_format(mock_jira_cls):
    """Test that JQL query is formatted correctly."""
    mock_jira = MagicMock()
    mock_jira.jql.return_value = {"issues": []}
    mock_jira_cls.return_value = mock_jira

    config = {
        "base_url": "https://example.atlassian.net",
        "username": "user@example.com",
        "api_token": "fake-token",
    }

    fetch_atlassian_items(date(2023, 11, 21), config)

    # Verify JQL was called with date range
    mock_jira.jql.assert_called_once()
    call_args = mock_jira.jql.call_args
    jql_query = call_args[0][0] if call_args[0] else call_args[1].get("jql", "")

    assert "2023-11-21" in jql_query
    assert "2023-11-22" in jql_query or "updated >=" in jql_query


def test_atlassian_item_model_validation():
    """Test AtlassianItem model validation."""
    # Valid Jira item
    jira_item = AtlassianItem(
        type="jira_issue",
        title="Test",
        url="https://example.atlassian.net/browse/PROJ-123",
        key="PROJ-123",
        status="Done",
        updated=datetime(2023, 11, 21, 10, 30),
    )
    assert jira_item.type == "jira_issue"
    assert jira_item.status == "Done"

    # Valid Confluence item (status can be None)
    confluence_item = AtlassianItem(
        type="confluence_page",
        title="Test Page",
        url="https://example.atlassian.net/wiki/spaces/TEST/pages/123",
        key="123",
        status=None,
        updated=datetime(2023, 11, 21, 9, 0),
    )
    assert confluence_item.type == "confluence_page"
    assert confluence_item.status is None
