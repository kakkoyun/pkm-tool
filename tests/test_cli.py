"""CLI snapshot tests."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from syrupy.assertion import SnapshotAssertion

from pkm_tool.cli import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create a temporary config file with only GitHub and Wakatime enabled."""
    config_path = tmp_path / "test_config.yaml"
    config_content = """
exclude_weekends: false

github:
  enabled: true
  exclude_weekends: false
  config:
    token: test_github_token

wakatime:
  enabled: true
  exclude_weekends: false
  config:
    api_key: test_wakatime_key

atlassian:
  enabled: false
  exclude_weekends: false

apple_calendar:
  enabled: false
  exclude_weekends: false

things:
  enabled: false
  exclude_weekends: false

google_docs:
  enabled: false
  exclude_weekends: false
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def full_sources_config(tmp_path: Path) -> Path:
    """Create a temporary config file with multiple sources enabled.

    Enables GitHub, Wakatime, and Atlassian for snapshot testing.
    Things and Apple Calendar are disabled to avoid SQLite/subprocess mocking
    complexity in CI environments.
    """
    config_path = tmp_path / "full_config.yaml"
    config_content = """
github:
  enabled: true
  config:
    token: test_github_token

wakatime:
  enabled: true
  config:
    api_key: test_wakatime_key

atlassian:
  enabled: true
  config:
    base_url: https://test.atlassian.net
    username: test@example.com
    api_token: test_token

apple_calendar:
  enabled: false

things:
  enabled: false

google_docs:
  enabled: false
"""
    config_path.write_text(config_content)
    return config_path


@pytest.fixture
def weekend_filter_config(tmp_path: Path) -> Path:
    """Config with global weekend exclusion to test CLI overrides."""
    config_path = tmp_path / "weekend_filter.yaml"
    config_content = """
exclude_weekends: true

github:
  enabled: true
  exclude_weekends: false
  config:
    token: test_github_token

wakatime:
  enabled: false

atlassian:
  enabled: false

apple_calendar:
  enabled: false

things:
  enabled: false

google_docs:
  enabled: false
"""
    config_path.write_text(config_content)
    return config_path


@pytest.mark.snapshot
def test_cli_markdown_output_with_mocks(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test CLI markdown output with mocked data sources."""
    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.snapshot
