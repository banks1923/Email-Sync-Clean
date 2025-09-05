#!/usr/bin/env bash
set -euo pipefail

cmd=${1:-help}
ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)

function hygiene() {
  echo "== Hygiene checks (search surface) =="
  echo "Broad exception handlers (should be 0):"
  rg -n "except Exception" lib/ cli/ infrastructure/mcp_servers/ || true

  echo "Legacy imports (should be 0, excluding archive):"
  rg -n "search_intelligence" -g '!archive/**' || true

  # Fail if any matches
  if rg -n "except Exception" lib/ cli/ infrastructure/mcp_servers/ >/dev/null; then
    echo "ERROR: Broad exception handlers remain." >&2
    exit 1
  fi
  if rg -n "search_intelligence" -g '!archive/**' >/dev/null; then
    echo "ERROR: Legacy search_intelligence imports remain." >&2
    exit 1
  fi
  echo "OK: Hygiene passed."
}

function smoke() {
  echo "== Smoke checks (TEST_MODE=1) =="
  export TEST_MODE=1
  set +e
  python -m cli admin info >/dev/null 2>&1
  INFO_RC=$?
  python -m cli admin health --json >/dev/null 2>&1
  HEALTH_RC=$?
  set -e
  echo "info rc=$INFO_RC health rc=$HEALTH_RC"
  if [[ $INFO_RC -ne 0 || $HEALTH_RC -ne 0 ]]; then
    echo "ERROR: CLI info/health failed under TEST_MODE." >&2
    exit 1
  fi
  echo "OK: Smoke passed."
}

case "$cmd" in
  hygiene) hygiene ;;
  smoke) smoke ;;
  *) echo "Usage: $0 {hygiene|smoke}" ; exit 2 ;;
esac

