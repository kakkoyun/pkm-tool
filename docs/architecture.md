# Architecture

## Overview

PKM Tool is a personal knowledge management system that aggregates daily data from seven external sources into formatted
reports. The tool produces human-readable Markdown reports or machine-readable JSON output, enabling users to maintain
comprehensive daily activity logs across multiple platforms.

**Supported data sources:**

- GitHub (commits, PRs, issues, reviews)
- Apple Calendar (events)
- Things (completed tasks)
- Wakatime (coding activity)
- Atlassian (Jira issues, Confluence pages)
- Google Docs (recently opened documents)
- Whoop (health and fitness data)

## Architecture Diagram

```
CLI (cli.py)
    ↓
Aggregator (aggregator.py) ← Config (config.py)
    ↓
Sources (sources/*.py) → Models (models.py)
    ↓
Formatters (formatters.py)
    ↓
Output (Markdown/JSON)
```

## Module Responsibilities

### CLI Layer (cli.py)

**Purpose:** Command-line interface and entry point for all user interactions.

**Responsibilities:**

- Click-based CLI with subcommands (aggregate, github, wakatime, things, etc.)
- Date parsing (relative dates like "yesterday", ISO format, natural language)
- Authentication commands (`pkm auth list/status/login/logout/refresh`)
- Source-specific subcommands for fetching individual source data
- Server mode (`pkm server`) and MCP mode (`pkm mcp`) entry points
- Date range support (--from/--to flags) for batch report generation
- Weekend exclusion control (--exclude-weekends flag)
- Auto-OAuth control flags (--no-auto-oauth, --non-interactive, --no-preflight)

**Key features:**

- Rich terminal output for user feedback
- Error handling and user-friendly error messages
- Configuration file path override (--config flag)
- Output format selection (--format markdown|json)

### Aggregator (aggregator.py)

**Purpose:** Central orchestration layer that coordinates data collection from all sources.

**Responsibilities:**

- Load and validate configuration
- Execute preflight authentication checks (OAuth token validation)
- Call each enabled source's fetch function
- Isolate errors per source (one failure does not affect others)
- Collect timing metadata for each source
- Handle weekend exclusion logic (skip sources configured to exclude weekends)
- Aggregate results into a single AggregatedData model
- Store error messages in metadata dictionary

**Error handling:**

- Each source is called within a try-except block
- Errors are caught, logged, and stored in `metadata["source_error"]`
- Empty results are returned on error, never None
- Aggregator never raises exceptions to CLI

**Key features:**

- Parallel-ready design (sources are independent)
- Graceful degradation (partial data is useful)
- Timing instrumentation for performance monitoring

### Configuration (config.py)

**Purpose:** Centralized configuration management with validation.

**Responsibilities:**

- Load YAML configuration files from multiple locations
- Validate configuration schema using Pydantic
- Provide defaults for all optional settings
- Per-source configuration via SourceConfig pattern
- Cache configuration (CacheConfig for HTTP response caching)
- Authentication configuration (token storage paths, OAuth client IDs/secrets)
- Output configuration (filename templates, output directories)

**Configuration hierarchy:**

1. Project directory: `./.pkm.yaml`, `./.pkm.yml`, `./pkm-tool.yaml`
1. Home directory: `~/.pkm.yaml`, `~/.pkm.yml`, `~/.pkm-tool.yaml`
1. XDG config: `~/.config/pkm-tool/config.yaml`

**SourceConfig pattern:**

```python
class SourceConfig(BaseModel):
    enabled: bool = True
    exclude_weekends: bool = False
    config: dict[str, Any] = Field(default_factory=dict)
```

This pattern ensures consistency across all seven sources.

### Models (models.py)

**Purpose:** Type-safe data models for all domain objects.

**Responsibilities:**

- Define Pydantic models for each data source
- Enforce validation rules (required fields, types, constraints)
- Provide JSON serialization/deserialization
- Maintain immutability (frozen=False by default, but models are not mutated)

**Key models:**

