.PHONY: help setup install test format lint fix clean status search upload sync backup

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip

# =============================================================================
# CORE USER WORKFLOWS - Simple, Straightforward Commands
# =============================================================================

help: ## Show available commands
	@echo "📧 Email Sync System - Simple Commands"
	@echo "======================================"
	@echo ""
	@echo "🚀 SETUP (first time):"
	@echo "  make setup          Install everything and get started"
	@echo ""
	@echo "⚡ DEVELOPMENT (daily):"
	@echo "  make test           Run tests (fast)"
	@echo "  make format         Format code"
	@echo "  make lint           Check code quality"
	@echo "  make fix            Auto-fix common issues"
	@echo "  make clean          Clean up cache files"
	@echo ""
	@echo "📊 SYSTEM:"
	@echo "  make status         System health check"
	@echo "  make cloc           LOC for repo (excludes caches/venvs)"
	@echo "  make cloc-tracked   LOC for git-tracked files only"
	@echo "  make backup         Backup your data"
	@echo ""
	@echo "📄 CONTENT:"
	@echo "  make search QUERY=\"terms\"    Search documents"
	@echo "  make upload FILE=\"doc.pdf\"   Upload document"
	@echo "  make sync                     Sync Gmail emails"
	@echo ""
	@echo "🧠 EMBEDDINGS PIPELINE (one-liners):"
	@echo "  make pipeline-start [LIMIT=20 BATCH=16 TOKENS=512]   Start chunk+embed in background"
	@echo "  make pipeline-run   [LIMIT=20 BATCH=16 TOKENS=512]   Run chunk+embed in foreground with live output"
	@echo "  make pipeline-status                                 Show PID, DB counts, last log lines"
	@echo "  make pipeline-tail                                    Tail latest pipeline log"
	@echo "  make pipeline-stop                                    Stop running pipeline"
	@echo ""
	@echo "🔧 TROUBLESHOOTING:"
	@echo "  make diagnose       Deep system diagnostic"
	@echo "  make reset          Nuclear reset (when broken)"
	@echo ""

# =============================================================================
# SETUP - One command to get everything working
# =============================================================================

setup: ## Complete setup from scratch (recommended for first time)
	@echo "🚀 Setting up Email Sync system..."
	@echo ""
	@echo "Step 1: Installing dependencies..."
	@$(MAKE) install
	@echo ""
	@echo "Step 2: Installing vector search..."
	@$(MAKE) install-qdrant
	@echo ""
	@echo "Step 3: Testing basic functionality..."
	@$(MAKE) test-basic
	@echo ""
	@echo "Step 4: Checking system status..."
	@$(MAKE) status
	@echo ""
	@echo "✅ Setup complete!"
	@echo ""
	@echo "Try these commands:"
	@echo "  make search QUERY=\"test\""
	@echo "  make sync"
	@echo "  make status"

install: ## Install Python dependencies
	@echo "📦 Installing dependencies..."
	$(PIP) install -r requirements.txt
	$(PIP) install -r requirements-dev.txt
	pre-commit install --config .config/.pre-commit-config.yaml
	@echo "✅ Dependencies installed"

# =============================================================================
# DEVELOPMENT - Clean, simple commands
# =============================================================================

test: ## Run tests (fast, for daily development)
	@echo "🧪 Running tests..."
	pytest -c .config/pytest.ini --rootdir=. -m "not slow" -v --tb=short

test-all: ## Run all tests (including slow AI tests)
	@echo "🧪 Running complete test suite..."
	pytest -c .config/pytest.ini --rootdir=. -v

