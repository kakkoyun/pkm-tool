"""Tests for browser utilities."""

from __future__ import annotations

import webbrowser
from unittest.mock import MagicMock, patch

from pkm_tool.auth.browser import open_browser


class TestOpenBrowser:
    """Tests for open_browser function."""

    def test_default_browser_none(self) -> None:
        """Test that None uses system default browser."""
        with patch("pkm_tool.auth.browser.webbrowser.open") as mock_open:
            mock_open.return_value = True

            result = open_browser("https://example.com", preferred_browser=None)

            assert result is True
            mock_open.assert_called_once_with("https://example.com")

    def test_default_browser_string(self) -> None:
        """Test that 'default' string uses system default browser."""
        with patch("pkm_tool.auth.browser.webbrowser.open") as mock_open:
            mock_open.return_value = True

            result = open_browser("https://example.com", preferred_browser="default")

            assert result is True
            mock_open.assert_called_once_with("https://example.com")

    def test_preferred_browser_found(self) -> None:
        """Test that specific browser opens successfully when found."""
        mock_browser = MagicMock()
        mock_browser.open.return_value = True

        with patch("pkm_tool.auth.browser.webbrowser.get") as mock_get:
            mock_get.return_value = mock_browser

            result = open_browser("https://example.com", preferred_browser="firefox")

            assert result is True
            mock_get.assert_called_once_with("firefox")
            mock_browser.open.assert_called_once_with("https://example.com")

    def test_preferred_browser_not_found_fallback(self) -> None:
        """Test fallback to default browser when preferred browser is not found."""
        with (
            patch("pkm_tool.auth.browser.webbrowser.get") as mock_get,
            patch("pkm_tool.auth.browser.webbrowser.open") as mock_open,
        ):
            mock_get.side_effect = webbrowser.Error("Browser not found")
            mock_open.return_value = True

            result = open_browser("https://example.com", preferred_browser="nonexistent")

            assert result is True
            mock_get.assert_called_once_with("nonexistent")
            mock_open.assert_called_once_with("https://example.com")

    def test_browser_open_returns_true(self) -> None:
        """Test that successful browser open returns True."""
        with patch("pkm_tool.auth.browser.webbrowser.open") as mock_open:
            mock_open.return_value = True

            result = open_browser("https://example.com")

            assert result is True

    def test_browser_open_returns_false(self) -> None:
        """Test that failed browser open returns False."""
        with patch("pkm_tool.auth.browser.webbrowser.open") as mock_open:
            mock_open.return_value = False

            result = open_browser("https://example.com")

            assert result is False

    def test_handles_exception_gracefully(self) -> None:
        """Test that unexpected exceptions return False and don't raise."""
        with patch("pkm_tool.auth.browser.webbrowser.open") as mock_open:
            mock_open.side_effect = RuntimeError("Unexpected error")

            # Should not raise, should return False
            result = open_browser("https://example.com")

            assert result is False

    def test_case_insensitive_default(self) -> None:
        """Test that 'DEFAULT', 'Default', etc. are all treated the same."""
        with patch("pkm_tool.auth.browser.webbrowser.open") as mock_open:
            mock_open.return_value = True

            # Test uppercase
            result_upper = open_browser("https://example.com", preferred_browser="DEFAULT")
            assert result_upper is True

            # Test mixed case
            result_mixed = open_browser("https://example.com", preferred_browser="Default")
            assert result_mixed is True

            # Test title case
            result_title = open_browser("https://example.com", preferred_browser="DeFaUlT")
            assert result_title is True

            # All calls should use system default (webbrowser.open, not webbrowser.get)
            assert mock_open.call_count == 3

    def test_preferred_browser_returns_false(self) -> None:
        """Test that preferred browser returning False is propagated."""
        mock_browser = MagicMock()
        mock_browser.open.return_value = False

        with patch("pkm_tool.auth.browser.webbrowser.get") as mock_get:
            mock_get.return_value = mock_browser

            result = open_browser("https://example.com", preferred_browser="chrome")

            assert result is False

    def test_exception_in_preferred_browser_open(self) -> None:
        """Test exception during preferred browser.open() falls through to outer handler."""
        mock_browser = MagicMock()
        mock_browser.open.side_effect = RuntimeError("Browser crashed")

        with patch("pkm_tool.auth.browser.webbrowser.get") as mock_get:
            mock_get.return_value = mock_browser

            result = open_browser("https://example.com", preferred_browser="chrome")

            # The outer exception handler catches this and returns False
            assert result is False

    def test_empty_string_preferred_browser(self) -> None:
        """Test that empty string uses system default browser."""
        with patch("pkm_tool.auth.browser.webbrowser.open") as mock_open:
            mock_open.return_value = True

            # Empty string is falsy, so should use default
            result = open_browser("https://example.com", preferred_browser="")

            assert result is True
            mock_open.assert_called_once_with("https://example.com")

    def test_url_passed_correctly(self) -> None:
        """Test that URL is passed correctly to browser."""
        test_url = "https://oauth.example.com/authorize?client_id=abc&scope=read"

        with patch("pkm_tool.auth.browser.webbrowser.open") as mock_open:
            mock_open.return_value = True

            open_browser(test_url)

            mock_open.assert_called_once_with(test_url)

    def test_preferred_browser_url_passed_correctly(self) -> None:
        """Test that URL is passed correctly to preferred browser."""
        test_url = "https://oauth.example.com/callback?code=xyz"
        mock_browser = MagicMock()
        mock_browser.open.return_value = True

        with patch("pkm_tool.auth.browser.webbrowser.get") as mock_get:
            mock_get.return_value = mock_browser

            open_browser(test_url, preferred_browser="safari")

            mock_browser.open.assert_called_once_with(test_url)


