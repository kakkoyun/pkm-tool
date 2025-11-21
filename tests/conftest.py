"""Shared test configuration and fixtures."""

# Import all fixtures to make them available to tests
from tests.fixtures.atlassian_fixtures import (
    confluence_page_data,
    confluence_page_data_2,
    confluence_search_results,
    jira_issue_data,
    jira_issue_data_2,
    jira_search_results,
    mock_atlassian_clients,
    mock_confluence_client,
    mock_confluence_client_error,
    mock_jira_client,
    mock_jira_client_error,
)
from tests.fixtures.github_fixtures import (
    mock_github_auth,
    mock_github_client,
    mock_github_events,
    mock_github_issue_event,
    mock_github_pr_event,
    mock_github_push_event,
    mock_github_review_event,
    mock_github_user,
)
from tests.fixtures.system_fixtures import (
    mock_osascript_error,
    mock_osascript_success,
    mock_platform_linux,
    mock_platform_macos,
    mock_things_database,
    mock_things_database_missing,
    mock_things_database_path,
)
from tests.fixtures.wakatime_fixtures import (
    mock_wakatime_api_empty,
    mock_wakatime_api_rate_limit,
    mock_wakatime_api_server_error,
    mock_wakatime_api_success,
    mock_wakatime_api_unauthorized,
    wakatime_api_response_data,
)

# Make all fixtures available
__all__ = [
    "confluence_page_data",
    "confluence_page_data_2",
    "confluence_search_results",
    "jira_issue_data",
    "jira_issue_data_2",
    "jira_search_results",
    "mock_atlassian_clients",
    "mock_confluence_client",
    "mock_confluence_client_error",
    "mock_github_auth",
    "mock_github_client",
    "mock_github_events",
    "mock_github_issue_event",
    "mock_github_pr_event",
    "mock_github_push_event",
    "mock_github_review_event",
    "mock_github_user",
    "mock_jira_client",
    "mock_jira_client_error",
    "mock_osascript_error",
    "mock_osascript_success",
    "mock_platform_linux",
    "mock_platform_macos",
    "mock_things_database",
    "mock_things_database_missing",
    "mock_things_database_path",
    "mock_wakatime_api_empty",
    "mock_wakatime_api_rate_limit",
    "mock_wakatime_api_server_error",
    "mock_wakatime_api_success",
    "mock_wakatime_api_unauthorized",
    "wakatime_api_response_data",
]
