# pkm-tool

[![CI](https://github.com/kakkoyun/pkm-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/kakkoyun/pkm-tool/actions/workflows/ci.yml)
[![Commitlint](https://github.com/kakkoyun/pkm-tool/actions/workflows/commitlint.yml/badge.svg)](https://github.com/kakkoyun/pkm-tool/actions/workflows/commitlint.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/kakkoyun/pkm-tool)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![codecov](https://codecov.io/gh/kakkoyun/pkm-tool/branch/main/graph/badge.svg)](https://codecov.io/gh/kakkoyun/pkm-tool)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-%23FE5196?logo=conventionalcommits&logoColor=white)](https://conventionalcommits.org)

Personal Knowledge Management Tool to fetch and format data from several resources.

## Features

PKM Tool aggregates data from multiple sources into a unified daily report:

- **📅 Apple Calendar** - Agenda and events (macOS only)
- **🐙 GitHub** - Activities including commits, PRs, issues, and reviews (via gh CLI or API)
- **🏢 Atlassian** - Jira issues and Confluence pages
- **✅ Things** - Completed tasks from logbook (macOS only)
- **⏱️ Wakatime** - Coding activity per project
- **📝 Google Docs** - Recently opened documents
- **💪 Whoop** - Recovery, sleep, and workout data

### Phase 2 Features (NEW!)

- **📆 Date Ranges** - Generate reports for multiple days with `--from` and `--to` flags
- **🗂️ Smart File Updates** - Intelligently merge PKM sections with existing notes while preserving manual content
- **📝 Configurable Filenames** - Template-based naming (default: `2025-11-22 (Fri).md`)
- **🚫 Weekend Exclusion** - Skip weekends globally or per-source with `--exclude-weekends`

## Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
# Clone the repository
git clone https://github.com/kakkoyun/pkm-tool.git
cd pkm-tool

# Install with uv
uv sync

# Optional: Install server extras for FastAPI web server
uv sync --extra server

# Optional: Install MCP extras for Model Context Protocol server
uv sync --extra mcp

# Run the CLI
uv run pkm
```

Or install directly:

```bash
uv pip install -e .

# Or with extras
uv pip install -e ".[server,mcp]"
```

## Usage

<!-- CLI_USAGE_START -->

```bash
pkm --help
```

```
Usage: cli [OPTIONS] COMMAND [ARGS]...

  Personal Knowledge Management Tool.

  Fetches and formats data from various sources including: - Apple Calendar
  Agenda - GitHub - Atlassian (Jira/Confluence) - Things Logbook - Wakatime -
  Google Docs - Whoop

  Use subcommands to aggregate all sources or fetch from individual sources:

  pkm aggregate --date yesterday      Aggregate all sources
  pkm calendar --date yesterday       Fetch Apple Calendar events only
  pkm github --date yesterday         Fetch GitHub activities only
  pkm atlassian --date yesterday      Fetch Atlassian (Jira/Confluence) items only
  pkm things --date yesterday         Fetch Things tasks only
  pkm wakatime --date yesterday       Fetch Wakatime coding activities only
  pkm google-docs --date yesterday    Fetch Google Docs only
  pkm whoop --date yesterday          Fetch Whoop health data only
  pkm server                          Start FastAPI web server
  pkm mcp                             Run as MCP (Model Context Protocol) server

Options:
  --help  Show this message and exit.

Commands:
  aggregate    Aggregate data from all configured sources (default behavior).
  atlassian    Fetch Atlassian (Jira/Confluence) items only.
  auth         Manage authentication credentials.
  calendar     Fetch Apple Calendar events only.
  github       Fetch GitHub activities only.
  google-docs  Fetch Google Docs only.
  mcp          Run PKM Tool as an MCP (Model Context Protocol) server.
  server       Start the PKM Tool web server.
  things       Fetch Things tasks only.
  wakatime     Fetch Wakatime coding activities only.
  whoop        Fetch Whoop health data only.
```

### MCP Server Mode (NEW!)

PKM Tool can run as an MCP (Model Context Protocol) server,
allowing AI assistants like Claude to access your personal data securely:

```bash
# Run as MCP server (stdio mode)
pkm mcp
```

**Integration with Claude Desktop:**

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "pkm-tool": {
      "command": "pkm",
      "args": ["mcp"],
      "env": {}
    }
  }
}
```

**Available MCP Tools:**

- `fetch_aggregated_data` - Get data from all configured sources
- `fetch_calendar_events` - Get Apple Calendar events
- `fetch_github_activities` - Get GitHub activities
- `fetch_atlassian_items` - Get Atlassian (Jira/Confluence) items
- `fetch_things_tasks` - Get Things tasks
- `fetch_wakatime_activities` - Get Wakatime coding activities
- `fetch_google_docs` - Get Google Docs
- `fetch_whoop_data` - Get Whoop health data

Once configured, Claude can fetch and analyze your daily data on demand.

### Available Options

- **`--help`**: Show this message and exit.

<!-- CLI_USAGE_END -->

### Server Mode

PKM Tool can run as a web server providing a REST API for fetching data. This is useful for:

- Testing and troubleshooting data sources
- Integrating with other tools and services
- Building custom UIs or dashboards

#### Starting the Server

```bash
# Start server on default port (8000)
pkm server

# Start on custom port with auto-reload
pkm server --port 8080 --reload

# Start with verbose logging
pkm server --verbose
```

The server will be accessible at `http://127.0.0.1:8000` by default.

#### Server Options

- `--host TEXT` - Host to bind the server to (default: 127.0.0.1)
- `--port INTEGER` - Port to bind the server to (default: 8000)
- `--reload` - Enable auto-reload on code changes (development mode)
- `-c, --config PATH` - Path to configuration file
- `-v, --verbose` - Enable verbose (DEBUG) logging
- `--log-format [human|json]` - Log output format (default: human)

#### API Endpoints

Once the server is running, you can access:

- **Interactive API docs**: `http://127.0.0.1:8000/docs`
- **ReDoc documentation**: `http://127.0.0.1:8000/redoc`

**Available Endpoints:**

- `GET /health` - Health check endpoint

  ```bash
  curl http://127.0.0.1:8000/health
  ```

- `GET /api/sources` - List all available data sources

  ```bash
  curl http://127.0.0.1:8000/api/sources
  ```

- `GET /api/config` - Get configuration information

  ```bash
  curl http://127.0.0.1:8000/api/config
  ```

- `GET /api/data` - Fetch aggregated data for a specific date

  ```bash
  # Get today's data in markdown format
  curl "http://127.0.0.1:8000/api/data"

  # Get specific date in JSON format
  curl "http://127.0.0.1:8000/api/data?date=2025-12-02&format=json"

  # Get data from specific sources only
  curl "http://127.0.0.1:8000/api/data?date=2025-12-02&sources=github,wakatime"
  ```

**Query Parameters:**

- `date` - Date to fetch (YYYY-MM-DD format, default: today)
- `format` - Output format (`markdown` or `json`, default: markdown)
- `sources` - Comma-separated list of sources to fetch (default: all enabled sources)

#### Installing Server Dependencies

The server requires additional dependencies that are installed as an optional extra:

```bash
# Install server dependencies
uv sync --extra server

# Or with pip
pip install -e ".[server]"
```

### Logging

The tool includes comprehensive structured logging for troubleshooting:

```bash
# Enable verbose logging to see detailed debug information
pkm --verbose

# Use JSON logging format for production/log aggregation
pkm --verbose --log-format json

# Standard (INFO) logging is enabled by default
pkm
```

**Log levels:**

- **INFO** (default): Start/end of operations, source status, config loading
- **DEBUG** (with `--verbose`): Detailed API calls, authentication, data parsing, file paths

**Log formats:**

- **human** (default): Colored, human-readable console output for development
- **json**: Structured JSON logs for production and log aggregation systems

### Configuration

Copy the example configuration file:

```bash
cp config.example.yaml ~/.config/pkm-tool/config.yaml
```

Edit the configuration file to enable/disable sources and add credentials:

```yaml
# Output settings (Phase 2)
output_filename_template: "{date} ({day_abbr}).{format}"  # Default: "2025-11-22 (Fri).md"
output_directory: "./daily-notes"  # Where to write files

github:
  enabled: true
  exclude_weekends: false  # Set to true to skip GitHub on weekends
  config:
    use_gh_cli: true  # Uses gh CLI for authentication

wakatime:
  enabled: true
  exclude_weekends: true  # Example: skip coding activity tracking on weekends
  config:
    api_key: waka_your_api_key_here

atlassian:
  enabled: true
  config:
    base_url: https://your-domain.atlassian.net
    username: your.email@example.com
    api_token: your_api_token_here

google_docs:
  enabled: true
  config:
    client_id: your_google_client_id.apps.googleusercontent.com
    client_secret: your_google_client_secret
    scopes:
      - https://www.googleapis.com/auth/drive.readonly
    # Optional legacy fallback (not recommended)
    # access_token: your_access_token_here

whoop:
  enabled: true
  config:
    # Preferred: store tokens via `pkm auth login whoop`
    # access_token: your_whoop_access_token_here
```

#### Filename Template Variables

The `output_filename_template` supports the following variables:

- `{date}` - Full date in YYYY-MM-DD format (e.g., "2025-11-22")
- `{year}` - Four-digit year (e.g., "2025")
- `{month}` - Two-digit month (e.g., "11")
- `{day}` - Two-digit day (e.g., "22")
- `{day_abbr}` - Abbreviated day name (e.g., "Mon", "Fri")
- `{format}` - Output format extension ("md" for markdown, "json" for json)

Examples:

- `"{date} ({day_abbr}).{format}"` → `2025-11-22 (Fri).md`
- `"{year}/{month}/{day}.{format}"` → `2025/11/22.md`
- `"daily-note-{date}.{format}"` → `daily-note-2025-11-22.md`

### Output Formats

#### Markdown (Default)

```markdown
# Daily Report - 2025-11-21

## 📅 Calendar Events

- **10:00 - 11:00** Team Standup
  - Location: Conference Room A

## 🐙 GitHub Activities

- 📝 **09:30** [owner/repo](https://github.com/owner/repo) - Pushed 3 commits

## ✅ Things - Completed Tasks

- **14:30** Review PR #123 (Work)

## ⏱️ Wakatime - Coding Activity

**Total Time:** 6.5 hours

- pkm-tool (Python): 4.2h
- my-project (Go): 2.3h
```

#### JSON

```json
{
  "date": "2025-11-21",
  "calendar_events": [...],
  "github_activities": [...],
  "atlassian_items": [...],
  "things_tasks": [...],
  "wakatime_activities": [...],
  "google_docs": [...],
  "metadata": {}
}
```

## Development

Want to contribute? See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed development instructions.

### Quick Start

```bash
# Install with dev dependencies
make install

# Install pre-commit hooks
make install-hooks

# Run all checks (format, lint, typecheck, test)
make all
```

### Project Structure

```text
pkm-tool/
├── src/pkm_tool/
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration management
│   ├── models.py           # Pydantic data models
│   ├── aggregator.py       # Data aggregation logic
│   ├── formatters.py       # Output formatters
│   ├── auth/               # Authentication system
│   ├── sources/            # Data source integrations
│   ├── server/             # FastAPI web server
│   └── mcp_server/         # MCP server
├── tests/                  # Comprehensive test suite (88% coverage)
└── .github/                # CI/CD workflows
```

### Testing

The project has comprehensive test coverage (88%) with unit tests, integration tests, and snapshot tests.

```bash
# Run all tests
make test

# Run with coverage report
make test/coverage
```

See [CONTRIBUTING.md](CONTRIBUTING.md#testing) for detailed testing documentation.

## Data Sources

### Apple Calendar

Requires macOS. Uses AppleScript to query Calendar.app.

### GitHub

Two authentication methods:

1. **gh CLI** (recommended): Uses the installed `gh` CLI tool
1. **Personal Access Token**: Set `GITHUB_TOKEN` and `GITHUB_USERNAME` environment variables

### Atlassian (Jira/Confluence)

Requires:

- Atlassian Cloud instance URL
- Email address
- API token (create at <https://id.atlassian.com/manage-profile/security/api-tokens>)

### Things

Requires macOS. Reads from Things' SQLite database located at:
`~/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/Things Database.thingsdatabase/main.sqlite`

### Wakatime

Requires Wakatime API key. Get it from <https://wakatime.com/settings/account>

### Google Docs

Requires OAuth2 access token. See Google Drive API documentation for setup.

## LLM Tool Integration

The PKM tool can be used as an LLM tool/function. See the JSON output format for structured data that can be
consumed by LLMs.

Example tool definition:

```json
{
  "name": "get_daily_report",
  "description": "Get aggregated daily report from multiple knowledge sources",
  "parameters": {
    "type": "object",
    "properties": {
      "date": {
        "type": "string",
        "description": "Date to fetch report for (YYYY-MM-DD or natural language)"
      }
    }
  }
}
```

## License

See [LICENSE](LICENSE) file.
