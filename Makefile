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

tools/install: ## Install dependencies with all extras
	uv sync --all-extras
	@if command -v npm >/dev/null 2>&1; then \
		echo "Installing Node.js dependencies for commitlint..."; \
		npm install --silent; \
	else \
		echo "npm not available, skipping Node.js dependencies installation."; \
	fi

tools/install/dev: tools/install tools/install-hooks ## Install with dev dependencies (alias for install)

tools/install-hooks: ## Install pre-commit hooks
	pre-commit install

tools/update: ## Update dev tooling (pre-commit hooks, dependencies)
	pre-commit autoupdate
	uv sync --all-extras --upgrade

# ============================================================================
# Section 2: Testing
# ============================================================================

.PHONY: test test/coverage test/timing test/slow test/parallel

test: ## Run all tests
	uv run pytest -v --durations=10

test/parallel: ## Run all tests in parallel (use for slow/large test suites >30s)
	@echo "Note: Parallel execution adds overhead. Only use if test suite is slow."
	uv run pytest -v -n auto --durations=10

test/coverage: ## Run tests with coverage report
	uv run pytest -v --durations=10 --cov --cov-report=term-missing --cov-report=html

test/timing: ## Run tests with detailed timing information
	uv run pytest -v --durations=0

test/slow: ## Show only slow tests (>1s)
	uv run pytest -v --durations=10 --durations-min=1.0

# ============================================================================
# Section 3: Code Quality
# ============================================================================

.PHONY: format lint check format/python format/python/check format/yaml format/markdown format/shell typecheck/python
.PHONY: lint/python lint/python/fix lint/shell lint/actions lint/yaml lint/makefile
.PHONY: lint/markdown lint/markdown/fix lint/skylos lint/complexipy
.PHONY: lint/security audit/deps

format: format/python format/markdown format/shell format/yaml ## Format all code (Python, Markdown, Shell, YAML)

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
	fi

format/markdown: ## Format Markdown files with mdformat
	uv run mdformat .

format/shell: ## Format shell scripts with shfmt
	@if command -v shfmt >/dev/null 2>&1; then \
		find . -name "*.sh" -not -path "./.venv/*" -not -path "./venv/*" -exec shfmt -i 2 -ci -w {} + 2>/dev/null || true; \
	fi

lint: lint/python lint/shell lint/actions lint/yaml lint/markdown lint/makefile typecheck/python lint/skylos lint/complexipy lint/security ## Run all linters

lint/python: ## Run Python linter (via pre-commit)
	pre-commit run ruff --all-files

lint/python/fix: ## Auto-fix Python linting issues
	uv run ruff check --fix src tests

lint/markdown: ## Lint Markdown files (via pre-commit)
	pre-commit run markdownlint --all-files

lint/markdown/fix: ## Format and lint Markdown files
	uv run mdformat .
	pre-commit run markdownlint --all-files

typecheck/python: ## Type check with ty (via pre-commit)
	pre-commit run ty --all-files

lint/shell: ## Check shell scripts (via pre-commit)
	pre-commit run shellcheck --all-files

lint/actions: ## Check GitHub Actions (via pre-commit)
	pre-commit run actionlint --all-files
	pre-commit run check-github-workflows --all-files

lint/yaml: ## Check YAML files (via pre-commit)
	pre-commit run yamllint --all-files

lint/makefile: ## Check Makefile (via pre-commit)
	pre-commit run checkmake --all-files

lint/skylos: ## Run Skylos quality gate (via pre-commit)
	pre-commit run skylos --all-files

lint/complexipy: ## Run complexity gate (via pre-commit)
	pre-commit run complexipy --all-files

lint/security: ## Run security linter (bandit)
	uv run bandit -r src/ -c pyproject.toml -q

audit/deps: ## Audit dependencies for vulnerabilities (pip-audit)
	uv run pip-audit

lint/commits: ## Check commit messages with commitlint
	@echo "Validating commit messages with commitlint..."
	@if [ -f node_modules/.bin/commitlint ]; then \
		echo "Checking last commit message..."; \
		node_modules/.bin/commitlint --config .commitlintrc.yaml --from HEAD~1 --to HEAD --verbose ; \
	elif command -v npx >/dev/null 2>&1; then \
		echo "Local commitlint not found. Using npx..."; \
		npx --yes --package=@commitlint/cli@19.8.1 --package=@commitlint/config-conventional@19.8.1 -- commitlint --config .commitlintrc.yaml --from HEAD~1 --to HEAD --verbose ; \
	else \
		echo "Error: commitlint not available. Run 'make tools/install' or install Node.js."; \
		exit 1; \
	fi

lint/commits/range: ## Check commit messages in a range (usage: make lint/commits/range FROM=<sha> TO=<sha>)
	@echo "Validating commit messages with commitlint..."
	@if [ -z "$(FROM)" ] || [ -z "$(TO)" ]; then \
		echo "Error: FROM and TO must be specified"; \
		echo "Usage: make lint/commits/range FROM=<sha> TO=<sha>"; \
		exit 1; \
	fi
	@if [ -f node_modules/.bin/commitlint ]; then \
		echo "Checking commits from $(FROM) to $(TO)..."; \
		node_modules/.bin/commitlint --config .commitlintrc.yaml --from $(FROM) --to $(TO) --verbose ; \
	elif command -v npx >/dev/null 2>&1; then \
		echo "Local commitlint not found. Using npx..."; \
		npx --yes --package=@commitlint/cli@19.8.1 --package=@commitlint/config-conventional@19.8.1 -- commitlint --config .commitlintrc.yaml --from $(FROM) --to $(TO) --verbose ; \
	else \
		echo "Error: commitlint not available. Run 'make tools/install' or install Node.js."; \
		exit 1; \
	fi

check: ## Run all checks via pre-commit (no modifications)
	pre-commit run --all-files

.PHONY: fix
fix: fix/python format/markdown format/shell ## Auto-fix all fixable issues (format + lint)

.PHONY: fix/python
fix/python: ## Auto-fix Python issues (format + lint --fix)
	uv run ruff check --fix src tests
	uv run ruff format src tests

# ============================================================================
# Section 4: Pre-commit Integration
# ============================================================================

.PHONY: pre-commit pre-commit/install

pre-commit: ## Run pre-commit on all files (source of truth for static analysis)
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
	rm -rf .pytest_cache .ruff_cache .mypy_cache dist build htmlcov .coverage skylos_report.json complexipy_report.json complexipy-snapshot.json
	rm -f complexipy_results_*.json || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null

clean/all: clean ## Deep clean (clean + remove virtual environment)
	rm -rf .venv venv

# ============================================================================
# Section 8: Combined Workflows
# ============================================================================

.PHONY: all ci

all: ## Run full pipeline: pre-commit → test
	pre-commit run --all-files
	$(MAKE) test

ci: ## Run CI pipeline: pre-commit → test/coverage
	pre-commit run --all-files
	$(MAKE) test/coverage

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
	@grep -E '^(tools/install|tools/update)[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 2: Testing"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^test[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Section 3: Code Quality"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@grep -E '^(format|lint|typecheck|check|fix|audit)[a-z/-]*:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
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
	@echo "  Development:      make tools/install → make tools/install-hooks → make all"
	@echo "  Before commit:    make all (or rely on pre-commit hooks)"
	@echo "  CI simulation:    make ci"
	@echo "  Quick check:      make check (runs pre-commit)"
	@echo ""
	@echo "Note: Pre-commit is the source of truth for static analysis."
	@echo "      Makefile targets wrap pre-commit commands for convenience."
	@echo ""

# Set default target
.DEFAULT_GOAL := help
