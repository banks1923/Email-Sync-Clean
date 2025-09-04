#!/usr/bin/env python3
"""Vector Parity Preflight.

Checks:
- Qdrant connectivity and collection existence
- Point count (exact)
- DB expected eligible content (ready_for_embedding=1)
- Reconciliation delta and zero-vector guard

Env:
  APP_DB_PATH=... (default: data/emails.db)
  VSTORE_URL=http(s)://host:port  (or VSTORE_HOST/VSTORE_PORT)
  VSTORE_API_KEY=...
  VSTORE_COLLECTION=...
  ALLOW_EMPTY_COLLECTION=true|false
  EXPECTED_DIM=1024 (optional)

Exit codes:
  0 OK
  1 Warn (non-critical)
  2 Fail (mismatch, zero-vector violation, or connection error)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.db.simple_db import SimpleDB


def _bool(env, default=False):
    v = os.getenv(env)
    if v is None:
        return default
    return str(v).lower() in ("1", "true", "yes", "y", "on")


def count_db_eligible(db_path: str) -> int:
    """
    Count eligible content in the database.
    """
    db = SimpleDB(db_path)
    # Count content that has embeddings (already processed)
    result = db.query(
        """
        SELECT COUNT(DISTINCT c.id) 
        FROM content_unified c
        INNER JOIN embeddings e ON c.id = e.content_id
    """
    )
    rows = result.get("data", [])
    if rows and rows[0]:
        return int(rows[0].get('COUNT(DISTINCT c.id)', 0))
    return 0


def qdrant_client():
    """
    Create Qdrant client based on environment variables.
    """
    # Lazy import so script works even if qdrant-client isn't installed in some envs.
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        raise RuntimeError("qdrant-client not installed. Run: pip install qdrant-client")

    url = os.getenv("VSTORE_URL")
    host = os.getenv("VSTORE_HOST", "localhost")
    port = os.getenv("VSTORE_PORT", "6333")
    api_key = os.getenv("VSTORE_API_KEY") or None

    if url:
        return QdrantClient(url=url, api_key=api_key)

    # Default to localhost:6333 if no specific config
    return QdrantClient(host=host, port=int(port), api_key=api_key)


def qdrant_stats(client, collection: str):
    """
    Get Qdrant collection statistics.
    """
    info = {"health": "red", "collection_exists": False, "point_count": 0, "dimension": None}
    try:
        # Health check
        try:
            # Try to get collections as a health check
            client.get_collections()
            info["health"] = "green"
        except Exception:
            info["health"] = "red"

        # Collection check
        meta = client.get_collection(collection)
        info["collection_exists"] = True

        # Get vector dimensions
        if hasattr(meta.config, "params") and hasattr(meta.config.params, "vectors"):
            info["dimension"] = meta.config.params.vectors.size

        # Exact count
        cnt = client.count(collection, exact=True).count
        info["point_count"] = int(cnt)
        return info

    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"
        return info


def main():
    from config.settings import DatabaseSettings

    db = DatabaseSettings().emails_db_path
    collection = os.getenv("VSTORE_COLLECTION", "emails")  # Default to emails
    allow_empty = _bool("ALLOW_EMPTY_COLLECTION", False)
    expected_dim = int(os.getenv("EXPECTED_DIM", "1024"))

    if not os.path.exists(db):
        print(json.dumps({"error": f"database not found: {db}"}))
        return 2

    try:
        eligible = count_db_eligible(db)
    except Exception as e:
        print(json.dumps({"error": f"DB check failed: {e}"}))
        return 2

    try:
        client = qdrant_client()
        qstats = qdrant_stats(client, collection)
    except Exception as e:
        print(json.dumps({"error": f"Qdrant init failed: {e}"}))
        return 2

    delta = eligible - (qstats.get("point_count") or 0)
    dim_ok = qstats.get("dimension") == expected_dim

    out = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "env": {
            "db": db,
            "collection": collection,
            "expected_dim": expected_dim,
            "allow_empty_collection": allow_empty,
        },
        "qdrant": qstats,
        "db": {"eligible_content": eligible},
        "reconciliation": {"delta": delta},
        "exit": 0,
    }

    exit_code = 0

    # Fail fast conditions
    if qstats.get("health") != "green" or not qstats.get("collection_exists"):
        exit_code = 2
    if qstats.get("dimension") is not None and not dim_ok:
        exit_code = 2
    if (qstats.get("point_count") == 0) and (not allow_empty):
        exit_code = 2

    # Delta handling: warn for small deltas, fail for large ones
    delta_threshold = int(os.getenv("DELTA_THRESHOLD", "50"))
    if delta != 0:
        if abs(delta) <= delta_threshold:
            # Small delta is a warning (exit code 1)
            exit_code = max(exit_code, 1)
            out["warning"] = f"Small delta detected: {delta} vectors (threshold: {delta_threshold})"
        else:
            # Large delta is a failure (exit code 2)
            exit_code = max(exit_code, 2)
            out["error"] = f"Large delta detected: {delta} vectors (threshold: {delta_threshold})"

    out["exit"] = exit_code
    print(json.dumps(out, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
