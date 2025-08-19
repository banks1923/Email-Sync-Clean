.PHONY: install install-dev format-advanced lint-all lint-fix type-check test test-fast test-unit test-integration test-slow test-coverage test-smoke security-check docs-check docs-fix complexity-check complexity-report validate clean help fix-all cleanup setup sonar-check sonar-fix sonar-report

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip

help: ## Show this help message
	@echo "Email Sync Quality Control Makefile"
	@echo "=================================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies
	$(PIP) install -r requirements.txt

install-dev: install ## Install development dependencies
	$(PIP) install -r requirements-dev.txt
	pre-commit install --config .config/.pre-commit-config.yaml

setup: install-dev ## Complete development setup
	@echo "✅ Development environment setup complete!"

# Code Quality
format-advanced: ## Advanced formatting with all cleanup tools
	@echo "🔧 Running comprehensive code cleanup..."
	@echo "   1. Removing unused imports..."
	autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .
	@echo "   2. Upgrading Python syntax..."
	find . -name "*.py" -not -path "*/__pycache__/*" | xargs pyupgrade --py311-plus
	@echo "   3. Formatting docstrings..."
	find . -name "*.py" -not -path "*/__pycache__/*" | xargs docformatter --in-place --make-summary-multi-line
	@echo "   4. Fixing import order..."
	isort .
	@echo "   5. Final code formatting..."
	black .
	@echo "✅ Advanced formatting complete!"

lint-all: ## Run all linting tools (flake8 + ruff)
	@echo "🔍 Running flake8..."
	flake8 --config .config/.flake8 . || true
	@echo ""
	@echo "🦀 Running ruff..."
	ruff check . --statistics

lint-fix: ## Auto-fix linting issues where possible
	@echo "🔧 Auto-fixing with ruff..."
	ruff check . --fix --unsafe-fixes
	@echo "🔧 Auto-fixing with autoflake..."
	autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .

type-check: ## Run type checking with mypy
	@echo "🔍 Running type checking with mypy..."
	mypy --config-file .config/mypy.ini gmail/ shared/ utilities/ infrastructure/ --ignore-missing-imports || true

# Testing
test: ## Run all tests (full suite)
	@echo "🧪 Running full test suite (405 tests)..."
	pytest -c .config/pytest.ini -v

test-fast: ## Run fast categorized tests (CI/CD optimized)
	@echo "🚀 Running fast categorized tests for CI/CD..."
	@echo "   Stage 1: Unit tests (fast, isolated)"
	@$(MAKE) test-unit
	@echo ""
	@echo "   Stage 2: Integration tests (cross-service)"
	@$(MAKE) test-integration
	@echo ""
	@echo "✅ Fast test pipeline complete!"

test-unit: ## Run unit tests only (fast, isolated - ~77 tests)
	@echo "⚡ Running unit tests (fast, isolated)..."
	pytest -c .config/pytest.ini -m "unit" --tb=short -v

test-integration: ## Run integration tests only (cross-service)
	@echo "🔗 Running integration tests (cross-service)..."
	pytest -c .config/pytest.ini -m "integration" --tb=short -v

test-slow: ## Run slow tests only (performance, AI models)
	@echo "🐌 Running slow tests (performance, AI models)..."
	pytest -c .config/pytest.ini -m "slow" --tb=short -v

test-smoke: ## Run smoke tests only (system health checks)
	@echo "💨 Running smoke tests (system health)..."
	pytest -c .config/pytest.ini tests/smoke/ --tb=short -v

test-coverage: ## Run tests with coverage report
	@echo "📊 Running tests with coverage analysis..."
	pytest -c .config/pytest.ini --cov=. --cov-config=.config/.coveragerc --cov-report=html --cov-report=term-missing -v

# Security
security-check: ## Run security checks with bandit
	bandit -r gmail/ search/ vector_store/ embeddings/ shared/

