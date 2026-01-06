# Contributing to PKM Tool

Thank you for your interest in contributing to PKM Tool! This guide will help you get started with development.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Pull Requests](#pull-requests)
- [Project Structure](#project-structure)
- [Adding a New Data Source](#adding-a-new-data-source)

## Getting Started

### Prerequisites

- **Python 3.14+** (required)
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package installer (recommended)
- **Node.js 20+** (optional) - Required for commit message validation with commitlint
- **Make** - For running development commands

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/kakkoyun/pkm-tool.git
   cd pkm-tool
   ```

1. Install dependencies:

   ```bash
   make install
   ```

   This will:

   - Install Python dependencies using `uv`
   - Install Node.js dependencies for commitlint (if npm is available)

1. Install pre-commit hooks:

   ```bash
   make install-hooks
   ```

   This enables automatic code quality checks before each commit.

## Development Workflow

### Quick Commands

The project uses a comprehensive Makefile for development automation:

```bash
# Initial setup
make install && make install-hooks

# Before committing changes
make all                       # Run full pipeline (format, lint, typecheck, test)

# Individual checks
make format                    # Format all code (Python, YAML, Markdown, Shell)
make lint                      # Run all linters
make typecheck/python          # Type check with ty
make test                      # Run tests
make test/coverage             # Run tests with coverage report

# Auto-fix issues
make fix/python                # Format + auto-fix linting issues

# Check without modifications
make check                     # Run all checks (what CI runs)
```

### Making Changes

1. **Create a branch** for your changes:

   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

1. **Make your changes** following the [Code Standards](#code-standards)

1. **Run quality checks**:

   ```bash
   make all
   ```

1. **Commit your changes** using [Conventional Commits](#commit-message-format)

1. **Push and create a Pull Request**:

   ```bash
   git push -u origin your-branch-name
   ```

## Code Standards

### Code Quality Tools

All tools are accessed via **Makefile targets**. Never call tools directly.

- **ruff** - Fast Python linter and formatter (via `make format` / `make lint`)
- **ty** - Astral's type checker (via `make typecheck/python`)
- **yamllint** - YAML file linting (via `make lint/yaml`)
- **markdownlint** - Markdown file linting (via `make lint/markdown`)
- **shellcheck** - Shell script linting (via `make lint/shell`)
- **actionlint** - GitHub Actions workflow linting (via `make lint/actions`)

**Why use Makefile?**

- Ensures consistency across all environments
- Provides proper flags and configuration
- Makes it easy to update tool versions or configurations
- Single source of truth for all commands

### Python Style Guide

- **Line length**: 100 characters
- **Type hints**: All functions must have full type hints
- **Import order**: stdlib → third-party → local (enforced by ruff)
- **Python version**: 3.14+ with modern syntax (`list[str]`, `dict[str, Any]`, `str | None`)
- **Docstrings**: Not required but encouraged for complex functions
- **Comments**: Explain WHY, not WHAT or HOW

### Commit Message Format

This project uses [Conventional Commits](https://www.conventionalcommits.org/) v1.0.0:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types

- `feat` - New feature (MINOR version bump)
- `fix` - Bug fix (PATCH version bump)
- `docs` - Documentation only
- `style` - Code style (formatting, whitespace)
- `refactor` - Code changes (neither fix nor feature)
- `perf` - Performance improvements (PATCH version bump)
- `test` - Adding or updating tests
- `build` - Build system or dependencies
- `ci` - CI/CD configuration changes
- `chore` - Maintenance tasks, tooling

#### Examples

```bash
# Simple commit
git commit -m "docs: correct spelling of CHANGELOG"

# With scope
git commit -m "feat(auth): add login form component"

# With body
git commit -m "fix(parser): handle null values in date parsing

Previously null dates would cause parser to crash.
Now returns default date value instead.

Fixes #456"

# Breaking change
git commit -m "feat(api)!: redesign authentication flow

BREAKING CHANGE: API now requires Authorization header"
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit` and include:

- **ruff** - Format and lint Python code
- **ty** - Type checking
- **shellcheck** - Shell script linting
- **actionlint** - GitHub Actions linting
- **yamllint** - YAML linting
- **mdformat** - Markdown formatting
- **checkmake** - Makefile linting
- **commitlint** - Commit message validation

If a check fails, the commit is blocked. Fix the issues and try again.

## Testing

### Test Organization

```text
tests/
├── __snapshots__/         # Auto-generated snapshot files
├── fixtures/              # Reusable test fixtures
├── conftest.py            # Shared pytest configuration
├── test_cli.py            # CLI snapshot and unit tests
├── test_integration.py    # End-to-end integration tests
├── test_models.py         # Data model tests
├── test_config.py         # Configuration tests
└── test_formatters.py     # Output formatter tests
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage report
make test/coverage

# Run tests in parallel (for large test suites)
make test/parallel

# Show timing for all tests
make test/timing

# Update snapshots after intentional changes
# Note: No Makefile target exists for this. Use directly when needed:
# uv run pytest --snapshot-update
```

**Note on direct tool usage:** According to project policy, prefer Makefile targets
for all standard workflows. For advanced scenarios not covered by Makefile targets
(like updating snapshots), you may invoke tools directly, but avoid documenting
these as primary workflows.

### Writing Tests

- **Models**: Test Pydantic validation, defaults, field requirements
- **Config**: Test YAML loading, defaults, file discovery
- **Formatters**: Test Markdown structure, sorting, error display
- **Integration**: Mock external APIs with `pytest-mock`, `respx`, `responses`

### Coverage Requirements

- **Minimum coverage**: 80% (enforced by CI)
- **Current coverage**: 88% (see CI reports)

Add tests for new features to maintain or improve coverage.

## Pull Requests

### Before Submitting

1. **Run all checks locally**:

   ```bash
   make all
   ```

1. **Update documentation** if needed:

   - README.md for user-facing changes
   - CLAUDE.md for AI agent context
   - This CONTRIBUTING.md for development changes

1. **Add tests** for new features

1. **Update CHANGELOG** (if applicable)

### PR Guidelines

- **Title**: Use Conventional Commit format (`feat: add new feature`)
- **Description**: Explain what and why, not how
- **Link issues**: Reference related issues with `Fixes #123`
- **Keep PRs focused**: One feature/fix per PR
- **Respond to feedback**: Address review comments promptly

### CI Checks

All PRs must pass:

- ✅ Python linting (ruff)
- ✅ Type checking (ty)
- ✅ Tests (pytest)
- ✅ Coverage (≥80%)
- ✅ Commit message validation (commitlint)
- ✅ Markdown/YAML linting

## Project Structure

```text
pkm-tool/
├── src/pkm_tool/
│   ├── cli.py              # CLI entry point
│   ├── config.py           # Configuration management
│   ├── models.py           # Pydantic data models
│   ├── aggregator.py       # Data aggregation logic
│   ├── formatters.py       # Output formatters (Markdown/JSON)
│   ├── auth/               # Authentication system
│   │   ├── manager.py      # Central auth orchestration
│   │   ├── token_store.py  # Encrypted token storage
│   │   └── oauth/          # OAuth2 providers
│   ├── sources/            # Data source integrations
│   │   ├── apple_calendar.py
│   │   ├── github.py
│   │   ├── atlassian.py
│   │   ├── things.py
│   │   ├── wakatime.py
│   │   ├── google_docs.py
│   │   └── whoop.py
│   ├── server/             # FastAPI web server
│   └── mcp_server/         # Model Context Protocol server
├── tests/                  # Test files
├── .config/                # Tool configurations
├── .github/                # GitHub Actions workflows
├── pyproject.toml          # Project configuration
├── Makefile                # Development automation
├── README.md               # User documentation
├── CONTRIBUTING.md         # This file
└── CLAUDE.md               # AI agent context
```

### Key Design Patterns

#### Source Architecture

All data sources follow a consistent interface:

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

**Key characteristics:**

- Return empty list on failure (never raise)
- Graceful degradation
- Platform detection (macOS-specific sources)
- Multiple auth methods

#### Error Handling

- **Never crash the aggregator**: Each source handles its own errors
- **Empty list on failure**: Sources return `[]` rather than raising
- **Error metadata**: Capture error messages in `AggregatedData.metadata`
- **User visibility**: Display errors in formatted output

#### Configuration

- **YAML-based** with sensible defaults
- **Per-source configuration**: Enable/disable independently
- **Environment variable fallback**: API keys can come from env vars
- **Optional authentication**: Some sources work without auth

## Adding a New Data Source

Follow these steps to add a new data source:

### 1. Create Model

In `src/pkm_tool/models.py`:

```python
class NewSourceItem(BaseModel):
    title: str
    timestamp: datetime
    # ... other fields
```

### 2. Update AggregatedData

In `src/pkm_tool/models.py`:

```python
class AggregatedData(BaseModel):
    # ... existing fields
    new_source_items: list[NewSourceItem] = Field(default_factory=list)
```

### 3. Create Source Module

Create `src/pkm_tool/sources/new_source.py`:

```python
def fetch_new_source_items(
    target_date: date, config: dict[str, Any]
) -> list[NewSourceItem]:
    """
    Fetch items from new source.

    Args:
        target_date: Date to fetch data for
        config: Configuration dictionary

    Returns:
        List of NewSourceItem objects, empty on failure
    """
    try:
        # Implementation here
        return items
    except Exception as e:
        logger.error("failed_to_fetch_new_source", error=str(e))
        return []
```

### 4. Add to Aggregator

In `src/pkm_tool/aggregator.py`:

```python
if config.new_source.enabled:
    try:
        data.new_source_items = fetch_new_source_items(
            target_date, config.new_source.config
        )
    except Exception as e:
        data.metadata["new_source_error"] = str(e)
```

### 5. Add to Config

In `src/pkm_tool/config.py`:

```python
class Config(BaseModel):
    # ... existing sources
    new_source: SourceConfig = Field(default_factory=SourceConfig)
```

### 6. Update Formatters

In `src/pkm_tool/formatters.py`:

- Add Markdown section for the new source
- JSON formatter will automatically include it via Pydantic

### 7. Add CLI Subcommand

In `src/pkm_tool/cli.py`:

- Add a new subcommand for fetching only from the new source

### 8. Write Tests

In `tests/test_models.py`:

- Test model validation
- Test defaults and field requirements

Create `tests/fixtures/new_source_fixtures.py` if needed for mock data.

## Maintaining the Makefile

The Makefile is the **single source of truth** for all development commands. When adding new tools or workflows:

### Adding New Targets

1. **Choose the right section** (see Makefile comments for 9 organized sections)
1. **Add documentation** with `##` comment for `make help`
1. **Test the target** locally before committing
1. **Update documentation** if the target is user-facing

Example:

```makefile
# In appropriate section
lint/newtool: ## Check code with newtool
    @echo "Running newtool..."
    uv run newtool check src tests
```

### Guidelines

- **Never bypass Makefile** - All quality checks must go through `make` targets
- **Use `.PHONY`** for targets that don't create files
- **Check tool availability** before running (see existing targets for examples)
- **Provide helpful output** using `@echo` for user feedback
- **Keep targets composable** - allow combining multiple targets (e.g., `make format lint`)
- **Update `make help`** - Ensure all targets have documentation

### Testing Changes

```bash
# Test individual targets
make lint/newtool

# Test combined targets
make all

# Verify help output
make help
```

## Additional Resources

- [Project README](README.md) - User documentation
- [CLAUDE.md](CLAUDE.md) - Comprehensive technical documentation for AI agents
- [GitHub Issues](https://github.com/kakkoyun/pkm-tool/issues) - Report bugs or request features
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit message specification

## Questions?

If you have questions or need help, please:

1. Check existing documentation
1. Search [GitHub Issues](https://github.com/kakkoyun/pkm-tool/issues)
1. Open a new issue for discussion

Thank you for contributing! 🎉
