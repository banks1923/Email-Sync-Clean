"""
Quarantine Recovery CLI Handler Manages failed documents with retry logic and
purging.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

from lib.db import SimpleDB


class QuarantineHandler:
    """
    Handles quarantine operations for failed documents.
    """

    def __init__(self):
        from config.settings import DatabaseSettings

        self.db_path = DatabaseSettings().emails_db_path
        self.db = SimpleDB(self.db_path)
        self.quarantine_dir = Path("data/quarantine")

    def list_quarantined(self, limit: int = 50) -> list[dict[str, Any]]:
        """
        List documents in quarantine.
        """
        result = self.db.query(
            """
            SELECT DISTINCT 
                sha256, file_name, status, 
                attempt_count, error_message, next_retry_at,
                COUNT(*) as chunk_count,
                MIN(processed_at) as first_attempt
            FROM documents 
            WHERE status IN ('failed', 'quarantined')
            GROUP BY sha256
            ORDER BY attempt_count DESC, first_attempt DESC
            LIMIT ?
        """,
            (limit,),
        )

        results = []
        for row in result.get("data", []):
            results.append(
                {
                    "sha256": row["sha256"][:8] + "..." if row["sha256"] else "N/A",
                    "file": row["file_name"],
                    "attempts": row["attempt_count"],
                    "error": row["error_message"][:50] if row["error_message"] else "Unknown",
                    "next_retry": row["next_retry_at"] if row["next_retry_at"] else "Never",
                    "chunks": row["chunk_count"],
                }
            )

        conn.close()
        return results

    def retry_document(self, sha256_prefix: str) -> dict[str, Any]:
        """
        Retry processing a quarantined document.
        """
        # Find full SHA256
        result = self.db.query(
            """
            SELECT DISTINCT sha256, file_path, file_name
            FROM documents 
            WHERE sha256 LIKE ? AND status IN ('failed', 'quarantined')
            LIMIT 1
        """,
            (sha256_prefix + "%",),
        )

        rows = result.get("data", [])
        if not rows:
            return {
                "success": False,
                "error": f"No quarantined document found with SHA {sha256_prefix}",
            }

        sha256, file_path, file_name = rows[0]['sha256'], rows[0]['file_path'], rows[0]['file_name']

        # Check if retry is allowed
        attempt_result = self.db.query(
            """
            SELECT attempt_count, next_retry_at 
            FROM documents 
            WHERE sha256 = ? 
            LIMIT 1
        """,
            (sha256,),
        )

        attempt_rows = attempt_result.get("data", [])
        if attempt_rows:
            attempts, next_retry = attempt_rows[0]['attempt_count'], attempt_rows[0]['next_retry_at']
            if attempts >= 3:
                return {
                    "success": False,
                    "error": f"Document has failed {attempts} times - manual intervention required",
                }

            if next_retry and datetime.fromisoformat(next_retry) > datetime.now():
                return {"success": False, "error": f"Retry not allowed until {next_retry}"}

        # Reset status for retry
        self.db.execute_query(
            """
            UPDATE documents 
            SET status = 'pending_retry',
                next_retry_at = NULL
            WHERE sha256 = ?
        """,
            (sha256,),
        )

        # Trigger reprocessing
        from pdf.wiring import get_pdf_service

        try:
            pdf_service = get_pdf_service(self.db_path)
            result = pdf_service.upload_single_pdf(file_path, use_pipeline=False)

            if result.get("success"):
                return {
                    "success": True,
                    "message": f"Successfully reprocessed {file_name}",
                    "chunks": result.get("chunks_processed", 0),
                }
            else:
                return {
                    "success": False,
                    "error": f"Retry failed: {result.get('error', 'Unknown error')}",
                }
        except Exception as e:
            return {"success": False, "error": f"Failed to initialize PDF service: {e}"}

    def purge_quarantined(
        self, older_than_days: int = 30, permanent_only: bool = True
    ) -> dict[str, Any]:
        """
        Purge old quarantined documents.
        """
        query = """
            DELETE FROM documents 
            WHERE status IN ('failed', 'quarantined')
            AND datetime(processed_at) < datetime('now', '-{} days')
        """.format(
            older_than_days
        )

        if permanent_only:
            query += " AND attempt_count >= 3"

        result = self.db.execute_query(query)
        deleted = result.get("rows_affected", 0)

        # Also clean up quarantine directory
        cleaned_files = 0
        if self.quarantine_dir.exists():
            cutoff = datetime.now().timestamp() - (older_than_days * 86400)
            for file in self.quarantine_dir.glob("*"):
                if file.stat().st_mtime < cutoff:
                    file.unlink()
                    cleaned_files += 1

        return {"success": True, "db_records_deleted": deleted, "files_cleaned": cleaned_files}

    def get_stats(self) -> dict[str, Any]:
        """
        Get quarantine statistics.
        """
        result = self.db.query(
            """
            SELECT 
                COUNT(DISTINCT sha256) as unique_docs,
                COUNT(*) as total_chunks,
                SUM(CASE WHEN attempt_count = 1 THEN 1 ELSE 0 END) as first_attempt,
                SUM(CASE WHEN attempt_count = 2 THEN 1 ELSE 0 END) as second_attempt,
                SUM(CASE WHEN attempt_count >= 3 THEN 1 ELSE 0 END) as permanent_failures,
                AVG(attempt_count) as avg_attempts
            FROM documents
            WHERE status IN ('failed', 'quarantined')
        """
        )

        rows = result.get("data", [])
        row = rows[0] if rows else {}

        return {
            "unique_documents": row.get('unique_docs', 0) or 0,
            "total_chunks": row.get('total_chunks', 0) or 0,
            "first_attempt": row.get('first_attempt', 0) or 0,
            "second_attempt": row.get('second_attempt', 0) or 0,
            "permanent_failures": row.get('permanent_failures', 0) or 0,
            "average_attempts": round(row.get('avg_attempts', 0) or 0, 1),
            "retry_eligible": (row.get('first_attempt', 0) or 0) + (row.get('second_attempt', 0) or 0),
        }


def add_quarantine_commands(subparsers):
    """
    Add quarantine commands to vsearch CLI.
    """
    quarantine_parser = subparsers.add_parser("quarantine", help="Manage quarantined documents")
    quarantine_subparsers = quarantine_parser.add_subparsers(dest="quarantine_command")

    # List command
    list_parser = quarantine_subparsers.add_parser("list", help="List quarantined documents")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximum results")

    # Retry command
    retry_parser = quarantine_subparsers.add_parser("retry", help="Retry a quarantined document")
    retry_parser.add_argument("sha256", help="SHA256 prefix of document to retry")

    # Purge command
    purge_parser = quarantine_subparsers.add_parser("purge", help="Purge old quarantined documents")
    purge_parser.add_argument("--days", type=int, default=30, help="Delete older than N days")
    purge_parser.add_argument(
        "--all", action="store_true", help="Delete all, not just permanent failures"
    )

    # Stats command
    quarantine_subparsers.add_parser("stats", help="Show quarantine statistics")


def handle_quarantine_command(args):
    """
    Handle quarantine commands.
    """
    handler = QuarantineHandler()

    if args.quarantine_command == "list":
        results = handler.list_quarantined(args.limit)
        if results:
            print(f"{'SHA256':<12} {'File':<30} {'Attempts':<8} {'Error':<40} {'Next Retry'}")
            print("-" * 100)
            for r in results:
                print(
                    f"{r['sha256']:<12} {r['file'][:29]:<30} {r['attempts']:<8} {r['error'][:39]:<40} {r['next_retry']}"
                )
        else:
            print("No quarantined documents found")

    elif args.quarantine_command == "retry":
        result = handler.retry_document(args.sha256)
        if result["success"]:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")

    elif args.quarantine_command == "purge":
        result = handler.purge_quarantined(args.days, not args.all)
        print(
            f"✅ Purged {result['db_records_deleted']} database records and {result['files_cleaned']} files"
        )

    elif args.quarantine_command == "stats":
        stats = handler.get_stats()
        print("Quarantine Statistics")
        print("=" * 40)
        print(f"Unique documents:    {stats['unique_documents']}")
        print(f"Total chunks:        {stats['total_chunks']}")
        print(f"Retry eligible:      {stats['retry_eligible']}")
        print(f"Permanent failures:  {stats['permanent_failures']}")
        print(f"Average attempts:    {stats['average_attempts']}")

    else:
        print("Unknown quarantine command")
