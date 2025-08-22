#!/usr/bin/env python3
"""
Backfill SHA256 for uploads and repair documents ⇄ content_unified chain.

- Creates missing content_unified rows for upload documents (chunk-aware).
- Sets content_unified.sha256 where NULL by matching to documents; fallback: hash text.
- Produces machine-readable JSON and appropriate exit codes.

Assumptions (override via CLI if needed):
- Tables: documents(chunk_id, source_type, file_name, sha256, chunk_index, text_content)
-          content_unified(id, sha256, chunk_index, ready_for_embedding, source_type, body)
-          embeddings(content_id|sha256?)  # not modified here
"""

import argparse
import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

LIKELY_DOC_TEXT_COLS = ["text_content", "text", "chunk_text", "content", "body"]
LIKELY_CNT_TEXT_COLS = ["body", "text", "content"]

@dataclass
class Columns:
    doc_text_col: Optional[str]
    cnt_text_col: Optional[str]
    documents_has_chunk_index: bool
    content_has_chunk_index: bool
    content_has_source_type: bool

def detect_columns(cur) -> Columns:
    def cols(table: str) -> List[str]:
        cur.execute(f"PRAGMA table_info({table})")
        return [r[1] for r in cur.fetchall()]

    dcols = cols("documents")
    ccols = cols("content_unified")

    doc_text_col = next((c for c in LIKELY_DOC_TEXT_COLS if c in dcols), None)
    cnt_text_col = next((c for c in LIKELY_CNT_TEXT_COLS if c in ccols), None)

    return Columns(
        doc_text_col=doc_text_col,
        cnt_text_col=cnt_text_col,
        documents_has_chunk_index=("chunk_index" in dcols),
        content_has_chunk_index=("chunk_index" in ccols),
        content_has_source_type=("source_type" in ccols),
    )

