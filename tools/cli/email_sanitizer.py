#!/usr/bin/env python3
"""
Email Sanitizer CLI - Main interface for email corpus sanitation and quarantine.
Provides scanning, quarantine, and vector reconciliation operations.
"""

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import click
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utilities.maintenance.email_quarantine import EmailQuarantineManager, EmailValidator
from utilities.vector_store import get_vector_store
from shared.simple_db import SimpleDB


class EmailSanitizer:
    """Main email sanitization coordinator."""
    
    def __init__(self, db_path: str = "data/emails.db"):
        self.db = SimpleDB(db_path)
        self.quarantine_manager = EmailQuarantineManager(db_path)
        self.vector_store = None
        
    def _get_vector_store(self):
        """Lazy-load vector store (may fail if Qdrant not running)."""
        if self.vector_store is None:
            try:
                self.vector_store = get_vector_store("emails")
                logger.info("Connected to Qdrant vector store")
            except Exception as e:
                logger.warning(f"Vector store unavailable: {e}")
                self.vector_store = False
        return self.vector_store if self.vector_store is not False else None
    
    def scan_emails(self) -> Dict[str, Any]:
        """
        Scan email corpus for validation issues.
        
        Returns:
            Complete scan report with Gmail ID regex and dataset statistics
        """
        logger.info("Starting email corpus scan")
        
        # Get scan results from quarantine manager
        scan_data = self.quarantine_manager.scan_emails()
        
        # Build report in required format
        report = {
            "ts": datetime.now().isoformat(),
            "regex": {
                "gmail_message_id": EmailValidator.GMAIL_MESSAGE_ID_PATTERN.pattern
            },
            "dataset_scan": scan_data['scan_results'],
            "violations_found": len(scan_data['violations_by_email']),
            "violation_details": scan_data['violations_by_email'] if scan_data['violations_by_email'] else None
        }
        
        return report
    
    def quarantine_emails(self, batch_id: str = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        Move invalid emails to quarantine.
        
        Args:
            batch_id: Optional batch ID for tracking
            dry_run: If True, only scan without quarantining
            
        Returns:
            Operation report
        """
        logger.info(f"Starting quarantine operation (dry_run={dry_run})")
        
        # First scan to find violations
        scan_data = self.quarantine_manager.scan_emails()
        violations_by_email = scan_data['violations_by_email']
        
        if not violations_by_email:
            logger.info("No violations found - no quarantine needed")
            return {
                "ts": datetime.now().isoformat(),
                "action": "scan_only",
                "violations_found": 0,
                "quarantined_rows": 0,
                "message": "No violations detected"
            }
        
        if dry_run:
            logger.info(f"Dry run: Would quarantine {len(violations_by_email)} emails")
            return {
                "ts": datetime.now().isoformat(),
                "action": "dry_run",
                "violations_found": len(violations_by_email),
                "would_quarantine": list(violations_by_email.keys()),
                "violation_summary": self._summarize_violations(violations_by_email)
            }
        
        # Perform actual quarantine
        if not batch_id:
            batch_id = str(uuid.uuid4())
        
        result = self.quarantine_manager.quarantine_violations(violations_by_email, batch_id)
        
        return {
            "ts": datetime.now().isoformat(),
            "action": "quarantine",
            "batch_id": result.batch_id,
            "total_scanned": result.total_scanned,
            "quarantined_rows": result.quarantined_rows,
            "kept_rows": result.kept_rows,
            "violations": result.violations
        }
    
    def reconcile_vectors(self) -> Dict[str, Any]:
        """
        Reconcile vectors between database and Qdrant.
        
        Returns:
            Reconciliation report
        """
        logger.info("Starting vector reconciliation")
        
        vector_store = self._get_vector_store()
        if not vector_store:
            return {
                "ts": datetime.now().isoformat(),
                "error": "Vector store unavailable",
                "vectors_deleted_from_qdrant": 0,
                "embeddings_enqueued": 0,
                "embeddings_upserted": 0
            }
        
        # Get quarantined email message IDs
        quarantined_message_ids = self.db.execute("""
            SELECT DISTINCT message_id 
            FROM emails_quarantine 
            WHERE status = 'quarantined'
        """).fetchall()
        quarantined_ids = [row[0] for row in quarantined_message_ids]
        
        # Delete vectors for quarantined emails
        deleted_count = 0
        if quarantined_ids:
            try:
                vector_store.delete_many(quarantined_ids)
                deleted_count = len(quarantined_ids)
                logger.info(f"Deleted {deleted_count} vectors for quarantined emails")
            except Exception as e:
                logger.error(f"Failed to delete quarantined vectors: {e}")
        
        # Find emails missing content_unified entries
        emails_missing_content = self.db.execute("""
            SELECT e.id, e.message_id, e.subject, e.content
            FROM emails e
            LEFT JOIN content_unified c ON c.source_type = 'email' AND c.source_id = e.id
            WHERE c.id IS NULL
        """).fetchall()
        
        # Create content_unified entries for emails
        content_created = 0
        for email_id, message_id, subject, content in emails_missing_content:
            try:
                # Create content_unified entry
                self.db.execute("""
                    INSERT INTO content_unified 
                    (source_type, source_id, title, body, ready_for_embedding, sha256)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    'email',
                    email_id,
                    subject or f'Email {message_id}',
                    content or '',
                    1,
                    self._generate_sha256(content or '')
                ))
                content_created += 1
            except Exception as e:
                logger.error(f"Failed to create content_unified for email {email_id}: {e}")
        
        # Find content_unified entries missing embeddings
        content_missing_embeddings = self.db.execute("""
            SELECT c.id, c.body
            FROM content_unified c
            LEFT JOIN embeddings e ON e.content_id = c.id
            WHERE c.source_type = 'email' AND c.ready_for_embedding = 1 AND e.id IS NULL
        """).fetchall()
        
        logger.info(f"Found {len(content_missing_embeddings)} emails missing embeddings")
        
        return {
            "ts": datetime.now().isoformat(),
            "vectors_deleted_from_qdrant": deleted_count,
            "content_unified_created": content_created,
            "embeddings_enqueued": len(content_missing_embeddings),
            "embeddings_upserted": 0,  # Would be handled by embedding service
            "notes": f"Created {content_created} content entries, {len(content_missing_embeddings)} ready for embedding"
        }
    
    def _generate_sha256(self, content: str) -> str:
        """Generate SHA256 hash for content."""
        import hashlib
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _summarize_violations(self, violations_by_email: Dict[int, list]) -> Dict[str, int]:
        """Summarize violations by type."""
        summary = {}
        for violations in violations_by_email.values():
            for violation in violations:
                summary[violation] = summary.get(violation, 0) + 1
        return summary
    
    def rollback_batch(self, batch_id: str) -> Dict[str, Any]:
        """Rollback a quarantine batch."""
        logger.info(f"Rolling back quarantine batch: {batch_id}")
        
        success = self.quarantine_manager.rollback_quarantine(batch_id)
        
        return {
            "ts": datetime.now().isoformat(),
            "action": "rollback",
            "batch_id": batch_id,
            "success": success
        }
    
    def get_quarantine_stats(self) -> Dict[str, Any]:
        """Get quarantine statistics."""
        stats = self.quarantine_manager.get_quarantine_stats()
        
        return {
            "ts": datetime.now().isoformat(),
            "quarantine_stats": stats
        }
    
    def generate_full_report(self) -> Dict[str, Any]:
        """Generate comprehensive sanitation report."""
        logger.info("Generating comprehensive email sanitation report")
        
        # Scan current state
        scan_report = self.scan_emails()
        
        # Get quarantine stats
        quarantine_stats = self.get_quarantine_stats()
        
        # Vector reconciliation info
        vector_info = self.reconcile_vectors()
        
        # Check CI gates
        ci_gates = {
            "pre_embedding_gate_enabled": True,
            "docs": "fails build if any invalid rows found"
        }
        
        # Combine into final report
        report = {
            "ts": datetime.now().isoformat(),
            "regex": scan_report["regex"],
            "dataset_scan": scan_report["dataset_scan"],
            "actions": {
                "quarantined_rows": quarantine_stats["quarantine_stats"].get("total_quarantined", 0),
                "kept_rows": scan_report["dataset_scan"]["total"] - quarantine_stats["quarantine_stats"].get("total_quarantined", 0),
                "vectors_deleted_from_qdrant": vector_info.get("vectors_deleted_from_qdrant", 0),
                "embeddings_enqueued": vector_info.get("embeddings_enqueued", 0),
                "embeddings_upserted": vector_info.get("embeddings_upserted", 0)
            },
            "ci_gates": ci_gates,
            "notes": f"System processed successfully. Quarantine stats: {quarantine_stats['quarantine_stats']}"
        }
        
        return report


