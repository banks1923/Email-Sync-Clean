#!/usr/bin/env python3
"""
Setup semantic enrichment tables in database.
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))



def setup_semantic_schema(db_path="data/system_data/emails.db"):
    """
    Create tables needed for semantic enrichment.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Setting up semantic enrichment schema...")

    # Create entity_content_mapping table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS entity_content_mapping (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT,
            entity_value TEXT,
            entity_type TEXT,
            content_id TEXT,
            message_id TEXT,
            confidence REAL DEFAULT 1.0,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    print("✅ Created entity_content_mapping table")

    # Create indices for entity table
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_content 
        ON entity_content_mapping(content_id)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_message 
        ON entity_content_mapping(message_id)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_entity_type 
        ON entity_content_mapping(entity_type)
    """
    )
    print("✅ Created entity indices")

    # Create timeline_events table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS timeline_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content_id TEXT,
            event_date TEXT,
            event_type TEXT,
            description TEXT,
            metadata TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    print("✅ Created timeline_events table")

    # Create indices for timeline
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_timeline_content 
        ON timeline_events(content_id)
    """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_timeline_date 
        ON timeline_events(event_date)
    """
    )
    print("✅ Created timeline indices")

    # Create consolidated_entities table for entity normalization
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS consolidated_entities (
            entity_id TEXT PRIMARY KEY,
            primary_name TEXT,
            entity_type TEXT,
            aliases TEXT,
            additional_info TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    print("✅ Created consolidated_entities table")

    # Create entity_relationships table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS entity_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entity_id TEXT,
            target_entity_id TEXT,
            relationship_type TEXT,
            confidence REAL DEFAULT 0.5,
            source_message_id TEXT,
            context_snippet TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    print("✅ Created entity_relationships table")

    conn.commit()
    conn.close()

    print("\n✅ Semantic schema setup complete!")

    # Show table info
    print("\n📊 Database tables:")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """
    )

    for row in cursor.fetchall():
        print(f"  - {row[0]}")

    conn.close()


if __name__ == "__main__":
    setup_semantic_schema()
