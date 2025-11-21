# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

KEEP THIS FILE UP TO DATE! (Add the end of each plan)!
WHEN USER WORKS WITH A NEW FLOW!

## Coding Standards and Principles

- ACT LIKE A PROFESSIONAL EXPERIENCED SOFTWARE ENGINEER!
- Be pedantic about code quality and consistency
- Be consitent!
- Use debug logs to understand the code and the data flow
- Add inline comments on WHY? instead of WHAT? and HOW?
- Always writes tests!
- Add well-described TODO comments whe you want to cut corners or when you want to come back to a task later
- NEVER CALL SOMETHING DONE without VALIDATING!
- Never write code to JUST make the tests pass, write the tests first!

## Quick Commands

### Makefile (Preferred)

Professional-grade development automation with 10 organized sections:

```bash
# 1. Development Setup
make install                   # Install with dev dependencies
make install-hooks             # Install pre-commit hooks

# 2. Testing
make test                      # Run all tests
make test-verbose              # Run tests with verbose output
make test-cov                  # Run tests with coverage

# 3. Code Quality - Python
make format                    # Format Python code (modifies files)
make format-check              # Check formatting without modifying
make lint                      # Run Python linting (ruff)
make lint-fix                  # Auto-fix Python linting issues
make typecheck                 # Type check with ty

# 4. Code Quality - Other Languages
make lint-shell                # Lint shell scripts (shellcheck)
make lint-actions              # Lint GitHub Actions (actionlint)
make lint-yaml                 # Lint YAML files (yamllint)
make lint-markdown             # Lint markdown files (mdformat)

# 5. Combined Quality Checks
make lint-all                  # Run ALL linters (Python + shell + actions + yaml + markdown)
make check-all                 # Run all checks without modifying (format-check + lint-all + typecheck)

# 6. Pre-commit Integration
make pre-commit                # Run pre-commit (all quality checks)
                               # Includes: ruff, ty, shellcheck, actionlint, yamllint, mdformat

# 7. Documentation
make docs                      # Generate CLI documentation

# 8. Utilities
make clean                     # Clean caches and build artifacts
make clean-all                 # Deep clean (includes venv)

# 9. Combined Workflows
make all                       # Full pipeline: format → lint-all → typecheck → test
make ci                        # CI pipeline: check-all → test (non-modifying)

# 10. Help
make help                      # Display comprehensive help with sections
```

**Common Workflows:**

```bash
# Initial setup
make install && make install-hooks

# Before commit
make all

# CI simulation (what GitHub Actions runs)
make ci

# Quick check without modifications
make check-all
```

### Running the tool

```bash
uv run pkm                     # Today's report (Markdown)
uv run pkm --date yesterday    # Specific date
uv run pkm --format json       # JSON output
pkm --config /path/config.yaml # Custom config
```

### Direct uv commands (reference)

```bash
# Development setup
uv sync --all-extras           # Install with dev dependencies

# Testing
uv run pytest                  # Run all tests
uv run pytest -v               # Verbose test output
uv run pytest tests/test_*.py  # Run specific test file
uv run pytest --cov            # With coverage

# Code quality
uv run ty src                  # Type checking (Astral's ty)
uv run ruff check src tests    # Linting
uv run ruff format src tests   # Auto-formatting
uv run ruff check --fix src tests # Auto-fix lint issues
```

## Architecture Overview

### High-Level Design

```
CLI Entry (cli.py)
    ↓
Aggregator (aggregator.py) ← Config (config.py)
    ↓
Sources (sources/*.py) → Models (models.py)
    ↓
Formatters (formatters.py)
    ↓
Output (Markdown/JSON)
```

The tool follows a clean, modular architecture:

1. **CLI Layer**: Click-based interface handles user input and date parsing
1. **Aggregator**: Orchestrates data collection from all enabled sources
1. **Sources**: Independent plugins for each data provider
1. **Models**: Pydantic models ensure type safety and validation
1. **Formatters**: Transform aggregated data into output formats

### Core Components

#### Models (`models.py`)

- **Pydantic-based data models** with strict typing and validation
- **Event**: Calendar events with title, start/end times, location, description
- **GitHubActivity**: Commits, PRs, issues, reviews with repository context
- **AtlassianItem**: Jira issues and Confluence pages with status tracking
- **ThingsTask**: Completed tasks with projects and tags
- **WakatimeActivity**: Coding time per project and language
- **GoogleDoc**: Recently opened documents
- **AggregatedData**: Container for all source data + metadata (including errors)

#### Configuration (`config.py`)

