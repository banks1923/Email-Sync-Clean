.PHONY: install install-dev format-advanced lint-all lint-fix type-check test test-fast test-unit test-integration test-slow test-coverage test-smoke security-check validate clean help fix-all cleanup setup

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
	pre-commit install

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
	flake8 . || true
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
	mypy gmail/ shared/ utilities/ infrastructure/ --ignore-missing-imports || true

# Testing
test: ## Run all tests (full suite)
	@echo "🧪 Running full test suite (405 tests)..."
	pytest -v

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
	pytest -m "unit" --tb=short -v

test-integration: ## Run integration tests only (cross-service)
	@echo "🔗 Running integration tests (cross-service)..."
	pytest -m "integration" --tb=short -v

test-slow: ## Run slow tests only (performance, AI models)
	@echo "🐌 Running slow tests (performance, AI models)..."
	pytest -m "slow" --tb=short -v

test-smoke: ## Run smoke tests only (system health checks)
	@echo "💨 Running smoke tests (system health)..."
	pytest tests/smoke/ --tb=short -v

test-coverage: ## Run tests with coverage report
	@echo "📊 Running tests with coverage analysis..."
	pytest --cov=. --cov-report=html --cov-report=term-missing -v

# Security
security-check: ## Run security checks with bandit
	bandit -r gmail/ search/ vector_store/ embeddings/ shared/

# Validation
validate: ## Run complete validation suite
	$(PYTHON) scripts/validate_refactoring.py -v

# Workflow Commands
fix-all: lint-fix format-advanced ## Auto-fix all possible issues and format code

cleanup: ## Complete code cleanup and quality improvements
	@echo "🚀 Starting comprehensive code cleanup..."
	@echo ""
	make lint-fix
	@echo ""
	make format-advanced
	@echo ""
	@echo "📊 Final quality check..."
	make lint-all || true
	@echo ""
	@echo "✅ Cleanup complete! Review changes before committing."

check: format-advanced lint-all type-check test-fast ## Run fast quality checks (recommended)

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