# ============================================================================
# PKM Tool - Makefile
# ============================================================================
# Professional-grade development automation with comprehensive quality checks
#
# Quick Start:
#   make install        # Install dependencies
#   make all            # Run full pipeline (format, lint, typecheck, test)
#   make help           # Show all available targets

# Shell configuration
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# ============================================================================
# Section 1: Development Setup
# ============================================================================

.PHONY: install install/dev install-hooks update

install: ## Install dependencies with all extras
	uv sync --all-extras

install/dev: install install-hooks ## Install with dev dependencies (alias for install)

install-hooks: ## Install pre-commit hooks
	pre-commit install

update: ## Update dev tooling (pre-commit hooks, dependencies)
	pre-commit autoupdate
	uv sync --all-extras --upgrade

# ============================================================================
# Section 2: Testing
# ============================================================================

.PHONY: test test/coverage

test: ## Run all tests
	uv run pytest -v

test/coverage: ## Run tests with coverage report
	uv run pytest --cov --cov-report=term-missing --cov-report=html

# ============================================================================
# Section 3: Code Quality
# ============================================================================

.PHONY: format lint check format/python format/python/check format/yaml format/markdown format/shell typecheck/python
.PHONY: lint/python lint/python/fix lint/shell lint/actions lint/yaml lint/makefile
.PHONY: lint/markdown lint/markdown/fix

format: format/python format/yaml format/markdown format/shell ## Format all code (Python, YAML, Markdown, Shell)

format/python: ## Format Python code with ruff
	uv run ruff format src tests

format/python/check: ## Check Python formatting without modifying files
	uv run ruff format --check src tests

format/yaml: ## Format YAML files with yamlfmt
	@echo "Formatting YAML files..."
	@if command -v yamlfmt >/dev/null 2>&1; then \
		yamlfmt -conf .config/yamlfmt.yaml .; \
	else \
		echo "yamlfmt not available (install: go install github.com/google/yamlfmt/cmd/yamlfmt@latest)"; \
		echo "Using yamllint for checking only..."; \
		uv run yamllint -f colored -c .config/yamllint.yaml . ; \
	fi

format/markdown: ## Format Markdown files with mdformat
	@echo "Formatting Markdown files..."
	@pre-commit run mdformat --all-files

format/shell: ## Format shell scripts with shfmt
	@echo "Formatting shell scripts..."
	@if command -v shfmt >/dev/null 2>&1; then \
		echo "Running shfmt on shell scripts..."; \
		find . -name "*.sh" -not -path "./.venv/*" -not -path "./venv/*" -exec shfmt -i 2 -ci -w {} + ; \
	else \
		echo "shfmt not available (install: go install mvdan.cc/sh/v3/cmd/shfmt@latest), skipping"; \
	fi

lint: lint/python lint/shell lint/actions lint/yaml lint/markdown

lint/python: ## Run Python linter (ruff)
	uv run ruff check src tests

lint/python/fix: ## Auto-fix Python linting issues
	uv run ruff check --fix src tests

lint/markdown: ## Lint check Markdown files with markdownlint
	@echo "Linting Markdown files..."
	@if command -v npx >/dev/null 2>&1; then \
		npx --yes markdownlint-cli **/*.md --config .config/markdownlint.json ; \
	else \
		echo "npx not available, using pre-commit mdformat instead"; \
		pre-commit run mdformat --all-files ; \
	fi

lint/markdown/fix: ## Lint and fix Markdown files with markdownlint
	@echo "Linting and fixing Markdown files..."
	@if command -v npx >/dev/null 2>&1; then \
		npx --yes markdownlint-cli **/*.md --fix --config .config/markdownlint.json ; \
	else \
		echo "npx not available, using pre-commit mdformat instead"; \
		pre-commit run mdformat --all-files ; \
	fi

typecheck/python: ## Type check with ty
	uv run ty check

lint/shell: ## Check shell scripts with shellcheck
	@if command -v shellcheck >/dev/null 2>&1 || uv run shellcheck --version >/dev/null 2>&1; then \
		echo "Running shellcheck on shell scripts..."; \
		find . -name "*.sh" -not -path "./.venv/*" -not -path "./venv/*" -exec uv run shellcheck {} + ; \
	else \
		echo "shellcheck not available, skipping"; \
	fi

lint/actions: ## Check GitHub Actions workflows with actionlint
	@if command -v actionlint >/dev/null 2>&1 || uv run actionlint --version >/dev/null 2>&1; then \
		echo "Running actionlint on GitHub Actions workflows..."; \
		uv run actionlint ; \
	else \
		echo "actionlint not available, skipping"; \
	fi

lint/yaml: ## Check YAML files with yamllint
	@echo "Running yamllint on YAML files..."
	@uv run yamllint -f colored -c .config/yamllint.yaml .

