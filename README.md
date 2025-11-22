# pkm-tool

[![CI](https://github.com/kakkoyun/pkm-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/kakkoyun/pkm-tool/actions/workflows/ci.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/kakkoyun/pkm-tool)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![codecov](https://codecov.io/gh/kakkoyun/pkm-tool/branch/main/graph/badge.svg)](https://codecov.io/gh/kakkoyun/pkm-tool)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

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

# Run the CLI
uv run pkm
```

Or install directly:

```bash
uv pip install -e .
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
  Google Docs

  Run without subcommand to aggregate all sources, or use subcommands to fetch
  from individual sources:

  pkm --date yesterday                Aggregate all sources (backward compat)
  pkm aggregate --date yesterday      Explicitly aggregate all sources
  pkm calendar --date yesterday       Fetch Apple Calendar events only
  pkm github --date yesterday         Fetch GitHub activities only
  pkm atlassian --date yesterday      Fetch Atlassian (Jira/Confluence) items only
  pkm things --date yesterday         Fetch Things tasks only
  pkm wakatime --date yesterday       Fetch Wakatime coding activities only
  pkm google-docs --date yesterday    Fetch Google Docs only

Options:
  -d, --date TEXT               Date to fetch data for (default: today). Format:
                                YYYY-MM-DD or natural language.
  -f, --format [markdown|json]  Output format (default: markdown)
  -c, --config PATH             Path to configuration file
  -v, --verbose                 Enable verbose (DEBUG) logging
  --log-format [human|json]     Log output format (default: human)
  --help                        Show this message and exit.

Commands:
  aggregate    Aggregate data from all configured sources (default behavior).
  auth         Manage authentication credentials.
  atlassian    Fetch Atlassian (Jira/Confluence) items only.
  calendar     Fetch Apple Calendar events only.
  github       Fetch GitHub activities only.
  google-docs  Fetch Google Docs only.
  things       Fetch Things tasks only.
  wakatime     Fetch Wakatime coding activities only.
```

### Available Options

- **`-d, --date TEXT`**: Date to fetch data for (default: today). Format: YYYY-MM-DD or natural language.
- **`--from DATE`**: Start date for date range (requires `--to`). Format: YYYY-MM-DD or natural language.
- **`--to DATE`**: End date for date range (requires `--from`). Format: YYYY-MM-DD or natural language.
- **`-o, --output-dir PATH`**: Output directory for batch mode (date ranges). Overrides config setting.
- **`--exclude-weekends`**: Skip weekends (Saturdays and Sundays) in date ranges and source fetching.
- **`-f, --format [markdown|json]`**: Output format (default: markdown)
- **`-c, --config PATH`**: Path to configuration file
- **`-v, --verbose`**: Enable verbose (DEBUG) logging
- **`--log-format [human|json]`**: Log output format (default: human)
- **`--help`**: Show this message and exit.

### Date Range Examples (Phase 2)

Generate reports for multiple days at once:

```bash
# Generate reports for a week
pkm --from 2025-11-17 --to 2025-11-23

# Skip weekends globally
pkm --from 2025-11-17 --to 2025-11-23 --exclude-weekends

# Custom output directory
pkm --from 2025-11-17 --to 2025-11-23 -o ~/Documents/daily-notes/

# Date ranges work with all subcommands
pkm github --from 2025-11-17 --to 2025-11-23
pkm wakatime --from 2025-11-17 --to 2025-11-23 --exclude-weekends
```

**Smart File Updates**: When generating reports for existing files, the tool intelligently:

- Preserves your manual notes (preamble and postamble)
- Updates PKM sections with fresh data
- Appends new PKM sections that weren't in the file
- Allows seamless mixing of automated data with personal journaling

### Authentication Management

Credentials are stored in an encrypted SQLite database at `~/.pkm-tool/tokens.db`
(encrypted with a machine-specific key). Manage them via the `auth` subcommands:

```bash
# Discover supported sources and auth types
pkm auth list

# Check which sources are authenticated
pkm auth status

# Store tokens and API keys securely (interactive prompts)
pkm auth login github
pkm auth login wakatime
pkm auth login atlassian
pkm auth login google-docs --config ~/.config/pkm-tool/config.yaml
pkm auth login whoop

# Remove or refresh credentials
pkm auth logout github
pkm auth refresh google-docs --config ~/.config/pkm-tool/config.yaml
```

Google Docs uses the OAuth2 device code flow. Add your Google client ID/secret to
the config file (see below) and run `pkm auth login google-docs` to authorize the
CLI without running a local server.

<!-- CLI_USAGE_END -->

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

### Setup

```bash
# Install with dev dependencies
uv sync --all-extras

# Install pre-commit hooks
make install-hooks

# Run all checks (format, lint, typecheck, test)
make all
```

### Testing

The project has comprehensive test coverage (77%) with multiple testing strategies:

#### Test Organization

```text
tests/
├── __snapshots__/         # Auto-generated snapshot files
│   └── test_cli.ambr      # CLI output snapshots
├── fixtures/              # Reusable test fixtures
│   ├── github_fixtures.py      # Mock GitHub API responses
│   ├── wakatime_fixtures.py    # Mock Wakatime API responses
│   ├── atlassian_fixtures.py   # Mock Atlassian API responses
│   └── system_fixtures.py      # Mock system calls (subprocess, SQLite)
├── conftest.py            # Shared pytest configuration
├── test_cli.py            # CLI snapshot and unit tests (9 tests)
├── test_integration.py    # End-to-end integration tests (12 tests)
├── test_models.py         # Data model tests
├── test_config.py         # Configuration tests
├── test_formatters.py     # Output formatter tests
└── test_*_migration.py    # Source-specific integration tests
```

#### Test Types

##### 1. Snapshot Tests

Location: `tests/test_cli.py`

Snapshot tests validate CLI output remains consistent across changes:

```python
@pytest.mark.snapshot
def test_cli_markdown_output_with_mocks(snapshot: SnapshotAssertion):
    result = cli_runner.invoke(main, ["--date", "2025-11-21", "--format", "markdown"])
    assert result.output == snapshot  # Compared against saved snapshot
```

Snapshots are stored in `tests/__snapshots__/test_cli.ambr` and can be updated with:

```bash
pytest --snapshot-update
```

##### 2. Integration Tests

Location: `tests/test_integration.py`

End-to-end tests with mocked external APIs:

- Full aggregation with all sources enabled
- Selective source testing
- Error handling and graceful degradation
- Date parsing and filtering
- Config file integration

##### 3. Unit Tests

Individual component tests with comprehensive mocking:

- Models: Pydantic validation
- Config: YAML loading and defaults
- Formatters: Markdown/JSON output
- Sources: Individual data source logic

#### Running Tests

```bash
# Run all tests
make test
# or: uv run pytest

# Run with coverage report
make test/coverage
# or: uv run pytest --cov --cov-report=html

# Run specific test types
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests only
pytest -m snapshot          # Snapshot tests only

# Run specific test file
pytest tests/test_cli.py

# Run with verbose output
pytest -v

# Update snapshots after intentional changes
pytest --snapshot-update
```

#### Test Coverage

Current coverage: **77%**

| Module            | Coverage | Notes                    |
| ----------------- | -------- | ------------------------ |
| models.py         | 100%     | Full Pydantic validation |
| wakatime.py       | 100%     | Complete HTTP mocking    |
| github.py         | 94%      | PyGithub mocked          |
| atlassian.py      | 89%      | Jira/Confluence mocked   |
| cli.py            | 87%      | Snapshot tested          |
| apple_calendar.py | 85%      | Subprocess mocked        |
| config.py         | 92%      | YAML loading tested      |
| aggregator.py     | 77%      | Integration tested       |

#### Mocking Strategy

All external dependencies are mocked to ensure fast, reliable tests:

- **GitHub**: PyGithub client mocked with `pytest-mock`
- **Wakatime**: HTTP API mocked with `respx`
- **Atlassian**: Jira/Confluence clients mocked
- **Apple Calendar**: `subprocess.run()` mocked for osascript calls
- **Things**: In-memory SQLite database with test data

No actual API calls are made during testing.

### Code Quality

```bash
# Run all quality checks
make all

# Individual checks
make format              # Format all code
make lint                # Run all linters
make typecheck/python    # Type check with ty
make test                # Run tests

# Auto-fix issues
make fix/python          # Format + lint --fix
```

### Project Structure

```text
pkm-tool/
├── src/pkm_tool/
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration management
│   ├── models.py           # Data models
│   ├── aggregator.py       # Data aggregation logic
│   ├── formatters.py       # Output formatters
│   └── sources/            # Data source integrations
│       ├── apple_calendar.py
│       ├── github.py
│       ├── atlassian.py
│       ├── things.py
│       ├── wakatime.py
│       └── google_docs.py
├── tests/                  # Test files
├── pyproject.toml         # Project configuration
└── config.example.yaml    # Example configuration
```

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
