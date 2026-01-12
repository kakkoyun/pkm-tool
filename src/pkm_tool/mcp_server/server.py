"""MCP server implementation for PKM Tool.

This module implements an MCP (Model Context Protocol) server that exposes
PKM Tool's data fetching capabilities as tools that can be used by AI assistants.
"""

from collections.abc import Callable
from datetime import date, datetime
from typing import Any, cast

from dateutil import parser as date_parser
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from pkm_tool.aggregator import aggregate_data
from pkm_tool.config import CacheConfig, load_config
from pkm_tool.formatters import format_as_json, format_as_markdown
from pkm_tool.logging import get_logger
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

logger = get_logger(__name__)


def _parse_relative_date(date_input: str) -> date | None:
    """
    Parse relative date strings like 'yesterday', 'today', 'tomorrow'.

    Args:
        date_input: Relative date string (case-insensitive)

    Returns:
        Parsed date object or None if not a recognized relative date
    """
    from datetime import timedelta

    today = datetime.now().date()
    normalized = date_input.lower().strip()

    relative_dates = {
        "today": timedelta(days=0),
        "yesterday": timedelta(days=-1),
        "tomorrow": timedelta(days=1),
    }

    if normalized in relative_dates:
        return today + relative_dates[normalized]

    return None


def _parse_date_string(date_str: str | None) -> date:
    """
    Parse date string to date object.

    Supports:
    - None: returns today's date
    - Relative dates: 'yesterday', 'today', 'tomorrow' (case-insensitive)
    - Absolute dates: YYYY-MM-DD, natural language via dateutil
    """
    if date_str is None:
        return datetime.now().date()

    # Try relative date parsing first
    relative_result = _parse_relative_date(date_str)
    if relative_result is not None:
        return relative_result

    # Fall back to dateutil for absolute dates
    try:
        parsed = date_parser.parse(date_str)
        return parsed.date()
    except (ValueError, TypeError) as e:
        logger.error("date_parsing_failed", error=str(e), input=date_str)
        raise ValueError(f"Invalid date format: {date_str}") from e


def _fetch_aggregated_data(target_date: date, config_path: str | None = None) -> AggregatedData:
    """Fetch aggregated data from all sources."""
    logger.info("fetching_aggregated_data", date=str(target_date))
    data = aggregate_data(target_date, config_path)
    logger.info("aggregated_data_fetched", date=str(target_date))
    return data


def _fetch_source_data(
    source: str, target_date: date, config_path: str | None = None
) -> AggregatedData:
    """Fetch data from a specific source."""
    logger.info("fetching_source_data", source=source, date=str(target_date))
    config = load_config(config_path)
    data = AggregatedData(date=target_date)

    # Get cache config for HTTP-based sources
    cache_config: CacheConfig | None = config.cache if config.cache.enabled else None

    # Map source names to fetch functions with their config and cache requirements
    # Tuple structure: (fetch_func: Callable, source_config: dict, uses_cache: bool)
    source_handlers: dict[
        str,
        tuple[
            Callable[[date, dict[str, Any]], Any]
            | Callable[[date, dict[str, Any], CacheConfig | None], Any],
            dict[str, Any],
            bool,
        ],
    ] = {
        "calendar": (fetch_calendar_events, config.apple_calendar.config, False),
        "github": (fetch_github_activities, config.github.config, False),
        "atlassian": (fetch_atlassian_items, config.atlassian.config, False),
        "things": (fetch_things_tasks, config.things.config, False),
        "wakatime": (fetch_wakatime_activities, config.wakatime.config, True),
        "google-docs": (fetch_google_docs, config.google_docs.config, True),
    }

    # Handle regular sources
    if source in source_handlers:
        fetch_func, source_config, uses_cache = source_handlers[source]
        if uses_cache:
            result = cast(Callable[[date, dict[str, Any], CacheConfig | None], Any], fetch_func)(
                target_date, source_config, cache_config
            )
        else:
            result = cast(Callable[[date, dict[str, Any]], Any], fetch_func)(
                target_date, source_config
            )

        # Set result on appropriate data field
        field_mapping = {
            "calendar": "calendar_events",
            "github": "github_activities",
            "atlassian": "atlassian_items",
            "things": "things_tasks",
            "wakatime": "wakatime_activities",
            "google-docs": "google_docs",
        }
        setattr(data, field_mapping[source], result)
    elif source == "whoop":
        # Whoop has multiple endpoints
        data.whoop_recovery = fetch_whoop_recovery(target_date, config.whoop.config, cache_config)
        data.whoop_sleep = fetch_whoop_sleep(target_date, config.whoop.config, cache_config)
        data.whoop_workouts = fetch_whoop_workouts(target_date, config.whoop.config, cache_config)
    else:
        raise ValueError(f"Unknown source: {source}")

    logger.info("source_data_fetched", source=source, date=str(target_date))
    return data


