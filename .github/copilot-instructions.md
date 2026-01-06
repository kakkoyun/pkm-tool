# GitHub Copilot Instructions for PKM Tool

This file provides coding standards and patterns for GitHub Copilot when working with this repository.

## Core Principles

- **Professional Engineering**: Write production-quality code with attention to detail
- **Type Safety**: All functions must have complete type hints
- **Error Handling**: Sources return empty lists on failure, never raise
- **Consistency**: Follow existing patterns and conventions
- **Testing**: Write tests for new features
- **Documentation**: Update docs for user-facing changes

## Code Standards

### Python Style

- **Python Version**: 3.14+ with modern syntax
- **Line Length**: 100 characters
- **Type Hints**: Required for all functions
  - Use `list[str]`, `dict[str, Any]`, `str | None` (modern Python syntax)
  - No `Optional[]` or `List[]` (use modern syntax)
- **Import Order**: stdlib → third-party → local (enforced by ruff)
- **Docstrings**: Optional but encouraged for complex functions
- **Comments**: Explain WHY, not WHAT or HOW

### Tools

All tools are accessed via **Makefile** or **pre-commit hooks**. Never call tools directly.

- **Formatter**: `make format` (not `ruff format`)
- **Linter**: `make lint` (not `ruff check`)
- **Type Checker**: `make typecheck/python` (not `ty check`)
- **All Checks**: `make all` or `make check`

**Direct tool access is discouraged** - always use Makefile targets to ensure consistency.

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new feature
fix: correct bug
docs: update documentation
test: add tests
refactor: restructure code
```

## Project Architecture

### Data Flow

```
CLI → Aggregator → Sources → Models → Formatters → Output
```

### Source Pattern

All data sources follow this interface:

```python
def fetch_*_activities(target_date: date, config: dict[str, Any]) -> list[Model]:
    """
    Fetch activities from source.

    Args:
        target_date: Date to fetch data for
        config: Configuration dictionary

    Returns:
        List of model objects (empty on failure, never None)
    """
    try:
        # Implementation
        return items
    except Exception as e:
        logger.error("fetch_failed", source="source_name", error=str(e))
        return []  # Always return empty list, never raise
```

### Key Patterns

#### Error Handling

```python
# ✅ Good: Return empty list on failure
def fetch_data(config: dict[str, Any]) -> list[Item]:
    try:
        return fetch_from_api(config)
    except Exception as e:
        logger.error("fetch_failed", error=str(e))
        return []


# ❌ Bad: Raising exceptions
def fetch_data(config: dict[str, Any]) -> list[Item]:
    response = requests.get(url)
    response.raise_for_status()  # Don't do this
    return parse_response(response)
```

#### Logging

Use structured logging with `structlog`:

```python
import structlog

logger = structlog.get_logger()

# ✅ Good: Structured logging
logger.info("fetching_data", source="github", date=str(date))
logger.error("fetch_failed", source="github", error=str(e))

# ❌ Bad: String formatting
logger.info(f"Fetching data from {source}")
```

#### Type Hints

```python
# ✅ Good: Modern Python 3.10+ syntax
def process_items(items: list[str]) -> dict[str, Any]:
    result: dict[str, list[str]] = {}
    return result


# ❌ Bad: Old-style typing
from typing import List, Dict, Optional


def process_items(items: List[str]) -> Dict[str, Any]:
    pass
```

#### Configuration

```python
# ✅ Good: Use config parameter
def fetch_data(target_date: date, config: dict[str, Any]) -> list[Item]:
    api_key = config.get("api_key") or os.getenv("API_KEY")
    return fetch_from_api(api_key, target_date)


# ❌ Bad: Hard-coded values
def fetch_data(target_date: date) -> list[Item]:
    api_key = "hardcoded_key"  # Don't do this
    return fetch_from_api(api_key, target_date)
```

## Common Tasks

### Adding a New Data Source

1. **Create model** in `src/pkm_tool/models.py`:

   ```python
   class NewSourceItem(BaseModel):
       title: str
       timestamp: datetime
       description: str | None = None
   ```

1. **Update AggregatedData** in `src/pkm_tool/models.py`:

   ```python
   class AggregatedData(BaseModel):
       # ... existing fields
       new_source_items: list[NewSourceItem] = Field(default_factory=list)
   ```

1. **Create source** in `src/pkm_tool/sources/new_source.py`:

   ```python
   def fetch_new_source_items(
       target_date: date, config: dict[str, Any]
   ) -> list[NewSourceItem]:
       try:
           # Implementation
           return items
       except Exception as e:
           logger.error("fetch_failed", source="new_source", error=str(e))
           return []
   ```

1. **Add to aggregator** in `src/pkm_tool/aggregator.py`

1. **Add to config** in `src/pkm_tool/config.py`

1. **Update formatters** in `src/pkm_tool/formatters.py`

1. **Write tests** in `tests/test_models.py`

### Testing

```python
# Use pytest with fixtures
def test_fetch_items(mock_api):
    items = fetch_items(date.today(), {"api_key": "test"})
    assert len(items) > 0
    assert items[0].title is not None


# Mock external APIs
@pytest.fixture
def mock_api(mocker):
    return mocker.patch("module.api_call", return_value={"data": []})
```

## File Organization

```
src/pkm_tool/
├── cli.py              # Click-based CLI
├── config.py           # YAML configuration
├── models.py           # Pydantic models
├── aggregator.py       # Orchestration
├── formatters.py       # Output formatting
├── auth/               # Authentication
│   ├── manager.py      # Auth orchestration
│   ├── token_store.py  # Encrypted storage
│   └── oauth/          # OAuth providers
└── sources/            # Data sources
    ├── github.py       # GitHub events
    ├── wakatime.py     # Coding time
    ├── things.py       # Things tasks
    └── ...             # Other sources
```

## Quality Checks

**Always use Makefile targets** - never call tools directly:

```bash
make all              # Format, lint, typecheck, test (full pipeline)
make check            # Run checks without modifying files
make fix/python       # Auto-fix formatting and linting
make test             # Run test suite
make format           # Format all code
make lint             # Run all linters
make typecheck/python # Type check with ty
```

**Maintaining the Makefile:**

- Keep Makefile up-to-date when adding new tools or workflows
- Add new targets for new quality checks
- Document all targets in `make help`
- Test targets locally before committing

## Dependencies

### Core

- **click** - CLI framework
- **pydantic** - Data validation
- **httpx** - HTTP client
- **structlog** - Structured logging
- **pyyaml** - Configuration

### Development

- **pytest** - Testing
- **ruff** - Linting and formatting
- **ty** - Type checking
- **pre-commit** - Git hooks

## References

- [README.md](../README.md) - User documentation
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guide
- [CLAUDE.md](../CLAUDE.md) - Comprehensive technical documentation
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit format
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [Click](https://click.palletsprojects.com/) - CLI framework