- **Event:** Calendar events with title, start/end times, location, description
- **GitHubActivity:** Commits, PRs, issues, reviews with repository context
- **AtlassianItem:** Jira issues and Confluence pages with status tracking
- **ThingsTask:** Completed tasks with projects, tags, completion times
- **WakatimeActivity:** Coding time per project and language
- **GoogleDoc:** Recently opened documents with titles and URLs
- **WhoopRecovery:** Recovery score, HRV, resting heart rate, SpO2
- **WhoopSleep:** Sleep cycles with stages (deep/light/REM/awake), efficiency
- **WhoopWorkout:** Workout activities with strain score, heart rate zones
- **AggregatedData:** Container for all source data plus metadata (errors, timing)

### Formatters (formatters.py)

**Purpose:** Transform aggregated data into human-readable or machine-readable output.

**Responsibilities:**

- Markdown formatting with emoji and structured sections
- JSON formatting using Pydantic's model_dump_json
- Sort events by timestamp for chronological display
- Display error messages for failed sources
- Filename templating for batch mode (e.g., `{date} ({day_abbr}).md`)
- Smart file merging: update existing files while preserving manual content

**Smart file merging algorithm:**

1. Parse existing markdown file to extract sections
1. Identify PKM-generated sections (case-insensitive matching)
1. Preserve preamble (content before first PKM section)
1. Update existing PKM sections with new data
1. Append new PKM sections that don't exist in file
1. Preserve postamble (content after last PKM section)

This allows users to mix automated data with personal journaling.

### Sources Common (sources/common.py)

**Purpose:** Shared utilities for all source plugins.

**Responsibilities:**

- Token retrieval with fallback chain: token store → config → environment variables
- HTTP client factory with caching support (hishel integration)
- Common error handling patterns
- Shared type definitions

**Token retrieval order:**

1. Check encrypted token store (`~/.pkm-tool/tokens.db`)
1. Check config YAML (`config.source.config["token"]`)
1. Check environment variables (e.g., `GITHUB_TOKEN`)
1. Return None if no token found

### Source Plugins (sources/\*.py)

**Purpose:** Independent data fetchers for each external service.

**Source interface contract:**

```python
def fetch_*_activities(
    target_date: date,
    config: dict[str, Any]
) -> list[Model]:
    """
    Standard source interface.

    Args:
        target_date: Date to fetch data for
        config: Configuration dictionary from SourceConfig.config

    Returns:
        List of typed model objects (never None, empty list on error)
    """
```

**Common patterns across all sources:**

- Platform detection for macOS-specific sources (Apple Calendar, Things)
- Multiple authentication methods (CLI tools, direct API, OAuth)
- Graceful degradation: return empty list on error, never raise
- Date filtering: query broader range, filter results by exact date
- Error suppression: catch all exceptions to prevent cascading failures

**Source-specific implementations:**

**GitHub (github.py):**

- Smart auth: prefer `gh` CLI, fallback to browser-guided PAT creation
- Event types: PushEvent, PullRequestEvent, IssuesEvent, PullRequestReviewEvent
- Username auto-detection from `gh` CLI

**Apple Calendar (apple_calendar.py):**

- macOS only: uses AppleScript via `osascript` command
- Platform check via `uname` command
- Cross-calendar: queries all calendars in Calendar.app

**Things (things.py):**

- macOS only: direct SQLite database access
- Database path: `~/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/`
- Custom timestamp format: seconds since 2001-01-01
- Read-only mode for database safety

**Wakatime (wakatime.py):**

- REST API: summaries endpoint
- Bearer token authentication
- Per-project aggregation
- Language detection (best-effort, API limitation)

**Atlassian (atlassian.py):**

- Dual integration: Jira issues and Confluence pages
- Basic authentication: email + API token
- Date filtering: items updated on target date
- Status tracking for Jira issues

**Google Docs (google_docs.py):**

- OAuth2 required: Google Drive API access token
- Recently opened documents
- Document metadata: title, URL, opened time, type

**Whoop (whoop.py):**

- OAuth2 required: Whoop API access token
- Three data types: Recovery (single/day), Sleep cycles (multiple), Workouts (multiple)
- Recovery metrics: score, HRV, resting heart rate, SpO2
- Sleep tracking: stages, efficiency, disturbances
- Workout data: sport type, strain, heart rate zones

