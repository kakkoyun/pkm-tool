"""Browser utilities for authentication flows.

Centralizes browser opening logic to support user-configured preferred browsers
for OAuth flows and other authentication-related browser interactions.
"""

import webbrowser

import structlog

logger = structlog.get_logger(__name__)


def open_browser(url: str, preferred_browser: str | None = None) -> bool:
    """Open URL in browser, using preferred browser if configured.

    This function provides a centralized way to open URLs in the browser,
    respecting user preferences while gracefully falling back to the system
    default browser when the preferred browser is unavailable.

    Args:
        url: URL to open
        preferred_browser: Browser name or None for system default.
            Supported values match Python's webbrowser module:
            "firefox", "chrome", "chromium", "safari", "opera", "edge",
            or any browser registered with the webbrowser module.
            "default" is treated the same as None.

    Returns:
        True if browser opened successfully, False otherwise.
    """
    try:
        # Use system default if no preference or explicitly set to "default"
        if preferred_browser and preferred_browser.lower() != "default":
            try:
                browser = webbrowser.get(preferred_browser)
                result = browser.open(url)
                logger.debug(
                    "browser_open_preferred",
                    browser=preferred_browser,
                    url=url,
                    success=result,
                )
                return result
            except webbrowser.Error:
                # Preferred browser not available, fall back to default
                logger.warning(
                    "preferred_browser_not_found",
                    browser=preferred_browser,
                    fallback="default",
                )

        # Use system default browser
        result = webbrowser.open(url)
        logger.debug("browser_open_default", url=url, success=result)
        return result

    except Exception as e:
        # Catch any unexpected errors during browser opening
        logger.warning("browser_open_failed", url=url, error=str(e))
        return False
