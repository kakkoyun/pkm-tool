"""Atlassian (Jira/Confluence) mock fixtures."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def jira_issue_data() -> dict:
    """Sample Jira issue data."""
    return {
        "key": "PROJ-123",
        "fields": {
            "summary": "Implement new authentication feature",
            "status": {"name": "In Progress"},
            "updated": "2025-11-21T10:30:00.000+0000",
        },
    }


@pytest.fixture
def jira_issue_data_2() -> dict:
    """Sample Jira issue data (second issue)."""
    return {
        "key": "PROJ-456",
        "fields": {
            "summary": "Fix critical bug in payment processing",
            "status": {"name": "Done"},
            "updated": "2025-11-21T14:45:00.000+0000",
        },
    }


@pytest.fixture
def jira_search_results(jira_issue_data: dict, jira_issue_data_2: dict) -> dict:
    """Sample Jira JQL search results."""
    return {"issues": [jira_issue_data, jira_issue_data_2]}


@pytest.fixture
def confluence_page_data() -> dict:
    """Sample Confluence page data."""
    return {
        "id": "123456",
        "title": "API Documentation",
        "_links": {"webui": "/spaces/DEV/pages/123456/API+Documentation"},
        "history": {"lastUpdated": {"when": "2025-11-21T09:15:00.000+0000"}},
    }


@pytest.fixture
def confluence_page_data_2() -> dict:
    """Sample Confluence page data (second page)."""
    return {
        "id": "789012",
        "title": "Team Meeting Notes - Nov 21",
        "_links": {"webui": "/spaces/TEAM/pages/789012/Meeting+Notes"},
        "history": {"lastUpdated": {"when": "2025-11-21T16:00:00.000+0000"}},
    }


@pytest.fixture
def confluence_search_results(confluence_page_data: dict, confluence_page_data_2: dict) -> dict:
    """Sample Confluence CQL search results."""
    return {"results": [confluence_page_data, confluence_page_data_2]}


@pytest.fixture
def mock_jira_client(mocker: Mock, jira_search_results: dict) -> Mock:
    """Mock Jira client."""
    mock_jira = mocker.patch("pkm_tool.sources.atlassian.Jira")
    mock_instance = Mock()
    mock_instance.jql.return_value = jira_search_results
    mock_jira.return_value = mock_instance
    return mock_instance


@pytest.fixture
def mock_confluence_client(mocker: Mock, confluence_search_results: dict) -> Mock:
    """Mock Confluence client."""
    mock_confluence = mocker.patch("pkm_tool.sources.atlassian.Confluence")
    mock_instance = Mock()
    mock_instance.cql.return_value = confluence_search_results
    mock_confluence.return_value = mock_instance
    return mock_instance


@pytest.fixture
def mock_jira_client_error(mocker: Mock) -> Mock:
    """Mock Jira client that raises an error."""
    mock_jira = mocker.patch("pkm_tool.sources.atlassian.Jira")
    mock_instance = Mock()
    mock_instance.jql.side_effect = Exception("API connection failed")
    mock_jira.return_value = mock_instance
    return mock_instance


@pytest.fixture
def mock_confluence_client_error(mocker: Mock) -> Mock:
    """Mock Confluence client that raises an error."""
    mock_confluence = mocker.patch("pkm_tool.sources.atlassian.Confluence")
    mock_instance = Mock()
    mock_instance.cql.side_effect = Exception("API connection failed")
    mock_confluence.return_value = mock_instance
    return mock_instance


@pytest.fixture
def mock_atlassian_clients(
    mock_jira_client: Mock, mock_confluence_client: Mock
) -> tuple[Mock, Mock]:
    """Mock both Jira and Confluence clients."""
    return mock_jira_client, mock_confluence_client
