#!/usr/bin/env python3
"""Test script for semantic enrichment pipeline.

Tests that semantic enrichment happens during email ingestion.
"""

import os

# Enable semantic processing
os.environ["SEMANTICS_ON_INGEST"] = "true"


from config.settings import semantic_settings
from lib.db import SimpleDB


def test_semantic_pipeline():
    """
    Test semantic enrichment pipeline with a small batch of emails.
    """

    print("=" * 60)
    print("Semantic Pipeline Test")
    print("=" * 60)

    # Check configuration
    print("\n📋 Configuration:")
    print(f"  SEMANTICS_ON_INGEST: {semantic_settings.semantics_on_ingest}")
    print(f"  Steps configured: {', '.join(semantic_settings.semantics_steps)}")
    print(f"  Max batch size: {semantic_settings.semantics_max_batch}")
    print(f"  Timeout per step: {semantic_settings.semantics_timeout_s}s")

    # Get baseline counts
    db = SimpleDB()

    print("\n📊 Baseline counts:")
    cursor = db.execute("SELECT COUNT(*) FROM emails")
    email_count = cursor.fetchone()[0]
    print(f"  Total emails: {email_count}")

    cursor = db.execute("SELECT COUNT(*) FROM entity_content_mapping")
    entity_count = cursor.fetchone()[0]
    print(f"  Total entities: {entity_count}")

    cursor = db.execute("SELECT COUNT(*) FROM content_unified WHERE embedding_generated = 1")
    vector_count = cursor.fetchone()[0]
    print(f"  Vectorized content: {vector_count}")

    cursor = db.execute("SELECT COUNT(*) FROM timeline_events")
    timeline_count = cursor.fetchone()[0]
    print(f"  Timeline events: {timeline_count}")

    # Test the pipeline directly with existing emails
    print("\n🧪 Testing semantic pipeline with existing emails...")

    # Get 5 recent emails that might not be fully processed
    # Check if eid column exists
    cursor = db.execute("PRAGMA table_info(emails)")
    columns = [col[1] for col in cursor.fetchall()]

    if "eid" in columns:
        cursor = db.execute(
            """
            SELECT message_id FROM emails 
            WHERE eid IS NOT NULL
            ORDER BY datetime_utc DESC
            LIMIT 5
        """
        )
    else:
        # Fallback if eid column doesn't exist
        cursor = db.execute(
            """
            SELECT message_id FROM emails 
            ORDER BY datetime_utc DESC
            LIMIT 5
        """
        )

    test_emails = [row["message_id"] for row in cursor.fetchall()]

    if test_emails:
        print(f"  Testing with {len(test_emails)} emails")

        from lib.pipelines import get_semantic_pipeline

        pipeline = get_semantic_pipeline()
        result = pipeline.run_for_messages(
            message_ids=test_emails, steps=["entities", "embeddings", "timeline"]  # Skip summary
        )

        print("\n📈 Pipeline Results:")
        for step, step_result in result.get("step_results", {}).items():
            print(f"\n  {step}:")
            print(f"    Processed: {step_result.get('processed', 0)}")
            print(f"    Skipped: {step_result.get('skipped', 0)}")
            print(f"    Errors: {step_result.get('errors', 0)}")
            if "elapsed_s" in step_result:
                print(f"    Time: {step_result['elapsed_s']:.2f}s")

        # Check for changes
        print("\n📊 After pipeline:")

        cursor = db.execute("SELECT COUNT(*) FROM entity_content_mapping")
        new_entity_count = cursor.fetchone()[0]
        print(f"  Total entities: {new_entity_count} (+{new_entity_count - entity_count})")

        cursor = db.execute("SELECT COUNT(*) FROM content_unified WHERE embedding_generated = 1")
        new_vector_count = cursor.fetchone()[0]
        print(f"  Vectorized content: {new_vector_count} (+{new_vector_count - vector_count})")

        cursor = db.execute("SELECT COUNT(*) FROM timeline_events")
        new_timeline_count = cursor.fetchone()[0]
        print(f"  Timeline events: {new_timeline_count} (+{new_timeline_count - timeline_count})")

        # Verify EID references
        print("\n🔍 Checking EID integration:")

        # Check if entities have EID references
        cursor = db.execute(
            """
            SELECT COUNT(*) FROM entity_content_mapping
        """
        )
        eid_entity_count = cursor.fetchone()[0]
        print(f"  Total entities mapped: {eid_entity_count}")

        # Check if timeline events have EID references
        cursor = db.execute(
            """
            SELECT COUNT(*) FROM timeline_events
            WHERE metadata LIKE '%eid_ref%'
        """
        )
        eid_timeline_count = cursor.fetchone()[0]
        print(f"  Timeline events with EID refs: {eid_timeline_count}")

        print("\n✅ Semantic pipeline test complete!")

    else:
        print("⚠️  No emails with EIDs found.")


if __name__ == "__main__":
    test_semantic_pipeline()
