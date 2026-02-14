# Testing Strategy

## Philosophy

PKM Tool follows a pragmatic testing approach that balances comprehensive coverage with development velocity:

- **Unit tests** for models, configuration, and formatters (pure functions, no external dependencies)
- **Integration tests** for aggregator and CLI (test component interactions)
- **Snapshot tests** for output stability (Markdown/JSON format regression detection)
- **HTTP mocking** for source plugins (respx for deterministic API testing)
- **System mocking** for platform-specific features (subprocess, platform detection)

**Key principles:**

- Tests should be fast (target: <10s for full suite)
- Tests should be deterministic (no flaky tests)
- Tests should be readable (clear arrange-act-assert structure)
- Source tests use respx HTTP mocking instead of live APIs
- Platform-specific features use pytest-mock for system calls
- Coverage target: 80% minimum (enforced in CI)

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                    # Import all fixtures, make them available
├── fixtures/                      # Organized fixture modules
│   ├── __init__.py
│   ├── atlassian_fixtures.py      # Atlassian API mocks
│   ├── github_fixtures.py         # GitHub API mocks
│   ├── wakatime_fixtures.py       # Wakatime API mocks
│   ├── whoop_fixtures.py          # Whoop API mocks
│   └── system_fixtures.py         # System call mocks (osascript, platform)
├── __snapshots__/                 # Syrupy snapshot files (auto-generated)
│   ├── test_formatters/           # Snapshots per test module
│   └── test_integration/
├── test_models.py                 # Pydantic model validation tests
├── test_config.py                 # Configuration loading and validation
├── test_formatters.py             # Markdown/JSON formatting tests
├── test_aggregator.py             # Aggregation orchestration tests
├── test_cli.py                    # CLI argument parsing and commands
├── test_cache.py                  # HTTP caching tests
├── test_auth.py                   # Token store and auth manager tests
├── test_preflight.py              # Authentication preflight checks
├── test_google_oauth.py           # Google OAuth flow tests
├── test_whoop_oauth.py            # Whoop OAuth flow tests
├── test_callback_server.py        # OAuth callback server tests
├── test_browser.py                # Browser launcher tests
├── test_sources_common.py         # Common source utilities tests
├── test_github.py                 # GitHub source tests (respx mocks)
├── test_wakatime.py               # Wakatime source tests (respx mocks)
├── test_google_docs.py            # Google Docs source tests (respx mocks)
├── test_whoop.py                  # Whoop source tests (respx mocks)
├── test_apple_calendar.py         # Apple Calendar tests (subprocess mocks)
├── test_server.py                 # FastAPI server tests
├── test_mcp_server.py             # MCP server tests
├── test_integration.py            # End-to-end integration tests
└── test_error_handling.py         # Error isolation and graceful degradation
```

## Fixture Patterns

### Centralized Fixture Import (conftest.py)

All fixtures are defined in modular `fixtures/*.py` files and imported into `conftest.py` for availability across all test modules:

```python
# tests/conftest.py
from tests.fixtures.atlassian_fixtures import (
    confluence_page_data,
    confluence_search_results,
    mock_atlassian_clients,
    # ... more fixtures
)
from tests.fixtures.github_fixtures import (
    mock_github_auth,
    mock_github_client,
    mock_github_events,
    # ... more fixtures
)
# ... other fixture imports

__all__ = [
    "confluence_page_data",
    "mock_github_auth",
    # ... all exported fixtures
]
```

### Fixture Module Structure

Each fixture module follows a consistent pattern:

**Data fixtures** - Return sample API response data:

```python
@pytest.fixture
def wakatime_api_response_data() -> dict:
    """Sample Wakatime API response data."""
    return {
        "data": [
            {
                "projects": [
                    {"name": "pkm-tool", "total_seconds": 7200},
                ],
                "languages": [
                    {"name": "Python", "total_seconds": 9000},
                ],
            }
        ]
    }
```

**Mock fixtures** - Configure respx HTTP mocks:

```python
@pytest.fixture
def mock_wakatime_api_success(
    respx_mock: respx.MockRouter,
    wakatime_api_response_data: dict
) -> respx.Route:
    """Mock successful Wakatime API response."""
    route = respx_mock.get(
        "https://wakatime.com/api/v1/users/current/summaries"
    ).mock(
        return_value=Response(200, json=wakatime_api_response_data)
    )
    return route
```

**Error scenario fixtures** - Test error handling:

```python
@pytest.fixture
def mock_wakatime_api_unauthorized(respx_mock: respx.MockRouter) -> respx.Route:
    """Mock unauthorized Wakatime API response."""
    route = respx_mock.get(
        "https://wakatime.com/api/v1/users/current/summaries"
    ).mock(
        return_value=Response(401, json={"error": "Unauthorized"})
    )
    return route
```

### Existing Fixture Modules

**atlassian_fixtures.py:**

- `jira_issue_data`, `jira_issue_data_2` - Sample Jira issue responses
- `confluence_page_data`, `confluence_page_data_2` - Sample Confluence pages
- `jira_search_results`, `confluence_search_results` - Search result wrappers
- `mock_jira_client`, `mock_confluence_client` - Successful API mocks
- `mock_jira_client_error`, `mock_confluence_client_error` - Error scenarios
- `mock_atlassian_clients` - Combined Jira + Confluence mocks

**github_fixtures.py:**

- `mock_github_user` - User data for authenticated user
- `mock_github_auth` - Token extraction from gh CLI
- `mock_github_push_event` - Push event data
- `mock_github_pr_event` - Pull request event data
- `mock_github_issue_event` - Issue event data
- `mock_github_review_event` - PR review event data
- `mock_github_events` - Combined event list
- `mock_github_client` - Complete GitHub API mock

**wakatime_fixtures.py:**

- `wakatime_api_response_data` - Sample API response
- `mock_wakatime_api_success` - Successful request
- `mock_wakatime_api_unauthorized` - 401 error
- `mock_wakatime_api_rate_limit` - 429 rate limit
- `mock_wakatime_api_server_error` - 500 server error
- `mock_wakatime_api_empty` - No data for date

**whoop_fixtures.py:**

- Similar pattern to wakatime: data fixtures, success mocks, error mocks
- Coverage for recovery, sleep, and workout endpoints

**system_fixtures.py:**

- `mock_platform_macos`, `mock_platform_linux` - Platform detection
- `mock_osascript_success`, `mock_osascript_error` - Apple Calendar subprocess mocks
- `mock_things_database_path` - Things database path override
- `mock_things_database` - Mock SQLite database for Things
- `mock_things_database_missing` - Database not found scenario

## Mocking Strategy

### HTTP Mocking with respx

For sources that use HTTP APIs (Wakatime, Google Docs, Whoop, Atlassian):

```python
def test_fetch_wakatime_activities_success(mock_wakatime_api_success):
    """Test successful Wakatime API call."""
    target_date = date(2025, 11, 21)
    config = {"api_key": "test_key"}

    # Act
    activities = fetch_wakatime_activities(target_date, config)

    # Assert
    assert len(activities) == 2
    assert activities[0].project == "pkm-tool"
    assert activities[0].duration_seconds == 7200
    assert mock_wakatime_api_success.called
```

**Benefits of respx:**

- No actual HTTP calls (fast, deterministic)
- Test different HTTP status codes (200, 401, 429, 500)
- Verify request details (URL, headers, params)
- Simulate network timeouts and errors

### System Call Mocking with pytest-mock

For sources that use subprocess or platform detection:

```python
def test_fetch_calendar_events_macos(mock_platform_macos, mock_osascript_success):
    """Test calendar events on macOS."""
    target_date = date(2025, 11, 21)
    config = {}

    # Act
    events = fetch_calendar_events(target_date, config)

    # Assert
    assert len(events) > 0
    assert events[0].title == "Team Meeting"
    mock_osascript_success.assert_called_once()
```

### Direct Pydantic Model Testing

For unit tests that don't require external dependencies:

```python
def test_github_activity_validation():
    """Test GitHubActivity model validation."""
    # Valid data
    activity = GitHubActivity(
        type="commit",
        repository="owner/repo",
        title="Fix bug in aggregator",
        timestamp=datetime.now(),
        url="https://github.com/owner/repo/commit/abc123",
    )
    assert activity.type == "commit"

    # Invalid data - missing required field
    with pytest.raises(ValidationError):
        GitHubActivity(
            type="commit",
            repository="owner/repo",
            # Missing title
            timestamp=datetime.now(),
        )
```

## Coverage Expectations

**Target: 80% minimum** (enforced in CI with `--cov-fail-under=80`)

**Coverage by module:**

- **models.py:** 90%+ (Pydantic validation, field defaults)
- **config.py:** 85%+ (YAML loading, defaults, validation)
- **formatters.py:** 90%+ (Markdown/JSON formatting, sorting)
- **aggregator.py:** 80%+ (Source orchestration, error handling)
- **sources/*.py:** 75%+ (Happy path, error paths, empty results)
- **auth/*.py:** 80%+ (Token storage, OAuth flows, preflight)
- **cli.py:** 70%+ (Command parsing, user interactions)

**Excluded from coverage:**

- `if __name__ == "__main__":` blocks
- Debug/development code paths
- Platform-specific fallbacks that can't be tested in CI

## How to Add Tests for a New Source

Follow this step-by-step guide when adding a new data source:

### Step 1: Create Fixture Module

Create `tests/fixtures/new_source_fixtures.py`:

```python
"""New Source API mock fixtures."""

import pytest
import respx
from httpx import Response


@pytest.fixture
def new_source_api_response_data() -> dict:
    """Sample New Source API response data."""
    return {
        "items": [
            {
                "id": "123",
                "title": "Sample Item",
                "created_at": "2025-11-21T10:00:00Z",
            }
        ]
    }


@pytest.fixture
def mock_new_source_api_success(
    respx_mock: respx.MockRouter,
    new_source_api_response_data: dict
) -> respx.Route:
    """Mock successful New Source API response."""
    route = respx_mock.get(
        "https://api.newsource.com/v1/items"
    ).mock(
        return_value=Response(200, json=new_source_api_response_data)
    )
    return route


@pytest.fixture
def mock_new_source_api_unauthorized(respx_mock: respx.MockRouter) -> respx.Route:
    """Mock unauthorized New Source API response."""
    route = respx_mock.get(
        "https://api.newsource.com/v1/items"
    ).mock(
        return_value=Response(401, json={"error": "Unauthorized"})
    )
    return route


@pytest.fixture
def mock_new_source_api_empty(respx_mock: respx.MockRouter) -> respx.Route:
    """Mock empty New Source API response."""
    route = respx_mock.get(
        "https://api.newsource.com/v1/items"
    ).mock(
        return_value=Response(200, json={"items": []})
    )
    return route
```

### Step 2: Import Fixtures in conftest.py

Add to `tests/conftest.py`:

```python
from tests.fixtures.new_source_fixtures import (
    mock_new_source_api_empty,
    mock_new_source_api_success,
    mock_new_source_api_unauthorized,
    new_source_api_response_data,
)

__all__ = [
    # ... existing fixtures
    "mock_new_source_api_empty",
    "mock_new_source_api_success",
    "mock_new_source_api_unauthorized",
    "new_source_api_response_data",
]
```

### Step 3: Create Test File

Create `tests/test_new_source.py`:

```python
"""Tests for New Source integration."""

from datetime import date

from pkm_tool.sources.new_source import fetch_new_source_items


def test_fetch_new_source_items_success(mock_new_source_api_success):
    """Test successful New Source API call."""
    target_date = date(2025, 11, 21)
    config = {"api_key": "test_key"}

    items = fetch_new_source_items(target_date, config)

    assert len(items) == 1
    assert items[0].title == "Sample Item"
    assert mock_new_source_api_success.called


def test_fetch_new_source_items_unauthorized(mock_new_source_api_unauthorized):
    """Test New Source API unauthorized error."""
    target_date = date(2025, 11, 21)
    config = {"api_key": "invalid_key"}

    items = fetch_new_source_items(target_date, config)

    # Source should return empty list on error
    assert items == []
    assert mock_new_source_api_unauthorized.called


def test_fetch_new_source_items_empty(mock_new_source_api_empty):
    """Test New Source API with no data."""
    target_date = date(2025, 11, 21)
    config = {"api_key": "test_key"}

    items = fetch_new_source_items(target_date, config)

    assert items == []
    assert mock_new_source_api_empty.called


def test_fetch_new_source_items_missing_config():
    """Test New Source with missing API key."""
    target_date = date(2025, 11, 21)
    config = {}  # No API key

    items = fetch_new_source_items(target_date, config)

    # Should return empty list, not raise exception
    assert items == []
```

### Step 4: Test Error Paths

Ensure error handling is tested:

```python
def test_fetch_new_source_items_network_error(respx_mock):
    """Test New Source with network error."""
    respx_mock.get("https://api.newsource.com/v1/items").mock(
        side_effect=httpx.ConnectError("Network unreachable")
    )

    target_date = date(2025, 11, 21)
    config = {"api_key": "test_key"}

    items = fetch_new_source_items(target_date, config)

    # Source should catch exception and return empty list
    assert items == []


def test_fetch_new_source_items_timeout(respx_mock):
    """Test New Source with timeout."""
    respx_mock.get("https://api.newsource.com/v1/items").mock(
        side_effect=httpx.TimeoutException("Request timeout")
    )

    target_date = date(2025, 11, 21)
    config = {"api_key": "test_key"}

    items = fetch_new_source_items(target_date, config)

    assert items == []
```

### Step 5: Add Model Tests

Add to `tests/test_models.py`:

```python
def test_new_source_item_creation():
    """Test NewSourceItem model creation."""
    item = NewSourceItem(
        title="Test Item",
        timestamp=datetime(2025, 11, 21, 10, 0, 0),
        url="https://newsource.com/items/123",
    )

    assert item.title == "Test Item"
    assert item.timestamp.year == 2025


def test_new_source_item_validation():
    """Test NewSourceItem required fields."""
    with pytest.raises(ValidationError) as exc_info:
        NewSourceItem(
            # Missing required title field
            timestamp=datetime.now(),
        )

    assert "title" in str(exc_info.value)
```

### Step 6: Add Integration Test

Update `tests/test_integration.py`:

```python
def test_aggregate_data_with_new_source(
    mock_new_source_api_success,
    # ... other mocks
):
    """Test aggregation including new source."""
    config = Config(
        new_source=SourceConfig(
            enabled=True,
            config={"api_key": "test_key"}
        )
    )

    data = aggregate_data(date(2025, 11, 21), config)

    assert len(data.new_source_items) == 1
    assert data.new_source_items[0].title == "Sample Item"
```

## Running Tests

### Basic Test Execution

```bash
# Run all tests (recommended)
make test

# Run with coverage report
make test/coverage

# Run with timing report (identify slow tests)
make test/timing

# Run only slow tests (>1s)
make test/slow

# Run tests in parallel (only useful for large suites)
make test/parallel
```

### Running Specific Tests

```bash
# Run specific test file
uv run pytest tests/test_models.py

# Run specific test function
uv run pytest tests/test_models.py::test_github_activity_validation

# Run tests matching pattern
uv run pytest -k "test_wakatime"

# Run tests with verbose output
uv run pytest -v

# Run with very verbose output (show test names)
uv run pytest -vv
```

### Coverage Analysis

```bash
# Generate coverage report (HTML + terminal)
make test/coverage

# View HTML coverage report
open htmlcov/index.html

# Check coverage for specific module
uv run pytest --cov=pkm_tool.sources.github tests/test_github.py
```

### Test Debugging

```bash
# Run with print output visible
uv run pytest -s

# Drop into debugger on failure
uv run pytest --pdb

# Show local variables on failure
uv run pytest -l

# Run last failed tests only
uv run pytest --lf

# Run failed tests first, then all
uv run pytest --ff
```

## Test Best Practices

**DO:**

- Write tests before implementation (TDD)
- Test both happy path and error paths
- Use descriptive test names (test_fetch_items_returns_empty_on_auth_error)
- Keep tests focused (one assertion per test when possible)
- Use fixtures for common setup
- Mock external dependencies (HTTP, subprocess, file system)
- Test error messages and exceptions
- Validate model validation rules

**DON'T:**

- Skip tests with pytest.mark.skip (fix or remove the test)
- Write flaky tests (use deterministic data, mock time)
- Test implementation details (test behavior, not internals)
- Make actual HTTP calls in tests (use respx)
- Access real databases in tests (use mocks)
- Write tests that depend on execution order
- Ignore test failures in CI

## CI Integration

Tests run automatically in GitHub Actions on every push and pull request:

```yaml
# .github/workflows/ci.yml
- name: Run tests with coverage
  run: make ci  # Runs: make check && make test/coverage
```

**CI enforcement:**

- All tests must pass (no flaky tests allowed)
- Coverage must be ≥80% (`--cov-fail-under=80`)
- Type checking must pass (ty)
- Linting must pass (ruff)
- Format checking must pass (ruff format --check)

## Snapshot Testing with Syrupy

Snapshot tests ensure output format stability:

```python
def test_format_markdown_snapshot(snapshot):
    """Test Markdown formatting produces consistent output."""
    data = AggregatedData(
        date=date(2025, 11, 21),
        github_activities=[
            GitHubActivity(
                type="commit",
                repository="owner/repo",
                title="Fix bug",
                timestamp=datetime(2025, 11, 21, 10, 0),
                url="https://github.com/owner/repo/commit/abc",
            )
        ],
    )

    output = format_markdown(data)

    # Snapshot will be saved in __snapshots__/test_formatters/
    assert output == snapshot
```

**Updating snapshots:**

```bash
# Update all snapshots
uv run pytest --snapshot-update

# Update specific test snapshots
uv run pytest tests/test_formatters.py --snapshot-update
```

**When to use snapshots:**

- Testing Markdown/JSON output format
- Detecting unintended formatting changes
- Regression testing for complex string output
- Validating consistent structure across dates

## Future Testing Improvements

**Planned enhancements:**

- Property-based testing with Hypothesis (generate random valid dates)
- Contract testing for external APIs (record real responses)
- Performance benchmarks (track aggregation time over releases)
- Mutation testing (ensure tests actually catch bugs)
- Visual regression testing for CLI output (terminal rendering)
