# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

KEEP THIS FILE UP TO DATE! (Add the end of each plan)!
WHEN USER WORKS WITH A NEW FLOW!

MAKE SURE TO KEEP llm-tool.json UP TO DATE!

## Coding Standards and Principles

- ACT LIKE A PROFESSIONAL EXPERIENCED SOFTWARE ENGINEER!
- Be pedantic about code quality and consistency
- Be consitent!
- Use structured logging (structlog) extensively for troubleshooting
- Add inline comments on WHY? instead of WHAT? and HOW?
- Always writes tests!
- Add well-described TODO comments whe you want to cut corners or when you want to come back to a task later
- NEVER CALL SOMETHING DONE without VALIDATING!
- Never write code to JUST make the tests pass, write the tests first!
- Use conventional commits for all commits (see Version Control Workflow below)

## Version Control Workflow

### Conventional Commits

All commits MUST follow the [Conventional Commits v1.0.0](https://www.conventionalcommits.org/) specification.

#### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types

| Type       | Description                            | Semantic Version |
| ---------- | -------------------------------------- | ---------------- |
| `feat`     | New feature                            | MINOR            |
| `fix`      | Bug fix                                | PATCH            |
| `docs`     | Documentation only                     | -                |
| `style`    | Code style (formatting, whitespace)    | -                |
| `refactor` | Code changes (neither fix nor feature) | -                |
| `perf`     | Performance improvements               | PATCH            |
| `test`     | Adding or updating tests               | -                |
| `build`    | Build system or dependencies           | -                |
| `ci`       | CI/CD configuration changes            | -                |
| `chore`    | Maintenance tasks, tooling             | -                |

#### Scope

Scope provides context about the affected area (component, module, package):

```bash
feat(api): add user authentication endpoint
fix(parser): handle edge case in date parsing
docs(readme): update installation instructions
test(auth): add integration tests for login flow
```

#### Breaking Changes

Use `!` after type/scope OR add `BREAKING CHANGE:` footer:

```bash
# Method 1: Exclamation mark
feat!: remove deprecated API endpoints
feat(api)!: change authentication method

# Method 2: Footer
feat(config): change default port

BREAKING CHANGE: environment variables now take precedence over config files
```

Breaking changes trigger MAJOR version bump in semantic versioning.

#### Examples

**Simple commit:**

```bash
docs: correct spelling of CHANGELOG
```

**With scope:**

```bash
feat(lang): add Polish language support
```

**With body and footer:**

```bash
fix(parser): handle null values in date parsing

Previously null dates would cause parser to crash.
Now returns default date value instead.

Fixes #456
```

**Breaking change:**

```bash
feat(api): redesign authentication flow

Migrate from session-based to JWT authentication.
All existing sessions will be invalidated.

BREAKING CHANGE: API now requires Authorization header
Fixes #456
Reviewed-by: Alice Smith
```

#### Benefits

- Automated CHANGELOG generation
- Automatic semantic version determination
- Clear communication of changes to stakeholders
- Structured commit history for navigation
- Triggers for CI/CD processes

#### Validation

Commit messages are automatically validated using **commitlint**:

**Local validation (pre-commit hook):**

```bash
# Install pre-commit hooks (includes commitlint)
make tools/install-hooks

# Commits are automatically validated when you run git commit
git commit -m "feat(auth): add login"  # ✓ passes
git commit -m "Added login"            # ✗ fails
```

**Manual validation:**

```bash
# Check last commit message
make lint/commits

# Check a range of commits
make lint/commits/range FROM=abc123 TO=def456
```

**CI validation:**

- GitHub Actions automatically validates all commits in PRs
- See `.github/workflows/commitlint.yml` for CI configuration

**Configuration:**

- Commitlint config: `.commitlintrc.yaml`
- Pre-commit hook: `.pre-commit-config.yaml`
- Dependencies: `package.json` (Node.js packages)

### Git Workflow (Simple Features)

Use standard git workflow for simple, isolated features:

```bash
# Always start from main
git checkout main
git pull origin main

# Create feature branch
git checkout -b feat/add-login-form

# Make changes and commit with conventional commits
git add .
git commit -m "feat(auth): add login form component"

# Push and create PR
git push -u origin feat/add-login-form
gh pr create --title "feat(auth): Add login form component"
```

**When to use standard git:**

- Single PR suffices for the entire change
- Simple, isolated features or bug fixes
- No dependencies between changes
- Quick fixes or documentation updates

### Graphite (gt) Workflow for Stacked PRs

Use [Graphite CLI](https://graphite.dev/) for large features requiring multiple dependent PRs.

#### What are Stacked PRs?

Stacked PRs break large features into small, incremental changes built on top of each other.
Each PR can be tested, reviewed, and merged independently while maintaining development velocity.

**Benefits:**

- Continue building while waiting for reviews
- Smaller, more focused PRs (easier to review)
- Faster feedback cycles
- Reduced merge conflicts
- Better code organization

#### Installation

```bash
# Install Graphite CLI
npm install -g @withgraphite/graphite-cli@stable

# Or with homebrew
brew install graphite

# Initialize in repository
gt repo init

# Enable automatic conflict resolution
git config rerere.enabled true
```

#### Basic Commands

| Command                   | Git Equivalent                                      | Description                   |
| ------------------------- | --------------------------------------------------- | ----------------------------- |
| `gt create -am "message"` | `git branch` + `git checkout` + `git commit`        | Create branch with commit     |
| `gt modify -a`            | `git commit --fixup` + `git rebase -i --autosquash` | Amend current branch          |
| `gt sync`                 | `git checkout main` + `git pull` + `git merge main` | Sync all branches with remote |
| `gt restack`              | `git rebase` (manual)                               | Update stack after changes    |
| `gt log short` / `gt ls`  | Multiple `git log` commands                         | View stack structure          |
| `gt submit`               | `gh pr create`                                      | Create PR for current branch  |
| `gt submit --stack`       | Multiple `gh pr create`                             | Create PRs for entire stack   |

#### Creating a Stack

```bash
# Start from main
gt checkout main

# Create first branch in stack
gt create -am "feat(db): add user table schema"

# Create second branch stacked on top
gt create -am "feat(models): add User model"

# Create third branch
gt create -am "feat(api): add user endpoints"

# View your stack
gt log short
```

Output shows dependency structure:

```
● feat/user-endpoints (current)
● feat/user-model
● feat/user-schema
◯ main
```

#### Submitting Stack

```bash
# Submit entire stack as PRs
gt submit --stack

# Or submit current branch only
gt submit

# Open PR in browser
gt pr
```

#### Making Changes

```bash
# Amend changes to current branch
gt modify -a

# Add new commit to current branch
gt modify -cam "Address review feedback"

# Navigate to different branch in stack
gt checkout    # Interactive selection
```

#### Syncing and Restacking

```bash
# Sync all branches with remote
gt sync

# Restack after upstream changes
gt restack

# Fix conflicts incrementally
gt stack fix --one-at-a-time
```

#### When to Use Graphite

**Use gt for:**

- Large features spanning multiple PRs (>500 lines)
- Features with clear logical layers (DB → Models → API → UI)
- Work requiring async reviews (don't block on upstream PRs)
- Complex features with multiple reviewers
- Teams practicing trunk-based development

**Use standard git for:**

- Simple bug fixes (\<100 lines)
- Documentation updates
- Single-component changes
- Quick hotfixes
- Features completed in single PR

#### Stacked PR Best Practices

1. **Structure Logically**

   - Each PR represents one logical unit
   - Clear dependencies: `Schema → Models → Repositories → Services → API`
   - Bottom layer = foundational, top layer = user-facing

1. **Keep PRs Small**

   - Target 200-400 lines per PR
   - One concern per PR (easier to review)
   - Better test coverage per layer

1. **Use Conventional Commits**

   ```bash
   gt create -am "feat(db): add user authentication schema"
   gt create -am "feat(models): implement User model with validation"
   gt create -am "feat(api): add /auth/login endpoint"
   gt create -am "test(auth): add integration tests for auth flow"
   ```

1. **Review Strategy**

   - Review PRs bottom-to-top (foundation first)
   - Each PR reviewable independently
   - Provide timely feedback to avoid blocking downstream work

1. **Merge Patterns**

   - PRs can merge in any order when ready
   - `gt sync` handles automatic rebasing
   - Middle PRs merging first is supported
   - Graphite restacks remaining PRs automatically

1. **Conflict Management**

   ```bash
   # Enable rerere (reuse recorded resolution)
   git config rerere.enabled true

   # Fix conflicts one branch at a time
   gt stack fix --one-at-a-time
   ```

#### Complete Workflow Example

```bash
# 1. Initialize
gt checkout main
git config rerere.enabled true

# 2. Create stack for authentication feature
gt create -am "feat(db): add users table and auth schema"
gt create -am "feat(models): implement User and Token models"
gt create -am "feat(services): add authentication service"
gt create -am "feat(api): add /auth/login and /auth/register endpoints"
gt create -am "feat(frontend): add login form component"
gt create -am "test(auth): add end-to-end auth tests"

# 3. View stack structure
gt log short

# 4. Submit all as PRs
gt submit --stack

# 5. Address review feedback on services layer
gt checkout feat/auth-service
# Make changes
gt modify -a
gt sync    # Updates dependent PRs automatically

# 6. Continue work while PRs are in review
# (Already on top of stack, keep building)

# 7. As PRs merge, sync periodically
gt sync    # Rebases remaining PRs on merged work
```

#### GitHub Integration

- PRs created with stack context automatically
- Stack visualization in Graphite web interface
- Works with GitHub branch protection rules
- Integrates with GitHub Actions and status checks
- Supports GitHub merge queue

### Command Reference

#### Quick Comparison

**Create feature branch with first commit:**

```bash
# Git
git checkout -b feat/new-feature
git commit -m "feat: initial implementation"

# Graphite
gt create -am "feat: initial implementation"
```

**Add more work on feature:**

```bash
# Git
git add .
git commit -m "feat: additional work"

# Graphite (creates new branch on stack)
gt create -am "feat: additional work"
```

**Update after review feedback:**

```bash
# Git
git add .
git commit --amend

# Graphite
gt modify -a
```

**Sync with main:**

```bash
# Git
git checkout main
git pull
git checkout feat/new-feature
git merge main

# Graphite
gt sync
```

#### Common Workflows

**Simple feature (use git):**

```bash
git checkout main && git pull
git checkout -b fix/typo-in-readme
git commit -am "docs: fix typo in README"
git push -u origin fix/typo-in-readme
gh pr create
```

**Large feature (use gt):**

```bash
gt checkout main
gt create -am "feat(db): add schema"
gt create -am "feat(api): add endpoints"
gt create -am "test: add integration tests"
gt submit --stack
```

**Emergency hotfix (use git):**

```bash
git checkout main && git pull
git checkout -b hotfix/critical-bug
git commit -am "fix: critical production bug"
git push -u origin hotfix/critical-bug
gh pr create --title "HOTFIX: Critical production bug"
```

## Quick Commands

### Makefile (Preferred)

Professional-grade development automation with 9 organized sections:

```bash
# 1. Development Setup
make install                   # Install with dev dependencies
make install/dev               # Install with dev dependencies (alias)
make install-hooks             # Install pre-commit hooks
make update                    # Update dev tooling (pre-commit hooks, dependencies)

# 2. Testing
make test                      # Run all tests (verbose)
make test/parallel             # Run tests in parallel (only useful for slow/large suites >30s)
make test/coverage             # Run tests with coverage report (HTML + terminal)
make test/timing               # Show timing for all tests
make test/slow                 # Show only slow tests (>1s)

# 3. Code Quality
make format                    # Format all code (Python, YAML, Markdown, Shell)
make format/python             # Format Python code with ruff
make format/python/check       # Check Python formatting without modifying
make format/yaml               # Format YAML files with yamlfmt
make format/markdown           # Format Markdown files with mdformat
make format/shell              # Format shell scripts with shfmt

make lint                      # Run all linters (Python, shell, actions, YAML, markdown)
make lint/python               # Run Python linter (ruff)
make lint/python/fix           # Auto-fix Python linting issues
make lint/shell                # Lint shell scripts (shellcheck)
make lint/actions              # Lint GitHub Actions (actionlint)
make lint/yaml                 # Lint YAML files (yamllint)
make lint/markdown             # Lint Markdown files (markdownlint)
make lint/markdown/fix         # Lint and fix Markdown files
make lint/makefile             # Lint Makefile (checkmake)
make lint/commits              # Check last commit message with commitlint
make lint/commits/range        # Check commit message range (FROM=<sha> TO=<sha>)

make typecheck/python          # Type check with ty
make check                     # Run all checks without modifying (lint + format/python/check + typecheck)
make fix/python                # Auto-fix all fixable issues (format + lint --fix)

# 4. Pre-commit Integration
make pre-commit                # Run pre-commit on all files
                               # Includes: ruff, ty, shellcheck, actionlint, yamllint, mdformat,
                               # checkmake, commitlint (on commit-msg hook)
make pre-commit/install        # Alias for install-hooks

# 5. GitHub Actions Pinning (Ratchet)
make ratchet                   # Install ratchet if not present
make ratchet/pin               # Pin GitHub Actions to commit SHAs
make ratchet/update            # Update pinned GitHub Actions to latest versions
make ratchet/check             # Verify all GitHub Actions are pinned

# 6. Documentation
make docs                      # Generate CLI documentation

# 7. Utilities
make shfmt                     # Install shfmt if not present
make yamlfmt                   # Install yamlfmt if not present
make clean                     # Clean caches and build artifacts
make clean/all                 # Deep clean (includes venv)

# 8. Combined Workflows
make all                       # Full pipeline: format → lint → typecheck → test
make ci                        # CI pipeline: check → test (what GitHub Actions runs)

# 9. Help
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
make check

# Auto-fix Python issues
make fix/python
```

### Running the tool

The tool provides a main command with subcommands for each datasource.

#### Single-day reports (to stdout)

```bash
uv run pkm                           # Today's report, all sources (Markdown)
uv run pkm --date yesterday          # Specific date, all sources
uv run pkm --format json             # JSON output, all sources
uv run pkm --config /path/config.yaml --date 2025-11-21  # Custom config
uv run pkm aggregate --date yesterday # Explicit aggregate subcommand (preferred)
uv run pkm mcp                       # Run as MCP server (Model Context Protocol)
```

#### Date range reports (Phase 2 - to files)

Generate reports for multiple days, each in a separate file:

```bash
# Generate reports for a week
uv run pkm --from 2025-11-17 --to 2025-11-23

# Skip weekends globally
uv run pkm --from 2025-11-17 --to 2025-11-23 --exclude-weekends

# Custom output directory (overrides config)
uv run pkm --from 2025-11-17 --to 2025-11-23 -o ~/Documents/daily-notes/

# Date ranges work with all subcommands
uv run pkm github --from 2025-11-17 --to 2025-11-23
uv run pkm wakatime --from 2025-11-17 --to 2025-11-23 --exclude-weekends
```

**Key behaviors**:

- `--date` outputs to stdout (existing behavior)
- `--from`/`--to` writes files to disk (batch mode)
- Files use configurable template: `{date} ({day_abbr}).{format}` (default)
- Existing files are intelligently merged (PKM sections updated, manual content preserved)

#### Individual datasource subcommands

Fetch data from specific sources only:

```bash
# Single-day mode (stdout)
uv run pkm github --date yesterday       # GitHub activities only
uv run pkm things --date yesterday       # Things tasks only
uv run pkm wakatime --date yesterday     # Wakatime coding time only
uv run pkm atlassian --date yesterday    # Atlassian (Jira + Confluence) only
uv run pkm calendar --date yesterday     # Apple Calendar events only
uv run pkm google-docs --date yesterday  # Google Docs only
uv run pkm whoop --date yesterday        # Whoop health data only

# Batch mode (files) - Phase 2
uv run pkm github --from 2025-11-17 --to 2025-11-23 -o ~/notes/
uv run pkm wakatime --from 2025-11-17 --to 2025-11-23 --exclude-weekends

# With format and config options
uv run pkm github --format json --date yesterday
uv run pkm wakatime --config ~/.config/pkm-tool/config.yaml --date 2025-11-21
```

#### Server mode

Run as a web server with REST API:

```bash
# Start server on default port (8000)
uv run pkm server

# Start on custom port with auto-reload
uv run pkm server --port 8080 --reload

# Start with verbose logging
uv run pkm server --verbose

# The server provides:
# - REST API at http://127.0.0.1:8000/api/*
# - Interactive API docs at http://127.0.0.1:8000/docs
# - Health check at http://127.0.0.1:8000/health
```

**Server dependencies** (optional):

```bash
# Install server dependencies
uv sync --extra server
```

#### MCP mode

Run as an MCP (Model Context Protocol) server for AI assistants:

```bash
# Start MCP server (stdio mode)
uv run pkm mcp

# The MCP server exposes tools that AI assistants can use:
# - fetch_aggregated_data: Get data from all sources
# - fetch_calendar_events: Get Apple Calendar events
# - fetch_github_activities: Get GitHub activities
# - fetch_atlassian_items: Get Atlassian items
# - fetch_things_tasks: Get Things tasks
# - fetch_wakatime_activities: Get Wakatime activities
# - fetch_google_docs: Get Google Docs
# - fetch_whoop_data: Get Whoop health data
```

**MCP dependencies** (optional):

```bash
# Install MCP dependencies
uv sync --extra mcp
```

**Claude Desktop Integration:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

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

## Project Structure

### Tool Configuration Organization

Project-level tool configurations are organized in the `.config/` directory for cleaner repository structure:

```
.config/
├── yamllint.yaml          # YAML linting configuration
├── yamlfmt.yaml           # YAML formatting configuration
├── markdownlint.json      # Markdown linting configuration
└── markdownlintignore     # Markdown linting ignore patterns
```

**Files at root** (required by tools):

- `.gitignore` - Git requires at root
- `.python-version` - pyenv/uv expect at root
- `.pre-commit-config.yaml` - pre-commit requires at root

All Makefile targets and pre-commit hooks reference configs from `.config/` directory.

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
- **WhoopRecovery**: Recovery score, HRV, resting heart rate, SpO2
- **WhoopSleep**: Sleep cycles with stages, efficiency, duration
- **WhoopWorkout**: Workout activities with strain, duration, heart rate
- **AggregatedData**: Container for all source data + metadata (including errors)

#### Configuration (`config.py`)

- **YAML-based configuration** with sensible defaults
- **Per-source configuration**: Each source can be enabled/disabled independently
- **Weekend exclusion**: Global and per-source configuration (Phase 2)
- **Output settings**: Filename template and directory (Phase 2)
- **Default config locations**:
  - `~/.config/pkm-tool/config.yaml` (preferred)
  - `~/.pkm-tool.yaml`
  - `./pkm-tool.yaml` (project directory)
- **SourceConfig pattern**: Consistent structure across all sources
  - `enabled: bool` - Enable/disable source
  - `exclude_weekends: bool` - Skip source on weekends (Phase 2)
  - `config: dict` - Source-specific settings

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
- **Filename templating**: Generate filenames with date variables (Phase 2)
- **Smart file merging**: Update existing files while preserving manual content (Phase 2)
  - Parse existing markdown to extract PKM sections
  - Identify section types (flexible, case-insensitive matching)
  - Merge: preserve preamble/postamble, update PKM sections, append new sections
  - Allows mixing automated data with personal journaling

### Authentication Architecture

- **Token storage**: Encrypted SQLite database at `~/.pkm-tool/tokens.db` using `cryptography.fernet`.
  - Encryption key derived from machine identifier + home directory path.
  - Stores `token`, `refresh_token`, `expires_at`, and `token_type` per source.
- **Auth Manager** (`auth/manager.py`):
  - Central orchestration for token loading, auto-refresh, and interactive login flows.
  - Automatically refreshes OAuth tokens when they are within 5 minutes of expiry.
  - Provides helper APIs for API keys / PATs and OAuth responses.
- **OAuth providers** (`auth/oauth/`):
  - Base protocol plus Google implementation using the OAuth2 device code flow.
  - Device code avoids running a local callback server; works in headless shells.
- **CLI integration** (`pkm auth ...`):
  - `pkm auth list/status/login/logout/refresh` manages credentials with encrypted storage.
  - Google Docs login requires `client_id`/`client_secret` in config; other sources prompt for tokens.
- **Fallback support**:
  - When no stored credentials exist, sources fall back to values from config or environment variables.

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

#### Whoop (`sources/whoop.py`)

- **OAuth2 required**: Needs Whoop API access token
- **Authentication**: `pkm auth login whoop` securely stores the token (fallback to config/env)
- **Three data types**: Recovery (single per day), Sleep cycles (multiple), Workouts (multiple)
- **Recovery metrics**: Recovery score, HRV, resting heart rate, SpO2, skin temperature
- **Sleep tracking**: Sleep stages (deep/light/REM/awake), efficiency, disturbances
- **Workout data**: Sport type, strain score, duration, heart rate zones, calories

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
make fix/python                    # Auto-fix Python issues (format + lint --fix)
make format                        # Format all code
make typecheck/python              # Type check
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
| Whoop          | OAuth2      | `access_token: ...` | `WHOOP_ACCESS_TOKEN` |
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
- **commitlint** (Node.js): Validates commit messages against Conventional Commits spec

### Build System

- **uv**: Fast Python package installer and resolver
- Python 3.14 required (set in `.python-version` as source of truth)
- **Node.js 20+** (optional): Required for commitlint commit message validation

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

**Main CI Workflow:**

- **Workflow**: `.github/workflows/ci.yml`
- **Triggers**: Push and pull requests to main/master
- **Python version**: 3.14
- **Commands**: Uses Makefile for consistency with local development
- **Checks**: `make ci` (check, test with coverage)
- **Coverage**: Uploads to Codecov (optional failure)

**Commitlint Workflow:**

- **Workflow**: `.github/workflows/commitlint.yml`
- **Triggers**: Push and pull requests to main/master
- **Purpose**: Validates all commit messages follow Conventional Commits spec
- **Tool**: commitlint with @commitlint/config-conventional

Local development and CI use identical commands via the Makefile, ensuring consistency.

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`:

- **Setup**: `make install-hooks` or `make pre-commit/install`
- **Manual run**: `make pre-commit`
- **Hooks**: ruff (lint + format), ty (type check), shellcheck, actionlint, yamllint,
  mdformat, checkmake, commitlint (commit-msg stage)

Pre-commit hooks catch issues before commit, reducing CI failures.
