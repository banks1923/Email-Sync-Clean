#!/bin/bash
# Cache directory configuration for Python tools
# Source this file if the tools don't respect pyproject.toml settings

# Create cache directory if it doesn't exist
mkdir -p .cache

# Python tool caches (backup environment variables)
# These are fallbacks - the tools should use pyproject.toml settings first
export MYPY_CACHE_DIR=".cache/mypy_cache"
export RUFF_CACHE_DIR=".cache/ruff_cache"
export HYPOTHESIS_STORAGE_DIRECTORY=".cache/hypothesis"

echo "Python tool cache directories configured to use .cache/"