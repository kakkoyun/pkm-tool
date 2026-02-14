'"""Tests for authentication utilities."""'

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest
from click.testing import CliRunner

from pkm_tool.auth.manager import AuthManager
from pkm_tool.auth.oauth.base import OAuthTokenResponse
from pkm_tool.auth.token_store import TokenStore
from pkm_tool.cli import cli


@pytest.fixture
def token_store(tmp_path: Path) -> TokenStore:
    return TokenStore(tmp_path / "tokens.db")


@pytest.fixture
def auth_manager(token_store: TokenStore, monkeypatch: pytest.MonkeyPatch) -> AuthManager:
    manager = AuthManager(token_store=token_store, refresh_margin_seconds=0)
    monkeypatch.setattr("pkm_tool.cli.common._AUTH_MANAGER", manager)
    return manager


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_token_store_round_trip(token_store: TokenStore) -> None:
    expires = datetime.now(UTC) + timedelta(hours=1)
    token_store.save_token("github", "secret", refresh_token="refresh", expires_at=expires)
    stored = token_store.get_token("github")
    assert stored is not None
    assert stored.token == "secret"
    assert stored.refresh_token == "refresh"
    assert stored.expires_at == expires.replace(microsecond=0)


def test_token_store_list_and_delete(token_store: TokenStore) -> None:
    token_store.save_token("github", "secret")
    token_store.save_token("wakatime", "waka")
    tokens = token_store.list_tokens()
    assert {t.source for t in tokens} == {"github", "wakatime"}
    token_store.delete_token("github")
    assert token_store.get_token("github") is None


def test_auth_manager_refreshes_token(token_store: TokenStore) -> None:
    manager = AuthManager(token_store=token_store, refresh_margin_seconds=0)
    expired = datetime.now(UTC) - timedelta(minutes=5)
    token_store.save_token("google_docs", "old", refresh_token="refresh", expires_at=expired)
    provider = Mock()
    provider.refresh_access_token.return_value = OAuthTokenResponse(
        access_token="new",
        refresh_token="refresh",
        expires_in=3600,
    )
    refreshed = manager.ensure_oauth_token("google_docs", provider)
    assert refreshed is not None
    assert refreshed.token == "new"
    provider.refresh_access_token.assert_called_once_with("refresh")


def test_auth_manager_interactive_flow(token_store: TokenStore) -> None:
    manager = AuthManager(token_store=token_store, refresh_margin_seconds=0)
    provider = Mock()
    provider.refresh_access_token.return_value = None
    provider.obtain_token_interactive.return_value = OAuthTokenResponse(
        access_token="interactive",
        refresh_token=None,
        expires_in=None,
    )
    stored = manager.ensure_oauth_token("google_docs", provider, allow_interactive=True)
    assert stored is not None
    assert stored.token == "interactive"
    provider.obtain_token_interactive.assert_called_once()


def test_auth_cli_login_and_status(auth_manager: AuthManager, cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["auth", "login", "github"], input="ghp_test\n")
    assert result.exit_code == 0
    status = cli_runner.invoke(cli, ["auth", "status"])
    assert status.exit_code == 0
    assert "GitHub" in status.output
    assert "authenticated" in status.output


def test_auth_cli_logout_removes_token(auth_manager: AuthManager, cli_runner: CliRunner) -> None:
    cli_runner.invoke(cli, ["auth", "login", "wakatime"], input="waka_key\n")
    assert auth_manager.get_token("wakatime") is not None
    result = cli_runner.invoke(cli, ["auth", "logout", "wakatime"])
    assert result.exit_code == 0
    assert "Removed stored credentials" in result.output
    assert auth_manager.get_token("wakatime") is None


def test_auth_cli_login_whoop(auth_manager: AuthManager, cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["auth", "login", "whoop"], input="whoop_access\n")
    assert result.exit_code == 0
    stored = auth_manager.get_token("whoop")
    assert stored is not None
    assert stored.token == "whoop_access"
