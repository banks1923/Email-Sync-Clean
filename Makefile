.PHONY: install install-dev format-advanced lint-all lint-fix type-check test test-fast test-unit test-integration test-slow test-coverage test-smoke security-check docs-check docs-truth-check docs-fix docs-audit docs-audit-summary docs-update complexity-check complexity-report validate clean help fix-all cleanup setup sonar-check sonar-fix sonar-report diag-wiring vector-smoke full-run email-scan email-quarantine vectors-reconcile ci-email-gate first-time-setup test-basic install-qdrant test-vector search upload sync-gmail health-check recent-activity install-all setup-gmail test-everything update-system backup diagnose check-requirements setup-gmail-auth test-gmail sync-gmail-recent db-stats performance-stats reindex-all start-qdrant qdrant-status fix-permissions check-disk-space memory-check system-report configure-advanced setup-backups setup-search-aliases optimize-db cleanup-old-data monitor-performance encrypt-database setup-secure-backups

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
QDRANT_PID := $(shell pgrep -f "qdrant" 2>/dev/null)

# Qdrant Management
ensure-qdrant: ## Ensure Qdrant is running (auto-start if needed)
	@if ! curl -s http://localhost:6333/readyz >/dev/null 2>&1; then \
		echo "🚀 Starting Qdrant (vector database required for search)..."; \
		if [ ! -f ~/bin/qdrant ]; then \
			echo "⚠️  Qdrant not found. Installing..."; \
			echo "   Download from: https://github.com/qdrant/qdrant/releases"; \
			echo "   Or run: curl -L https://install.qdrant.io | bash"; \
			exit 1; \
		fi; \
		QDRANT__STORAGE__PATH=./qdrant_data ~/bin/qdrant > qdrant.log 2>&1 & \
		echo "   Waiting for Qdrant to start..."; \
		for i in 1 2 3 4 5; do \
			sleep 2; \
			if curl -s http://localhost:6333/readyz >/dev/null 2>&1; then \
				echo "✅ Qdrant started successfully!"; \
				break; \
			fi; \
			if [ $$i -eq 5 ]; then \
				echo "❌ Failed to start Qdrant. Check qdrant.log for details."; \
				exit 1; \
			fi; \
		done; \
	else \
		echo "✅ Qdrant is already running"; \
	fi

