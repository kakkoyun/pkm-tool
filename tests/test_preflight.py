"""Tests for pre-flight authentication checking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from pkm_tool.auth.preflight import (
    SOURCE_AUTH_INFO,
    AuthState,
    PreflightChecker,
    SourceAuthStatus,
)
from pkm_tool.auth.token_store import StoredToken
from pkm_tool.config import Config, SourceConfig

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


# ============================================================================
# AuthState Tests
# ============================================================================


@pytest.mark.unit
class TestAuthState:
    """Tests for AuthState enum."""

    def test_auth_state_values(self) -> None:
        """Test AuthState enum has expected values."""
        assert AuthState.VALID.value == "valid"
        assert AuthState.EXPIRED.value == "expired"
        assert AuthState.MISSING.value == "missing"
        assert AuthState.NOT_REQUIRED.value == "not_required"
        assert AuthState.INVALID_CONFIG.value == "invalid_config"
        assert AuthState.DISABLED.value == "disabled"

    def test_auth_state_count(self) -> None:
        """Test AuthState has all expected states."""
        assert len(AuthState) == 6


# ============================================================================
# SourceAuthStatus Tests
# ============================================================================


@pytest.mark.unit
class TestSourceAuthStatus:
    """Tests for SourceAuthStatus dataclass."""

    def test_basic_creation(self) -> None:
        """Test creating a basic status."""
        status = SourceAuthStatus(
            source="github",
            state=AuthState.VALID,
            message="Token valid",
        )
        assert status.source == "github"
        assert status.state == AuthState.VALID
        assert status.message == "Token valid"
        # display_name is auto-generated from source via __post_init__
        assert status.display_name == "Github"
        assert status.can_refresh is False
        assert status.expires_at is None
        assert status.missing_fields == []

    def test_full_creation(self) -> None:
        """Test creating a status with all fields."""
        expires = datetime.now(UTC) + timedelta(hours=1)
        status = SourceAuthStatus(
            source="google_docs",
            state=AuthState.EXPIRED,
            message="Token expired",
            display_name="Google Docs",
            can_refresh=True,
            expires_at=expires,
            missing_fields=["client_id"],
        )
        assert status.source == "google_docs"
        assert status.state == AuthState.EXPIRED
        assert status.message == "Token expired"
        assert status.display_name == "Google Docs"
        assert status.can_refresh is True
        assert status.expires_at == expires
        assert status.missing_fields == ["client_id"]


# ============================================================================
# PreflightChecker Tests
# ============================================================================


@pytest.fixture
def mock_auth_manager(mocker: MockerFixture) -> Mock:
    """Create a mock AuthManager."""
    manager = mocker.Mock()
    manager.get_token.return_value = None
    return manager


@pytest.fixture
def checker(mock_auth_manager: Mock) -> PreflightChecker:
    """Create a PreflightChecker with mocked auth manager."""
    return PreflightChecker(mock_auth_manager)


@pytest.fixture
def minimal_config() -> Config:
    """Create a minimal config with only disabled sources."""
    return Config(
        github=SourceConfig(enabled=False),
        wakatime=SourceConfig(enabled=False),
        atlassian=SourceConfig(enabled=False),
        apple_calendar=SourceConfig(enabled=False),
        things=SourceConfig(enabled=False),
        google_docs=SourceConfig(enabled=False),
        whoop=SourceConfig(enabled=False),
    )


@pytest.fixture
def github_config() -> Config:
    """Create a config with only GitHub enabled."""
    return Config(
        github=SourceConfig(enabled=True, config={"token": "test-token"}),
        wakatime=SourceConfig(enabled=False),
        atlassian=SourceConfig(enabled=False),
        apple_calendar=SourceConfig(enabled=False),
        things=SourceConfig(enabled=False),
        google_docs=SourceConfig(enabled=False),
        whoop=SourceConfig(enabled=False),
    )


@pytest.mark.unit
class TestPreflightCheckerBasics:
    """Basic PreflightChecker tests."""

    def test_checker_initialization(self, mock_auth_manager: Mock) -> None:
        """Test PreflightChecker can be initialized."""
        checker = PreflightChecker(mock_auth_manager)
        assert checker.auth_manager == mock_auth_manager

    def test_check_all_sources_all_disabled(
        self, checker: PreflightChecker, minimal_config: Config
    ) -> None:
        """Test checking all sources when all are disabled."""
        statuses = checker.check_all_sources(minimal_config)

        # Should get one status per source
        assert len(statuses) == 7

        # All should be disabled
        for status in statuses:
            assert status.state == AuthState.DISABLED

    def test_get_summary(self, checker: PreflightChecker) -> None:
        """Test get_summary aggregates states correctly."""
        statuses = [
            SourceAuthStatus("a", AuthState.VALID, "ok"),
            SourceAuthStatus("b", AuthState.VALID, "ok"),
            SourceAuthStatus("c", AuthState.MISSING, "missing"),
            SourceAuthStatus("d", AuthState.DISABLED, "disabled"),
        ]

        summary = checker.get_summary(statuses)

        assert summary["valid"] == 2
        assert summary["missing"] == 1
        assert summary["disabled"] == 1
        assert summary["expired"] == 0

    def test_all_ready_true(self, checker: PreflightChecker) -> None:
        """Test all_ready returns True when all sources are ready."""
        statuses = [
            SourceAuthStatus("a", AuthState.VALID, "ok"),
            SourceAuthStatus("b", AuthState.NOT_REQUIRED, "no auth needed"),
            SourceAuthStatus("c", AuthState.DISABLED, "disabled"),
        ]

        assert checker.all_ready(statuses) is True

    def test_all_ready_false(self, checker: PreflightChecker) -> None:
        """Test all_ready returns False when any source needs auth."""
        statuses = [
            SourceAuthStatus("a", AuthState.VALID, "ok"),
            SourceAuthStatus("b", AuthState.MISSING, "missing"),
        ]

        assert checker.all_ready(statuses) is False

    def test_needs_resolution(self, checker: PreflightChecker) -> None:
        """Test needs_resolution returns sources needing auth."""
        statuses = [
            SourceAuthStatus("a", AuthState.VALID, "ok"),
            SourceAuthStatus("b", AuthState.MISSING, "missing"),
            SourceAuthStatus("c", AuthState.EXPIRED, "expired"),
            SourceAuthStatus("d", AuthState.DISABLED, "disabled"),
        ]

        needs = checker.needs_resolution(statuses)

        assert len(needs) == 2
        assert needs[0].source == "b"
        assert needs[1].source == "c"


@pytest.mark.unit
class TestPreflightCheckerGitHub:
    """GitHub-specific PreflightChecker tests."""

    def test_github_with_config_token(
        self, checker: PreflightChecker, github_config: Config
    ) -> None:
        """Test GitHub auth check with token in config."""
        status = checker.check_source("github", github_config.github)

        assert status.state == AuthState.VALID
        assert status.source == "github"
        assert "valid" in status.message.lower() or "configured" in status.message.lower()

    def test_github_missing_token(self, checker: PreflightChecker, mocker: MockerFixture) -> None:
        """Test GitHub auth check with no token anywhere."""
        # Ensure no token in config, env, or store
        mocker.patch.dict("os.environ", {}, clear=True)

        source_config = SourceConfig(enabled=True, config={})
        status = checker.check_source("github", source_config)

        assert status.state == AuthState.MISSING
        assert status.source == "github"

    def test_github_with_stored_token(self, mock_auth_manager: Mock, mocker: MockerFixture) -> None:
        """Test GitHub auth check with stored token."""
        stored = StoredToken(
            source="github",
            token="stored-token",
            refresh_token=None,
            expires_at=None,
            token_type="pat",
        )
        mock_auth_manager.get_token.return_value = stored

        checker = PreflightChecker(mock_auth_manager)
        source_config = SourceConfig(enabled=True, config={})

        # Clear env vars
        mocker.patch.dict("os.environ", {}, clear=True)

        status = checker.check_source("github", source_config)

        assert status.state == AuthState.VALID
        mock_auth_manager.get_token.assert_called_with("github")


@pytest.mark.unit
class TestPreflightCheckerOAuth:
    """OAuth source (Google Docs, Whoop) PreflightChecker tests."""

    def test_google_docs_with_valid_token(
        self, mock_auth_manager: Mock, mocker: MockerFixture
    ) -> None:
        """Test Google Docs auth check with valid OAuth token."""
        expires = datetime.now(UTC) + timedelta(hours=1)
        stored = StoredToken(
            source="google_docs",
            token="access-token",
            refresh_token="refresh-token",
            expires_at=expires,
            token_type="oauth",
        )
        mock_auth_manager.get_token.return_value = stored

        checker = PreflightChecker(mock_auth_manager)
        source_config = SourceConfig(enabled=True, config={})

        status = checker.check_source("google_docs", source_config)

        assert status.state == AuthState.VALID
        # can_refresh is only set to True for EXPIRED tokens that have refresh_token
        # For VALID tokens, it's False since no refresh is needed
        assert status.can_refresh is False

    def test_google_docs_with_expired_token(
        self, mock_auth_manager: Mock, mocker: MockerFixture
    ) -> None:
        """Test Google Docs auth check with expired OAuth token."""
        expires = datetime.now(UTC) - timedelta(hours=1)  # Already expired
        stored = StoredToken(
            source="google_docs",
            token="access-token",
            refresh_token="refresh-token",
            expires_at=expires,
            token_type="oauth",
        )
        mock_auth_manager.get_token.return_value = stored

        checker = PreflightChecker(mock_auth_manager)
        source_config = SourceConfig(enabled=True, config={})

        status = checker.check_source("google_docs", source_config)

        assert status.state == AuthState.EXPIRED
        assert status.can_refresh is True  # Has refresh token

    def test_whoop_missing_token(self, mock_auth_manager: Mock, mocker: MockerFixture) -> None:
        """Test Whoop auth check with no token."""
        mock_auth_manager.get_token.return_value = None
        mocker.patch.dict("os.environ", {}, clear=True)

        checker = PreflightChecker(mock_auth_manager)
        source_config = SourceConfig(enabled=True, config={})

        status = checker.check_source("whoop", source_config)

        assert status.state == AuthState.MISSING


@pytest.mark.unit
class TestPreflightCheckerPlatformSources:
    """Platform-specific source (Calendar, Things) PreflightChecker tests."""

    def test_calendar_on_macos(self, checker: PreflightChecker, mocker: MockerFixture) -> None:
        """Test Apple Calendar auth check on macOS."""
        mocker.patch("pkm_tool.auth.preflight.platform.system", return_value="Darwin")

        source_config = SourceConfig(enabled=True, config={})
        status = checker.check_source("apple_calendar", source_config)

        assert status.state == AuthState.NOT_REQUIRED
        assert "No authentication required" in status.message

    def test_calendar_on_linux(self, checker: PreflightChecker, mocker: MockerFixture) -> None:
        """Test Apple Calendar auth check on Linux (returns NOT_REQUIRED with platform message)."""
        mocker.patch("pkm_tool.auth.preflight.platform.system", return_value="Linux")

        source_config = SourceConfig(enabled=True, config={})
        status = checker.check_source("apple_calendar", source_config)

        # Platform sources still return NOT_REQUIRED but with message about platform
        assert status.state == AuthState.NOT_REQUIRED
        assert "Darwin" in status.message
        assert "Linux" in status.message

    def test_things_on_macos(self, checker: PreflightChecker, mocker: MockerFixture) -> None:
        """Test Things auth check on macOS."""
        mocker.patch("pkm_tool.auth.preflight.platform.system", return_value="Darwin")

        source_config = SourceConfig(enabled=True, config={})
        status = checker.check_source("things", source_config)

        assert status.state == AuthState.NOT_REQUIRED

    def test_things_on_windows(self, checker: PreflightChecker, mocker: MockerFixture) -> None:
        """Test Things auth check on Windows (returns NOT_REQUIRED with platform message)."""
        mocker.patch("pkm_tool.auth.preflight.platform.system", return_value="Windows")

        source_config = SourceConfig(enabled=True, config={})
        status = checker.check_source("things", source_config)

        # Platform sources still return NOT_REQUIRED but with message about platform
        assert status.state == AuthState.NOT_REQUIRED
        assert "Darwin" in status.message
        assert "Windows" in status.message


@pytest.mark.unit
class TestPreflightCheckerAtlassian:
    """Atlassian-specific PreflightChecker tests."""

    def test_atlassian_with_complete_config(self, checker: PreflightChecker) -> None:
        """Test Atlassian auth check with all required fields."""
        source_config = SourceConfig(
            enabled=True,
            config={
                "base_url": "https://test.atlassian.net",
                "username": "test@example.com",
                "api_token": "test-token",
            },
        )

        status = checker.check_source("atlassian", source_config)

        assert status.state == AuthState.VALID

    def test_atlassian_missing_base_url(self, checker: PreflightChecker) -> None:
        """Test Atlassian auth check missing base_url."""
        source_config = SourceConfig(
            enabled=True,
            config={
                "username": "test@example.com",
                "api_token": "test-token",
            },
        )

        status = checker.check_source("atlassian", source_config)

        assert status.state == AuthState.MISSING
        assert "base_url" in status.missing_fields

    def test_atlassian_missing_all_fields(self, checker: PreflightChecker) -> None:
        """Test Atlassian auth check missing all fields."""
        source_config = SourceConfig(enabled=True, config={})

        status = checker.check_source("atlassian", source_config)

        assert status.state == AuthState.MISSING
        assert "base_url" in status.missing_fields
        assert "username" in status.missing_fields
        assert "api_token" in status.missing_fields


# ============================================================================
# SOURCE_AUTH_INFO Tests
# ============================================================================


@pytest.mark.unit
class TestSourceAuthInfo:
    """Tests for SOURCE_AUTH_INFO constant."""

    def test_all_sources_have_info(self) -> None:
        """Test all expected sources are in SOURCE_AUTH_INFO."""
        expected_sources = {
            "github",
            "wakatime",
            "atlassian",
            "google_docs",
            "whoop",
            "apple_calendar",
            "things",
        }
        assert set(SOURCE_AUTH_INFO.keys()) == expected_sources

    def test_source_info_has_required_fields(self) -> None:
        """Test each source info has required fields."""
        for source, info in SOURCE_AUTH_INFO.items():
            assert "display" in info, f"{source} missing 'display'"
            assert "auth_type" in info, f"{source} missing 'auth_type'"

    def test_source_info_auth_types(self) -> None:
        """Test source auth types are valid."""
        valid_auth_types = {"token", "api_key", "oauth", "basic_auth", "native"}

        for source, info in SOURCE_AUTH_INFO.items():
            assert info["auth_type"] in valid_auth_types, (
                f"{source} has invalid auth_type: {info['auth_type']}"
            )


# ============================================================================
# GitHub Auth Resolution Tests
# ============================================================================


@pytest.mark.unit
class TestGitHubAuthResolution:
    """Tests for GitHub-specific authentication resolution."""

    def test_try_gh_cli_token_success(self, mock_auth_manager: Mock, mocker: MockerFixture) -> None:
        """Test _try_gh_cli_token returns token when gh CLI is authenticated."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(returncode=0, stdout="ghp_test_token_123\n")

        checker = PreflightChecker(mock_auth_manager)
        token = checker._try_gh_cli_token()

        assert token == "ghp_test_token_123"
        mock_run.assert_called_once_with(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=5,
        )

    def test_try_gh_cli_token_not_installed(
        self, mock_auth_manager: Mock, mocker: MockerFixture
    ) -> None:
        """Test _try_gh_cli_token returns None when gh CLI is not installed."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError("gh not found")

        checker = PreflightChecker(mock_auth_manager)
        token = checker._try_gh_cli_token()

        assert token is None

    def test_try_gh_cli_token_not_authenticated(
        self, mock_auth_manager: Mock, mocker: MockerFixture
    ) -> None:
        """Test _try_gh_cli_token returns None when gh CLI is not authenticated."""
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(returncode=1, stdout="")

        checker = PreflightChecker(mock_auth_manager)
        token = checker._try_gh_cli_token()

        assert token is None

    def test_try_gh_cli_token_timeout(self, mock_auth_manager: Mock, mocker: MockerFixture) -> None:
        """Test _try_gh_cli_token returns None on timeout."""
        import subprocess

        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=5)

        checker = PreflightChecker(mock_auth_manager)
        token = checker._try_gh_cli_token()

        assert token is None

    def test_resolve_github_with_gh_cli(
        self, mock_auth_manager: Mock, mocker: MockerFixture
    ) -> None:
        """Test GitHub resolution uses gh CLI token when available."""
        # Mock gh CLI returning a token
        mock_run = mocker.patch("subprocess.run")
        mock_run.return_value = Mock(returncode=0, stdout="ghp_cli_token\n")

        # Mock click.echo to avoid output
        mocker.patch("pkm_tool.auth.preflight.click.echo")

        checker = PreflightChecker(mock_auth_manager)
        source_config = SourceConfig(enabled=True, config={})
        info = {"display": "GitHub"}

        result = checker._resolve_github_source("github", source_config, info, interactive=True)

        # Should store the token
        mock_auth_manager.store_api_token.assert_called_once_with("github", "ghp_cli_token")
        assert result is not None

    def test_resolve_github_browser_fallback(
        self, mock_auth_manager: Mock, mocker: MockerFixture
    ) -> None:
        """Test GitHub resolution opens browser when gh CLI not available."""
        # Mock gh CLI not installed
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        # Mock user interactions
        mocker.patch("pkm_tool.auth.preflight.click.echo")
        mock_confirm = mocker.patch("pkm_tool.auth.preflight.click.confirm")
        mock_confirm.return_value = True
        mock_prompt = mocker.patch("pkm_tool.auth.preflight.click.prompt")
        mock_prompt.return_value = "ghp_manual_token"

        # Mock webbrowser
        mock_webbrowser = mocker.patch("webbrowser.open")

        checker = PreflightChecker(mock_auth_manager)
        source_config = SourceConfig(enabled=True, config={})
        info = {"display": "GitHub"}

        result = checker._resolve_github_source("github", source_config, info, interactive=True)

        # Should open browser with PAT URL
        mock_webbrowser.assert_called_once()
        call_url = mock_webbrowser.call_args[0][0]
        assert "github.com/settings/tokens/new" in call_url
        assert "scopes=repo,read:user" in call_url

        # Should store the manually entered token
        mock_auth_manager.store_api_token.assert_called_once_with("github", "ghp_manual_token")
        assert result is not None

    def test_resolve_github_user_declines(
        self, mock_auth_manager: Mock, mocker: MockerFixture
    ) -> None:
        """Test GitHub resolution returns None when user declines."""
        # Mock gh CLI not installed
        mock_run = mocker.patch("subprocess.run")
        mock_run.side_effect = FileNotFoundError()

        # Mock user declining
        mocker.patch("pkm_tool.auth.preflight.click.echo")
        mock_confirm = mocker.patch("pkm_tool.auth.preflight.click.confirm")
        mock_confirm.return_value = False

        checker = PreflightChecker(mock_auth_manager)
        source_config = SourceConfig(enabled=True, config={})
        info = {"display": "GitHub"}

        result = checker._resolve_github_source("github", source_config, info, interactive=True)

        assert result is None
        mock_auth_manager.store_api_token.assert_not_called()

    def test_resolve_github_non_interactive(
        self, mock_auth_manager: Mock, mocker: MockerFixture
    ) -> None:
        """Test GitHub resolution returns None in non-interactive mode."""
        checker = PreflightChecker(mock_auth_manager)
        source_config = SourceConfig(enabled=True, config={})
        info = {"display": "GitHub"}

        result = checker._resolve_github_source("github", source_config, info, interactive=False)

        assert result is None
