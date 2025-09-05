# Configuration Management Guide

## Configuration Overview

The system uses a centralized configuration approach with Pydantic settings, environment variables, and tool-specific config files.

## Directory Structure

```
.config/                        # Centralized tool configurations
├── .coveragerc                 # Coverage.py configuration
├── .flake8                     # Flake8 linting rules
├── .markdownlint.json         # Markdownlint documentation style
├── .mcpignore                 # MCP server ignore patterns
├── .pre-commit-config.yaml    # Pre-commit hooks
├── .radon.cfg                 # Radon complexity analysis
├── mypy.ini                   # MyPy type checking
├── pyrightconfig.json         # Pyright (VS Code) type checking
├── pytest.ini                 # Pytest configuration
└── settings.py                # Centralized application settings

config/                         # Application configuration
└── settings.py                # Main Pydantic settings

.envrc                         # direnv environment loader
.env                          # Local environment variables
~/Secrets/.env                # User secrets (preferred location)
```

## Environment Variables

### Core Application Settings

```bash
# Logging Configuration
LOG_LEVEL=INFO                 # Options: DEBUG, INFO, WARNING, ERROR
USE_LOGURU=true               # Enable enhanced logging with loguru

# Python Configuration
PYTHONPATH=/path/to/project   # Project root path

# Database Configuration
DB_PATH=data/system_data/emails.db  # SQLite database location

# Storage Paths
MCP_STORAGE_DIR=data/sequential_thinking  # MCP data storage
```

### Qdrant Vector Database

```bash
# Qdrant Connection
QDRANT_HOST=localhost         # Qdrant server host
QDRANT_PORT=6333             # Qdrant server port
QDRANT_TIMEOUT_S=0.5         # Connection timeout in seconds

# Qdrant Storage
QDRANT__STORAGE__PATH=./qdrant_data    # Data storage path
QDRANT__LOG__PATH=./logs/qdrant.log    # Log file path

# Qdrant Control
QDRANT_DISABLED=1            # Force mock vector store (testing)
```

### Testing & Development

```bash
# Test Mode Configuration
TEST_MODE=1                  # Use mock services for testing
SKIP_MODEL_LOAD=1           # Skip loading ML models
DEBUG=1                     # Enable debug output

# CI/CD Environment
CI=true                     # Running in CI environment
GITHUB_ACTIONS=true         # Running in GitHub Actions
```

### API Keys & Secrets

```bash
# AI Service API Keys (stored in ~/Secrets/.env)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
PERPLEXITY_API_KEY=pplx-...
GOOGLE_API_KEY=...
MISTRAL_API_KEY=...

# Email Service
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
```

## Configuration Files

### Pydantic Settings (`config/settings.py`)

```python
from pydantic import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Database
    db_path: Path = Path("data/system_data/emails.db")
    
    # Logging
    log_level: str = "INFO"
    use_loguru: bool = True
    
    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_timeout: float = 0.5
    
    # Testing
    test_mode: bool = False
    skip_model_load: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

### Tool Configurations

#### Pytest (`pytest.ini`)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
```

#### Coverage (`.coveragerc`)
```ini
[run]
source = .
omit = 
    tests/*
    */migrations/*
    */venv/*
    */virtualenv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
```

#### Flake8 (`.flake8`)
```ini
[flake8]
max-line-length = 120
exclude = .git,__pycache__,venv,migrations
ignore = E203, W503
```

#### MyPy (`mypy.ini`)
```ini
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = False
ignore_missing_imports = True
```

## Environment Setup

### Using direnv (Recommended)

1. Install direnv:
```bash
# macOS
brew install direnv

# Ubuntu/Debian
apt-get install direnv
```

2. Hook into shell:
```bash
# Add to ~/.bashrc or ~/.zshrc
eval "$(direnv hook bash)"  # or zsh
```

3. Allow project:
```bash
cd /path/to/project
direnv allow
```

### Manual Environment Setup

```bash
# Load environment variables
source .envrc

# Or export manually
export PYTHONPATH="$(pwd)"
export LOG_LEVEL=DEBUG
export USE_LOGURU=true
```

### Secrets Management

