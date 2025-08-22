#!/usr/bin/env python3
"""
Email Sanitation Report Generator - Creates comprehensive JSON reports.
Implements the exact deliverable format specified in the assignment.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from utilities.maintenance.email_quarantine import EmailQuarantineManager, EmailValidator
from utilities.maintenance.vector_reconciliation import VectorReconciliationService
from shared.simple_db import SimpleDB
from loguru import logger


class EmailSanitationReporter:
    """Generates comprehensive email sanitation reports."""
    
    def __init__(self, db_path: str = "data/emails.db"):
        self.db = SimpleDB(db_path)
        self.quarantine_manager = EmailQuarantineManager(db_path)
        self.vector_service = VectorReconciliationService(db_path)
        
    def generate_scan_report(self) -> Dict[str, Any]:
        """
        Generate the exact JSON format specified in the deliverables.
        
        Returns:
            Dictionary matching the required schema
        """
        logger.info("Generating comprehensive email sanitation report")
        
        # Get scan data
        scan_data = self.quarantine_manager.scan_emails()
        
        # Get vector sync status
        vector_status = self.vector_service.get_vector_sync_status()
        
        # Get quarantine stats
        quarantine_stats = self.quarantine_manager.get_quarantine_stats()
        
        # Build the exact format required
        report = {
            "ts": datetime.now().isoformat(),
            "regex": {
                "gmail_message_id": EmailValidator.GMAIL_MESSAGE_ID_PATTERN.pattern
            },
            "dataset_scan": scan_data['scan_results'],
            "actions": {
                "quarantined_rows": quarantine_stats.get("total_quarantined", 0),
                "kept_rows": scan_data['scan_results']['total'] - quarantine_stats.get("total_quarantined", 0),
                "vectors_deleted_from_qdrant": 0,  # Will be updated during actual operations
                "embeddings_enqueued": 0,          # Will be updated during actual operations  
                "embeddings_upserted": 0           # Will be updated during actual operations
            },
            "ci_gates": {
                "pre_embedding_gate_enabled": True,
                "docs": "fails build if any invalid rows found"
            },
            "notes": self._generate_notes(scan_data, vector_status, quarantine_stats)
        }
        
        return report
    
    def generate_operation_report(self, operation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate report after actual sanitation operations.
        
        Args:
            operation_results: Results from quarantine and vector operations
            
        Returns:
            Complete operation report
        """
        # Get fresh scan data
        scan_data = self.quarantine_manager.scan_emails()
        
        report = {
            "ts": datetime.now().isoformat(),
            "regex": {
                "gmail_message_id": EmailValidator.GMAIL_MESSAGE_ID_PATTERN.pattern
            },
            "dataset_scan": scan_data['scan_results'],
            "actions": {
                "quarantined_rows": operation_results.get("quarantined_rows", 0),
                "kept_rows": operation_results.get("kept_rows", 0),
                "vectors_deleted_from_qdrant": operation_results.get("vectors_deleted", 0),
                "embeddings_enqueued": operation_results.get("embeddings_enqueued", 0),
                "embeddings_upserted": operation_results.get("embeddings_upserted", 0)
            },
            "ci_gates": {
                "pre_embedding_gate_enabled": True,
                "docs": "fails build if any invalid rows found"
            },
            "notes": self._generate_operation_notes(operation_results)
        }
        
        return report
    
    def _generate_notes(self, scan_data: Dict, vector_status: Dict, quarantine_stats: Dict) -> str:
        """Generate notes section for scan report."""
        violations = scan_data['violations_by_email']
        total_emails = scan_data['scan_results']['total']
        
        if not violations:
            return f"Clean dataset: {total_emails} emails, no violations found. Vector sync status: {vector_status.get('sync_ratio', 0):.2%}"
        
        violation_count = len(violations)
        return f"Found {violation_count} emails with violations out of {total_emails} total. " + \
               f"Current quarantine: {quarantine_stats.get('total_quarantined', 0)} emails. " + \
               f"Vector store has {vector_status.get('qdrant_vectors', 0)} vectors."
    
    def _generate_operation_notes(self, operation_results: Dict[str, Any]) -> str:
        """Generate notes for operation report."""
        quarantined = operation_results.get("quarantined_rows", 0)
        kept = operation_results.get("kept_rows", 0)
        vectors_deleted = operation_results.get("vectors_deleted", 0)
        
        return f"Sanitation complete: {quarantined} emails quarantined, {kept} kept. " + \
               f"Removed {vectors_deleted} vectors from Qdrant. " + \
               "Pre-embedding validation gate active."
    
    def validate_report_schema(self, report: Dict[str, Any]) -> bool:
        """
        Validate that report matches required schema.
        
        Returns:
            True if schema is valid
        """
        required_keys = {
            "ts": str,
            "regex": dict,
            "dataset_scan": dict,
            "actions": dict,
            "ci_gates": dict,
            "notes": str
        }
        
        for key, expected_type in required_keys.items():
            if key not in report:
                logger.error(f"Missing required key: {key}")
                return False
            if not isinstance(report[key], expected_type):
                logger.error(f"Key {key} has wrong type: expected {expected_type}, got {type(report[key])}")
                return False
        
        # Check nested structures
        if "gmail_message_id" not in report["regex"]:
            logger.error("Missing gmail_message_id in regex section")
            return False
        
        required_dataset_keys = ["total", "invalid_ids", "no_subject", "whitespace_body", "tiny_body_lt5", "out_of_range_dates", "duplicates"]
        for key in required_dataset_keys:
            if key not in report["dataset_scan"]:
                logger.error(f"Missing dataset_scan key: {key}")
                return False
        
        required_action_keys = ["quarantined_rows", "kept_rows", "vectors_deleted_from_qdrant", "embeddings_enqueued", "embeddings_upserted"]
        for key in required_action_keys:
            if key not in report["actions"]:
                logger.error(f"Missing actions key: {key}")
                return False
        
        logger.info("Report schema validation passed")
        return True
    
    def export_report(self, report: Dict[str, Any], output_file: str = None) -> str:
        """
        Export report to JSON file.
        
        Args:
            report: Report dictionary
            output_file: Optional output file path
            
        Returns:
            Path to exported file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"data/reports/email_sanitation_report_{timestamp}.json"
        
        # Ensure directory exists
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate schema before export
        if not self.validate_report_schema(report):
            raise ValueError("Report does not match required schema")
        
        # Write report
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Report exported to: {output_path}")
        return str(output_path)
    
    def get_ci_validation_status(self) -> Dict[str, Any]:
        """
        Get current CI validation status.
        
        Returns:
            CI validation result
        """
        scan_data = self.quarantine_manager.scan_emails()
        violations = scan_data['violations_by_email']
        
        # CI fails if any invalid rows found
        has_violations = len(violations) > 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "validation_passed": not has_violations,
            "exit_code": 1 if has_violations else 0,
            "violations_found": len(violations),
            "violation_types": list(set(
                violation 
                for violation_list in violations.values() 
                for violation in violation_list
            )) if violations else [],
            "message": f"Found {len(violations)} emails with violations" if has_violations else "All emails valid"
        }


def main():
    """CLI entry point for report generation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Email sanitation report generator")
    parser.add_argument("--output", help="Output file path")
    parser.add_argument("--db-path", default="data/emails.db", help="Database path")
    parser.add_argument("--format", choices=["json", "pretty"], default="json", help="Output format")
    parser.add_argument("--ci-check", action="store_true", help="CI validation check (exits with code)")
    
    args = parser.parse_args()
    
    reporter = EmailSanitationReporter(args.db_path)
    
    if args.ci_check:
        # CI validation mode
        result = reporter.get_ci_validation_status()
        
        if args.format == "pretty":
            print(f"CI Validation: {'PASS' if result['validation_passed'] else 'FAIL'}")
            print(f"Violations: {result['violations_found']}")
            if result['violation_types']:
                print(f"Types: {', '.join(result['violation_types'])}")
        else:
            print(json.dumps(result, indent=2))
        
        sys.exit(result['exit_code'])
    
    else:
        # Generate full report
        report = reporter.generate_scan_report()
        
        if args.output:
            output_path = reporter.export_report(report, args.output)
            print(f"Report saved to: {output_path}")
        else:
            if args.format == "pretty":
                print("Email Sanitation Report")
                print("=" * 40)
                print(f"Timestamp: {report['ts']}")
                print(f"Total emails: {report['dataset_scan']['total']}")
                print(f"Quarantined: {report['actions']['quarantined_rows']}")
                print(f"Kept: {report['actions']['kept_rows']}")
                print(f"Gmail ID pattern: {report['regex']['gmail_message_id']}")
                print(f"Notes: {report['notes']}")
            else:
                print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()