def canonical_sha(text: str, file_sha: Optional[str], chunk_index: Optional[int]) -> str:
    """
    Deterministic hash. Prefer pairing to document sha if available; otherwise hash text+chunk.
    """
    norm = (text or "").strip()
    base = f"{file_sha or ''}|{chunk_index if chunk_index is not None else ''}|{norm}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.getenv("APP_DB_PATH", "data/emails.db"))
    ap.add_argument("--source-type", default="upload")
    ap.add_argument("--limit", type=int, default=100000, help="Max rows to process per category")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ready-flag", type=int, default=1, help="value for content_unified.ready_for_embedding")
    args = ap.parse_args()

    db_path = args.db
    if not Path(db_path).exists():
        print(json.dumps({"error": f"database not found: {db_path}"}))
        return 3

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")

    cols = detect_columns(cur)

    # sanity
    for tbl in ("documents", "content_unified"):
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'")
        if cur.fetchone() is None:
            print(json.dumps({"error": f"required table missing: {tbl}"}))
            return 3

    # ---------------------------
    # 1) Fix content_unified rows with NULL sha256 (pair to documents first)
    # ---------------------------
    updated_content_sha = 0
    
    # First try to match by chunk_index and find documents with sha256
    if cols.documents_has_chunk_index and cols.content_has_chunk_index:
        cur.execute("""
            SELECT c.id as cid, c.chunk_index as c_chunk, d.sha256 as dsha
            FROM content_unified c
            LEFT JOIN documents d
              ON c.chunk_index = d.chunk_index
             AND d.sha256 IS NOT NULL
             AND d.source_type = ?
            WHERE c.sha256 IS NULL
              AND d.sha256 IS NOT NULL
            LIMIT ?
        """, (args.source_type, args.limit))
        to_fix = cur.fetchall()

        for row in to_fix:
            cid = row["cid"]
            dsha = row["dsha"]
            if dsha and not args.dry_run:
                cur.execute("UPDATE content_unified SET sha256=? WHERE id=?", (dsha, cid))
                updated_content_sha += 1

    # Fallback: remaining NULL sha256 rows → hash their own text
    cur.execute("SELECT id, {} as t, chunk_index FROM content_unified WHERE sha256 IS NULL LIMIT ?".format(
        cols.cnt_text_col or "''"
    ), (args.limit,))
    fallback = cur.fetchall()
    for row in fallback:
        t = row["t"] or ""
        sha = canonical_sha(t, None, row["chunk_index"] if cols.content_has_chunk_index else None)
        if not args.dry_run:
            cur.execute("UPDATE content_unified SET sha256=? WHERE id=?", (sha, row["id"]))
            updated_content_sha += 1

    # ---------------------------
    # 2) Create missing content_unified rows for documents (upload) with no content match
    # ---------------------------
    missing_created = 0
    unresolved_missing = 0
    
    if not (cols.documents_has_chunk_index and cols.content_has_chunk_index):
        # join is unsafe without chunk_index
        pass
    else:
        cur.execute(f"""
            SELECT d.chunk_id as did, d.sha256 as dsha, d.chunk_index as dchunk,
                   {cols.doc_text_col or "NULL"} AS dtext,
                   d.file_name, d.source_type
            FROM documents d
            LEFT JOIN content_unified c
              ON d.sha256 = c.sha256
             AND d.chunk_index = c.chunk_index
            WHERE d.source_type = ?
              AND d.sha256 IS NOT NULL
              AND c.id IS NULL
            LIMIT ?
        """, (args.source_type, args.limit))
        missing = cur.fetchall()

        for row in missing:
            text = row["dtext"]
            if text is None or (isinstance(text, str) and text.strip() == ""):
                unresolved_missing += 1
                continue

            # Use 'pdf' as default source_type for content_unified to match documents table
            # Use chunk_id as source_id for the unique constraint
            payload = {
                "source_type": "pdf",  # matches document source processing pattern
                "source_id": row["did"],  # use chunk_id as unique identifier
                "sha256": row["dsha"],
                "chunk_index": row["dchunk"],
                cols.cnt_text_col or "body": text,
                "ready_for_embedding": args.ready_flag
            }
            
            cols_list = list(payload.keys())
            vals = [payload[k] for k in cols_list]

            if not args.dry_run:
                try:
                    cur.execute(f"INSERT OR IGNORE INTO content_unified ({','.join(cols_list)}) VALUES ({','.join(['?']*len(cols_list))})", vals)
                    if cur.rowcount > 0:
                        missing_created += 1
                except sqlite3.IntegrityError:
                    # Handle unique constraint violations gracefully
                    continue

    # ---------------------------
    # 3) Metrics + exit
    # ---------------------------
    # counts
    cur.execute("SELECT COUNT(*) FROM documents WHERE source_type=?", (args.source_type,))
    upload_docs_total = cur.fetchone()[0]
    
    if cols.documents_has_chunk_index and cols.content_has_chunk_index:
        cur.execute("""
            SELECT COUNT(*)
            FROM documents d
            LEFT JOIN content_unified c
              ON d.sha256 = c.sha256
             AND d.chunk_index = c.chunk_index
            WHERE d.source_type = ?
              AND d.sha256 IS NOT NULL
              AND c.id IS NULL
        """, (args.source_type,))
        docs_without_content = cur.fetchone()[0]
    else:
        docs_without_content = -1  # Cannot determine without chunk_index

    cur.execute("SELECT COUNT(*) FROM content_unified WHERE sha256 IS NULL")
    content_null_sha = cur.fetchone()[0]

    result = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "db": db_path,
        "source_type": args.source_type,
        "dry_run": args.dry_run,
        "columns": {
            "documents_text_col": cols.doc_text_col,
            "content_text_col": cols.cnt_text_col,
            "chunk_index_on_both": cols.documents_has_chunk_index and cols.content_has_chunk_index
        },
        "actions": {
            "content_sha256_fixed": updated_content_sha,
            "content_rows_created": missing_created,
            "unresolved_missing_docs": unresolved_missing
        },
        "post_check": {
            "upload_docs_total": upload_docs_total,
            "docs_without_content": docs_without_content,
            "content_null_sha256": content_null_sha
        }
    }

    exit_code = 0
    # Fail if unresolved or still broken links remain
    if result["actions"]["unresolved_missing_docs"] > 0:
        exit_code = 2
    elif result["post_check"]["docs_without_content"] > 0 or result["post_check"]["content_null_sha256"] > 0:
        exit_code = 1

    if not args.dry_run:
        conn.commit()
    conn.close()

    print(json.dumps(result, indent=2))
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())