- **YAML-based configuration** with sensible defaults
- **Per-source configuration**: Each source can be enabled/disabled independently
- **Default config locations**:
  - `~/.config/pkm-tool/config.yaml` (preferred)
  - `~/.pkm-tool.yaml`
  - `./pkm-tool.yaml` (project directory)
- **SourceConfig pattern**: Consistent structure across all sources

#### Aggregator (`aggregator.py`)

- **Central coordination** of all data sources
- **Graceful error handling**: Each source fails independently, errors stored in metadata
- **No cascading failures**: One broken source doesn't affect others
- **Config-driven execution**: Only enabled sources are queried

#### Formatters (`formatters.py`)

- **Markdown formatter**: Human-readable daily reports with emojis and structure
- **JSON formatter**: Machine-readable output (uses Pydantic's `model_dump_json`)
- **Sorted outputs**: Events sorted by time for better readability
- **Error reporting**: Displays any source errors at the end of reports

### Source Architecture Pattern

All sources follow a consistent interface pattern:

```python
def fetch_*_activities(target_date: date, config: dict[str, Any]) -> list[Model]:
    """
    Standard source interface.

    Args:
        target_date: Date to fetch data for
        config: Configuration dictionary (from YAML)

    Returns:
        List of typed model objects (never None, empty list on failure)
    """
```

**Key source characteristics:**

- **Platform detection**: macOS-specific sources check platform first
- **Multiple auth methods**: Prefer CLI tools (gh, osascript) over direct API access
- **Graceful degradation**: Return empty list on any error, never raise
- **Date filtering**: Query broader range, filter results by exact date
- **Error suppression**: Catch all exceptions to prevent cascading failures

#### GitHub Source (`sources/github.py`)

- **Dual authentication**: gh CLI (preferred) or Personal Access Token
- **Event types**: PushEvent, PullRequestEvent, IssuesEvent, PullRequestReviewEvent
- **Date filtering**: Fetches recent events, filters by target date
- **Username detection**: Auto-detect from gh CLI if not configured

#### Apple Calendar (`sources/apple_calendar.py`)

- **macOS only**: Uses AppleScript via `osascript` command
- **Platform check**: Detects macOS via `uname` command
- **Cross-calendar**: Queries all calendars in Calendar.app

#### Things (`sources/things.py`)

- **macOS only**: Direct SQLite database access
- **Database path**: `~/Library/Group Containers/JLMPQHK86H.com.culturedcode.ThingsMac/...`
- **Custom timestamp format**: Things uses seconds since 2001-01-01
- **Rich metadata**: Includes projects, tags, completion times
- **Read-only mode**: Opens database in read-only mode for safety

#### Wakatime (`sources/wakatime.py`)

- **REST API**: Uses Wakatime's summaries endpoint
- **Bearer token auth**: Requires Wakatime API key
- **Per-project aggregation**: Groups coding time by project
- **Language detection**: Best-effort language matching (API limitation)

#### Atlassian (`sources/atlassian.py`)

- **Dual integration**: Jira issues and Confluence pages
- **Basic auth**: Uses email + API token
- **Date filtering**: Queries items updated on target date
- **Status tracking**: Includes Jira issue status

#### Google Docs (`sources/google_docs.py`)

- **OAuth2 required**: Needs Google Drive API access token
- **Recently opened**: Fetches documents opened on target date
- **Document metadata**: Title, URL, opened time, document type

## Key Patterns & Conventions

### Type Hints

- **Strict typing**: All functions fully type-hinted
- **Python 3.14**: Latest Python version with modern syntax (`list[str]`, `dict[str, Any]`, `str | None`)
- **ty enforcement**: Astral's ty type checker required to pass CI (replaces mypy)
- **Pydantic validation**: Runtime type checking for data models

### Error Handling Philosophy

- **Never crash the aggregator**: Each source handles its own errors
- **Empty list on failure**: Sources return `[]` rather than raising
- **Error metadata**: Capture error messages in `AggregatedData.metadata`
- **User visibility**: Display errors in formatted output

### Configuration Design

- **Enable/disable per source**: Fine-grained control
- **Nested config**: Each source has its own config dictionary
- **Environment variable fallback**: API keys can come from env vars
- **Optional authentication**: Some sources work without auth (GitHub via gh CLI)

### Code Quality Standards

- **Line length**: 100 characters (ruff configured)
- **Import order**: Enforced by ruff (stdlib → third-party → local)
- **Type checking**: ty (Astral's type checker) for strict type validation
- **Linting rules**: E (errors), F (pyflakes), I (imports), N (naming), UP (pyupgrade), RUF (ruff)
- **Pre-commit hooks**: Automatic validation on commit (ruff, ty, file formatters)

## Development Workflow

### Adding a New Source

1. **Create model** in `models.py`:

   ```python
   class NewSourceItem(BaseModel):
       title: str
       timestamp: datetime
       # ... other fields
   ```

1. **Add to AggregatedData**:

   ```python
   class AggregatedData(BaseModel):
       # ...
       new_source_items: list[NewSourceItem] = Field(default_factory=list)
   ```

1. **Create source module** in `sources/new_source.py`:

   ```python
   def fetch_new_source_items(
       target_date: date, config: dict[str, Any]
   ) -> list[NewSourceItem]:
       # Implementation
       return []
   ```

1. **Add to aggregator** in `aggregator.py`:

   ```python
   if config.new_source.enabled:
       try:
           data.new_source_items = fetch_new_source_items(
               target_date, config.new_source.config
           )
       except Exception as e:
           data.metadata["new_source_error"] = str(e)
   ```

1. **Add to config** in `config.py`:

   ```python
   class Config(BaseModel):
       # ...
       new_source: SourceConfig = Field(default_factory=SourceConfig)
   ```

1. **Update formatters** in `formatters.py` (both Markdown and JSON)

1. **Write tests** in `tests/test_models.py` for the new model

### Testing Strategy

- **Models**: Test Pydantic validation, defaults, field requirements
- **Config**: Test YAML loading, defaults, file discovery
- **Formatters**: Test Markdown structure, sorting, error display
- **Sources**: Manual testing (no mocks by design, requires external services)

### Pre-Commit Checklist

```bash
make all                           # Run all quality checks (format, lint, typecheck, test)
# Or run individually:
make lint-fix                      # Auto-fix lint issues
make format                        # Format code
make typecheck                     # Type check
make test                          # Run tests
```

## Configuration Reference

### Authentication Methods

| Source         | Method      | Config Key          | Environment Variable |
| -------------- | ----------- | ------------------- | -------------------- |
| GitHub         | gh CLI      | `use_gh_cli: true`  | N/A                  |
| GitHub         | Token       | `token: ...`        | `GITHUB_TOKEN`       |
| Wakatime       | API Key     | `api_key: ...`      | `WAKATIME_API_KEY`   |
| Atlassian      | API Token   | `api_token: ...`    | N/A                  |
| Google Docs    | OAuth2      | `access_token: ...` | N/A                  |
| Apple Calendar | AppleScript | N/A                 | N/A (macOS only)     |
| Things         | SQLite      | N/A                 | N/A (macOS only)     |

## Dependencies

### Core Runtime

- **click**: CLI framework with decorators
- **python-dateutil**: Natural language date parsing
- **pydantic**: Data validation and serialization
- **rich**: Terminal formatting
- **httpx**: Modern HTTP client (async-ready)
- **pyyaml**: YAML configuration parsing

### Development

- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **ruff**: Fast Python linter and formatter (replaces black, flake8, isort)
- **ty**: Astral's fast type checker (replaces mypy)
- **pre-commit**: Git hook framework for code quality enforcement

### Build System

- **uv**: Fast Python package installer and resolver
- Python 3.14 required (set in `.python-version` as source of truth)

## Project Workflow Patterns

### Workbench Workflow for Multi-Task Initiatives

For complex initiatives with multiple related tasks, use the workbench structure:

1. **Create workbench directory**: `.workbench/[initiative-name]/`
1. **Create planning docs**:
   - `PLAN.md`: Detailed plan with task breakdown and subagent assignments
   - `PROGRESS.md`: Real-time progress tracking
1. **Execute with parallel subagents**: Launch multiple subagents for independent tasks
1. **Track progress**: Update PROGRESS.md as tasks complete
1. **Clean up**: Archive workbench when initiative is complete

**Example**: `.workbench/00-plumbing/` for infrastructure improvements

This workflow enables:

- Clear project organization and documentation
- Parallel execution of independent tasks
- Real-time progress visibility
- Historical record of decision-making

## CI/CD

### GitHub Actions

The project uses GitHub Actions for continuous integration:

- **Workflow**: `.github/workflows/ci.yml`
- **Triggers**: Push and pull requests to main/master
- **Python version**: 3.14
- **Commands**: Uses Makefile for consistency with local development
- **Checks**: `make all` (format, lint, typecheck, test)
- **Coverage**: Uploads to Codecov (optional failure)

Local development and CI use identical commands via the Makefile, ensuring consistency.

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`:

- **Setup**: `make pre-commit-install`
- **Manual run**: `make pre-commit`
- **Hooks**: ruff (lint + format), ty (type check), standard file checks

Pre-commit hooks catch issues before commit, reducing CI failures.