def create_mcp_server() -> Server:
    """Create and configure the MCP server with PKM Tool capabilities."""
    server = Server("pkm-tool")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="fetch_aggregated_data",
                description=(
                    "Fetch aggregated data from all configured PKM sources for a specific date. "
                    "Returns data from Apple Calendar, GitHub, Atlassian (Jira/Confluence), "
                    "Things, Wakatime, Google Docs, and Whoop."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": (
                                "Date to fetch data for in YYYY-MM-DD format or natural language "
                                "(e.g., 'today', 'yesterday', '2025-12-01'). Defaults to today."
                            ),
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format for the data. Defaults to 'markdown'.",
                            "default": "markdown",
                        },
                    },
                },
            ),
            Tool(
                name="fetch_calendar_events",
                description=(
                    "Fetch Apple Calendar events for a specific date. "
                    "Returns calendar agenda and events (macOS only)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": (
                                "Date to fetch events for in YYYY-MM-DD format or natural "
                                "language. Defaults to today."
                            ),
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format. Defaults to 'markdown'.",
                            "default": "markdown",
                        },
                    },
                },
            ),
            Tool(
                name="fetch_github_activities",
                description=(
                    "Fetch GitHub activities for a specific date. "
                    "Includes commits, pull requests, issues, and reviews."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date to fetch activities for. Defaults to today.",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format. Defaults to 'markdown'.",
                            "default": "markdown",
                        },
                    },
                },
            ),
            Tool(
                name="fetch_atlassian_items",
                description=(
                    "Fetch Atlassian (Jira/Confluence) items for a specific date. "
                    "Returns Jira issues and Confluence pages updated on the date."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date to fetch items for. Defaults to today.",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format. Defaults to 'markdown'.",
                            "default": "markdown",
                        },
                    },
                },
            ),
            Tool(
                name="fetch_things_tasks",
                description=(
                    "Fetch completed Things tasks for a specific date. "
                    "Returns tasks from Things logbook (macOS only)."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date to fetch tasks for. Defaults to today.",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format. Defaults to 'markdown'.",
                            "default": "markdown",
                        },
                    },
                },
            ),
            Tool(
                name="fetch_wakatime_activities",
                description=(
                    "Fetch Wakatime coding activities for a specific date. "
                    "Returns coding time per project and languages used."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date to fetch activities for. Defaults to today.",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format. Defaults to 'markdown'.",
                            "default": "markdown",
                        },
                    },
                },
            ),
            Tool(
                name="fetch_google_docs",
                description=(
                    "Fetch recently opened Google Docs for a specific date. "
                    "Returns documents accessed on the specified date."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date to fetch documents for. Defaults to today.",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format. Defaults to 'markdown'.",
                            "default": "markdown",
                        },
                    },
                },
            ),
            Tool(
                name="fetch_whoop_data",
                description=(
                    "Fetch Whoop health data for a specific date. "
                    "Includes recovery metrics, sleep cycles, and workout activities."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date to fetch data for. Defaults to today.",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json"],
                            "description": "Output format. Defaults to 'markdown'.",
                            "default": "markdown",
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        logger.info("tool_called", tool_name=name, arguments=arguments)

        try:
            date_str = arguments.get("date")
            output_format = arguments.get("format", "markdown")
            target_date = _parse_date_string(date_str)

            if name == "fetch_aggregated_data":
                data = _fetch_aggregated_data(target_date)
            else:
                # Map tool names to source names
                source_map = {
                    "fetch_calendar_events": "calendar",
                    "fetch_github_activities": "github",
                    "fetch_atlassian_items": "atlassian",
                    "fetch_things_tasks": "things",
                    "fetch_wakatime_activities": "wakatime",
                    "fetch_google_docs": "google-docs",
                    "fetch_whoop_data": "whoop",
                }
                source = source_map.get(name)
                if source is None:
                    raise ValueError(f"Unknown tool: {name}")
                data = _fetch_source_data(source, target_date)

            # Format output
            if output_format.lower() == "json":
                formatted_output = format_as_json(data)
            else:
                config = load_config(None)
                formatted_output = format_as_markdown(data, config)

            logger.info("tool_executed_successfully", tool_name=name, date=str(target_date))

            return [TextContent(type="text", text=formatted_output)]

        except Exception as e:
            logger.error("tool_execution_failed", tool_name=name, error=str(e), exc_info=True)
            error_msg = f"Error executing {name}: {e!s}"
            return [TextContent(type="text", text=error_msg)]

    return server


async def run_mcp_server(config_path: str | None = None) -> None:
    """Run the MCP server using stdio transport.

    Args:
        config_path: Optional path to configuration file
    """
    logger.info("starting_mcp_server", config_path=config_path)
    server = create_mcp_server()

    async with stdio_server() as (read_stream, write_stream):
        logger.info("mcp_server_running")
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
