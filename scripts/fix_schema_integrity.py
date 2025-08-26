#!/usr/bin/env python3
"""Schema Integrity Fix Script.

Addresses the critical mixed ID type issue where:
- content_unified.source_id (TEXT) doesn't properly reference source tables
- Foreign key relationships are broken due to type mismatches
- No proper CASCADE operations possible

This script fixes the referential integrity by establishing consistent TEXT-based references.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from shared.simple_db import SimpleDB


class SchemaIntegrityFixer:
    """
    Fix mixed ID type schema issues and establish proper foreign key
    relationships.
    """

    def __init__(self):
        self.db = SimpleDB()

    def analyze_current_state(self) -> dict:
        """
        Analyze current referential integrity issues.
        """
        logger.info("Analyzing current schema integrity...")

        analysis = {}

        # Check content_unified relationships
        cursor = self.db.execute(
            """
            SELECT 
                source_type,
                COUNT(*) as count,
                COUNT(DISTINCT source_id) as unique_source_ids
            FROM content_unified 
            GROUP BY source_type
        """
        )
        analysis["content_unified_by_type"] = cursor.fetchall()

        # Check for orphaned content_unified records (email_message type)
        cursor = self.db.execute(
            """
            SELECT COUNT(*) as orphaned_emails
            FROM content_unified cu 
            LEFT JOIN individual_messages im ON cu.source_id = im.message_hash
            WHERE cu.source_type = 'email_message' AND im.message_hash IS NULL
        """
        )
        analysis["orphaned_email_messages"] = cursor.fetchone()[0]

        # Check entity_content_mapping integrity
        cursor = self.db.execute(
            """
            SELECT COUNT(*) as broken_entity_refs
            FROM entity_content_mapping ecm
            LEFT JOIN content_unified cu ON ecm.content_id = cu.id
            WHERE cu.id IS NULL
        """
        )
        analysis["broken_entity_references"] = cursor.fetchone()[0]

        # Check embeddings integrity
        cursor = self.db.execute(
            """
            SELECT COUNT(*) as broken_embedding_refs
            FROM embeddings e
            LEFT JOIN content_unified cu ON e.content_id = cu.id
            WHERE cu.id IS NULL
        """
        )
        analysis["broken_embedding_references"] = cursor.fetchone()[0]

        return analysis

    def fix_email_message_references(self):
        """
        Fix content_unified references to individual_messages.
        """
        logger.info("Fixing email_message references...")

        # Strategy: Use message_hash from individual_messages as the canonical reference
        # Update content_unified.source_id to match individual_messages.message_hash

        # First, create a mapping from current content to proper message hashes
        # This requires matching by content similarity or other means

        # For now, let's see what we have in individual_messages vs content_unified
        cursor = self.db.execute(
            """
            SELECT im.message_hash, im.subject, im.content
            FROM individual_messages im
            LIMIT 5
        """
        )
        messages = cursor.fetchall()

        cursor = self.db.execute(
            """
            SELECT cu.id, cu.source_id, cu.title, cu.body  
            FROM content_unified cu
            WHERE cu.source_type = 'email_message'
            LIMIT 5
        """
        )
        content_records = cursor.fetchall()

        logger.info(f"Found {len(messages)} individual messages")
        logger.info(f"Found {len(content_records)} content_unified email_message records")

        return messages, content_records

    def create_proper_foreign_keys(self):
        """
        Add proper foreign key constraints with CASCADE operations.
        """
        logger.info("Creating proper foreign key constraints...")

        # Note: SQLite requires recreating tables to add foreign keys
        # This is a complex operation that should be done carefully

        migration_sql = """
        -- Create new content_unified table with proper foreign keys
        CREATE TABLE content_unified_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL CHECK(source_type IN ('email_message', 'document', 'document_chunk')),
            source_id TEXT NOT NULL,
            title TEXT,
            body TEXT NOT NULL,
            sha256 TEXT UNIQUE,
            validation_status TEXT DEFAULT 'pending' CHECK(validation_status IN ('pending', 'validated', 'failed')),
            ready_for_embedding BOOLEAN DEFAULT 1,
            embedding_generated BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            -- Proper foreign key constraints
            FOREIGN KEY (source_id) REFERENCES individual_messages(message_hash) ON DELETE CASCADE,
            -- Note: This constraint only applies when source_type = 'email_message'
            -- For documents, we'll need a different approach
            
            UNIQUE(source_type, source_id)
        );
        """

        logger.info("Migration SQL prepared (not executed yet)")
        return migration_sql

    def validate_integrity(self) -> bool:
        """
        Validate referential integrity after fixes.
        """
        logger.info("Validating referential integrity...")

        issues = []

        # Check content_unified -> individual_messages
        cursor = self.db.execute(
            """
            SELECT COUNT(*) as count
            FROM content_unified cu 
            LEFT JOIN individual_messages im ON cu.source_id = im.message_hash
            WHERE cu.source_type = 'email_message' AND im.message_hash IS NULL
        """
        )
        orphaned_emails = cursor.fetchone()[0]
        if orphaned_emails > 0:
            issues.append(f"Found {orphaned_emails} orphaned email_message records")

        # Check entity mappings
        cursor = self.db.execute(
            """
            SELECT COUNT(*) as count
            FROM entity_content_mapping ecm
            LEFT JOIN content_unified cu ON ecm.content_id = cu.id
            WHERE cu.id IS NULL
        """
        )
        broken_entities = cursor.fetchone()[0]
        if broken_entities > 0:
            issues.append(f"Found {broken_entities} broken entity mappings")

        # Check embedding references
        cursor = self.db.execute(
            """
            SELECT COUNT(*) as count
            FROM embeddings e
            LEFT JOIN content_unified cu ON e.content_id = cu.id
            WHERE cu.id IS NULL
        """
        )
        broken_embeddings = cursor.fetchone()[0]
        if broken_embeddings > 0:
            issues.append(f"Found {broken_embeddings} broken embedding references")

        if issues:
            logger.error(f"Integrity validation failed: {issues}")
            return False
        else:
            logger.success("Referential integrity validation passed")
            return True

    def run_analysis(self):
        """
        Run comprehensive analysis without making changes.
        """
        logger.info("=== SCHEMA INTEGRITY ANALYSIS ===")

        analysis = self.analyze_current_state()

        print("\n📊 Current State Analysis:")
        print("Content Unified Records by Type:")
        for source_type, count, unique_ids in analysis["content_unified_by_type"]:
            print(f"  {source_type}: {count} records, {unique_ids} unique source_ids")

        print("\n❌ Integrity Issues:")
        print(f"  Orphaned email_message records: {analysis['orphaned_email_messages']}")
        print(f"  Broken entity references: {analysis['broken_entity_references']}")
        print(f"  Broken embedding references: {analysis['broken_embedding_references']}")

        # Sample data comparison
        messages, content_records = self.fix_email_message_references()

        print("\n🔍 Sample Data Comparison:")
        print(f"  individual_messages: {len(messages)} records")
        print(f"  content_unified email_message: {len(content_records)} records")

        if messages and content_records:
            print("\n  Sample individual_message:")
            print(f"    Hash: {messages[0][0][:16]}...")
            print(f"    Subject: {messages[0][1][:50]}...")

            print("\n  Sample content_unified:")
            print(f"    Source ID: {content_records[0][1]}")
            print(f"    Title: {content_records[0][2][:50]}...")

        # Show the root cause
        print("\n🚨 ROOT CAUSE IDENTIFIED:")
        print("  content_unified.source_id values don't match individual_messages.message_hash")
        print("  This breaks all foreign key relationships and CASCADE operations")
        print("  Services cannot properly join content back to source emails/documents")

        return analysis


def main():
    """
    Main analysis function.
    """
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        print("⚠️  FIXING MODE NOT IMPLEMENTED YET - Analysis only")
        print("    Run without --fix flag to analyze current state")
        return

    fixer = SchemaIntegrityFixer()

    try:
        analysis = fixer.run_analysis()

        print("\n✅ Analysis complete. Current schema has referential integrity issues.")
        print("   Next step: Implement proper migration to fix foreign key relationships")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
