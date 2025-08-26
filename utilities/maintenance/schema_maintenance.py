#!/usr/bin/env python3
"""Consolidated Schema Maintenance Utilities.

Combines functionality from:
- fix_content_schema.py
- migrate_emails_to_content.py
- update_simpledb_schema_refs.py
"""

import argparse
import sys
from datetime import datetime
from typing import Any

from loguru import logger

from shared.simple_db import SimpleDB


class SchemaMaintenance:
    """
    Unified database schema maintenance operations.
    """

    def __init__(self):
        self.db = SimpleDB()

    def fix_content_schema(self, dry_run: bool = True) -> dict[str, Any]:
        """
        Fix content schema issues and inconsistencies.
        """
        logger.info(f"Fixing content schema (dry_run={dry_run})")

        issues_found = []
        fixes_applied = 0

        # Check for missing required fields
        logger.info("Checking for missing required fields...")

        try:
            # Get all content entries
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id, source_type, source_id, body, title
                    FROM content_unified
                """
                )
                rows = cursor.fetchall()

                for row in rows:
                    content_id, source_type, source_id, body, title = row
                    issues = []

                    # Check for null body
                    if not body:
                        issues.append("missing_text")

                    # Check for null source_type
                    if not source_type:
                        issues.append("missing_source_type")

                    # Check for null source_id
                    if not source_id:
                        issues.append("missing_source_id")

                    if issues:
                        issues_found.append({"id": content_id, "issues": issues})

                        if not dry_run:
                            # Apply fixes
                            updates = []
                            params = []

                            if "missing_text" in issues:
                                updates.append("body = ?")
                                params.append("[Content unavailable]")

                            if "missing_source_type" in issues:
                                updates.append("source_type = ?")
                                params.append("unknown")

                            if "missing_source_id" in issues:
                                updates.append("source_id = ?")
                                params.append(f"legacy_{content_id}")

                            if updates:
                                params.append(content_id)
                                cursor.execute(
                                    f"""
                                    UPDATE unified_content
                                    SET {', '.join(updates)}
                                    WHERE id = ?
                                """,
                                    params,
                                )
                                fixes_applied += 1

                if not dry_run:
                    conn.commit()

        except Exception as e:
            logger.error(f"Failed to fix content schema: {e}")
            return {"error": str(e), "status": "failed"}

        return {
            "issues_found": len(issues_found),
            "issues": issues_found[:10],  # First 10 for summary
            "fixes_applied": fixes_applied,
            "dry_run": dry_run,
            "status": "completed",
        }

    def migrate_emails_to_content(self, batch_size: int = 100) -> dict[str, Any]:
        """
        Migrate emails from legacy table to unified_content.
        """
        logger.info(f"Migrating emails to unified_content (batch_size={batch_size})")

        migrated_count = 0
        errors = []

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Check if emails table exists
                cursor.execute(
                    """
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='emails'
                """
                )

                if not cursor.fetchone():
                    logger.info("No legacy emails table found")
                    return {"migrated": 0, "status": "no_legacy_table"}

                # Get emails not in unified_content
                cursor.execute(
                    """
                    SELECT e.id, e.subject, e.sender, e.body, e.date, e.thread_id
                    FROM emails e
                    LEFT JOIN unified_content uc ON uc.source_id = e.id
                    WHERE uc.id IS NULL
                    LIMIT ?
                """,
                    (batch_size,),
                )

                emails = cursor.fetchall()

                if not emails:
                    logger.info("No emails to migrate")
                    return {"migrated": 0, "status": "all_migrated"}

                for email in emails:
                    email_id, subject, sender, body, date, thread_id = email

                    try:
                        # Insert into content_unified
                        cursor.execute(
                            """
                            INSERT INTO content_unified (
                                source_type, source_id, title, body, created_at
                            ) VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                "email_message",
                                email_id,
                                subject or "",
                                body or "",
                                datetime.now().isoformat(),
                            ),
                        )

                        migrated_count += 1

                    except Exception as e:
                        logger.error(f"Failed to migrate email {email_id}: {e}")
                        errors.append({"email_id": email_id, "error": str(e)})

                conn.commit()

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return {"error": str(e), "status": "failed"}

        logger.info(f"Migrated {migrated_count} emails")

        return {
            "migrated": migrated_count,
            "errors": errors,
            "status": "completed" if migrated_count > 0 else "nothing_to_migrate",
        }

    def update_schema_refs(self, table_mappings: dict[str, str] | None = None) -> dict[str, Any]:
        """
        Update schema references after table changes.
        """
        logger.info("Updating schema references")

        if not table_mappings:
            # Default mappings for common renames
            table_mappings = {
                "documents": "unified_content",
                "emails": "unified_content",
                "pdfs": "unified_content",
                "transcriptions": "unified_content",
            }

        updates_made = []

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Update views that reference old tables
                cursor.execute(
                    """
                    SELECT name, sql FROM sqlite_master
                    WHERE type = 'view'
                """
                )

                views = cursor.fetchall()

                for view_name, view_sql in views:
                    if not view_sql:
                        continue

                    updated_sql = view_sql
                    changed = False

                    for old_table, new_table in table_mappings.items():
                        if old_table in updated_sql:
                            updated_sql = updated_sql.replace(f" {old_table} ", f" {new_table} ")
                            updated_sql = updated_sql.replace(f" {old_table}.", f" {new_table}.")
                            changed = True

                    if changed:
                        logger.info(f"Updating view: {view_name}")

                        # Drop and recreate view
                        cursor.execute(f"DROP VIEW IF EXISTS {view_name}")
                        cursor.execute(updated_sql)

                        updates_made.append(
                            {"type": "view", "name": view_name, "action": "recreated"}
                        )

                # Update indexes on renamed tables
                for old_table, new_table in table_mappings.items():
                    cursor.execute(
                        """
                        SELECT name FROM sqlite_master
                        WHERE type = 'index' AND tbl_name = ?
                    """,
                        (old_table,),
                    )

                    indexes = cursor.fetchall()

                    for (index_name,) in indexes:
                        logger.info(f"Index {index_name} references old table {old_table}")
                        updates_made.append(
                            {
                                "type": "index",
                                "name": index_name,
                                "action": "needs_recreation",
                                "old_table": old_table,
                                "new_table": new_table,
                            }
                        )

                conn.commit()

        except Exception as e:
            logger.error(f"Failed to update schema references: {e}")
            return {"error": str(e), "status": "failed"}

        return {"updates_made": len(updates_made), "updates": updates_made, "status": "completed"}

    def validate_schema(self) -> dict[str, Any]:
        """
        Validate current schema integrity.
        """
        logger.info("Validating schema integrity")

        validation_results = {"tables": {}, "indexes": {}, "constraints": {}, "issues": []}

        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Check required tables
                required_tables = ["unified_content", "jobs", "relationships"]

                for table in required_tables:
                    cursor.execute(
                        """
                        SELECT name FROM sqlite_master
                        WHERE type='table' AND name=?
                    """,
                        (table,),
                    )

                    exists = cursor.fetchone() is not None
                    validation_results["tables"][table] = "exists" if exists else "missing"

                    if not exists:
                        validation_results["issues"].append(f"Missing required table: {table}")

                # Check indexes
                cursor.execute(
                    """
                    SELECT name, tbl_name FROM sqlite_master
                    WHERE type='index'
                """
                )

                indexes = cursor.fetchall()

                for index_name, table_name in indexes:
                    validation_results["indexes"][index_name] = {
                        "table": table_name,
                        "status": "exists",
                    }

                # Check for orphaned records
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM unified_content
                    WHERE source_type IS NULL OR source_id IS NULL
                """
                )

                orphaned_count = cursor.fetchone()[0]

                if orphaned_count > 0:
                    validation_results["issues"].append(
                        f"Found {orphaned_count} records with missing required fields"
                    )

                # Check for duplicate source_ids
                cursor.execute(
                    """
                    SELECT source_id, COUNT(*) as count
                    FROM unified_content
                    GROUP BY source_id
                    HAVING count > 1
                """
                )

                duplicates = cursor.fetchall()

                if duplicates:
                    validation_results["issues"].append(
                        f"Found {len(duplicates)} duplicate source_ids"
                    )

        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return {"error": str(e), "status": "failed"}

        # Determine overall status
        status = "healthy" if not validation_results["issues"] else "needs_attention"

        return {**validation_results, "status": status}


def main():
    """
    CLI interface for schema maintenance.
    """
    parser = argparse.ArgumentParser(description="Database Schema Maintenance")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Fix schema command
    fix = subparsers.add_parser("fix-schema", help="Fix schema issues")
    fix.add_argument("--execute", action="store_true", help="Apply fixes (not dry run)")

    # Migrate emails command
    migrate = subparsers.add_parser("migrate-emails", help="Migrate emails to unified_content")
    migrate.add_argument("--batch-size", type=int, default=100, help="Batch size for migration")

    # Update refs command
    subparsers.add_parser("update-refs", help="Update schema references")

    # Validate command
    subparsers.add_parser("validate", help="Validate schema integrity")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    maintenance = SchemaMaintenance()

    if args.command == "fix-schema":
        result = maintenance.fix_content_schema(dry_run=not args.execute)
    elif args.command == "migrate-emails":
        result = maintenance.migrate_emails_to_content(batch_size=args.batch_size)
    elif args.command == "update-refs":
        result = maintenance.update_schema_refs()
    elif args.command == "validate":
        result = maintenance.validate_schema()
    else:
        parser.print_help()
        sys.exit(1)

    # Print results
    import json

    print(json.dumps(result, indent=2))

    # Exit with error if not healthy
    if result.get("status") not in [
        "completed",
        "healthy",
        "no_legacy_table",
        "all_migrated",
        "nothing_to_migrate",
    ]:
        sys.exit(1)


if __name__ == "__main__":
    main()
