"""Domain exception hierarchy for PKM tool.

Provides structured error types for source failures, authentication errors,
rate limiting, network issues, and configuration problems. Used by sources
and the aggregator to classify and handle errors consistently.
"""


class PKMError(Exception):
    """Base exception for all PKM tool errors."""


class SourceError(PKMError):
    """Error from a data source.

    Attributes:
        source: Name of the source that failed (e.g., "github", "wakatime")
        retriable: Whether the operation can be retried
    """

    def __init__(self, source: str, message: str, *, retriable: bool = False) -> None:
        self.source = source
        self.retriable = retriable
        super().__init__(f"[{source}] {message}")


class AuthenticationError(SourceError):
    """Authentication failure (401, missing/invalid token). Non-retriable."""

    def __init__(self, source: str, message: str = "Authentication failed") -> None:
        super().__init__(source, message, retriable=False)


class RateLimitError(SourceError):
    """Rate limit exceeded (429). Retriable after delay.

    Attributes:
        retry_after: Seconds to wait before retrying (from Retry-After header)
    """

    def __init__(self, source: str, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        msg = "Rate limit exceeded"
        if retry_after is not None:
            msg = f"Rate limit exceeded (retry after {retry_after}s)"
        super().__init__(source, msg, retriable=True)


class NetworkError(SourceError):
    """Network connectivity or timeout error. Retriable."""

    def __init__(self, source: str, message: str = "Network error") -> None:
        super().__init__(source, message, retriable=True)


class ConfigurationError(PKMError):
    """Invalid or missing configuration."""