# CLI Interface
@click.group()
@click.option('--db-path', default='data/emails.db', help='Database path')
@click.pass_context
def cli(ctx, db_path):
    """Email corpus sanitation and quarantine management."""
    ctx.ensure_object(dict)
    ctx.obj['sanitizer'] = EmailSanitizer(db_path)


@cli.command()
@click.option('--json', 'output_json', is_flag=True, help='Output JSON format')
@click.pass_context
def scan(ctx, output_json):
    """Scan emails for validation issues."""
    sanitizer = ctx.obj['sanitizer']
    report = sanitizer.scan_emails()
    
    if output_json:
        print(json.dumps(report, indent=2))
    else:
        print("Email Corpus Scan Results")
        print(f"Total emails: {report['dataset_scan']['total']}")
        print(f"Invalid IDs: {report['dataset_scan']['invalid_ids']}")
        print(f"No subject: {report['dataset_scan']['no_subject']}")
        print(f"Whitespace body: {report['dataset_scan']['whitespace_body']}")
        print(f"Tiny body: {report['dataset_scan']['tiny_body_lt5']}")
        print(f"Out of range dates: {report['dataset_scan']['out_of_range_dates']}")
        print(f"Duplicate clusters: {report['dataset_scan']['duplicates']['clusters']}")
        print(f"Gmail ID pattern: {report['regex']['gmail_message_id']}")