class TestOpenBrowserLogging:
    """Tests for logging behavior in open_browser function."""

    def test_logs_debug_on_default_browser_success(self) -> None:
        """Test that debug logging occurs on successful default browser open."""
        with (
            patch("pkm_tool.auth.browser.webbrowser.open") as mock_open,
            patch("pkm_tool.auth.browser.logger") as mock_logger,
        ):
            mock_open.return_value = True

            open_browser("https://example.com")

            mock_logger.debug.assert_called_once_with(
                "browser_open_default", url="https://example.com", success=True
            )

    def test_logs_debug_on_preferred_browser_success(self) -> None:
        """Test that debug logging occurs on successful preferred browser open."""
        mock_browser = MagicMock()
        mock_browser.open.return_value = True

        with (
            patch("pkm_tool.auth.browser.webbrowser.get") as mock_get,
            patch("pkm_tool.auth.browser.logger") as mock_logger,
        ):
            mock_get.return_value = mock_browser

            open_browser("https://example.com", preferred_browser="firefox")

            mock_logger.debug.assert_called_once_with(
                "browser_open_preferred",
                browser="firefox",
                url="https://example.com",
                success=True,
            )

    def test_logs_warning_on_preferred_browser_not_found(self) -> None:
        """Test that warning logging occurs when preferred browser is not found."""
        with (
            patch("pkm_tool.auth.browser.webbrowser.get") as mock_get,
            patch("pkm_tool.auth.browser.webbrowser.open") as mock_open,
            patch("pkm_tool.auth.browser.logger") as mock_logger,
        ):
            mock_get.side_effect = webbrowser.Error("Browser not found")
            mock_open.return_value = True

            open_browser("https://example.com", preferred_browser="nonexistent")

            mock_logger.warning.assert_called_once_with(
                "preferred_browser_not_found",
                browser="nonexistent",
                fallback="default",
            )

    def test_logs_warning_on_exception(self) -> None:
        """Test that warning logging occurs on unexpected exception."""
        with (
            patch("pkm_tool.auth.browser.webbrowser.open") as mock_open,
            patch("pkm_tool.auth.browser.logger") as mock_logger,
        ):
            mock_open.side_effect = RuntimeError("Unexpected error")

            open_browser("https://example.com")

            mock_logger.warning.assert_called_once_with(
                "browser_open_failed",
                url="https://example.com",
                error="Unexpected error",
            )