lint/makefile: ## Check Makefile with checkmake
	@if command -v checkmake >/dev/null 2>&1; then \
		echo "Running checkmake on Makefile..."; \
		checkmake Makefile ; \
	else \
		echo "checkmake not available (install via pre-commit), skipping"; \
	fi

check: lint format/python/check typecheck/python ## Run all Python checks without modifying files

.PHONY: fix/python
fix/python: format/python lint/python/fix lint/markdown/fix ## Auto-fix all fixable issues (format + lint --fix)

# ============================================================================
# Section 4: Pre-commit Integration
# ============================================================================

.PHONY: pre-commit pre-commit/install

pre-commit: ## Run pre-commit on all files (ruff, ty, shellcheck, actionlint, yamllint, mdformat, checkmake)
	pre-commit run --all-files

pre-commit/install: install-hooks ## Alias for install-hooks

# ============================================================================
# Section 5: GitHub Actions Pinning (Ratchet)
# ============================================================================

.PHONY: ratchet ratchet/pin ratchet/update ratchet/check

ratchet: ## Install ratchet if not present
	@if ! command -v ratchet >/dev/null 2>&1; then \
		echo "Installing ratchet..."; \
		go install github.com/sethvargo/ratchet@latest || { \
			echo "Error: Failed to install ratchet. Ensure Go is installed."; \
			exit 1; \
		}; \
		echo "Ratchet installed successfully"; \
	else \
		echo "Ratchet is already installed at $$(command -v ratchet)"; \
	fi

ratchet/pin: ratchet ## Pin GitHub Actions to commit SHAs
	@echo "Pinning GitHub Actions to commit SHAs..."
	@find .github/workflows -name '*.yml' -o -name '*.yaml' | xargs ratchet pin

ratchet/update: ratchet ## Update pinned GitHub Actions to latest versions
	@echo "Updating pinned GitHub Actions to latest versions..."
	@find .github/workflows -name '*.yml' -o -name '*.yaml' | xargs ratchet update

ratchet/check: ratchet ## Verify all GitHub Actions are pinned
	@echo "Checking GitHub Actions are pinned..."
	@find .github/workflows -name '*.yml' -o -name '*.yaml' | xargs ratchet lint

# ============================================================================
# Section 6: Documentation
# ============================================================================

.PHONY: docs

docs: ## Generate CLI documentation
	uv run python scripts/generate_cli_docs.py

# ============================================================================
# Section 7: Utilities
# ============================================================================

.PHONY: clean clean/all shfmt yamlfmt

shfmt: ## Install shfmt if not present
	@if ! command -v shfmt >/dev/null 2>&1; then \
		echo "Installing shfmt..."; \
		go install mvdan.cc/sh/v3/cmd/shfmt@latest || { \
			echo "Error: Failed to install shfmt. Ensure Go is installed."; \
			exit 1; \
		}; \
		echo "shfmt installed successfully"; \
	else \
		echo "shfmt is already installed at $$(command -v shfmt)"; \
		shfmt -version; \
	fi

yamlfmt: ## Install yamlfmt if not present
	@if ! command -v yamlfmt >/dev/null 2>&1; then \
		echo "Installing yamlfmt..."; \
		go install github.com/google/yamlfmt/cmd/yamlfmt@latest || { \
			echo "Error: Failed to install yamlfmt. Ensure Go is installed."; \
			exit 1; \
		}; \
		echo "yamlfmt installed successfully"; \
	else \
		echo "yamlfmt is already installed at $$(command -v yamlfmt)"; \
		yamlfmt -version; \
	fi

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null

clean/all: clean ## Deep clean (clean + remove virtual environment)
	rm -rf .venv venv

# ============================================================================
# Section 8: Combined Workflows
# ============================================================================

.PHONY: all ci

all: format lint typecheck/python test ## Run full pipeline: format → lint → typecheck → test
ci: check test ## Run CI pipeline: check → test (what GitHub Actions runs)

# ============================================================================
# Section 9: Help
# ============================================================================

.PHONY: help

help: ## Display this help message
	@echo "PKM Tool - Development Makefile"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 1: Development Setup"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^(install|update)[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 2: Testing"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^test[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 3: Code Quality"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^(format|lint|typecheck|check|fix)[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 4: Pre-commit Integration"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^pre-commit[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 5: GitHub Actions Pinning (Ratchet)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^ratchet[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 6: Documentation"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^docs:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 7: Utilities"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^(clean|shfmt|yamlfmt)[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 8: Combined Workflows"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^(all|ci):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Common Workflows:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  Development:      make install → make install-hooks → make all"
	@echo "  Before commit:    make all (or rely on pre-commit hooks)"
	@echo "  CI simulation:    make ci"
	@echo "  Quick check:      make check"
	@echo ""

# Set default target
.DEFAULT_GOAL := help