def test_cli_json_output_with_mocks(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test CLI JSON output with mocked data sources."""
    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-21",
            "--format",
            "json",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.unit
def test_cli_invalid_date(cli_runner: CliRunner, temp_config: Path) -> None:
    """Test CLI with invalid date format."""
    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "not-a-date",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    # Should fail with an error
    assert result.exit_code != 0


@pytest.mark.unit
def test_cli_default_date(
    cli_runner: CliRunner,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test CLI with default date (today)."""
    result = cli_runner.invoke(
        cli,
        [
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    # Should succeed with today's date
    assert result.exit_code == 0
    assert "Daily Report" in result.output


@pytest.mark.unit
def test_cli_human_readable_date(
    cli_runner: CliRunner,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test CLI with human-readable date format (dateutil supports various formats)."""
    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "Nov 21, 2025",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert "Daily Report" in result.output


@pytest.mark.unit
def test_cli_date_range_markdown_summary(
    cli_runner: CliRunner,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Ensure date range output includes summary and separators."""
    result = cli_runner.invoke(
        cli,
        [
            "--start-date",
            "2025-11-20",
            "--end-date",
            "2025-11-21",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert "# Daily Reports Summary" in result.output
    assert result.output.count("# Daily Report -") == 2
    assert "---" in result.output


@pytest.mark.unit
def test_cli_exclude_weekends_filters_all_days(
    cli_runner: CliRunner,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Weekend-only ranges should abort when excluding weekends."""
    result = cli_runner.invoke(
        cli,
        [
            "--start-date",
            "2025-11-22",
            "--end-date",
            "2025-11-23",
            "--config",
            str(temp_config),
            "--exclude-weekends",
        ],
    )

    assert result.exit_code != 0
    assert "No dates to process" in result.output


@pytest.mark.unit
def test_cli_include_weekends_overrides_config(
    cli_runner: CliRunner,
    weekend_filter_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """--include-weekends should override config exclusion."""
    without_override = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-23",
            "--config",
            str(weekend_filter_config),
        ],
    )
    assert without_override.exit_code != 0
    assert "No dates to process" in without_override.output

    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-23",
            "--config",
            str(weekend_filter_config),
            "--include-weekends",
        ],
    )

    assert result.exit_code == 0
    assert "# Daily Report - 2025-11-23" in result.output


@pytest.mark.unit
def test_cli_missing_config_file(
    cli_runner: CliRunner, mock_platform_linux: Mock, mocker: Mock
) -> None:
    """Test CLI without config file (should use defaults)."""
    # Mock things library to avoid database access
    mocker.patch("things.todos", return_value=[])

    # Mock environment to prevent actual API calls
    # Set all potential API keys to empty to avoid timeouts
    result = cli_runner.invoke(
        cli,
        ["--date", "2025-11-21", "--format", "markdown"],
        env={
            "GITHUB_TOKEN": "",
            "WAKATIME_API_KEY": "",
            "ATLASSIAN_BASE_URL": "",
            "ATLASSIAN_USERNAME": "",
            "ATLASSIAN_API_TOKEN": "",
            "GOOGLE_ACCESS_TOKEN": "",
        },
    )

    # Should still succeed with empty data
    assert result.exit_code == 0


@pytest.mark.snapshot
def test_cli_with_api_errors(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_server_error: Mock,
) -> None:
    """Test CLI when API calls fail (should show errors in output)."""
    # Make GitHub mock raise an error
    mock_github_client.get_user.side_effect = Exception("API connection failed")

    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    # Should still succeed but with error messages
    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.unit
def test_cli_format_option(
    cli_runner: CliRunner,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test CLI with different format options."""
    # Test markdown format
    result_md = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )
    assert result_md.exit_code == 0
    assert "# Daily Report" in result_md.output

    # Test JSON format
    result_json = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-21",
            "--format",
            "json",
            "--config",
            str(temp_config),
        ],
    )
    assert result_json.exit_code == 0
    assert '"date"' in result_json.output


@pytest.mark.snapshot
def test_cli_markdown_output_all_sources(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    full_sources_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
    mock_atlassian_clients: tuple[Mock, Mock],
) -> None:
    """Test CLI markdown output with multiple data sources (GitHub, Wakatime, Atlassian).

    Note: Things is excluded from snapshot tests due to SQLite database mocking
    complexity in CI environments. Things has dedicated integration tests.
    """
    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(full_sources_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.snapshot
def test_cli_json_output_all_sources(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    full_sources_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
    mock_atlassian_clients: tuple[Mock, Mock],
) -> None:
    """Test CLI JSON output with multiple data sources (GitHub, Wakatime, Atlassian).

    Note: Things is excluded from snapshot tests due to SQLite database mocking
    complexity in CI environments. Things has dedicated integration tests.
    """
    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-21",
            "--format",
            "json",
            "--config",
            str(full_sources_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.unit
def test_cli_help(cli_runner: CliRunner) -> None:
    """Test CLI help output."""
    result = cli_runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Personal Knowledge Management Tool" in result.output
    assert "--date" in result.output
    assert "--format" in result.output
    assert "--config" in result.output
    # Verify subcommands are listed
    assert "calendar" in result.output
    assert "github" in result.output
    assert "atlassian" in result.output
    assert "things" in result.output
    assert "wakatime" in result.output
    assert "google-docs" in result.output
    assert "whoop" in result.output
    assert "aggregate" in result.output


# ===== Subcommand Tests =====


@pytest.mark.unit
def test_cli_aggregate_subcommand(
    cli_runner: CliRunner,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test explicit aggregate subcommand works identically to default behavior."""
    result = cli_runner.invoke(
        cli,
        [
            "aggregate",
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert "Daily Report" in result.output


@pytest.mark.unit
def test_cli_backward_compatibility(
    cli_runner: CliRunner,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test that pkm without subcommand still works (backward compatibility)."""
    result = cli_runner.invoke(
        cli,
        [
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert "Daily Report" in result.output


@pytest.mark.snapshot
def test_cli_github_subcommand(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test github subcommand fetches only GitHub data."""
    result = cli_runner.invoke(
        cli,
        [
            "github",
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.snapshot
def test_cli_wakatime_subcommand(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    temp_config: Path,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test wakatime subcommand fetches only Wakatime data."""
    result = cli_runner.invoke(
        cli,
        [
            "wakatime",
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.snapshot
def test_cli_atlassian_subcommand(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    full_sources_config: Path,
    mock_atlassian_clients: tuple[Mock, Mock],
) -> None:
    """Test atlassian subcommand fetches only Atlassian data."""
    result = cli_runner.invoke(
        cli,
        [
            "atlassian",
            "--date",
            "2025-11-21",
            "--format",
            "markdown",
            "--config",
            str(full_sources_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.unit
def test_cli_calendar_subcommand_help(cli_runner: CliRunner) -> None:
    """Test calendar subcommand help."""
    result = cli_runner.invoke(cli, ["calendar", "--help"])

    assert result.exit_code == 0
    assert "Fetch Apple Calendar events only" in result.output


@pytest.mark.unit
def test_cli_github_subcommand_help(cli_runner: CliRunner) -> None:
    """Test github subcommand help."""
    result = cli_runner.invoke(cli, ["github", "--help"])

    assert result.exit_code == 0
    assert "Fetch GitHub activities only" in result.output


@pytest.mark.unit
def test_cli_atlassian_subcommand_help(cli_runner: CliRunner) -> None:
    """Test atlassian subcommand help."""
    result = cli_runner.invoke(cli, ["atlassian", "--help"])

    assert result.exit_code == 0
    assert "Fetch Atlassian (Jira/Confluence) items only" in result.output


@pytest.mark.unit
def test_cli_things_subcommand_help(cli_runner: CliRunner) -> None:
    """Test things subcommand help."""
    result = cli_runner.invoke(cli, ["things", "--help"])

    assert result.exit_code == 0
    assert "Fetch Things tasks only" in result.output


@pytest.mark.unit
def test_cli_wakatime_subcommand_help(cli_runner: CliRunner) -> None:
    """Test wakatime subcommand help."""
    result = cli_runner.invoke(cli, ["wakatime", "--help"])

    assert result.exit_code == 0
    assert "Fetch Wakatime coding activities only" in result.output


@pytest.mark.unit
def test_cli_google_docs_subcommand_help(cli_runner: CliRunner) -> None:
    """Test google-docs subcommand help."""
    result = cli_runner.invoke(cli, ["google-docs", "--help"])

    assert result.exit_code == 0
    assert "Fetch Google Docs only" in result.output


@pytest.mark.unit
def test_cli_aggregate_subcommand_help(cli_runner: CliRunner) -> None:
    """Test aggregate subcommand help."""
    result = cli_runner.invoke(cli, ["aggregate", "--help"])

    assert result.exit_code == 0
    assert "Aggregate data from all configured sources" in result.output


@pytest.mark.snapshot
def test_cli_github_subcommand_json(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    temp_config: Path,
    mock_github_client: Mock,
    mock_github_auth: Mock,
) -> None:
    """Test github subcommand with JSON output."""
    result = cli_runner.invoke(
        cli,
        [
            "github",
            "--date",
            "2025-11-21",
            "--format",
            "json",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot


@pytest.mark.snapshot
def test_cli_wakatime_subcommand_json(
    cli_runner: CliRunner,
    snapshot: SnapshotAssertion,
    temp_config: Path,
    mock_wakatime_api_success: Mock,
) -> None:
    """Test wakatime subcommand with JSON output."""
    result = cli_runner.invoke(
        cli,
        [
            "wakatime",
            "--date",
            "2025-11-21",
            "--format",
            "json",
            "--config",
            str(temp_config),
        ],
    )

    assert result.exit_code == 0
    assert result.output == snapshot
