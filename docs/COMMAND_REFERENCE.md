# Command Reference

This reference is auto-generated from the `Makefile`. Do not edit it manually.

| Command | Description |
|---|---|| `make help` | Show available commands |
| `make setup` | Complete setup from scratch (recommended for first time) |
| `make install` | Install Python dependencies |
| `make test` | Run tests (fast, for daily development) |
| `make test-all` | Run all tests (including slow AI tests) |
| `make format` | Format code (black, isort, docformatter) |
| `make lint` | Check code quality (flake8, ruff, mypy) |
| `make fix` | Auto-fix common code issues |
| `make clean` | Clean up cache files and temporary data |
| `make status` | Quick system health check |
| `make diagnose` | Deep system diagnostic (when things are broken) |
| `make cloc` | Count lines, excluding caches/venvs/data |
| `make cloc-tracked` | Count lines for git-tracked files only |
| `make search QUERY="..."` | Search documents (usage: make search QUERY="your terms") |
| `make upload FILE="..."` | Upload document (usage: make upload FILE="document.pdf") |
| `make sync` | Sync Gmail emails |
| `make backup` | Backup your data |
| `make reset` | Nuclear reset - use when system is completely broken |
| `make ensure-qdrant` | Ensure Qdrant vector database is running |
| `make stop-qdrant` | Stop Qdrant vector database |
| `make restart-qdrant` | Restart Qdrant vector database |
| `make qdrant-status` | Check Qdrant vector database status |
| `make install-qdrant` | Install Qdrant vector database |
| `make test-basic` | Basic functionality test (no external dependencies) |
| `make pipeline-start` | Start chunk+embed in background (LIMIT,BATCH,TOKENS optional) |
| `make pipeline-run` | Run chunk+embed in foreground with live output |
| `make pipeline-status` | Show pipeline PID, DB counts, recent log |
| `make pipeline-tail` | Tail the latest pipeline log |
| `make pipeline-stop` | Stop the background pipeline process |
