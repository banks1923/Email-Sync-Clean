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
	@echo "  make backup         Backup your data"
	@echo ""
	@echo "📄 CONTENT:"
	@echo "  make search QUERY=\"terms\"    Search documents"
	@echo "  make upload FILE=\"doc.pdf\"   Upload document"
	@echo "  make sync                     Sync Gmail emails"
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
	pytest -c .config/pytest.ini -m "not slow" -v --tb=short

test-all: ## Run all tests (including slow AI tests)
	@echo "🧪 Running complete test suite..."
	pytest -c .config/pytest.ini -v

format: ## Format code (black, isort, docformatter)
	@echo "🎨 Formatting code..."
	black .
	isort .
	find . -name "*.py" -not -path "*/__pycache__/*" | xargs docformatter --in-place --make-summary-multi-line
	@echo "✅ Code formatted"

lint: ## Check code quality (flake8, ruff, mypy)
	@echo "🔍 Checking code quality..."
	@echo "Running flake8..."
	@flake8 --config .config/.flake8 . || true
	@echo "Running ruff..."
	@ruff check . --statistics || true
	@echo "Running mypy..."
	@mypy --config-file .config/mypy.ini gmail/ shared/ utilities/ infrastructure/ --ignore-missing-imports || true

fix: ## Auto-fix common code issues
	@echo "🔧 Auto-fixing issues..."
	ruff check . --fix --unsafe-fixes
	autoflake --remove-all-unused-imports --remove-unused-variables --in-place --recursive .
	$(MAKE) format
	@echo "✅ Auto-fixes applied"

clean: ## Clean up cache files and temporary data
	@echo "🧹 Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@rm -rf .mypy_cache/ .pytest_cache/ .ruff_cache/ htmlcov/ .coverage 2>/dev/null || true
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
	@$(PYTHON) -c "from shared.simple_db import SimpleDB; db = SimpleDB(); print('✅ Database connected'); cursor = db.execute('SELECT COUNT(*) FROM content_unified'); print(f'   Content records: {cursor.fetchone()[0]}'); cursor = db.execute('SELECT COUNT(*) FROM individual_messages'); print(f'   Email messages: {cursor.fetchone()[0]}')" 2>/dev/null || echo "❌ Database connection failed"
	@echo ""
	@echo "🔍 Search status:"
	@tools/scripts/vsearch info 2>/dev/null || echo "❌ Search system unavailable"

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
	@if ! curl -s http://localhost:6333/readyz >/dev/null 2>&1; then \
		echo "🚀 Starting vector database..."; \
		if [ ! -f ~/bin/qdrant ]; then \
			echo "❌ Qdrant not installed. Run 'make setup' first"; \
			exit 1; \
		fi; \
		QDRANT__STORAGE__PATH=./qdrant_data ~/bin/qdrant > qdrant.log 2>&1 & \
		echo "   Waiting for startup..."; \
		for i in 1 2 3 4 5; do \
			sleep 2; \
			if curl -s http://localhost:6333/readyz >/dev/null 2>&1; then \
				echo "✅ Vector database started"; \
				break; \
			fi; \
			if [ $$i -eq 5 ]; then \
				echo "❌ Failed to start vector database. Check qdrant.log"; \
				exit 1; \
			fi; \
		done; \
	fi

stop-qdrant: ## Stop Qdrant vector database
	@if pgrep -f "qdrant" >/dev/null 2>&1; then \
		echo "🛑 Stopping vector database..."; \
		pkill -f "qdrant"; \
		sleep 2; \
		echo "✅ Vector database stopped"; \
	fi

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
	@$(PYTHON) -c "from shared.simple_db import SimpleDB; db = SimpleDB(); print('✅ Database working')" || echo "❌ Database test failed"
	@$(PYTHON) -c "from utilities.embeddings.embedding_service import get_embedding_service; svc = get_embedding_service(); result = svc.encode('test'); print('✅ Embeddings working') if len(result) == 1024 else print('❌ Embeddings failed')" || echo "❌ Embeddings test failed"
	@echo "✅ Basic tests passed"