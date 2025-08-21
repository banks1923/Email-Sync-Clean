#!/usr/bin/env python3
"""
Email Quarantine Operations - Validation rules and quarantine management.
Handles email corpus sanitation and quality control.
"""

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from hashlib import sha256

from loguru import logger
from shared.simple_db import SimpleDB


@dataclass
class ValidationRule:
    """Represents a validation rule for emails."""
    name: str
    reason_code: str
    description: str
    
    
@dataclass
class QuarantineResult:
    """Result of quarantine operation."""
    batch_id: str
    total_scanned: int
    quarantined_rows: int
    kept_rows: int
    violations: Dict[str, int]
    

class EmailValidator:
    """Email validation rules based on Gmail patterns."""
    
    # Gmail message ID pattern: 16 hex characters starting with '1'
    GMAIL_MESSAGE_ID_PATTERN = re.compile(r'^1[0-9a-f]{15}$')
    
    # Validation rules
    RULES = {
        'BAD_ID': ValidationRule(
            'BAD_ID', 
            'BAD_ID',
            'Message ID does not match Gmail pattern (16 hex chars starting with 1)'
        ),
        'NO_SUBJECT': ValidationRule(
            'NO_SUBJECT',
            'NO_SUBJECT', 
            'Subject is empty or only whitespace'
        ),
        'WHITESPACE_BODY': ValidationRule(
            'WHITESPACE_BODY',
            'WHITESPACE_BODY',
            'Content is only whitespace characters'
        ),
        'TINY_BODY': ValidationRule(
            'TINY_BODY', 
            'TINY_BODY',
            'Content length less than 5 characters'
        ),
        'OUT_OF_RANGE_DATE': ValidationRule(
            'OUT_OF_RANGE_DATE',
            'OUT_OF_RANGE_DATE',
            'Date is before 2014-01-01 or in the future'
        ),
        'DUPLICATE': ValidationRule(
            'DUPLICATE',
            'DUPLICATE',
            'Duplicate content detected (keeping latest)'
        )
    }
    
    @classmethod
    def validate_message_id(cls, message_id: str) -> bool:
        """Validate Gmail message ID format."""
        if not message_id:
            return False
        return bool(cls.GMAIL_MESSAGE_ID_PATTERN.match(message_id))
    
    @classmethod
    def validate_subject(cls, subject: str) -> bool:
        """Validate email subject is not empty."""
        return len((subject or "").strip()) > 0
    
    @classmethod
    def validate_content(cls, content: str) -> bool:
        """Validate email content is substantial."""
        if not content:
            return False
        
        cleaned = content.strip()
        
        # Check for whitespace only
        if not cleaned:
            return False
            
        # Check minimum length
        if len(cleaned) < 5:
            return False
            
        return True
    
    @classmethod
    def validate_date(cls, date_str: str) -> bool:
        """Validate email date is in reasonable range."""
        if not date_str:
            return False
            
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            min_date = datetime(2014, 1, 1, tzinfo=timezone.utc)
            max_date = datetime.now(timezone.utc)
            
            return min_date <= dt <= max_date
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def validate_email(cls, email_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a single email record.
        
        Returns:
            (is_valid, list_of_violations)
        """
        violations = []
        
        # Check message ID
        if not cls.validate_message_id(email_data.get('message_id')):
            violations.append('BAD_ID')
        
        # Check subject
        if not cls.validate_subject(email_data.get('subject')):
            violations.append('NO_SUBJECT')
        
        # Check content
        content = email_data.get('content', '')
        if not content.strip():
            violations.append('WHITESPACE_BODY')
        elif len(content.strip()) < 5:
            violations.append('TINY_BODY')
        
        # Check date
        if not cls.validate_date(email_data.get('datetime_utc')):
            violations.append('OUT_OF_RANGE_DATE')
        
        return len(violations) == 0, violations


class EmailQuarantineManager:
    """Manages email quarantine operations."""
    
    def __init__(self, db_path: str = "data/emails.db"):
        self.db = SimpleDB(db_path)
        self.validator = EmailValidator()
        
    def scan_emails(self) -> Dict[str, Any]:
        """
        Scan all emails for validation issues.
        
        Returns:
            Dictionary with scan results
        """
        logger.info("Starting email corpus scan")
        
        # Get all emails
        emails = self.db.execute("""
            SELECT id, message_id, subject, content, datetime_utc, content_hash, thread_id
            FROM emails
            ORDER BY id
        """).fetchall()
        
        scan_results = {
            'total': len(emails),
            'invalid_ids': 0,
            'no_subject': 0,
            'whitespace_body': 0,
            'tiny_body_lt5': 0,
            'out_of_range_dates': 0,
            'duplicates': {
                'clusters': 0,
                'rows_in_clusters': 0
            }
        }
        
        violations_by_email = {}
        
        # Check each email
        for email in emails:
            email_dict = {
                'message_id': email[1],
                'subject': email[2], 
                'content': email[3],
                'datetime_utc': email[4]
            }
            
            is_valid, violations = self.validator.validate_email(email_dict)
            
            if violations:
                violations_by_email[email[0]] = violations
                
                for violation in violations:
                    if violation == 'BAD_ID':
                        scan_results['invalid_ids'] += 1
                    elif violation == 'NO_SUBJECT':
                        scan_results['no_subject'] += 1
                    elif violation == 'WHITESPACE_BODY':
                        scan_results['whitespace_body'] += 1
                    elif violation == 'TINY_BODY':
                        scan_results['tiny_body_lt5'] += 1
                    elif violation == 'OUT_OF_RANGE_DATE':
                        scan_results['out_of_range_dates'] += 1
        
        # Check for duplicates by content hash
        duplicate_info = self._find_duplicates()
        scan_results['duplicates'] = duplicate_info
        
        logger.info(f"Scan complete: {scan_results['total']} emails, "
                   f"{len(violations_by_email)} with violations")
        
        return {
            'scan_results': scan_results,
            'violations_by_email': violations_by_email,
            'duplicate_info': duplicate_info
        }
    
    def _find_duplicates(self) -> Dict[str, int]:
        """Find duplicate emails by content hash and thread grouping."""
        # Find content hash duplicates
        content_duplicates = self.db.execute("""
            SELECT content_hash, COUNT(*) as cnt
            FROM emails
            WHERE content_hash IS NOT NULL
            GROUP BY content_hash
            HAVING cnt > 1
        """).fetchall()
        
        duplicate_clusters = len(content_duplicates)
        rows_in_clusters = sum(row[1] for row in content_duplicates)
        
        return {
            'clusters': duplicate_clusters,
            'rows_in_clusters': rows_in_clusters
        }
    
    def quarantine_violations(self, violations_by_email: Dict[int, List[str]], 
                            batch_id: str = None) -> QuarantineResult:
        """
        Move emails with violations to quarantine.
        
        Args:
            violations_by_email: Dict mapping email_id to list of violations
            batch_id: Optional batch ID for tracking
        
        Returns:
            QuarantineResult with operation summary
        """
        if not batch_id:
            batch_id = str(uuid.uuid4())
        
        logger.info(f"Starting quarantine operation with batch_id: {batch_id}")
        
        # Create batch record
        self._create_quarantine_batch(batch_id, violations_by_email)
        
        quarantined_count = 0
        violation_counts = {}
        
        for email_id, violations in violations_by_email.items():
            try:
                # Get email data for backup
                email_data = self.db.execute(
                    "SELECT * FROM emails WHERE id = ?", (email_id,)
                ).fetchall()[0]
                
                # Convert to dict for JSON storage
                columns = ['id', 'message_id', 'subject', 'sender', 'recipient_to',
                          'content', 'datetime_utc', 'content_hash', 'created_at', 
                          'eid', 'thread_id']
                email_backup = dict(zip(columns, email_data))
                
                # Quarantine each violation
                for violation in violations:
                    self._quarantine_email(email_id, violation, batch_id, email_backup)
                    violation_counts[violation] = violation_counts.get(violation, 0) + 1
                
                # Delete from main table
                self.db.execute("DELETE FROM emails WHERE id = ?", (email_id,))
                quarantined_count += 1
                
            except Exception as e:
                logger.error(f"Failed to quarantine email {email_id}: {e}")
        
        # Update batch summary
        self._update_batch_summary(batch_id, quarantined_count, violation_counts)
        
        # Get remaining count
        remaining_count = self.db.execute("SELECT COUNT(*) FROM emails").fetchall()[0][0]
        
        result = QuarantineResult(
            batch_id=batch_id,
            total_scanned=quarantined_count + remaining_count,
            quarantined_rows=quarantined_count,
            kept_rows=remaining_count,
            violations=violation_counts
        )
        
        logger.info(f"Quarantine complete: {quarantined_count} quarantined, "
                   f"{remaining_count} kept")
        
        return result
    
    def _create_quarantine_batch(self, batch_id: str, violations_by_email: Dict):
        """Create quarantine batch record."""
        violation_summary = {}
        for violations in violations_by_email.values():
            for violation in violations:
                violation_summary[violation] = violation_summary.get(violation, 0) + 1
        
        self.db.execute("""
            INSERT INTO quarantine_batches 
            (batch_id, total_quarantined, reason_summary, operator)
            VALUES (?, ?, ?, ?)
        """, (
            batch_id,
            len(violations_by_email),
            json.dumps(violation_summary),
            "email_sanitizer"
        ))
    
    def _quarantine_email(self, email_id: int, reason: str, batch_id: str, 
                         email_backup: Dict):
        """Move single email to quarantine."""
        message_id = email_backup.get('message_id', '')
        
        self.db.execute("""
            INSERT INTO emails_quarantine
            (email_id, message_id, reason, batch_id, original_data, error_details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            email_id,
            message_id,
            reason,
            batch_id,
            json.dumps(email_backup),
            f"Validation failed: {self.validator.RULES[reason].description}"
        ))
    
    def _update_batch_summary(self, batch_id: str, total_quarantined: int, 
                            violation_counts: Dict):
        """Update batch with final summary."""
        self.db.execute("""
            UPDATE quarantine_batches 
            SET total_quarantined = ?, reason_summary = ?
            WHERE batch_id = ?
        """, (
            total_quarantined,
            json.dumps(violation_counts),
            batch_id
        ))
    
    def rollback_quarantine(self, batch_id: str) -> bool:
        """
        Restore emails from quarantine batch.
        
        Args:
            batch_id: Batch to restore
            
        Returns:
            Success status
        """
        logger.info(f"Rolling back quarantine batch: {batch_id}")
        
        try:
            # Get quarantined emails from this batch
            quarantined = self.db.execute("""
                SELECT email_id, original_data 
                FROM emails_quarantine 
                WHERE batch_id = ? AND status = 'quarantined'
            """, (batch_id,)).fetchall()
            
            restored_count = 0
            
            for email_id, original_data_json in quarantined:
                try:
                    # Parse original data
                    original_data = json.loads(original_data_json)
                    
                    # Restore to emails table
                    columns = list(original_data.keys())
                    placeholders = ','.join(['?' for _ in columns])
                    values = list(original_data.values())
                    
                    self.db.execute(f"""
                        INSERT OR REPLACE INTO emails ({','.join(columns)})
                        VALUES ({placeholders})
                    """, values)
                    
                    # Mark as restored in quarantine
                    self.db.execute("""
                        UPDATE emails_quarantine 
                        SET status = 'restored' 
                        WHERE email_id = ? AND batch_id = ?
                    """, (email_id, batch_id))
                    
                    restored_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to restore email {email_id}: {e}")
            
            # Mark batch as rolled back
            self.db.execute("""
                UPDATE quarantine_batches 
                SET rolled_back_at = CURRENT_TIMESTAMP 
                WHERE batch_id = ?
            """, (batch_id,))
            
            logger.info(f"Rollback complete: {restored_count} emails restored")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return False
    
    def get_quarantine_stats(self) -> Dict[str, Any]:
        """Get quarantine statistics."""
        stats = {}
        
        # Total quarantined
        total = self.db.execute(
            "SELECT COUNT(*) FROM emails_quarantine WHERE status = 'quarantined'"
        ).fetchall()[0][0]
        stats['total_quarantined'] = total
        
        # By reason
        by_reason = self.db.execute("""
            SELECT reason, COUNT(*) 
            FROM emails_quarantine 
            WHERE status = 'quarantined'
            GROUP BY reason
        """).fetchall()
        stats['by_reason'] = dict(by_reason)
        
        # Recent batches
        recent_batches = self.db.execute("""
            SELECT batch_id, total_quarantined, reason_summary, created_at
            FROM quarantine_batches
            ORDER BY created_at DESC
            LIMIT 5
        """).fetchall()
        stats['recent_batches'] = [
            {
                'batch_id': row[0],
                'total': row[1], 
                'reasons': json.loads(row[2] or '{}'),
                'created_at': row[3]
            }
            for row in recent_batches
        ]
        
        return stats