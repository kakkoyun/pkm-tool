# pkm-tool

Personal Knowledge Management Tool to fetch and format data from several resources.

## Features

PKM Tool aggregates data from multiple sources into a unified daily report:

- **📅 Apple Calendar** - Agenda and events (macOS only)
- **🐙 GitHub** - Activities including commits, PRs, issues, and reviews (via gh CLI or API)
- **🏢 Atlassian** - Jira issues and Confluence pages
- **✅ Things** - Completed tasks from logbook (macOS only)
- **⏱️ Wakatime** - Coding activity per project
- **📝 Google Docs** - Recently opened documents

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
Usage: main [OPTIONS]

  Personal Knowledge Management Tool.

  Fetches and formats data from various sources including: - Apple Calendar
  Agenda - GitHub - Atlassian (Jira/Confluence) - Things Logbook - Wakatime -
  Google Docs

Options:
  -d, --date TEXT               Date to fetch data for (default: today). Format:
                                YYYY-MM-DD or natural language.
  -f, --format [markdown|json]  Output format (default: markdown)
  -c, --config PATH             Path to configuration file
  --help                        Show this message and exit.
```

### Available Options

- **`-d, --date TEXT`**: Date to fetch data for (default: today). Format: YYYY-MM-DD or natural language.
- **`-f, --format [markdown|json]`**: Output format (default: markdown)
- **`-c, --config PATH`**: Path to configuration file
- **`--help`**: Show this message and exit.

<!-- CLI_USAGE_END -->

### Configuration

Copy the example configuration file:

```bash
cp config.example.yaml ~/.config/pkm-tool/config.yaml
```

Edit the configuration file to enable/disable sources and add credentials:

```yaml
github:
  enabled: true
  config:
    use_gh_cli: true  # Uses gh CLI for authentication

wakatime:
  enabled: true
  config:
    api_key: waka_your_api_key_here

atlassian:
  enabled: true
  config:
    base_url: https://your-domain.atlassian.net
    username: your.email@example.com
    api_token: your_api_token_here
```

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

# Run tests
uv run pytest

# Run type checking
uv run mypy src

# Run linting
uv run ruff check src
uv run ruff format src
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