format: ## Format code (black, isort, docformatter)
	@echo "🎨 Formatting code..."
	# Exclude vendor/venv/cache directories explicitly
	EXCLUDES='(.*/)?(\.venv|venv|env|node_modules|\.cache|site-packages)(/|$)'; \
	black --exclude "$$EXCLUDES" .; \
	isort --skip-gitignore --extend-skip-glob "**/.venv/**,**/site-packages/**,**/.cache/**" .; \
	find . -type f -name "*.py" \
	  -not -path "*/__pycache__/*" \
	  -not -path "*/.venv/*" \
	  -not -path "*/venv/*" \
	  -not -path "*/env/*" \
	  -not -path "*/node_modules/*" \
	  -not -path "*/.cache/*" \
	  -not -path "*/site-packages/*" \
	| xargs docformatter --in-place --make-summary-multi-line
	@echo "✅ Code formatted"

lint: ## Check code quality (flake8, ruff, mypy)
	@echo "🔍 Checking code quality..."
	@echo "Running flake8..."
	@flake8 --config .config/.flake8 --exclude .venv,venv,env,node_modules,.cache,**/site-packages/**,infrastructure/mcp_servers/mcp-sequential-thinking/.venv . || true
	@echo "Running ruff..."
	@ruff check . --statistics --exclude .venv,venv,env,node_modules,.cache,**/site-packages/**,infrastructure/mcp_servers/mcp-sequential-thinking/.venv || true
	@echo "Running mypy..."
	@mypy --config-file .config/mypy.ini gmail/ shared/ utilities/ infrastructure/ --ignore-missing-imports \
	  --exclude '(^|/)\.venv(/|$)|(^|/)venv(/|$)|(^|/)env(/|$)|(^|/)node_modules(/|$)|(^|/)\.cache(/|$)|(^|/)site-packages(/|$)|(^|/)infrastructure/mcp_servers/mcp-sequential-thinking/\.venv(/|$)' || true

fix: ## Auto-fix common code issues
	@echo "🔧 Auto-fixing issues..."
	ruff check . --fix --unsafe-fixes --exclude .venv,venv,env,node_modules,.cache,**/site-packages/**,infrastructure/mcp_servers/mcp-sequential-thinking/.venv
	# Run autoflake only on project files, not vendor/venv/cache
	find . -type f -name "*.py" \
	  -not -path "*/__pycache__/*" \
	  -not -path "*/.venv/*" \
	  -not -path "*/venv/*" \
	  -not -path "*/env/*" \
	  -not -path "*/node_modules/*" \
	  -not -path "*/.cache/*" \
	  -not -path "*/site-packages/*" \
	| xargs autoflake --remove-all-unused-imports --remove-unused-variables --in-place
	$(MAKE) format
	@echo "✅ Auto-fixes applied"

clean: ## Clean up cache files and temporary data
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@rm -rf .mypy_cache/ .pytest_cache/ .ruff_cache/ htmlcov/ .coverage .cache/ 2>/dev/null || true
	@find logs/ -name "*.log" -mtime +7 -delete 2>/dev/null || true
	@echo "✅ Cleanup complete"

# =============================================================================
# SYSTEM STATUS - Simple health checks
# =============================================================================

status: ## Quick system health check
	@echo "🏥 System Status"
	@echo "==============="
	@echo ""
	@$(MAKE) ensure-qdrant
	@echo ""
	@echo "📊 Database status:"
	@$(PYTHON) -c "from shared.db.simple_db import SimpleDB; db = SimpleDB(); print('✅ Database connected'); cursor = db.execute('SELECT COUNT(*) FROM content_unified'); print(f'   Content records: {cursor.fetchone()[0]}'); cursor = db.execute('SELECT COUNT(*) FROM individual_messages'); print(f'   Email messages: {cursor.fetchone()[0]}')" 2>/dev/null || echo "❌ Database connection failed"
	@echo ""
	@echo "🔍 Search status:"
	@tools/scripts/vsearch info 2>/dev/null || echo "❌ Search system unavailable"

# =============================================================================
# DATABASE MIGRATION COMMANDS
# =============================================================================

db.migrate: ## Apply database schema migration (adds metadata fields)
	@echo "🔄 Running database migration..."
	@echo ""
	@echo "This will add high-ROI metadata fields:"
	@echo "  • sha256 - Content deduplication"
	@echo "  • embedding_generated - Track vector generation"
	@echo "  • quality_score - Filter low-quality content"  
	@echo "  • is_validated - Content verification status"
	@echo ""
	@$(PYTHON) tools/migrations/analyze_duplicates.py
	@echo ""
	@$(PYTHON) tools/migrations/migrate_schema.py

db.verify: ## Verify database schema and integrity
	@echo "🔍 Verifying database schema..."
	@$(PYTHON) tools/migrations/verify_migration.py

diagnose: ## Deep system diagnostic (when things are broken)
	@echo "🔬 Running deep system diagnostic..."
	@echo ""
	@echo "=== Basic Health ==="
	@$(MAKE) status
	@echo ""
	@echo "=== Detailed Wiring Check ==="
	@$(PYTHON) tools/diag_wiring.py
	@echo ""
	@echo "=== Memory and Disk ==="
	@echo -n "Available memory: "
	@vm_stat | grep "Pages free" | awk '{print int($$3) * 4096 / 1024 / 1024 "MB"}' 2>/dev/null || echo "Unable to check"
	@echo -n "Disk space: "
	@df -h . | tail -1 | awk '{print $$4" available"}'
	@echo ""
	@echo "=== Recent Logs ==="
	@echo "Last 10 log entries:"
	@ls -la logs/ 2>/dev/null | head -5 || echo "No logs directory"

# =============================================================================
# CODE METRICS - Accurate line counts
# =============================================================================

cloc: ## Count lines, excluding caches/venvs/data
	@echo "📏 Counting lines (excluding caches/venvs/data via .clocignore)..."
	@cloc --exclude-list-file=.clocignore .

cloc-tracked: ## Count lines for git-tracked files only
	@echo "📏 Counting lines for git-tracked files only..."
	@cloc --vcs=git

# =============================================================================
# CONTENT OPERATIONS - User-facing functionality
# =============================================================================

search: ## Search documents (usage: make search QUERY="your terms")
	@if [ -z "$(QUERY)" ]; then \
		echo "❌ Usage: make search QUERY=\"your search terms\""; \
		echo "Example: make search QUERY=\"contract terms\""; \
		exit 1; \
	fi
	@echo "🔍 Searching for: $(QUERY)"
	@$(MAKE) ensure-qdrant
	@tools/scripts/vsearch search "$(QUERY)"

upload: ## Upload document (usage: make upload FILE="document.pdf")
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Usage: make upload FILE=\"document.pdf\""; \
		echo "Example: make upload FILE=\"contract.pdf\""; \
		exit 1; \
	fi
	@echo "📄 Uploading: $(FILE)"
	@$(MAKE) ensure-qdrant
	@tools/scripts/vsearch upload "$(FILE)"

sync: ## Sync Gmail emails
	@echo "📧 Syncing Gmail emails..."
	@$(MAKE) ensure-qdrant
	@tools/scripts/vsearch sync-gmail

# =============================================================================
# BACKUP & MAINTENANCE
# =============================================================================

backup: ## Backup your data
	@echo "💾 Creating backup..."
	@mkdir -p backups
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	cp data/system_data/emails.db "backups/emails_$$timestamp.db" 2>/dev/null || cp data/emails.db "backups/emails_$$timestamp.db" 2>/dev/null || echo "❌ No database found to backup"; \
	tar -czf "backups/qdrant_data_$$timestamp.tar.gz" qdrant_data/ 2>/dev/null || echo "⚠️ No vector data to backup"; \
	echo "✅ Backup created with timestamp: $$timestamp"

reset: ## Nuclear reset - use when system is completely broken
	@echo "💥 Nuclear Reset - This will:"
	@echo "   - Stop all services"
	@echo "   - Clear all caches"
	@echo "   - Reset vector database"
	@echo "   - Keep your email database intact"
	@echo ""
	@read -p "Are you sure? Type 'yes' to continue: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "🛑 Stopping services..."; \
		$(MAKE) stop-qdrant; \
		echo "🧹 Clearing caches..."; \
		$(MAKE) clean; \
		echo "🗑️ Resetting vector database..."; \
		rm -rf qdrant_data/ 2>/dev/null || true; \
		echo "🚀 Restarting services..."; \
		$(MAKE) ensure-qdrant; \
		echo "✅ Reset complete! Run 'make status' to verify"; \
	else \
		echo "❌ Reset cancelled"; \
	fi

# =============================================================================
# INTERNAL UTILITIES (used by other commands)
# =============================================================================

ensure-qdrant: ## Ensure Qdrant vector database is running
	@./scripts/shell/manage_qdrant.sh start

stop-qdrant: ## Stop Qdrant vector database
	@./scripts/shell/manage_qdrant.sh stop

restart-qdrant: ## Restart Qdrant vector database
	@./scripts/shell/manage_qdrant.sh restart

qdrant-status: ## Check Qdrant vector database status
	@./scripts/shell/manage_qdrant.sh status

install-qdrant: ## Install Qdrant vector database
	@echo "📦 Installing vector database..."
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
		echo "✅ Vector database installed"; \
	else \
		echo "✅ Vector database already installed"; \
	fi
	@$(MAKE) ensure-qdrant

test-basic: ## Basic functionality test (no external dependencies)
	@echo "🧪 Testing basic functionality..."
	@$(PYTHON) -c "from shared.db.simple_db import SimpleDB; db = SimpleDB(); print('✅ Database working')" || echo "❌ Database test failed"
	@$(PYTHON) -c "from utilities.embeddings.embedding_service import get_embedding_service; svc = get_embedding_service(); result = svc.encode('test'); print('✅ Embeddings working') if len(result) == 1024 else print('❌ Embeddings failed')" || echo "❌ Embeddings test failed"
	@echo "✅ Basic tests passed"

# =============================================================================
# EMBEDDINGS PIPELINE - Simple background controls
# =============================================================================

# Start chunking + embeddings in background with logging
# Usage: make pipeline-start [LIMIT=20] [BATCH=16] [TOKENS=512]
pipeline-start: ## Start chunk+embed in background (LIMIT,BATCH,TOKENS optional)
	@echo "🚀 Starting embeddings pipeline (background)"
	@$(MAKE) ensure-qdrant
	@mkdir -p logs
	@stamp=$$(date +%F_%H%M%S); \
	log=logs/pipeline_$$stamp.log; \
	echo "Log: $$log"; \
	BATCH_VAL=$${BATCH:-16}; \
	TOKENS_VAL=$${TOKENS:-512}; \
	LIMIT_FLAG=$$( [ -n "$$LIMIT" ] && echo "--limit $$LIMIT" ); \
	( EMBEDDING_BATCH_SIZE=$$BATCH_VAL EMBEDDING_MAX_TOKENS=$$TOKENS_VAL nohup $(PYTHON) tools/scripts/vsearch chunk-ingest --embeddings --batch-size $$BATCH_VAL $$LIMIT_FLAG > "$$log" 2>&1 & echo $$! > logs/pipeline.pid ); \
	ps -p $$(cat logs/pipeline.pid) -o pid,etime,%%cpu,%%mem,command | sed -n '1,2p'

# Run in foreground with line-buffered output and log capture
# Usage: make pipeline-run [LIMIT=20] [BATCH=16] [TOKENS=512]
pipeline-run: ## Run chunk+embed in foreground with live output
	@$(MAKE) ensure-qdrant
	@mkdir -p logs
	@stamp=$$(date +%F_%H%M%S); \
	log=logs/pipeline_$$stamp.log; \
	echo "📜 Logging to: $$log"; \
	BATCH_VAL=$${BATCH:-16}; \
	TOKENS_VAL=$${TOKENS:-512}; \
	LIMIT_FLAG=$$( [ -n "$$LIMIT" ] && echo "--limit $$LIMIT" ); \
	EMBEDDING_BATCH_SIZE=$$BATCH_VAL EMBEDDING_MAX_TOKENS=$$TOKENS_VAL stdbuf -oL -eL $(PYTHON) tools/scripts/vsearch chunk-ingest --embeddings --batch-size $$BATCH_VAL $$LIMIT_FLAG | tee "$$log"

# Show status: PID, quick DB counts, and last log lines
pipeline-status: ## Show pipeline PID, DB counts, recent log
	@PID=$$(cat logs/pipeline.pid 2>/dev/null || true); \
	if [ -z "$$PID" ]; then echo "❌ No PID file found (logs/pipeline.pid)"; exit 0; fi; \
	if ps -p "$$PID" >/dev/null 2>&1; then echo "✅ RUNNING: PID $$PID"; else echo "⚠️  Not running (stale PID $$PID)"; fi; \
	$(PYTHON) - << 'PY'
	import sqlite3, json
	path='data/system_data/emails.db'
	try:
	  con=sqlite3.connect(path); con.row_factory=sqlite3.Row; cur=con.cursor()
	  def q(sql):
	    try: return cur.execute(sql).fetchone()['c']
	    except Exception as e: return f"err: {e}"
	  counts={
	    'ready_to_chunk': q("""
	      SELECT COUNT(*) c FROM content_unified d
	      WHERE d.ready_for_embedding=1 AND d.source_type='email_message'
	      AND NOT EXISTS (
	        SELECT 1 FROM content_unified c2
	        WHERE c2.source_type='document_chunk' AND c2.source_id LIKE d.source_id || ':%'
	      )
	    """),
	    'chunks_total': q("SELECT COUNT(*) c FROM content_unified WHERE source_type='document_chunk'"),
	    'chunks_embedded': q("SELECT COUNT(*) c FROM content_unified WHERE source_type='document_chunk' AND embedding_generated=1"),
	    'chunks_pending_embed': q("SELECT COUNT(*) c FROM content_unified WHERE source_type='document_chunk' AND ready_for_embedding=1 AND embedding_generated=0")
	  }
	  print(json.dumps(counts))
	except Exception as e:
	  print('{"db":"unavailable","error":"%s"}' % e)
	PY
	@log_latest=$$(ls -t logs/pipeline_*.log 2>/dev/null | head -n1 || true); \
	if [ -n "$$log_latest" ]; then echo "--- $$log_latest (last 20) ---"; tail -n 20 "$$log_latest"; else echo "No pipeline logs found"; fi

# Tail the latest pipeline log
pipeline-tail: ## Tail the latest pipeline log
	@log_latest=$$(ls -t logs/pipeline_*.log 2>/dev/null | head -n1 || true); \
	if [ -z "$$log_latest" ]; then echo "❌ No pipeline logs found"; exit 1; fi; \
	echo "📜 Tailing: $$log_latest"; \
	tail -f "$$log_latest"

# Stop the running pipeline
pipeline-stop: ## Stop the background pipeline process
	@PID=$$(cat logs/pipeline.pid 2>/dev/null || true); \
	if [ -z "$$PID" ]; then echo "❌ No PID file found (logs/pipeline.pid)"; exit 0; fi; \
	if ps -p "$$PID" >/dev/null 2>&1; then echo "🛑 Killing $$PID"; kill "$$PID"; sleep 1; else echo "ℹ️  Process not running"; fi; \
	rm -f logs/pipeline.pid

# Validate import depth rules
validate-imports: ## Check for deep import violations
	@echo "🔍 Validating import depth rules..."
	@python3 scripts/validate_imports.py

# Run all validation checks
validate: validate-imports ## Run all validation checks
	@echo "✅ All validations passed"
