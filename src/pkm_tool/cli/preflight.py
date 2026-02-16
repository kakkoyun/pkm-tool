"""Preflight check logic and display helpers."""

from typing import Any

import click

from pkm_tool.auth.preflight import AuthState, PreflightChecker, SourceAuthStatus
from pkm_tool.config import Config, load_config

from .auth import _resolve_missing_auth
from .common import _get_auth_manager


def _display_auth_status(statuses: list[SourceAuthStatus]) -> None:
    """Display authentication status for all sources."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    console.print("\n[bold]Pre-flight Authentication Check[/bold]")
    console.print("-" * 40)

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Status", style="bold", width=3)
    table.add_column("Source", width=15)
    table.add_column("Message")

    state_symbols = {
        AuthState.VALID: ("[green]OK[/green]", "green"),
        AuthState.EXPIRED: ("[yellow]![/yellow]", "yellow"),
        AuthState.MISSING: ("[red]X[/red]", "red"),
        AuthState.NOT_REQUIRED: ("[dim]-[/dim]", "dim"),
        AuthState.INVALID_CONFIG: ("[red]X[/red]", "red"),
        AuthState.DISABLED: ("[dim]-[/dim]", "dim"),
    }

    for status in statuses:
        symbol, style = state_symbols.get(status.state, ("?", ""))
        table.add_row(
            symbol,
            f"[{style}]{status.display_name}[/{style}]",
            f"[{style}]{status.message}[/{style}]",
        )

    console.print(table)


def _display_failed_sources(statuses: list[SourceAuthStatus]) -> None:
    """Display sources that failed authentication."""
    from rich.console import Console

    console = Console()
    console.print("\n[yellow]Some sources still need configuration:[/yellow]")
    for status in statuses:
        console.print(f"  - [bold]{status.display_name}[/bold]: {status.message}")


def _run_preflight_check(
    cfg: Config,
    config_path: str | None,
    non_interactive: bool,
    auto_oauth: bool,
    logger: Any,
) -> None:
    """Run pre-flight authentication check and handle resolution.

    Args:
        cfg: Loaded configuration
        config_path: Path to config file (for OAuth flows)
        non_interactive: If True, fail instead of prompting
        auto_oauth: If True, automatically launch browser OAuth without confirmation
        logger: Logger instance

    Raises:
        SystemExit: If non-interactive and auth is missing, or user declines to proceed
    """
    from rich.console import Console

    console = Console()

    checker = PreflightChecker(preferred_browser=cfg.preferred_browser)
    statuses = checker.check_all_sources(cfg)

    # Display auth status summary
    _display_auth_status(statuses)

    # Handle missing/expired auth
    needs_auth = checker.needs_resolution(statuses)
    if needs_auth:
        if non_interactive:
            console.print(
                "[red]Missing authentication. "
                "Use 'pkm auth login' or remove --non-interactive.[/red]"
            )
            raise SystemExit(1)

        # Auto-prompt login for each source
        auth_manager = _get_auth_manager()
        statuses = _resolve_missing_auth(
            statuses, cfg, auth_manager, config_path, interactive=True, auto_oauth=auto_oauth
        )

    # Check if any still failed
    still_failed = [s for s in statuses if s.state in (AuthState.MISSING, AuthState.INVALID_CONFIG)]
    if still_failed:
        _display_failed_sources(still_failed)
        if not click.confirm("Proceed with available sources?", default=True):
            raise SystemExit(1)


@click.command("preflight")
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config file")
def preflight_cmd(config: str | None) -> None:
    """Check authentication status for all data sources."""
    from rich.console import Console

    console = Console()
    cfg = load_config(config)

    checker = PreflightChecker(preferred_browser=cfg.preferred_browser)
    statuses = checker.check_all_sources(cfg)

    # Display status table
    _display_auth_status(statuses)

    # Summary
    summary = checker.get_summary(statuses)
    valid = summary.get("valid", 0) + summary.get("not_required", 0)
    missing = summary.get("missing", 0) + summary.get("expired", 0)
    disabled = summary.get("disabled", 0)

    console.print()
    if missing > 0:
        console.print(f"[yellow]{valid} sources ready, {missing} need authentication[/yellow]")
        console.print("\nRun [bold]pkm auth login <source>[/bold] to authenticate.")
    else:
        console.print(f"[green]All {valid} sources ready![/green]")

    if disabled > 0:
        console.print(f"[dim]({disabled} sources disabled)[/dim]")
