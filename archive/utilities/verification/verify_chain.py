#!/usr/bin/env python3
"""Chain Integrity Verification Script.

Validates the documents → content_unified → embeddings chain integrity.
Reports broken links and data quality issues.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def check_chain_integrity(db_path):
    """
    Check the integrity of the document processing chain.
    """

    # Open in read-only mode for safety
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.execute("PRAGMA foreign_keys = ON")  # Smoke test latent issues
    cursor = conn.cursor()

    results = {"timestamp": datetime.now().isoformat(), "database_path": db_path}

    # 1. Documents with NULL SHA256
    cursor.execute("SELECT COUNT(*) FROM documents WHERE sha256 IS NULL")
    docs_null_sha256 = cursor.fetchone()[0]
    results["docs_null_sha256"] = docs_null_sha256

    # 2. Total documents
    cursor.execute("SELECT COUNT(*) FROM documents")
    docs_total = cursor.fetchone()[0]
    results["docs_total"] = docs_total

    # 3. Documents without content (chunk-aware for all chunked documents)
    # For chunked documents (both upload and pdf), only first chunk (chunk_index=0) needs direct content link
    # Other chunks are represented by the full document content
    cursor.execute(
        """
        SELECT COUNT(*) 
        FROM documents d 
        LEFT JOIN content_unified c ON d.sha256 = c.sha256 
        WHERE d.sha256 IS NOT NULL AND d.chunk_index = 0 AND c.id IS NULL
    """
    )
    first_chunks_without_content = cursor.fetchone()[0]

    docs_without_content = first_chunks_without_content
    results["docs_without_content"] = docs_without_content
    results["first_chunks_without_content"] = first_chunks_without_content

    # 4. Content without documents (orphaned content) — FIXED
    cursor.execute(
        """
        SELECT COUNT(*) 
        FROM content_unified c 
        LEFT JOIN documents d ON c.sha256 = d.sha256 
        WHERE c.sha256 IS NOT NULL AND d.sha256 IS NULL
    """
    )
    content_without_doc = cursor.fetchone()[0]
    results["content_without_doc"] = content_without_doc

    # 5. Total broken chain count
    broken_chain_total = docs_null_sha256 + docs_without_content + content_without_doc
    results["broken_chain_total"] = broken_chain_total

    # 6. Content unified stats
    cursor.execute("SELECT COUNT(*) FROM content_unified")
    content_total = cursor.fetchone()[0]
    results["content_total"] = content_total

    cursor.execute("SELECT COUNT(*) FROM content_unified WHERE ready_for_embedding = 1")
    content_ready_embedding = cursor.fetchone()[0]
    results["content_ready_embedding"] = content_ready_embedding

    # 6b. Content missing embeddings (coverage)
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM content_unified c
        LEFT JOIN embeddings e ON e.content_id = c.id
        WHERE c.ready_for_embedding = 1 AND e.id IS NULL
    """
    )
    content_without_embedding = cursor.fetchone()[0]
    results["content_without_embedding"] = content_without_embedding

    # 6c. Docs with content but missing embeddings (chunk-aware)
    # Count unique files, not individual chunks - only check chunk_index=0
    cursor.execute(
        """
        SELECT COUNT(DISTINCT d.file_name)
        FROM documents d
        JOIN content_unified c ON d.sha256 = c.sha256
        LEFT JOIN embeddings e ON e.content_id = c.id
        WHERE e.id IS NULL AND d.chunk_index = 0
    """
    )
    files_without_embedding = cursor.fetchone()[0]

    docs_with_content_without_embedding = files_without_embedding
    results["docs_with_content_without_embedding"] = docs_with_content_without_embedding
    results["files_without_embedding"] = files_without_embedding

    # 6d. SHA256 duplicate keys (documents)
    cursor.execute(
        """
        SELECT COUNT(*) FROM (
          SELECT sha256 FROM documents
          WHERE sha256 IS NOT NULL
          GROUP BY sha256
          HAVING COUNT(*) > 1
        )
    """
    )
    results["doc_sha256_dupe_keys"] = cursor.fetchone()[0]

    # 6e. SHA256 duplicate keys (content_unified)
    cursor.execute(
        """
        SELECT COUNT(*) FROM (
          SELECT sha256 FROM content_unified
          WHERE sha256 IS NOT NULL
          GROUP BY sha256
          HAVING COUNT(*) > 1
        )
    """
    )
    results["content_sha256_dupe_keys"] = cursor.fetchone()[0]

    # 7. Embeddings stats
    cursor.execute("SELECT COUNT(*) FROM embeddings")
    embeddings_total = cursor.fetchone()[0]
    results["embeddings_total"] = embeddings_total

    # 8. Documents by source type
    cursor.execute("SELECT source_type, COUNT(*) FROM documents GROUP BY source_type")
    docs_by_source = dict(cursor.fetchall())
    results["docs_by_source"] = docs_by_source

    # 9. Upload documents specifically (the repaired ones)
    cursor.execute("SELECT COUNT(*) FROM documents WHERE source_type = 'upload'")
    upload_docs_total = cursor.fetchone()[0]
    results["upload_docs_total"] = upload_docs_total

    cursor.execute(
        "SELECT COUNT(*) FROM documents WHERE source_type = 'upload' AND sha256 IS NOT NULL"
    )
    upload_docs_with_sha256 = cursor.fetchone()[0]
    results["upload_docs_with_sha256"] = upload_docs_with_sha256

    # 10. Content for upload documents (via join from documents - safer)
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM content_unified c
        JOIN documents d ON d.sha256 = c.sha256
        WHERE d.source_type = 'upload'
    """
    )
    upload_content_total = cursor.fetchone()[0]
    results["upload_content_total"] = upload_content_total

    # 11. Sample broken documents (if any)
    if docs_without_content > 0:
        cursor.execute(
            """
            SELECT d.chunk_id, d.file_name, d.sha256, d.source_type
            FROM documents d 
            LEFT JOIN content_unified c ON d.sha256 = c.sha256 
            WHERE d.sha256 IS NOT NULL AND c.id IS NULL
            LIMIT 5
        """
        )
        broken_samples = cursor.fetchall()
        results["broken_document_samples"] = [
            {"chunk_id": row[0], "file_name": row[1], "sha256": row[2], "source_type": row[3]}
            for row in broken_samples
        ]

    conn.close()
    return results


def print_verification_report(results):
    """
    Print a human-readable verification report.
    """

    print("Document Chain Integrity Verification")
    print("=" * 50)
    print(f"Database: {results['database_path']}")
    print(f"Timestamp: {results['timestamp']}")
    print()

    # Overall status with stricter FAIL conditions
    broken_total = results["broken_chain_total"]
    null_sha256 = results["docs_null_sha256"]
    dupe_docs = results["doc_sha256_dupe_keys"]
    dupe_content = results["content_sha256_dupe_keys"]

    # FAIL conditions: NULL SHA256, duplicates, broken chain
    if null_sha256 > 0 or dupe_docs > 0 or dupe_content > 0 or broken_total > 0:
        status = "❌ FAIL"
        color = "\033[91m"  # Red
        exit_code = 2
    elif results["content_without_embedding"] > 0:
        status = "⚠️  WARN"
        color = "\033[93m"  # Yellow
        exit_code = 1
    else:
        status = "✅ PASS"
        color = "\033[92m"  # Green
        exit_code = 0

    print(f"Overall Status: {color}{status}\033[0m")
    print(f"Broken Chain Total: {broken_total}")
    print()

    # Document stats
    print("📄 Document Statistics:")
    print(f"  Total documents: {results['docs_total']}")
    print(f"  Documents with NULL SHA256: {results['docs_null_sha256']}")
    print(f"  Documents without content: {results['docs_without_content']}")
    if results.get("first_chunks_without_content", 0) > 0:
        print(f"    First chunks without content: {results['first_chunks_without_content']}")
    print(f"  SHA256 duplicate keys in documents: {results['doc_sha256_dupe_keys']}")

    if "docs_by_source" in results:
        print("  By source type:")
        for source_type, count in results["docs_by_source"].items():
            print(f"    {source_type}: {count}")

    print()

    # Upload documents (the ones we repaired)
    print("📤 Upload Document Statistics:")
    print(f"  Total upload documents: {results['upload_docs_total']}")
    print(f"  Upload docs with SHA256: {results['upload_docs_with_sha256']}")
    print(f"  Upload content entries: {results['upload_content_total']}")
    print()

    # Content stats with embedding coverage
    print("📝 Content Statistics:")
    print(f"  Total content entries: {results['content_total']}")
    print(f"  Ready for embedding: {results['content_ready_embedding']}")
    print(f"  Content without embedding: {results['content_without_embedding']}")
    print(
        f"  Files with content without embedding: {results['docs_with_content_without_embedding']}"
    )
    if results.get("files_without_embedding", 0) > 0:
        print(f"    Files missing embeddings: {results['files_without_embedding']}")
    print(f"  Orphaned content: {results['content_without_doc']}")
    print(f"  SHA256 duplicate keys in content: {results['content_sha256_dupe_keys']}")
    print()

    # Embedding stats
    print("🔍 Embedding Statistics:")
    print(f"  Total embeddings: {results['embeddings_total']}")
    print()

    # Issues
    if broken_total > 0 or null_sha256 > 0 or dupe_docs > 0 or dupe_content > 0:
        print("❌ Critical Issues Found:")
        if results["docs_null_sha256"] > 0:
            print(f"  - {results['docs_null_sha256']} documents with NULL SHA256")
        if results["docs_without_content"] > 0:
            print(f"  - {results['docs_without_content']} documents without content")
        if results["content_without_doc"] > 0:
            print(f"  - {results['content_without_doc']} orphaned content entries")
        if results["doc_sha256_dupe_keys"] > 0:
            print(f"  - {results['doc_sha256_dupe_keys']} duplicate SHA256 keys in documents")
        if results["content_sha256_dupe_keys"] > 0:
            print(f"  - {results['content_sha256_dupe_keys']} duplicate SHA256 keys in content")

        if "broken_document_samples" in results:
            print("\n  Sample broken documents:")
            for sample in results["broken_document_samples"]:
                print(f"    {sample['chunk_id']} ({sample['source_type']}): {sample['file_name']}")
        print()

    if results["content_without_embedding"] > 0:
        print("⚠️  Embedding Coverage Issues:")
        print(f"  - {results['content_without_embedding']} content entries missing embeddings")
        print(
            f"  - {results['docs_with_content_without_embedding']} docs with content but no embeddings"
        )
        print()

    if exit_code == 0:
        print("✅ No chain integrity issues found!")

    # Store exit code for main function
    results["_exit_code"] = exit_code


def main():
    """
    Main verification entry point.
    """

    # Use environment variable or default path
    db_path = os.getenv("APP_DB_PATH", "data/emails.db")

    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return 1

    try:
        results = check_chain_integrity(db_path)

        # Print report
        print_verification_report(results)

        # Save JSON results
        os.makedirs("logs", exist_ok=True)
        results_path = "logs/chain_verification_results.json"
        with open(results_path, "w") as f:
            # Remove internal exit code from saved JSON
            save_results = {k: v for k, v in results.items() if not k.startswith("_")}
            json.dump(save_results, f, indent=2)

        print(f"\n💾 Results saved to: {results_path}")

        # Return appropriate exit code based on stricter FAIL conditions
        return results.get("_exit_code", 0)

    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return 3


if __name__ == "__main__":
    exit(main())
