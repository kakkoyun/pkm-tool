"""Tests for the server module."""

from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from pkm_tool.models import AggregatedData
from pkm_tool.server.api import app

# Create test client
client = TestClient(app)


def test_health_endpoint():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_list_sources():
    """Test the sources listing endpoint."""
    response = client.get("/api/sources")
    assert response.status_code == 200
    sources = response.json()
    assert len(sources) == 7  # All 7 sources

    # Check that all sources have required fields
    for source in sources:
        assert "name" in source
        assert "display_name" in source
        assert "enabled" in source
        assert "description" in source

    # Check specific sources
    source_names = [s["name"] for s in sources]
    assert "calendar" in source_names
    assert "github" in source_names
    assert "wakatime" in source_names


def test_get_config():
    """Test the config endpoint."""
    response = client.get("/api/config")
    assert response.status_code == 200
    config = response.json()

    assert "output_filename_template" in config
    assert "output_directory" in config
    assert "cache" in config
    assert "sources" in config

    # Check cache config
    assert "enabled" in config["cache"]
    assert "directory" in config["cache"]
    assert "ttl_hours" in config["cache"]

    # Check sources config
    assert "calendar" in config["sources"]
    assert "github" in config["sources"]


@patch("pkm_tool.server.api.aggregate_data")
def test_get_data_markdown(mock_aggregate):
    """Test fetching data in markdown format."""
    # Mock the aggregate_data function
    mock_data = AggregatedData(date=date(2025, 12, 2))
    mock_aggregate.return_value = mock_data

    response = client.get("/api/data?date=2025-12-02&format=markdown")
    assert response.status_code == 200
    data = response.json()

    assert data["date"] == "2025-12-02"
    assert data["format"] == "markdown"
    assert "data" in data
    assert data["raw_data"] is None  # Markdown format doesn't include raw data


@patch("pkm_tool.server.api.aggregate_data")
def test_get_data_json(mock_aggregate):
    """Test fetching data in JSON format."""
    # Mock the aggregate_data function
    mock_data = AggregatedData(date=date(2025, 12, 2))
    mock_aggregate.return_value = mock_data

    response = client.get("/api/data?date=2025-12-02&format=json")
    assert response.status_code == 200
    data = response.json()

    assert data["date"] == "2025-12-02"
    assert data["format"] == "json"
    assert "data" in data
    assert "raw_data" in data
    assert data["raw_data"] is not None  # JSON format includes raw data


def test_get_data_invalid_date():
    """Test fetching data with invalid date."""
    response = client.get("/api/data?date=invalid-date")
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Invalid date format" in data["detail"]


@patch("pkm_tool.server.api.fetch_github_activities")
@patch("pkm_tool.server.api.get_config")
def test_get_data_specific_sources(mock_get_config, mock_fetch_github):
    """Test fetching data from specific sources."""
    # Mock config
    mock_config = MagicMock()
    mock_config.github.enabled = True
    mock_config.github.config = {}
    mock_get_config.return_value = mock_config

    # Mock fetch function
    mock_fetch_github.return_value = []

    response = client.get("/api/data?date=2025-12-02&sources=github")
    assert response.status_code == 200
    data = response.json()

    assert data["date"] == "2025-12-02"
    mock_fetch_github.assert_called_once()


def test_docs_endpoint():
    """Test that API docs are accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_redoc_endpoint():
    """Test that ReDoc docs are accessible."""
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@patch("pkm_tool.server.api.aggregate_data")
def test_get_data_default_date(mock_aggregate):
    """Test fetching data with no date parameter (defaults to today)."""
    # Mock the aggregate_data function
    from datetime import date as dt_date

    mock_data = AggregatedData(date=dt_date.today())
    mock_aggregate.return_value = mock_data

    response = client.get("/api/data")
    assert response.status_code == 200
    data = response.json()

    assert "date" in data
    assert data["format"] == "markdown"  # Default format


def test_output_format_enum():
    """Test that OutputFormat enum is properly defined."""
    from pkm_tool.server.api import OutputFormat

    assert OutputFormat.MARKDOWN == "markdown"
    assert OutputFormat.JSON == "json"
    assert len(OutputFormat) == 2  # Only two values


def test_get_config_cache_settings():
    """Test that config endpoint returns cache settings."""
    response = client.get("/api/config")
    assert response.status_code == 200
    config = response.json()

    # Verify cache settings are present
    assert "cache" in config
    assert "enabled" in config["cache"]
    assert "directory" in config["cache"]
    assert "ttl_hours" in config["cache"]

    # Verify sources have exclude_weekends flag
    for source in ["calendar", "github", "wakatime"]:
        assert source in config["sources"]
        assert "exclude_weekends" in config["sources"][source]


@patch("pkm_tool.server.api.fetch_github_activities")
@patch("pkm_tool.server.api.fetch_wakatime_activities")
@patch("pkm_tool.server.api.get_config")
def test_get_data_multiple_sources(mock_get_config, mock_fetch_wakatime, mock_fetch_github):
    """Test fetching data from multiple specific sources."""

    # Mock config
    mock_config = MagicMock()
    mock_config.github.enabled = True
    mock_config.github.config = {}
    mock_config.wakatime.enabled = True
    mock_config.wakatime.config = {}
    mock_get_config.return_value = mock_config

    # Mock fetch functions
    mock_fetch_github.return_value = []
    mock_fetch_wakatime.return_value = []

    response = client.get("/api/data?date=2025-12-02&sources=github,wakatime")
    assert response.status_code == 200
    data = response.json()

    assert data["date"] == "2025-12-02"
    # Both sources should be called
    assert mock_fetch_github.call_count == 1
    assert mock_fetch_wakatime.call_count == 1