1. **Preferred Location**: `~/Secrets/.env`
```bash
# Create secrets file
mkdir -p ~/Secrets
touch ~/Secrets/.env
chmod 600 ~/Secrets/.env
```

2. **Add API Keys**:
```bash
# Edit ~/Secrets/.env
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
```

3. **Load Order** (`.envrc`):
   - First: `/secrets/.env` (Docker/container)
   - Second: `~/Secrets/.env` (user home)
   - Third: `./.env` (project local)

## Configuration Priority

Configuration values are resolved in this order (highest to lowest priority):

1. **Command-line arguments**: `--log-level DEBUG`
2. **Environment variables**: `LOG_LEVEL=DEBUG`
3. **`.env` file**: `LOG_LEVEL=INFO`
4. **Config files**: `.config/settings.py`
5. **Default values**: Hardcoded defaults

## Make Command Configuration

All make commands use centralized configs:

```makefile
# Linting with config
lint:
    flake8 --config .config/.flake8 .

# Testing with config
test:
    pytest -c .config/pytest.ini tests/

# Coverage with config
coverage:
    coverage run --rcfile=.config/.coveragerc -m pytest
```

## Development Workflows

### Debug Mode
```bash
# Enable all debug features
export DEBUG=1
export LOG_LEVEL=DEBUG
export USE_LOGURU=true
python3 -m gmail.main
```

### Test Mode
```bash
# Use all mocks for fast testing
export TEST_MODE=1
export SKIP_MODEL_LOAD=1
export QDRANT_DISABLED=1
pytest tests/
```

### Production Mode
```bash
# Production settings
export LOG_LEVEL=INFO
export TEST_MODE=0
unset DEBUG
make ensure-qdrant
python3 -m cli search "query"
```

## Configuration Validation

### Check Current Configuration
```bash
# View all environment variables
env | grep -E "^(LOG_|QDRANT_|TEST_|SKIP_)"

# Check Python path
python3 -c "import sys; print(sys.path)"

# Verify database path
python3 -c "from lib.db import SimpleDB; print(SimpleDB().get_db_path())"

# Check Qdrant settings
python3 -c "from lib.vector_store import get_vector_store; vs = get_vector_store(); print(vs.health_check())"
```

### Validate Configurations
```bash
# Validate all config files
make validate-configs

# Check specific config
python3 -m config.settings --validate

# Test environment loading
python3 -c "from config.settings import Settings; s = Settings(); print(s.dict())"
```

## Common Configuration Issues

### Issue: Environment Variables Not Loading
```bash
# Check direnv status
direnv status

# Manually reload
direnv allow .

# Or source directly
source .envrc
```

### Issue: API Keys Not Found
```bash
# Check load order
ls -la ~/Secrets/.env
ls -la ./.env

# Test key loading
python3 -c "import os; print('API Key set:', bool(os.getenv('ANTHROPIC_API_KEY')))"
```

### Issue: Wrong Database Path
```bash
# Check centralized path
python3 -c "from config.settings import get_db_path; print(get_db_path())"

# Verify database exists
ls -la data/system_data/emails.db
```

### Issue: Qdrant Connection Failed
```bash
# Check Qdrant status
curl http://localhost:6333/collections

# Start Qdrant
make ensure-qdrant

# Or use mock
export QDRANT_DISABLED=1
```

## Configuration Best Practices

1. **Never commit secrets**: Add `.env` to `.gitignore`
2. **Use environment variables**: For deployment-specific settings
3. **Centralize configurations**: In `.config/` directory
4. **Document all variables**: In this file and `.env.example`
5. **Validate on startup**: Check required configs early
6. **Provide defaults**: For optional configurations
7. **Use type hints**: In Pydantic settings classes
8. **Log configuration**: At startup (without secrets)

## Configuration Checklist

- [ ] All API keys in `~/Secrets/.env`
- [ ] `.envrc` configured and allowed
- [ ] Python path includes project root
- [ ] Database path correctly set
- [ ] Qdrant configured or disabled
- [ ] Log level appropriate for environment
- [ ] Test mode disabled in production
- [ ] All make commands use `.config/` files