#!/bin/bash
# Cache directory configuration
# Source this file or add to your shell profile to redirect temp directories

# Create cache directory if it doesn't exist
mkdir -p .cache

# Google Drive Desktop temp directories
export TMPDIR=".cache/tmp"
export TEMP=".cache/tmp" 
export TMP=".cache/tmp"

# Create temp directory
mkdir -p $TMPDIR

# Python tool caches (backup environment variables)
export MYPY_CACHE_DIR=".cache/mypy_cache"
export RUFF_CACHE_DIR=".cache/ruff_cache"
export HYPOTHESIS_STORAGE_DIRECTORY=".cache/hypothesis"

echo "Cache directories configured to use .cache/"