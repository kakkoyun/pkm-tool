"""FastAPI application for PKM tool REST API."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from dateutil import parser as date_parser
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from pkm_tool.aggregator import aggregate_data
from pkm_tool.config import Config, load_config
from pkm_tool.formatters import format_as_json, format_as_markdown
from pkm_tool.logging import configure_logging, get_logger
from pkm_tool.models import AggregatedData
from pkm_tool.sources.apple_calendar import fetch_calendar_events
from pkm_tool.sources.atlassian import fetch_atlassian_items
from pkm_tool.sources.github import fetch_github_activities
from pkm_tool.sources.google_docs import fetch_google_docs
from pkm_tool.sources.things import fetch_things_tasks
from pkm_tool.sources.wakatime import fetch_wakatime_activities
from pkm_tool.sources.whoop import (
    fetch_whoop_recovery,
    fetch_whoop_sleep,
    fetch_whoop_workouts,
)

# Configure logging for the server
configure_logging(verbose=False, log_format="human")
logger = get_logger(__name__)


class OutputFormat(str, Enum):
    """Output format options."""

    MARKDOWN = "markdown"
    JSON = "json"


# Create FastAPI app
app = FastAPI(
    title="PKM Tool API",
    description="REST API for Personal Knowledge Management Tool",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware - allow all origins for development
# TODO: Make this configurable via environment variable or config file for production
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]  # FastAPI/Starlette typing issue
    allow_origins=["*"],  # Development mode - configure for production use
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global config - loaded once at startup
_config: Config | None = None


def get_config() -> Config:
    """Get or load configuration."""
    global _config
    if _config is None:
        _config = load_config(None)
    return _config


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(default="ok", description="Service status")
    timestamp: str = Field(description="Current server timestamp")


class SourceInfo(BaseModel):
    """Information about a data source."""

    name: str = Field(description="Source name")
    display_name: str = Field(description="Display name")
    enabled: bool = Field(description="Whether source is enabled")
    description: str = Field(description="Source description")


class DataResponse(BaseModel):
    """Response with fetched data."""

    date: str = Field(description="Date of the data")
    format: str = Field(description="Output format")
    data: str = Field(description="Formatted data output")
    raw_data: dict[str, Any] | None = Field(
        default=None, description="Raw JSON data (if format=json)"
    )


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        Health status and timestamp
    """
    return HealthResponse(timestamp=datetime.now().isoformat())


@app.get("/api/sources", response_model=list[SourceInfo], tags=["Configuration"])
async def list_sources() -> list[SourceInfo]:
    """
    List all available data sources.

    Returns:
        List of source information
    """
    config = get_config()

    sources = [
        SourceInfo(
            name="calendar",
            display_name="Apple Calendar",
            enabled=config.apple_calendar.enabled,
            description="Agenda and events from Apple Calendar (macOS only)",
        ),
        SourceInfo(
            name="github",
            display_name="GitHub",
            enabled=config.github.enabled,
            description="Activities including commits, PRs, issues, and reviews",
        ),
        SourceInfo(
            name="atlassian",
            display_name="Atlassian",
            enabled=config.atlassian.enabled,
            description="Jira issues and Confluence pages",
        ),
        SourceInfo(
            name="things",
            display_name="Things",
            enabled=config.things.enabled,
            description="Completed tasks from Things logbook (macOS only)",
        ),
        SourceInfo(
            name="wakatime",
            display_name="Wakatime",
            enabled=config.wakatime.enabled,
            description="Coding activity per project",
        ),
        SourceInfo(
            name="google-docs",
            display_name="Google Docs",
            enabled=config.google_docs.enabled,
            description="Recently opened documents",
        ),
        SourceInfo(
            name="whoop",
            display_name="Whoop",
            enabled=config.whoop.enabled,
            description="Recovery, sleep, and workout data",
        ),
    ]

    return sources


@app.get("/api/config", tags=["Configuration"])
async def get_config_info() -> dict[str, Any]:
    """
    Get configuration information.

    Returns:
        Configuration details (excluding sensitive data)
    """
    config = get_config()

    return {
        "output_filename_template": config.output_filename_template,
        "output_directory": config.output_directory,
        "cache": {
            "enabled": config.cache.enabled,
            "directory": config.cache.directory,
            "ttl_hours": config.cache.ttl_hours,
        },
        "sources": {
            "calendar": {
                "enabled": config.apple_calendar.enabled,
                "exclude_weekends": config.apple_calendar.exclude_weekends,
            },
            "github": {
                "enabled": config.github.enabled,
                "exclude_weekends": config.github.exclude_weekends,
            },
            "atlassian": {
                "enabled": config.atlassian.enabled,
                "exclude_weekends": config.atlassian.exclude_weekends,
            },
            "things": {
                "enabled": config.things.enabled,
                "exclude_weekends": config.things.exclude_weekends,
            },
            "wakatime": {
                "enabled": config.wakatime.enabled,
                "exclude_weekends": config.wakatime.exclude_weekends,
            },
            "google_docs": {
                "enabled": config.google_docs.enabled,
                "exclude_weekends": config.google_docs.exclude_weekends,
            },
            "whoop": {
                "enabled": config.whoop.enabled,
                "exclude_weekends": config.whoop.exclude_weekends,
            },
        },
    }


