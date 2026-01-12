"""Tests for Wakatime integration and .wakatime.cfg file support."""

import configparser
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pkm_tool.sources.wakatime import _get_wakatime_token, _read_wakatime_cfg


class TestReadWakatimeCfg:
    """Tests for _read_wakatime_cfg function."""

    def test_read_valid_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reading a valid .wakatime.cfg file with api_key."""
        # Create a valid .wakatime.cfg file
        cfg_content = """[settings]
api_key = waka_test_12345_abcdef
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)

        # Mock Path.home() to return our tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        assert result == "waka_test_12345_abcdef"

    def test_read_missing_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reading when .wakatime.cfg file does not exist."""
        # Ensure no .wakatime.cfg exists
        cfg_file = tmp_path / ".wakatime.cfg"
        assert not cfg_file.exists()

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        assert result is None

    def test_read_missing_settings_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test reading when [settings] section is missing."""
        # Create config file without [settings] section
        cfg_content = """[other_section]
some_key = some_value
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        assert result is None

    def test_read_missing_api_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reading when [settings] section exists but api_key is missing."""
        cfg_content = """[settings]
debug = true
timeout = 30
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        assert result is None

    def test_read_empty_api_key(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reading when api_key exists but is empty string."""
        cfg_content = """[settings]
api_key =
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        # Empty string should be treated as no key
        assert result is None

    def test_read_whitespace_only_api_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test reading when api_key contains only whitespace."""
        cfg_content = """[settings]
api_key =
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        # Whitespace-only should be treated as no key (configparser strips whitespace)
        assert result is None

    def test_read_malformed_ini(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test reading a malformed INI file returns None gracefully."""
        # Create a malformed INI file (no section header)
        cfg_content = """this is not valid ini format
api_key = test123
[settings
broken section
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        # Should return None without raising exception
        assert result is None

    def test_read_permission_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test handling of permission/OS errors when reading file."""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text("[settings]\napi_key = test123")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Mock configparser.ConfigParser.read to raise OSError
        with patch.object(
            configparser.ConfigParser, "read", side_effect=OSError("Permission denied")
        ):
            result = _read_wakatime_cfg()

        assert result is None

    def test_read_config_with_extra_settings(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test reading config with additional settings besides api_key."""
        cfg_content = """[settings]
debug = true
api_key = waka_real_key_here
timeout = 120
hide_project_names = false
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        assert result == "waka_real_key_here"

    def test_read_config_with_multiple_sections(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test reading config with multiple INI sections."""
        cfg_content = """[internal]
debug = true

[settings]
api_key = waka_multi_section_key

[git]
enabled = true
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = _read_wakatime_cfg()

        assert result == "waka_multi_section_key"


class TestGetWakatimeToken:
    """Tests for _get_wakatime_token function."""

    def test_priority_token_store_first(self) -> None:
        """Test that token store has highest priority."""
        mock_token = MagicMock()
        mock_token.token = "stored_token"
        config = {"api_key": "config_token"}

        with (
            patch("pkm_tool.sources.common.AuthManager") as mock_auth_class,
            patch(
                "pkm_tool.sources.wakatime._read_wakatime_cfg", return_value="wakatime_cfg_token"
            ),
        ):
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = mock_token
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)

        # Token store should win over all others
        assert result == "stored_token"

    def test_priority_config_over_wakatime_cfg(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that config file has priority over .wakatime.cfg."""
        config = {"api_key": "config_api_key"}

        # Set up .wakatime.cfg
        cfg_content = """[settings]
api_key = wakatime_cfg_key
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None  # No stored token
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)

        # Config should win over .wakatime.cfg
        assert result == "config_api_key"

    def test_priority_wakatime_cfg_over_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that .wakatime.cfg has priority over environment variable."""
        config: dict = {}  # Empty config

        # Set up .wakatime.cfg
        cfg_content = """[settings]
api_key = wakatime_cfg_key
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Set environment variable
        monkeypatch.setenv("WAKATIME_API_KEY", "env_api_key")

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None  # No stored token
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)

        # .wakatime.cfg should win over environment variable
        assert result == "wakatime_cfg_key"

    def test_fallback_to_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fallback to environment variable when nothing else available."""
        config: dict = {}  # Empty config

        # Ensure no .wakatime.cfg exists
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Set environment variable
        monkeypatch.setenv("WAKATIME_API_KEY", "env_only_key")

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None  # No stored token
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)

        assert result == "env_only_key"

    def test_returns_none_when_nothing_available(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that None is returned when all sources are empty."""
        config: dict = {}  # Empty config

        # Ensure no .wakatime.cfg exists
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Ensure no environment variable
        monkeypatch.delenv("WAKATIME_API_KEY", raising=False)

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None  # No stored token
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)

        assert result is None

    def test_empty_config_value_falls_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that empty string in config falls through to next source."""
        config = {"api_key": ""}  # Empty string in config

        # Set up .wakatime.cfg
        cfg_content = """[settings]
api_key = wakatime_cfg_key
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)

        # Empty string is falsy, so should fall through to .wakatime.cfg
        assert result == "wakatime_cfg_key"

    def test_full_priority_chain(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test the complete priority chain: store > config > .wakatime.cfg > env."""
        # Set up all sources
        mock_token = MagicMock()
        mock_token.token = "stored_token"
        config = {"api_key": "config_token"}

        cfg_content = """[settings]
api_key = wakatime_cfg_token
"""
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text(cfg_content)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("WAKATIME_API_KEY", "env_token")

        # Test with token store available - should return stored token
        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = mock_token
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)
            assert result == "stored_token"

        # Test without token store - should return config token
        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)
            assert result == "config_token"

        # Test without token store and config - should return .wakatime.cfg token
        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token({})
            assert result == "wakatime_cfg_token"

        # Test without token store, config, and .wakatime.cfg - should return env token
        # Remove .wakatime.cfg
        cfg_file.unlink()

        with patch("pkm_tool.sources.common.AuthManager") as mock_auth_class:
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token({})
            assert result == "env_token"

    def test_wakatime_cfg_read_error_falls_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that read errors from .wakatime.cfg fall through to env var."""
        config: dict = {}

        # Create a file that will cause a read error
        cfg_file = tmp_path / ".wakatime.cfg"
        cfg_file.write_text("[settings]\napi_key = test")
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("WAKATIME_API_KEY", "env_fallback_key")

        with (
            patch("pkm_tool.sources.common.AuthManager") as mock_auth_class,
            patch.object(configparser.ConfigParser, "read", side_effect=OSError("Read error")),
        ):
            mock_auth = MagicMock()
            mock_auth.get_token.return_value = None
            mock_auth_class.return_value = mock_auth

            result = _get_wakatime_token(config)

        # Should fall through to env var due to read error
        assert result == "env_fallback_key"
