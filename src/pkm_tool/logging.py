"""Structured logging configuration for PKM tool."""

import logging
import sys
import uuid
from typing import Any

import structlog


def configure_logging(
    verbose: bool = False,
    log_format: str = "human",
) -> None:
    """
    Configure structured logging for the application.

    Args:
        verbose: Enable verbose (DEBUG) logging. Default is INFO level.
        log_format: Output format - "human" for colored console or "json" for structured JSON.
    """
    # Set log level
    log_level = logging.DEBUG if verbose else logging.INFO

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )

    # Common processors for both formats
    common_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if log_format == "json":
        # JSON format for production/structured logging
        # format_exc_info converts exceptions to strings for JSON serialization
        processors = [
            *common_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Human-readable format for development
        # ConsoleRenderer handles exception formatting automatically
        processors = [
            *common_processors,
            structlog.dev.ConsoleRenderer(
                colors=True, exception_formatter=structlog.dev.plain_traceback
            ),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """
    Get a structlog logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Structlog logger instance
    """
    return structlog.get_logger(name)


def bind_correlation_id(correlation_id: str | None = None) -> str:
    """
    Bind a correlation ID to the current structlog context.

    If no correlation_id is provided, generates a new UUID4.
    All subsequent log entries in the current context will include this ID.

    Args:
        correlation_id: Optional explicit correlation ID. Generates UUID4 if None.

    Returns:
        The correlation ID that was bound.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
    return correlation_id