def _parse_target_date(date_str: str | None) -> date:
    """Parse date string or return today's date."""
    if date_str is None:
        return datetime.now().date()

    try:
        parsed_date = date_parser.parse(date_str)
        return parsed_date.date()
    except (ValueError, TypeError) as e:
        logger.error("date_parsing_failed", error=str(e), input=date_str)
        raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}") from e


def _fetch_single_source(
    source: str, target_date: date, config: Config, data: AggregatedData
) -> None:
    """Fetch data from a single source and update the data object."""
    # Map source names to fetch functions and config attributes
    source_handlers: dict[str, tuple[Any, Any, Any]] = {
        "calendar": (
            config.apple_calendar.enabled,
            fetch_calendar_events,
            lambda d, result: setattr(d, "calendar_events", result),
        ),
        "github": (
            config.github.enabled,
            fetch_github_activities,
            lambda d, result: setattr(d, "github_activities", result),
        ),
        "atlassian": (
            config.atlassian.enabled,
            fetch_atlassian_items,
            lambda d, result: setattr(d, "atlassian_items", result),
        ),
        "things": (
            config.things.enabled,
            fetch_things_tasks,
            lambda d, result: setattr(d, "things_tasks", result),
        ),
        "wakatime": (
            config.wakatime.enabled,
            fetch_wakatime_activities,
            lambda d, result: setattr(d, "wakatime_activities", result),
        ),
        "google-docs": (
            config.google_docs.enabled,
            fetch_google_docs,
            lambda d, result: setattr(d, "google_docs", result),
        ),
    }

    # Handle regular sources
    if source in source_handlers:
        enabled, fetch_func, setter = source_handlers[source]
        if enabled:
            # Get config for the source
            config_attr = source.replace("-", "_")
            source_config = getattr(config, config_attr).config
            result = fetch_func(target_date, source_config)
            setter(data, result)
        return

    # Handle whoop separately (multiple endpoints)
    if source == "whoop" and config.whoop.enabled:
        data.whoop_recovery = fetch_whoop_recovery(target_date, config.whoop.config)
        data.whoop_sleep = fetch_whoop_sleep(target_date, config.whoop.config)
        data.whoop_workouts = fetch_whoop_workouts(target_date, config.whoop.config)


@app.get("/api/data", response_model=DataResponse, tags=["Data"])
async def get_data(
    date_str: str | None = Query(
        None, alias="date", description="Date to fetch (YYYY-MM-DD or natural language)"
    ),
    output_format: OutputFormat = Query(
        OutputFormat.MARKDOWN, alias="format", description="Output format"
    ),
    sources: str | None = Query(None, description="Comma-separated list of sources"),
) -> DataResponse:
    """
    Fetch aggregated data for a specific date.

    Args:
        date_str: Date to fetch data for (default: today)
        output_format: Output format (markdown or json)
        sources: Comma-separated list of sources to fetch

    Returns:
        Formatted data for the requested date
    """
    logger.info("api_data_request", date=date_str, format=output_format, sources=sources)

    # Parse date
    target_date = _parse_target_date(date_str)

    # Load config
    config = get_config()

    # Fetch data
    try:
        if sources:
            # Fetch specific sources
            selected_sources = [s.strip() for s in sources.split(",")]
            data = AggregatedData(date=target_date)
            for source in selected_sources:
                _fetch_single_source(source, target_date, config, data)
        else:
            # Aggregate all sources
            data = aggregate_data(target_date, config_path=None)

        # Format output
        if output_format == OutputFormat.JSON:
            formatted_data = format_as_json(data)
            return DataResponse(
                date=str(target_date),
                format="json",
                data=formatted_data,
                raw_data=data.model_dump(),
            )

        formatted_data = format_as_markdown(data, config)
        return DataResponse(date=str(target_date), format="markdown", data=formatted_data)

    except Exception as e:
        logger.error("data_fetch_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching data: {e!s}") from e


@app.exception_handler(Exception)
async def global_exception_handler(request: Any, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error("unhandled_exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )
