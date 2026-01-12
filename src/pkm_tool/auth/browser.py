"""Browser utilities for authentication flows.

Centralizes browser opening logic to support user-configured preferred browsers
for OAuth flows and other authentication-related browser interactions.
"""

import platform
import subprocess
import webbrowser

import structlog

logger = structlog.get_logger(__name__)

# macOS-specific browser names that need special handling
MACOS_BROWSER_APPS = {
    "brave": "Brave Browser",
    "arc": "Arc",
    "edge": "Microsoft Edge",
    "vivaldi": "Vivaldi",
}


def open_browser(url: str, preferred_browser: str | None = None) -> bool:
    """Open URL in browser, using preferred browser if configured.

    This function provides a centralized way to open URLs in the browser,
    respecting user preferences while gracefully falling back to the system
    default browser when the preferred browser is unavailable.

    Args:
        url: URL to open
        preferred_browser: Browser name or None for system default.
            Supported values:
            - Standard: "firefox", "chrome", "chromium", "safari", "opera"
            - macOS special: "brave", "arc", "edge", "vivaldi"
            - "default" or None: System default browser

    Returns:
        True if browser opened successfully, False otherwise.
    """
    try:
        # Use system default if no preference or explicitly set to "default"
        if preferred_browser and preferred_browser.lower() != "default":
            browser_name = preferred_browser.lower()

            # On macOS, try using 'open -a' for browsers that need special handling
            if platform.system() == "Darwin" and browser_name in MACOS_BROWSER_APPS:
                app_name = MACOS_BROWSER_APPS[browser_name]
                try:
                    subprocess.run(
                        ["open", "-a", app_name, url],
                        check=True,
                        capture_output=True,
                        timeout=5,
                    )
                    logger.debug(
                        "browser_open_macos",
                        browser=browser_name,
                        app=app_name,
                        url=url,
                        success=True,
                    )
                    return True
                except (
                    subprocess.CalledProcessError,
                    subprocess.TimeoutExpired,
                    FileNotFoundError,
                ) as e:
                    logger.warning(
                        "macos_browser_open_failed",
                        browser=browser_name,
                        app=app_name,
                        error=str(e),
                        fallback="webbrowser",
                    )
                    # Fall through to try webbrowser module

            # Try standard webbrowser module
            try:
                browser = webbrowser.get(browser_name)
                result = browser.open(url)
                logger.debug(
                    "browser_open_preferred",
                    browser=browser_name,
                    url=url,
                    success=result,
                )
                return result
            except webbrowser.Error:
                # Preferred browser not available, fall back to default
                logger.warning(
                    "preferred_browser_not_found",
                    browser=browser_name,
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
