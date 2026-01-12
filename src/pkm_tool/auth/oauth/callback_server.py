"""Local HTTP server for receiving OAuth authorization code callbacks.

This module provides a lightweight HTTP server that listens for OAuth callback
requests during the Authorization Code Flow. The server is single-use and
automatically stops after receiving one callback.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import structlog

if TYPE_CHECKING:
    from socket import socket

logger = structlog.get_logger(__name__)

DEFAULT_PORT = 8642
DEFAULT_TIMEOUT = 300.0  # 5 minutes

# HTML templates for callback responses
SUCCESS_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Authorization Successful</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background-color: #f5f5f5;
        }
        .container {
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 { color: #22c55e; margin-bottom: 16px; }
        p { color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Authorization Successful</h1>
        <p>You can close this window and return to the terminal.</p>
    </div>
</body>
</html>"""

ERROR_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Authorization Failed</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            background-color: #f5f5f5;
        }}
        .container {{
            text-align: center;
            padding: 40px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #ef4444; margin-bottom: 16px; }}
        p {{ color: #666; }}
        .error {{ color: #999; font-size: 14px; margin-top: 16px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Authorization Failed</h1>
        <p>The authorization request was denied or failed.</p>
        <p class="error">Error: {error}</p>
    </div>
</body>
</html>"""


@dataclass(slots=True)
class CallbackResult:
    """Result from an OAuth callback request.

    Attributes:
        code: The authorization code received from the OAuth provider.
        error: Error code if the authorization failed.
        state: The state parameter echoed back from the OAuth provider.
    """

    code: str | None = None
    error: str | None = None
    state: str | None = None


@dataclass
class OAuthCallbackServer:
    """Local HTTP server for receiving OAuth authorization code callbacks.

    This server is designed for the OAuth Authorization Code Flow. It listens
    on a local port for the callback request from the OAuth provider after
    the user authorizes the application.

    The server is single-use: it automatically stops after receiving one
    callback request, whether successful or not.

    Attributes:
        port: The local port to listen on.

    Example:
        >>> server = OAuthCallbackServer(port=8642)
        >>> callback_url = server.start()
        >>> # Open browser to auth URL with redirect_uri=callback_url
        >>> result = server.wait_for_callback(timeout=300)
        >>> server.stop()
        >>> if result.code:
        ...     # Exchange code for token
        ...     pass
    """

    port: int = DEFAULT_PORT

    _server: HTTPServer | None = field(default=None, init=False, repr=False)
    _server_thread: threading.Thread | None = field(default=None, init=False, repr=False)
    _result: CallbackResult | None = field(default=None, init=False, repr=False)
    _result_event: threading.Event = field(default_factory=threading.Event, init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def start(self) -> str:
        """Start the callback server and return the callback URL.

        Returns:
            The full callback URL to use as the OAuth redirect_uri.

        Raises:
            RuntimeError: If the server is already running.
            OSError: If the port is already in use.
        """
        with self._lock:
            if self._server is not None:
                msg = "Server is already running"
                raise RuntimeError(msg)

            # Reset state for reuse
            self._result = None
            self._result_event.clear()

            # Create the request handler with access to this server instance
            server_instance = self

            class CallbackHandler(BaseHTTPRequestHandler):
                """HTTP request handler for OAuth callbacks."""

                def log_message(self, format: str, *args: object) -> None:
                    """Suppress default HTTP logging, use structlog instead."""

                def do_GET(self) -> None:
                    """Handle GET requests to the callback endpoint."""
                    parsed = urlparse(self.path)

                    # Only handle the callback path
                    if parsed.path != "/callback":
                        self.send_error(404, "Not Found")
                        return

                    # Parse query parameters
                    params = parse_qs(parsed.query)

                    # Extract callback parameters (parse_qs returns lists)
                    code = params.get("code", [None])[0]
                    error = params.get("error", [None])[0]
                    state = params.get("state", [None])[0]

                    result = CallbackResult(code=code, error=error, state=state)

                    if error:
                        logger.warning(
                            "oauth_callback_error",
                            error=error,
                            state=state,
                        )
                        self._send_html_response(ERROR_HTML_TEMPLATE.format(error=error))
                    else:
                        logger.info(
                            "oauth_callback_success",
                            has_code=code is not None,
                            state=state,
                        )
                        self._send_html_response(SUCCESS_HTML)

                    # Store result and signal completion
                    server_instance._set_result(result)

                def _send_html_response(self, html: str) -> None:
                    """Send an HTML response to the client."""
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(html)))
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))

            # Create and start the server
            try:
                self._server = HTTPServer(("127.0.0.1", self.port), CallbackHandler)
            except OSError as e:
                logger.error("oauth_callback_server_start_failed", port=self.port, error=str(e))
                raise

            self._server_thread = threading.Thread(
                target=self._serve_forever,
                daemon=True,
                name="oauth-callback-server",
            )
            self._server_thread.start()

            callback_url = f"http://localhost:{self.port}/callback"
            logger.info("oauth_callback_server_started", port=self.port, callback_url=callback_url)

            return callback_url

    def wait_for_callback(self, timeout: float = DEFAULT_TIMEOUT) -> CallbackResult:
        """Wait for the OAuth callback to be received.

        This method blocks until either:
        - A callback is received (success or error)
        - The timeout expires

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            The callback result containing the authorization code or error.
            If timeout occurs, returns a CallbackResult with error="timeout".
        """
        logger.debug("oauth_callback_waiting", timeout=timeout)

        received = self._result_event.wait(timeout=timeout)

        if not received:
            logger.warning("oauth_callback_timeout", timeout=timeout)
            return CallbackResult(error="timeout")

        with self._lock:
            return self._result or CallbackResult(error="unknown")

    def stop(self) -> None:
        """Stop the callback server.

        This method is safe to call multiple times or even if the server
        was never started.
        """
        with self._lock:
            if self._server is not None:
                logger.debug("oauth_callback_server_stopping", port=self.port)
                self._server.shutdown()
                self._server.server_close()
                self._server = None

            if self._server_thread is not None:
                self._server_thread.join(timeout=5.0)
                self._server_thread = None

            logger.info("oauth_callback_server_stopped")

    def _set_result(self, result: CallbackResult) -> None:
        """Store the callback result and signal completion.

        Called by the request handler when a callback is received.
        """
        with self._lock:
            self._result = result
        self._result_event.set()

    def _serve_forever(self) -> None:
        """Run the server until shutdown is called.

        This method runs in a separate thread.
        """
        if self._server is not None:
            self._server.serve_forever()

    @property
    def is_running(self) -> bool:
        """Check if the server is currently running."""
        with self._lock:
            return self._server is not None

    @property
    def server_socket(self) -> socket | None:
        """Get the server socket for advanced use cases.

        This can be useful for getting the actual bound port if port 0
        was specified to let the OS choose a free port.
        """
        with self._lock:
            if self._server is not None:
                return self._server.socket
            return None

    def __enter__(self) -> OAuthCallbackServer:
        """Context manager entry: start the server."""
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        """Context manager exit: stop the server."""
        self.stop()