### Authentication (auth/)

**Purpose:** Secure credential management with OAuth support.

**Components:**

**Token Store (auth/token_store.py):**

- Encrypted SQLite database at `~/.pkm-tool/tokens.db`
- Fernet encryption (symmetric encryption)
- Encryption key derived from machine identifier + home directory path
- Stores: token, refresh_token, expires_at, token_type per source

**Auth Manager (auth/manager.py):**

- Central orchestration for token loading and refresh
- Automatic token refresh when within 5 minutes of expiry
- Helper APIs for API keys/PATs and OAuth responses
- Interactive login flows for missing credentials

**OAuth Providers (auth/oauth/):**

- Base protocol in `auth/oauth/base.py`
- Google implementation: device code flow (no local callback server)
- Whoop implementation: device code flow
- Atlassian implementation: OAuth 2.0 authorization code flow

**Preflight Checks (auth/preflight.py):**

- Validate OAuth tokens before making API calls
- Test token validity with lightweight API calls
- Auto-refresh expired tokens
- Report authentication status to user

**Auto-OAuth behavior:**

- Default: automatically launch browser OAuth for missing credentials
- `--no-auto-oauth`: prompt for confirmation before launching browser
- `--non-interactive`: fail fast in CI/headless environments
- `--no-preflight`: skip authentication checks entirely

### Caching (cache.py)

**Purpose:** HTTP response caching to reduce API calls and improve performance.

**Implementation:**

- Uses hishel library for HTTP caching
- SQLite-based cache storage
- Configurable cache directory
- Per-source cache control headers
- Respects HTTP cache semantics (Cache-Control, ETag, etc.)

### Logging (logging.py)

**Purpose:** Structured logging for debugging and troubleshooting.

**Features:**

- Structlog configuration
- Human-readable console output (default)
- JSON output for production/parsing (--format json flag in server mode)
- Colored output for terminals
- Configurable log levels

### Server (server/api.py)

**Purpose:** Optional REST API server for programmatic access.

**Features:**

- FastAPI-based REST API
- Interactive API documentation at /docs
- Health check endpoint at /health
- Same data sources as CLI
- JSON responses only
- Auto-reload for development (--reload flag)

**Endpoints:**

- `GET /api/aggregate?date=YYYY-MM-DD` - Aggregated data from all sources
- `GET /api/github?date=YYYY-MM-DD` - GitHub activities only
- `GET /api/wakatime?date=YYYY-MM-DD` - Wakatime activities only
- (similar endpoints for other sources)

### MCP Server (mcp_server/server.py)

**Purpose:** Model Context Protocol server for AI assistant integration.

**Features:**

- Stdio-based MCP protocol
- Exposes PKM tool as MCP tools
- Claude Desktop integration
- Same data sources as CLI

**MCP tools:**

- `fetch_aggregated_data` - Get data from all sources
- `fetch_calendar_events` - Apple Calendar events
- `fetch_github_activities` - GitHub activities
- `fetch_atlassian_items` - Atlassian items
- `fetch_things_tasks` - Things tasks
- `fetch_wakatime_activities` - Wakatime activities
- `fetch_google_docs` - Google Docs
- `fetch_whoop_data` - Whoop health data

## Data Flow

1. **User invokes CLI:** `uv run pkm aggregate --date yesterday`
1. **CLI parses arguments:** Validates date, loads configuration
1. **CLI calls aggregator:** `aggregate_data(target_date, config)`
1. **Aggregator loads config:** Validates YAML, applies defaults
1. **Aggregator runs preflight:** Checks OAuth tokens, auto-refreshes if needed
1. **Aggregator calls sources:** For each enabled source, calls `fetch_*_activities()`
1. **Sources fetch data:** Make API calls, query databases, run CLI tools
1. **Sources return models:** Typed Pydantic models, empty list on error
1. **Aggregator collects results:** Builds AggregatedData with all source data
1. **Aggregator returns to CLI:** AggregatedData with metadata (errors, timing)
1. **CLI calls formatter:** `format_markdown()` or `format_json()`
1. **Formatter produces output:** Structured text with sections, sorted by time
1. **CLI writes output:** To stdout (single date) or files (date range)