stop-qdrant: ## Stop Qdrant if running
	@if pgrep -f "qdrant" >/dev/null 2>&1; then \
		echo "🛑 Stopping Qdrant..."; \
		pkill -f "qdrant"; \
		sleep 2; \
		echo "✅ Qdrant stopped"; \
	else \
		echo "ℹ️  Qdrant is not running"; \
	fi

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
docs-check: ## Check documentation for style issues and truth alignment (CI guard)  
	@echo "📝 Running comprehensive documentation checks..."
	@echo "1. Checking markdown style..."
	@if command -v markdownlint >/dev/null 2>&1; then \
		markdownlint --config .config/.markdownlint.json *.md docs/*.md; \
	else \
		echo "⚠️  markdownlint not installed. Install with: npm install -g markdownlint-cli"; \
	fi
	@echo ""
	@echo "2. Auditing documentation truth alignment..."
	@$(PYTHON) tools/docs/audit.py --json | python3 -c "import sys, json; data=json.load(sys.stdin); missing_docs=[d for d in data['missing_docs'] if not d['exists']]; missing_tests=[t for t in data['test_paths'] if not t['exists']]; exit(1 if missing_docs or missing_tests else 0)" || (echo "❌ Documentation audit failed: missing files or incorrect paths" && $(PYTHON) tools/docs/audit.py --summary && exit 1)
	@echo "✅ Documentation checks passed!"

docs-truth-check: ## Check only documentation truth alignment (no style checking)
	@echo "🔍 Auditing documentation truth alignment..."
	@$(PYTHON) tools/docs/audit.py --json | python3 -c "import sys, json; data=json.load(sys.stdin); missing_docs=[d for d in data['missing_docs'] if not d['exists']]; missing_tests=[t for t in data['test_paths'] if not t['exists']]; exit(1 if missing_docs or missing_tests else 0)" || (echo "❌ Documentation audit failed: missing files or incorrect paths" && $(PYTHON) tools/docs/audit.py --summary && exit 1)
	@echo "✅ Documentation truth alignment verified!"

docs-fix: ## Auto-fix markdown documentation issues where possible
	@echo "🔧 Auto-fixing markdown issues..."
	@if command -v markdownlint >/dev/null 2>&1; then \
		markdownlint --config .config/.markdownlint.json --fix *.md docs/*.md; \
	else \
		echo "⚠️  markdownlint not installed. Install with: npm install -g markdownlint-cli"; \
	fi

docs-audit: ## Audit documentation claims against reality (outputs JSON)
	@echo "🔍 Auditing documentation claims against codebase..."
	@$(PYTHON) tools/docs/audit.py --json

docs-audit-summary: ## Show human-readable documentation audit summary
	@echo "📋 Documentation Audit Summary"
	@$(PYTHON) tools/docs/audit.py --summary

docs-update: ## Update documentation with auto-generated content (line counts, service tables)
	@echo "🔄 Updating documentation with current data..."
	@$(PYTHON) tools/docs/update_counts.py
	@echo "✅ Documentation updated with current line counts and service data"

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
	@$(PYTHON) utilities/maintenance/schema_maintenance.py validate

db-fix: ## Fix database schema issues (dry run)
	@echo "🔧 Checking for schema issues..."
	@$(PYTHON) utilities/maintenance/schema_maintenance.py fix-schema

db-fix-apply: ## Apply database schema fixes
	@echo "⚠️  Applying schema fixes..."
	@$(PYTHON) utilities/maintenance/schema_maintenance.py fix-schema --execute

vector-status: ensure-qdrant ## Check vector store sync status
	@echo "📊 Checking vector sync status..."
	@$(PYTHON) utilities/maintenance/vector_maintenance.py verify

vector-sync: ensure-qdrant ## Sync missing vectors with database
	@echo "🔄 Syncing missing vectors..."
	@$(PYTHON) utilities/maintenance/vector_maintenance.py sync-missing

vector-reconcile: ensure-qdrant ## Reconcile vectors with database (dry run)
	@echo "🔍 Reconciling vectors with database..."
	@$(PYTHON) utilities/maintenance/vector_maintenance.py reconcile

vector-reconcile-fix: ensure-qdrant ## Apply vector reconciliation fixes
	@echo "⚠️  Applying reconciliation fixes..."
	@$(PYTHON) utilities/maintenance/vector_maintenance.py reconcile --fix

vector-purge-test: ensure-qdrant ## Remove test vectors from production (dry run)
	@echo "🧹 Identifying test vectors..."
	@$(PYTHON) utilities/maintenance/vector_maintenance.py purge-test

vector-renormalize: ensure-qdrant ## Re-normalize vectors to unit length (dry run)
	@echo "📐 Checking vector normalization..."
	@$(PYTHON) utilities/maintenance/vector_maintenance.py renormalize

vector-renormalize-fix: ensure-qdrant ## Apply vector renormalization
	@echo "⚠️  Re-normalizing vectors to unit length..."
	@$(PYTHON) utilities/maintenance/vector_maintenance.py renormalize --execute

preflight-vector-parity: ensure-qdrant ## Check vector parity between database and Qdrant
	@echo "🔍 Checking vector parity..."
	@APP_DB_PATH=data/emails.db VSTORE_COLLECTION=emails ALLOW_EMPTY_COLLECTION=false EXPECTED_DIM=1024 DELTA_THRESHOLD=50 \
	$(PYTHON) tools/preflight/vector_parity_check.py

maintenance-all: ## Run all maintenance checks
	@echo "🛠️  Running all maintenance checks..."
	@make db-validate
	@make vector-status
	@echo "✅ Maintenance checks complete!"

# Semantic Pipeline Targets
semantic-preflight: ensure-qdrant ## Run preflight checks for semantic pipeline
	@echo "🔍 Running semantic pipeline preflight checks..."
	@$(PYTHON) scripts/preflight_check.py

semantic-status: ## Show semantic enrichment status
	@echo "📊 Semantic enrichment status..."
	@tools/scripts/vsearch semantic status

semantic-verify: ensure-qdrant ## Verify semantic pipeline wiring (comprehensive)
	@echo "🔍 Verifying semantic pipeline wiring..."
	@$(PYTHON) scripts/verify_semantic_wiring.py

semantic-verify-quick: ensure-qdrant ## Quick semantic pipeline verification
	@echo "⚡ Quick semantic pipeline check..."
	@$(PYTHON) scripts/verify_semantic_wiring.py --quick

eid-lookup: ## Lookup evidence by EID with all semantic data
	@if [ -z "$(EID)" ]; then \
		echo "❌ Usage: make eid-lookup EID=EID-2024-0001"; \
		exit 1; \
	fi
	@$(PYTHON) tools/scripts/vsearch semantic lookup --eid $(EID)

backfill-entities: ensure-qdrant ## Backfill entity extraction for old emails
	@echo "🏷️  Backfilling entity extraction..."
	@$(PYTHON) scripts/backfill_semantic.py --steps entities

backfill-embeddings: ensure-qdrant ## Backfill embeddings for old emails
	@echo "🔢 Backfilling embeddings..."
	@$(PYTHON) scripts/backfill_semantic.py --steps embeddings

backfill-timeline: ensure-qdrant ## Backfill timeline events for old emails
	@echo "📅 Backfilling timeline events..."
	@$(PYTHON) scripts/backfill_semantic.py --steps timeline

# Email Corpus Sanitation Targets
email-scan: ## Scan email corpus for validation issues (JSON output)
	@echo "🔍 Scanning email corpus for validation issues..."
	@$(PYTHON) tools/cli/email_sanitizer.py scan --json

email-quarantine: ## Move invalid emails to quarantine with batch tracking
	@echo "🚨 Quarantining invalid emails..."
	@$(PYTHON) tools/cli/email_sanitizer.py quarantine --json

email-quarantine-dry: ## Dry run quarantine (scan only, no changes)
	@echo "🔍 Dry run: checking what would be quarantined..."
	@$(PYTHON) tools/cli/email_sanitizer.py quarantine --dry-run --json

vectors-reconcile: ensure-qdrant ## Reconcile vectors between database and Qdrant
	@echo "🔄 Reconciling vectors between database and Qdrant..."
	@$(PYTHON) tools/cli/email_sanitizer.py reconcile --json

ci-email-gate: ## CI validation gate (exits non-zero on violations)
	@echo "🚪 Running CI email validation gate..."
	@$(PYTHON) tools/scripts/email_sanitation_report.py --ci-check

email-report: ## Generate comprehensive email sanitation report
	@echo "📊 Generating email sanitation report..."
	@$(PYTHON) tools/scripts/email_sanitation_report.py --format pretty

email-report-json: ## Generate JSON email sanitation report
	@echo "📊 Generating JSON email sanitation report..."
	@$(PYTHON) tools/scripts/email_sanitation_report.py --format json

email-setup: ## Setup email quarantine infrastructure
	@echo "🏗️  Setting up email quarantine infrastructure..."
	@$(PYTHON) scripts/create_quarantine_tables.py
	@echo "✅ Email quarantine infrastructure ready!"

email-rollback: ## Rollback quarantine batch (requires BATCH_ID)
	@if [ -z "$(BATCH_ID)" ]; then \
		echo "❌ Usage: make email-rollback BATCH_ID=batch-uuid"; \
		exit 1; \
	fi
	@echo "🔄 Rolling back quarantine batch: $(BATCH_ID)..."
	@$(PYTHON) tools/cli/email_sanitizer.py rollback $(BATCH_ID) --json

email-stats: ## Show quarantine statistics
	@echo "📈 Email quarantine statistics..."
	@$(PYTHON) tools/cli/email_sanitizer.py stats

backfill-all: ensure-qdrant ## Backfill all semantic enrichment for old emails
	@echo "🚀 Backfilling all semantic enrichment..."
	@$(PYTHON) scripts/backfill_semantic.py

backfill-recent: ensure-qdrant ## Backfill semantic enrichment for last 7 days
	@echo "📅 Backfilling recent emails (last 7 days)..."
	@$(PYTHON) scripts/backfill_semantic.py --since-days 7

test-semantic-pipeline: ensure-qdrant ## Test semantic pipeline with 5 recent emails
	@echo "🧪 Testing semantic pipeline..."
	@$(PYTHON) scripts/test_semantic_pipeline.py

diag-wiring: ensure-qdrant ## Full system diagnostic - validate wiring & efficiency
	@echo "🔍 Running system diagnostic..."
	$(PYTHON) tools/diag_wiring.py

diag-tools: ensure-qdrant ## Quick service smoke tests - verify all tools are working
	@echo "🔧 Running service diagnostics (smoke test)..."
	$(PYTHON) tools/scripts/run_service_test.py --mode smoke

diag-tools-deep: ensure-qdrant ## Thorough service tests with operations
	@echo "🔬 Running deep service diagnostics..."
	$(PYTHON) tools/scripts/run_service_test.py --mode deep

vector-smoke: ensure-qdrant ## Quick vector smoke test - upsert 50 points & run 2 searches  
	@echo "💨 Running vector smoke test..."
	$(PYTHON) -c "import sys, os, uuid; sys.path.insert(0, '.'); \
	from utilities.vector_store import get_vector_store; \
	from utilities.embeddings import get_embedding_service; \
	vs = get_vector_store('emails'); emb = get_embedding_service(); \
	texts = ['smoke test ' + str(i) for i in range(50)]; \
	embeddings = emb.batch_encode(texts, batch_size=16); \
	test_ids = [str(uuid.uuid4()) for _ in range(50)]; \
	points = [{'id': test_ids[i], 'vector': e, 'metadata': {'test': True}} for i, e in enumerate(embeddings)]; \
	vs.batch_upsert('emails', points); \
	print('✓ Upserted 50 test points'); \
	results1 = vs.search(emb.encode('test'), limit=5); \
	results2 = vs.search(emb.encode('smoke'), limit=5); \
	print('✓ Search 1: {} hits, top score: {:.3f}'.format(len(results1), results1[0]['score']) if results1 else '✗ No hits'); \
	print('✓ Search 2: {} hits, top score: {:.3f}'.format(len(results2), results2[0]['score']) if results2 else '✗ No hits'); \
	vs.delete_many(test_ids); \
	print('✓ Cleaned up test data')"

full-run: ensure-qdrant ## Complete end-to-end system pipeline (Qdrant required)
	@echo "🚀 Starting full system pipeline..."
	$(PYTHON) tools/scripts/run_full_system

diag-semantic: ensure-qdrant ## Test semantic enrichment pipeline with 10 emails
	@echo "🧪 Testing semantic enrichment pipeline..."
	@$(PYTHON) -c "import sys; sys.path.insert(0, '.'); \
	from gmail.main import GmailService; \
	from config.settings import semantic_settings; \
	from shared.simple_db import SimpleDB; \
	import os; \
	os.environ['SEMANTICS_ON_INGEST'] = 'true'; \
	print('📧 Syncing 10 emails with semantic enrichment...'); \
	service = GmailService(); \
	result = service.sync_emails(max_results=10, batch_mode=True); \
	print(f'✓ Sync result: {result}'); \
	print(''); \
	print('📊 Checking semantic enrichment results:'); \
	db = SimpleDB(); \
	cursor = db.execute('SELECT COUNT(*) FROM entity_content_mapping WHERE created_at > datetime(\"now\", \"-5 minutes\")'); \
	entity_count = cursor.fetchone()[0]; \
	print(f'  Entities extracted: {entity_count}'); \
	cursor = db.execute('SELECT COUNT(*) FROM content WHERE metadata LIKE \"%vectorized%\" AND updated_at > datetime(\"now\", \"-5 minutes\")'); \
	vector_count = cursor.fetchone()[0]; \
	print(f'  Vectors created: {vector_count}'); \
	cursor = db.execute('SELECT COUNT(*) FROM timeline_events WHERE created_at > datetime(\"now\", \"-5 minutes\")'); \
	timeline_count = cursor.fetchone()[0]; \
	print(f'  Timeline events: {timeline_count}'); \
	print(''); \
	if entity_count > 0 or vector_count > 0 or timeline_count > 0: \
	    print('✅ Semantic enrichment pipeline working!'); \
	else: \
	    print('⚠️  No semantic enrichment detected - check pipeline configuration');"
# PDF Pipeline Management
preflight:
	@python3 scripts/preflight_check.py

quarantine-list:
	@python3 -c "from tools.cli.quarantine_handler import QuarantineHandler; h = QuarantineHandler(); results = h.list_quarantined(); print('\n'.join([str(r) for r in results]) if results else 'No quarantined documents')"

quarantine-stats:
	@python3 -c "from tools.cli.quarantine_handler import QuarantineHandler; h = QuarantineHandler(); import json; print(json.dumps(h.get_stats(), indent=2))"

embeddings-backfill:
	@python3 scripts/backfill_embeddings.py

embeddings-backfill-dry:
	@python3 scripts/backfill_embeddings.py --dry-run

embeddings-backfill-pdf:
	@python3 scripts/backfill_embeddings.py --type pdf

ingest-status:
	@echo "=== Ingestion Pipeline Status ==="
	@echo -n "Ingestion: "; if [ -f INGESTION_FROZEN.txt ]; then echo "❄️  FROZEN"; else echo "✅ Active"; fi
	@echo -n "Schema Version: "; sqlite3 data/emails.db "SELECT MAX(version) FROM schema_version" 2>/dev/null || echo "Not tracked"
	@echo -n "Documents Total: "; sqlite3 data/emails.db "SELECT COUNT(DISTINCT sha256) FROM documents" 2>/dev/null || echo "0"
	@echo -n "Documents Processed: "; sqlite3 data/emails.db "SELECT COUNT(DISTINCT sha256) FROM documents WHERE status='processed'" 2>/dev/null || echo "0"
	@echo -n "Documents Failed: "; sqlite3 data/emails.db "SELECT COUNT(DISTINCT sha256) FROM documents WHERE status='failed'" 2>/dev/null || echo "0"
	@echo -n "Ready for Embedding: "; sqlite3 data/emails.db "SELECT COUNT(*) FROM content_unified WHERE ready_for_embedding=1" 2>/dev/null || echo "0"

sha-backfill: ## Repair SHA256 and content_unified chain for upload documents
	python3 scripts/backfill_sha256_uploads.py --db ${APP_DB_PATH} --source-type upload

sha-backfill-dry: ## Dry run SHA256 backfill (shows what would be fixed)
	python3 scripts/backfill_sha256_uploads.py --db ${APP_DB_PATH} --source-type upload --dry-run

.PHONY: preflight quarantine-list quarantine-stats embeddings-backfill ingest-status sha-backfill sha-backfill-dry

# =============================================================================
# USER-FRIENDLY COMMANDS (Easy setup and daily use)
# =============================================================================

# First-time setup commands
first-time-setup: ## Complete first-time setup from scratch
	@echo "🚀 Starting complete Email Sync setup..."
	@echo ""
	@echo "Step 1: Installing dependencies..."
	@$(MAKE) install-dev
	@echo ""
	@echo "Step 2: Testing basic functionality..."
	@$(MAKE) test-basic
	@echo ""
	@echo "Step 3: Setting up vector search..."
	@$(MAKE) install-qdrant || echo "⚠️  Vector search setup failed (optional)"
	@echo ""
	@echo "Step 4: Running health check..."
	@$(MAKE) health-check
	@echo ""
	@echo "✅ Setup complete! Try: make search QUERY=\"test\""

test-basic: ## Test basic system functionality (no external dependencies)
	@$(PYTHON) tools/scripts/make_helpers.py test_basic

install-qdrant: ## Install Qdrant vector database locally
	@echo "📦 Installing Qdrant vector database..."
	@if [ ! -f ~/bin/qdrant ]; then \
		echo "   Downloading Qdrant..."; \
		mkdir -p ~/bin; \
		if [ "$$(uname -m)" = "arm64" ]; then \
			curl -L -o /tmp/qdrant.tar.gz https://github.com/qdrant/qdrant/releases/download/v1.15.3/qdrant-aarch64-apple-darwin.tar.gz; \
		else \
			curl -L -o /tmp/qdrant.tar.gz https://github.com/qdrant/qdrant/releases/download/v1.15.3/qdrant-x86_64-apple-darwin.tar.gz; \
		fi; \
		tar -xzf /tmp/qdrant.tar.gz -C /tmp; \
		cp /tmp/qdrant ~/bin/qdrant; \
		chmod +x ~/bin/qdrant; \
		rm -f /tmp/qdrant.tar.gz; \
		echo "✅ Qdrant installed to ~/bin/qdrant"; \
	else \
		echo "✅ Qdrant already installed"; \
	fi
	@$(MAKE) start-qdrant

test-vector: ensure-qdrant ## Test vector search functionality
	@echo "🧪 Testing vector search..."
	@$(MAKE) vector-smoke

# Daily use commands
search: ## Search documents (usage: make search QUERY="your search terms")
	@if [ -z "$(QUERY)" ]; then \
		echo "❌ Usage: make search QUERY=\"your search terms\""; \
		echo "   Example: make search QUERY=\"contract terms\""; \
		exit 1; \
	fi
	@echo "🔍 Searching for: $(QUERY)"
	@tools/scripts/vsearch search "$(QUERY)"

upload: ## Upload document (usage: make upload FILE="document.pdf")
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Usage: make upload FILE=\"document.pdf\""; \
		echo "   Example: make upload FILE=\"contract.pdf\""; \
		exit 1; \
	fi
	@echo "📄 Uploading: $(FILE)"
	@tools/scripts/vsearch upload "$(FILE)"

sync-gmail: ## Sync Gmail emails
	@echo "📧 Syncing Gmail emails..."
	@tools/scripts/vsearch sync-gmail

health-check: ## Quick system health check
	@echo "🏥 System Health Check"
	@echo "===================="
	@tools/scripts/vsearch info
	@echo ""
	@$(MAKE) diag-wiring

recent-activity: ## Show recent system activity
	@$(PYTHON) tools/scripts/make_helpers.py recent_activity

# Setup and configuration commands
install-all: install-dev install-qdrant ## Install all components including optional ones
	@echo "✅ All components installed!"

setup-gmail: ## Setup Gmail integration (interactive)
	@echo "📧 Setting up Gmail integration..."
	@echo "This requires Gmail API credentials."
	@echo "Visit: https://developers.google.com/gmail/api/quickstart"
	@echo "Follow the setup guide in gmail/CLAUDE.md"

test-everything: ## Run comprehensive system test
	@echo "🧪 Running comprehensive tests..."
	@$(MAKE) test-basic
	@$(MAKE) test-vector
	@$(MAKE) health-check
	@echo "✅ All tests passed!"

# Maintenance commands
update-system: ## Update system components
	@echo "🔄 Updating system components..."
	@$(PIP) install --upgrade -r requirements.txt
	@$(PIP) install --upgrade -r requirements-dev.txt
	@echo "✅ System updated!"

backup: ## Backup your data
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	cp data/emails.db "backups/emails_$$timestamp.db"; \
	tar -czf "backups/qdrant_data_$$timestamp.tar.gz" qdrant_data/ 2>/dev/null || true; \
	echo "✅ Backup created: backups/emails_$$timestamp.db"

diagnose: ## Run comprehensive system diagnostics
	@echo "🔬 Running system diagnostics..."
	@echo ""
	@echo "=== Basic Health ==="
	@$(MAKE) health-check
	@echo ""
	@echo "=== Memory Usage ==="
	@$(MAKE) memory-check
	@echo ""
	@echo "=== Disk Space ==="
	@$(MAKE) check-disk-space
	@echo ""
	@echo "=== Recent Activity ==="
	@$(MAKE) recent-activity

# Utility commands
check-requirements: ## Check system requirements
	@echo "🔍 Checking system requirements..."
	@echo -n "Python version: "; python3 --version
	@echo -n "Available memory: "; \
	if command -v free >/dev/null 2>&1; then \
		free -h | grep Mem | awk '{print $$7}'; \
	elif command -v vm_stat >/dev/null 2>&1; then \
		vm_stat | grep "Pages free" | awk '{print int($$3) * 4096 / 1024 / 1024 "MB"}'; \
	else \
		echo "Unable to check"; \
	fi
	@echo -n "Disk space: "; df -h . | tail -1 | awk '{print $$4" available"}'
	@echo ""
	@if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then \
		echo "✅ Python 3.8+ detected"; \
	else \
		echo "❌ Python 3.8+ required"; \
	fi

setup-gmail-auth: ## Setup Gmail API authentication
	@echo "🔑 Gmail API setup instructions:"
	@echo "1. Go to: https://console.developers.google.com/"
	@echo "2. Create a new project or select existing"
	@echo "3. Enable Gmail API"
	@echo "4. Create OAuth 2.0 credentials"
	@echo "5. Download credentials.json to project root"
	@echo "6. Run: tools/scripts/vsearch sync-gmail"

test-gmail: ## Test Gmail connection
	@$(PYTHON) tools/scripts/make_helpers.py test_gmail

sync-gmail-recent: ## Sync recent Gmail emails (last 100)
	@echo "📧 Syncing recent emails..."
	@tools/scripts/vsearch process -n 100

# Statistics and monitoring
db-stats: ## Show database statistics
	@$(PYTHON) tools/scripts/make_helpers.py db_stats

performance-stats: ## Show performance statistics
	@$(PYTHON) tools/scripts/make_helpers.py performance_stats

# Quick fixes
reindex-all: ensure-qdrant ## Reindex all content for search
	@echo "🔄 Reindexing all content..."
	@$(MAKE) vector-sync

start-qdrant: ## Start Qdrant vector database
	@$(MAKE) ensure-qdrant

qdrant-status: ## Check Qdrant status
	@echo "📊 Qdrant Status"
	@echo "==============="
	@if curl -s http://localhost:6333/readyz >/dev/null 2>&1; then \
		echo "✅ Qdrant is running"; \
		curl -s http://localhost:6333/ | head -5; \
	else \
		echo "❌ Qdrant is not running"; \
		echo "   Run: make start-qdrant"; \
	fi

fix-permissions: ## Fix file permissions
	@echo "🔧 Fixing file permissions..."
	@chmod +x tools/scripts/vsearch 2>/dev/null || true
	@chmod +x tools/scripts/* 2>/dev/null || true
	@echo "✅ Permissions fixed"

check-disk-space: ## Check available disk space
	@echo "💾 Disk Space Check"
	@echo "=================="
	@df -h . | head -1
	@df -h . | tail -1
	@echo ""
	@du -sh data/ 2>/dev/null || echo "No data directory"
	@du -sh qdrant_data/ 2>/dev/null || echo "No qdrant_data directory"

memory-check: ## Check memory usage
	@echo "🧠 Memory Check"
	@echo "=============="
	@if command -v ps >/dev/null 2>&1; then \
		ps aux | grep -E "(python|qdrant)" | grep -v grep | head -5; \
	else \
		echo "Unable to check memory usage"; \
	fi

system-report: ## Generate comprehensive system report
	@echo "📋 Email Sync System Report"
	@echo "==========================="
	@date
	@echo ""
	@$(MAKE) check-requirements
	@echo ""
	@$(MAKE) db-stats
	@echo ""
	@$(MAKE) qdrant-status
	@echo ""
	@$(MAKE) performance-stats

# Advanced configuration (placeholders for future implementation)
configure-advanced: ## Configure advanced system settings
	@echo "⚙️  Advanced configuration (coming soon)"
	@echo "Edit config/settings.py for now"

setup-backups: ## Setup automated backups
	@echo "💾 Automated backup setup (coming soon)"
	@echo "For now, run: make backup"

setup-search-aliases: ## Setup custom search aliases
	@echo "🔍 Search alias setup (coming soon)"
	@echo "For now, use: make search QUERY=\"...\""

optimize-db: ## Optimize database performance
	@$(PYTHON) tools/scripts/make_helpers.py optimize_db

cleanup-old-data: ## Clean up old temporary data
	@echo "🧹 Cleaning up old data..."
	@find data/staged/ -type f -mtime +7 -delete 2>/dev/null || true
	@find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null || true
	@echo "✅ Old data cleaned up"

monitor-performance: ## Monitor system performance
	@echo "📊 Performance monitoring (coming soon)"
	@echo "For now, use: make performance-stats"

encrypt-database: ## Encrypt database (placeholder)
	@echo "🔒 Database encryption (coming soon)"
	@echo "Currently using SQLite without encryption"

setup-secure-backups: ## Setup secure encrypted backups
	@echo "🔐 Secure backup setup (coming soon)"
	@echo "For now, use: make backup"
