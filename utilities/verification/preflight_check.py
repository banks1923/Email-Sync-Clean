#!/usr/bin/env python3
"""Preflight check for PDF pipeline - verify schema and environment"""

import os
import sqlite3
import sys
from pathlib import Path


def check_schema():
    """
    Verify database schema has required columns.
    """

    db_path = os.getenv("APP_DB_PATH", "data/emails.db")

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check schema version
    try:
        cursor.execute("SELECT MAX(version) FROM schema_version")
        version = cursor.fetchone()[0]
        print(f"✓ Schema version: {version}")
    except sqlite3.OperationalError:
        print("❌ No schema_version table - migrations not applied")
        return False

    # Required columns for documents table
    required_columns = {
        "chunk_id",
        "file_path",
        "file_name",
        "text_content",
        "file_hash",
        "char_count",
        "word_count",
        "pages",
        "sha256",
        "status",
        "extraction_method",
        "ocr_confidence",
        "metadata",
    }

    cursor.execute("PRAGMA table_info(documents)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    missing = required_columns - existing_columns
    if missing:
        print(f"❌ Missing columns in documents: {missing}")
        return False
    print("✓ Documents table has all required columns")

    # Check other critical tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}

    required_tables = {"documents", "content", "embeddings", "schema_version"}
    missing_tables = required_tables - tables
    if missing_tables:
        print(f"❌ Missing tables: {missing_tables}")
        return False
    print("✓ All required tables exist")

    conn.close()
    return True


def check_environment():
    """
    Verify environment configuration.
    """

    # Check if ingestion is frozen
    if Path("INGESTION_FROZEN.txt").exists():
        print("⚠️  PDF ingestion is FROZEN (INGESTION_FROZEN.txt exists)")

    # Check DB path
    db_path = os.getenv("APP_DB_PATH")
    if not db_path:
        print("⚠️  APP_DB_PATH not set in environment (using default: data/emails.db)")
    else:
        print(f"✓ APP_DB_PATH set to: {db_path}")

    # Check Qdrant
    try:
        import requests

        resp = requests.get("http://localhost:6333/health", timeout=1)
        if resp.status_code == 200:
            print("✓ Qdrant vector database is running")
        else:
            print("❌ Qdrant not healthy")
            return False
    except:
        print("❌ Qdrant not accessible at localhost:6333")
        return False

    return True


def main():
    print("PDF Pipeline Preflight Check")
    print("=" * 40)

    schema_ok = check_schema()
    env_ok = check_environment()

    print("=" * 40)

    if schema_ok and env_ok:
        print("✅ All checks passed - ready for PDF processing")
        sys.exit(0)
    else:
        print("❌ Preflight checks failed - fix issues above")
        sys.exit(3)  # Exit code 3 for schema/env mismatch


if __name__ == "__main__":
    main()