# Documentation
docs-check: ## Check markdown documentation for style issues
	@echo "📝 Running markdownlint on documentation..."
	@if command -v markdownlint >/dev/null 2>&1; then \
		markdownlint --config .config/.markdownlint.json *.md docs/*.md; \
	else \
		echo "⚠️  markdownlint not installed. Install with: npm install -g markdownlint-cli"; \
	fi

docs-fix: ## Auto-fix markdown documentation issues where possible
	@echo "🔧 Auto-fixing markdown issues..."
	@if command -v markdownlint >/dev/null 2>&1; then \
		markdownlint --config .config/.markdownlint.json --fix *.md docs/*.md; \
	else \
		echo "⚠️  markdownlint not installed. Install with: npm install -g markdownlint-cli"; \
	fi

# Code Complexity Analysis
complexity-check: ## Analyze code complexity with radon
	@echo "🧮 Running complexity analysis..."
	@echo "📊 Cyclomatic Complexity (functions/classes above threshold):"
	radon cc --min B --exclude="tests/*,*test*.py,zarchive/*,bench/*" --average --show-complexity .
	@echo ""
	@echo "📈 Maintainability Index (below 20 needs attention):"
	radon mi --min B --exclude="tests/*,*test*.py,zarchive/*,bench/*" .

complexity-report: ## Generate detailed complexity report
	@echo "📋 Generating comprehensive complexity report..."
	@mkdir -p reports
	@echo "## Code Complexity Report - $(date)" > reports/complexity_report.md
	@echo "" >> reports/complexity_report.md
	@echo "### Cyclomatic Complexity" >> reports/complexity_report.md
	@radon cc --min A --show-complexity --average --exclude="tests/*,*test*.py,zarchive/*,bench/*" . >> reports/complexity_report.md
	@echo "" >> reports/complexity_report.md
	@echo "### Maintainability Index" >> reports/complexity_report.md
	@radon mi --min A --exclude="tests/*,*test*.py,zarchive/*,bench/*" . >> reports/complexity_report.md
	@echo "" >> reports/complexity_report.md
	@echo "### Raw Metrics" >> reports/complexity_report.md
	@radon raw --summary --exclude="tests/*,*test*.py,zarchive/*,bench/*" . >> reports/complexity_report.md
	@echo "✅ Complexity report generated: reports/complexity_report.md"

# SonarQube Code Quality
sonar-check: ## Run SonarLint analysis on Python codebase
	@echo "🔍 Running SonarLint code quality analysis..."
	@if command -v sonarlint >/dev/null 2>&1; then \
		sonarlint --src . --language python --html-report sonar-report.html; \
	else \
		echo "⚠️  sonarlint-cli not installed. Install with: brew install sonarlint-cli"; \
		echo "   Or use VS Code extension: SonarSource.sonarlint-vscode"; \
	fi

sonar-fix: ## Auto-fix SonarLint issues where possible
	@echo "🔧 Auto-fixing SonarLint issues..."
	@if command -v sonarlint >/dev/null 2>&1; then \
		sonarlint --src . --language python --fix; \
	else \
		echo "⚠️  sonarlint-cli not installed. Install with: brew install sonarlint-cli"; \
	fi

sonar-report: ## Generate HTML quality report with SonarLint
	@echo "📊 Generating SonarLint HTML report..."
	@if command -v sonarlint >/dev/null 2>&1; then \
		sonarlint --src . --language python --html-report reports/sonar-quality.html; \
		echo "✅ Report generated: reports/sonar-quality.html"; \
	else \
		echo "⚠️  sonarlint-cli not installed. Install with: brew install sonarlint-cli"; \
	fi

# Validation
validate: ## Run complete validation suite
	$(PYTHON) scripts/validate_refactoring.py -v

# Workflow Commands
fix-all: lint-fix format-advanced docs-fix ## Auto-fix all possible issues and format code

cleanup: ## Complete code cleanup and quality improvements
	@echo "🚀 Starting comprehensive code cleanup..."
	@echo ""
	make lint-fix
	@echo ""
	make format-advanced
	@echo ""
	make docs-fix
	@echo ""
	@echo "📊 Final quality check..."
	make lint-all || true
	make docs-check || true
	@echo ""
	@echo "✅ Cleanup complete! Review changes before committing."

check: format-advanced lint-all type-check complexity-check test-fast ## Run fast quality checks (recommended)

check-full: format-advanced lint-all type-check test ## Run comprehensive quality checks (all tests)

# Utilities
clean: ## Clean up generated files and linter caches
	@echo "🧹 Cleaning up generated files and caches..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.coverage" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage coverage.xml coverage.json 2>/dev/null || true
	@rm -rf .mypy_cache/ .pytest_cache/ .ruff_cache/ .flake8_cache/ __flake8__/ .vulture_cache/ 2>/dev/null || true
	@rm -rf dist/ build/ 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# Database & Vector Maintenance
db-validate: ## Validate database schema integrity
	@echo "🔍 Validating database schema..."
	@python utilities/maintenance/schema_maintenance.py validate

db-fix: ## Fix database schema issues (dry run)
	@echo "🔧 Checking for schema issues..."
	@python utilities/maintenance/schema_maintenance.py fix-schema

db-fix-apply: ## Apply database schema fixes
	@echo "⚠️  Applying schema fixes..."
	@python utilities/maintenance/schema_maintenance.py fix-schema --execute

vector-status: ## Check vector store sync status
	@echo "📊 Checking vector sync status..."
	@python utilities/maintenance/vector_maintenance.py verify

vector-sync: ## Sync missing vectors with database
	@echo "🔄 Syncing missing vectors..."
	@python utilities/maintenance/vector_maintenance.py sync-missing

vector-reconcile: ## Reconcile vectors with database (dry run)
	@echo "🔍 Reconciling vectors with database..."
	@python utilities/maintenance/vector_maintenance.py reconcile

vector-reconcile-fix: ## Apply vector reconciliation fixes
	@echo "⚠️  Applying reconciliation fixes..."
	@python utilities/maintenance/vector_maintenance.py reconcile --fix

vector-purge-test: ## Remove test vectors from production (dry run)
	@echo "🧹 Identifying test vectors..."
	@python utilities/maintenance/vector_maintenance.py purge-test

maintenance-all: ## Run all maintenance checks
	@echo "🛠️  Running all maintenance checks..."
	@make db-validate
	@make vector-status
	@echo "✅ Maintenance checks complete!"