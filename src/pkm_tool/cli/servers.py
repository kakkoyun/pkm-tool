"""Server and MCP CLI subcommands."""

import click

from pkm_tool.logging import bind_correlation_id, configure_logging, get_logger


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Path to configuration file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose (DEBUG) logging",
)
@click.option(
    "--log-format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    help="Log output format (default: human)",
)
def mcp(
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """
    Run PKM Tool as an MCP (Model Context Protocol) server.

    The MCP server exposes PKM Tool's data fetching capabilities as tools
    that can be used by AI assistants supporting the MCP protocol.

    Communication is via stdio (standard input/output), making it compatible
    with MCP clients like Claude Desktop.

    Available tools:
    - fetch_aggregated_data: Get data from all configured sources
    - fetch_calendar_events: Get Apple Calendar events
    - fetch_github_activities: Get GitHub activities
    - fetch_atlassian_items: Get Atlassian (Jira/Confluence) items
    - fetch_things_tasks: Get Things tasks
    - fetch_wakatime_activities: Get Wakatime coding activities
    - fetch_google_docs: Get Google Docs
    - fetch_whoop_data: Get Whoop health data

    Example configuration for Claude Desktop:
    (~/Library/Application Support/Claude/claude_desktop_config.json)

    \b
    {
      "mcpServers": {
        "pkm-tool": {
          "command": "pkm",
          "args": ["mcp"],
          "env": {}
        }
      }
    }
    """
    # Configure logging
    configure_logging(verbose=verbose, log_format=log_format)
    bind_correlation_id()
    logger = get_logger(__name__)

    logger.info("starting_mcp_server", config_path=config)

    try:
        import asyncio

        from pkm_tool.mcp_server import run_mcp_server

        # Run the MCP server with config path
        asyncio.run(run_mcp_server(config))
    except ImportError:
        logger.error("mcp_dependencies_missing")
        click.echo(
            "Error: MCP dependencies not installed. Install with: uv sync --extra mcp",
            err=True,
        )
        raise click.Abort()
    except Exception as e:
        logger.error("mcp_server_failed", error=str(e), exc_info=True)
        click.echo(f"Error running MCP server: {e}", err=True)
        raise click.Abort()


@click.command()
@click.option(
    "--host",
    default="127.0.0.1",
    help="Host to bind the server to (default: 127.0.0.1)",
)
@click.option(
    "--port",
    default=8000,
    type=int,
    help="Port to bind the server to (default: 8000)",
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload on code changes (development mode)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default=None,
    help="Path to configuration file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Enable verbose (DEBUG) logging",
)
@click.option(
    "--log-format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    help="Log output format (default: human)",
)
def server(
    host: str,
    port: int,
    reload: bool,
    config: str | None,
    verbose: bool,
    log_format: str,
) -> None:
    """
    Start the PKM Tool web server.

    Runs a FastAPI server that provides:
    - REST API endpoints for fetching data
    - Interactive API documentation at /docs

    Examples:

    \b
    # Start server on default port (8000)
    pkm server

    \b
    # Start on custom port with auto-reload
    pkm server --port 8080 --reload

    \b
    # Start with verbose logging
    pkm server --verbose

    The server will be accessible at http://{host}:{port}
    API documentation will be available at http://{host}:{port}/docs
    """
    # Configure logging
    configure_logging(verbose=verbose, log_format=log_format)
    bind_correlation_id()
    logger = get_logger(__name__)

    logger.info("starting_server", host=host, port=port, reload=reload)

    try:
        import uvicorn

        from pkm_tool.server.api import app

        # Display helpful information
        click.echo(f"🚀 Starting PKM Tool server on http://{host}:{port}")
        click.echo(f"📚 API documentation: http://{host}:{port}/docs")
        click.echo(f"📖 ReDoc documentation: http://{host}:{port}/redoc")
        click.echo()
        click.echo("Press CTRL+C to stop the server")
        click.echo()

        # Run the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="debug" if verbose else "info",
        )
    except ImportError:
        logger.error("server_dependencies_missing")
        click.echo(
            "Error: Server dependencies not installed. Install with: uv sync --extra server",
            err=True,
        )
        raise click.Abort()
    except Exception as e:
        logger.error("server_start_failed", error=str(e), exc_info=True)
        click.echo(f"Error starting server: {e}", err=True)
        raise click.Abort()