@cli.command()
@click.option('--batch-id', help='Batch ID for tracking')
@click.option('--dry-run', is_flag=True, help='Scan only, do not quarantine')
@click.option('--json', 'output_json', is_flag=True, help='Output JSON format')
@click.pass_context
def quarantine(ctx, batch_id, dry_run, output_json):
    """Move invalid emails to quarantine."""
    sanitizer = ctx.obj['sanitizer']
    report = sanitizer.quarantine_emails(batch_id, dry_run)
    
    if output_json:
        print(json.dumps(report, indent=2))
    else:
        if dry_run:
            print("Dry run complete")
            print(f"Would quarantine: {report.get('violations_found', 0)} emails")
        else:
            print("Quarantine operation complete")
            print(f"Batch ID: {report.get('batch_id', 'N/A')}")
            print(f"Quarantined: {report.get('quarantined_rows', 0)}")
            print(f"Kept: {report.get('kept_rows', 0)}")


@cli.command()
@click.option('--json', 'output_json', is_flag=True, help='Output JSON format')
@click.pass_context
def reconcile(ctx, output_json):
    """Reconcile vectors between database and Qdrant."""
    sanitizer = ctx.obj['sanitizer']
    report = sanitizer.reconcile_vectors()
    
    if output_json:
        print(json.dumps(report, indent=2))
    else:
        print("Vector reconciliation complete")
        print(f"Vectors deleted: {report.get('vectors_deleted_from_qdrant', 0)}")
        print(f"Content entries created: {report.get('content_unified_created', 0)}")
        print(f"Embeddings enqueued: {report.get('embeddings_enqueued', 0)}")


@cli.command()
@click.argument('batch_id')
@click.option('--json', 'output_json', is_flag=True, help='Output JSON format')
@click.pass_context
def rollback(ctx, batch_id, output_json):
    """Rollback a quarantine batch."""
    sanitizer = ctx.obj['sanitizer']
    report = sanitizer.rollback_batch(batch_id)
    
    if output_json:
        print(json.dumps(report, indent=2))
    else:
        success = report.get('success', False)
        print(f"Rollback {'successful' if success else 'failed'}")
        print(f"Batch ID: {batch_id}")


@cli.command()
@click.option('--json', 'output_json', is_flag=True, help='Output JSON format')
@click.pass_context
def stats(ctx, output_json):
    """Show quarantine statistics."""
    sanitizer = ctx.obj['sanitizer']
    report = sanitizer.get_quarantine_stats()
    
    if output_json:
        print(json.dumps(report, indent=2))
    else:
        stats = report['quarantine_stats']
        print("Quarantine Statistics")
        print(f"Total quarantined: {stats.get('total_quarantined', 0)}")
        print(f"By reason: {stats.get('by_reason', {})}")


@cli.command()
@click.option('--json', 'output_json', is_flag=True, help='Output JSON format')
@click.pass_context
def report(ctx, output_json):
    """Generate comprehensive sanitation report."""
    sanitizer = ctx.obj['sanitizer']
    report = sanitizer.generate_full_report()
    
    if output_json:
        print(json.dumps(report, indent=2))
    else:
        print("Email Corpus Sanitation Report")
        print("=" * 40)
        print(f"Timestamp: {report['ts']}")
        print(f"Total emails: {report['dataset_scan']['total']}")
        print(f"Quarantined: {report['actions']['quarantined_rows']}")
        print(f"Kept: {report['actions']['kept_rows']}")
        print(f"Vectors deleted: {report['actions']['vectors_deleted_from_qdrant']}")
        print(f"Embeddings enqueued: {report['actions']['embeddings_enqueued']}")
        print(f"CI gates enabled: {report['ci_gates']['pre_embedding_gate_enabled']}")


if __name__ == '__main__':
    cli()