## Error Handling Philosophy

**Core principle:** One source failure should never affect other sources or crash the tool.

**Error isolation:**

- Each source is called within a try-except block in the aggregator
- Errors are caught, logged with structlog, and stored in metadata
- Sources return empty list on error, never raise exceptions
- Aggregator continues execution even if multiple sources fail

**Error reporting:**

- Errors are collected in `AggregatedData.metadata["source_error"]`
- Formatters display errors at the end of reports
- User sees which sources failed and why
- Partial data is still useful and displayed

**Graceful degradation:**

- If GitHub fails, user still gets calendar events and Wakatime data
- If OAuth token is expired, preflight auto-refreshes
- If configuration is invalid, Pydantic validation provides clear error messages

## Authentication Flow

**Token retrieval priority:**

1. **Token store** (encrypted SQLite): `~/.pkm-tool/tokens.db`
1. **Config YAML**: `config.source.config["token"]`
1. **Environment variables**: `GITHUB_TOKEN`, `WAKATIME_API_KEY`, etc.

**OAuth token lifecycle:**

1. User runs `pkm auth login google-docs` (or auto-OAuth triggers)
1. Browser opens to OAuth consent page
1. User authorizes application
1. Device code flow completes, token returned
1. Token encrypted and stored in token store
1. On subsequent runs, token loaded from store
1. When token is within 5 minutes of expiry, auto-refresh
1. If refresh fails, user prompted to re-authenticate

**Auto-OAuth behavior:**

- Default: automatically launch browser for missing OAuth credentials
- No confirmation prompts - seamless experience
- Use `--no-auto-oauth` to restore confirmation prompts
- Use `--non-interactive` to fail fast in CI environments

## Extension Points

**Adding a new data source:**

1. Create Pydantic model in `models.py`
1. Add field to `AggregatedData` model
1. Create source module in `sources/new_source.py`
1. Implement `fetch_new_source_items(target_date, config)` function
1. Add source config to `Config` in `config.py`
1. Add source call to `aggregator.py` with error handling
1. Update formatters in `formatters.py` (Markdown and JSON)
1. Add CLI subcommand in `cli.py`
1. Write tests in `tests/test_new_source.py`
1. Add fixtures in `tests/fixtures/new_source_fixtures.py`

**Adding a new output format:**

1. Create formatter function in `formatters.py`
1. Add format option to CLI (--format new_format)
1. Update CLI to call new formatter
1. Write tests for new formatter

**Adding authentication for a new source:**

1. Create OAuth provider in `auth/oauth/new_source.py`
1. Add token storage support in `auth/manager.py`
1. Add login command to CLI (pkm auth login new-source)
1. Update preflight checks in `auth/preflight.py`
1. Update source to use auth manager for token retrieval

## Performance Considerations

**HTTP caching:**

- Reduces API calls for frequently accessed data
- Respects cache headers from APIs
- SQLite-based cache storage (configurable location)

**Parallel execution:**

- Sources are independent and can be parallelized (not yet implemented)
- Aggregator could use asyncio or threading for concurrent source calls

**Error timeouts:**

- HTTP clients have reasonable timeouts (10-30 seconds)
- Database queries are read-only and fast
- CLI tools (gh, osascript) have subprocess timeouts

**Database access:**

- Things database opened in read-only mode
- Single query per date, no complex joins
- SQLite is fast for small databases

## Security Considerations

**Token storage:**

- Fernet symmetric encryption for token database
- Encryption key derived from machine-specific identifier
- Tokens never logged or printed to console
- Token database permissions: 0600 (user read/write only)

**API credentials:**

- Never commit tokens to git
- Use environment variables or config files (gitignored)
- OAuth tokens expire and auto-refresh
- Personal access tokens should have minimal scopes

**External dependencies:**

- All dependencies pinned in pyproject.toml
- Regular updates via dependabot
- Security scanning with pip-audit (planned)
- Code scanning with bandit (planned)

**Input validation:**

- All user input validated by Pydantic models
- Date parsing validates format and range
- Configuration schema validation prevents malformed config
- No shell injection risks (subprocess calls use list args, not shell=True)
