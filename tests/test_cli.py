"""CLI snapshot tests."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from syrupy.assertion import SnapshotAssertion

from pkm_tool.cli import main


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Create a temporary config file with only GitHub and Wakatime enabled."""
    config_path = tmp_path / "test_config.yaml"
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
        main,
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
        main,
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
        main,
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
        main,
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
        main,
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
    assert "2025-11-21" in result.output


@pytest.mark.unit
def test_cli_missing_config_file(cli_runner: CliRunner) -> None:
    """Test CLI without config file (should use defaults)."""
    # Mock environment to prevent actual API calls
    result = cli_runner.invoke(
        main,
        ["--date", "2025-11-21", "--format", "markdown"],
        env={"GITHUB_TOKEN": "", "WAKATIME_API_KEY": ""},
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
        main,
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
        main,
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
        main,
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
        main,
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
        main,
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
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Personal Knowledge Management Tool" in result.output
    assert "--date" in result.output
    assert "--format" in result.output
    assert "--config" in result.output
