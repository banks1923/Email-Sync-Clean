#!/usr/bin/env python3
"""Backfill timeline events with missing titles.

Fixes NOT NULL constraint violations by generating meaningful titles
for timeline events that were created without them.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB


def backfill_timeline_titles():
    """Add titles to timeline events that don't have them."""
    print("🔧 Backfilling timeline event titles...")
    
    db = SimpleDB()
    
    # First, check how many events need titles
    cursor = db.execute("""
        SELECT COUNT(*) as count
        FROM timeline_events 
        WHERE title IS NULL OR trim(title) = ''
    """)
    
    count_missing = cursor.fetchone()['count']
    print(f"Found {count_missing} timeline events missing titles")
    
    if count_missing == 0:
        print("✅ All timeline events already have titles")
        return
    
    # Update titles based on available fields
    updates = 0
    
    # Strategy 1: Use event_type and event_date
    cursor = db.execute("""
        UPDATE timeline_events 
        SET title = CASE
            WHEN event_type IS NOT NULL AND event_date IS NOT NULL THEN 
                event_type || ' – ' || substr(event_date, 1, 10)
            WHEN event_type IS NOT NULL THEN 
                event_type
            ELSE 
                'Event'
        END
        WHERE (title IS NULL OR trim(title) = '')
          AND (event_type IS NOT NULL OR event_date IS NOT NULL)
    """)
    
    strategy1_updates = cursor.rowcount
    updates += strategy1_updates
    print(f"Updated {strategy1_updates} events using event_type + date")
    
    # Strategy 2: For remaining events, try to extract from description
    cursor = db.execute("""
        SELECT event_id, description, event_date
        FROM timeline_events 
        WHERE (title IS NULL OR trim(title) = '')
          AND description IS NOT NULL
        LIMIT 1000
    """)
    
    remaining_events = cursor.fetchall()
    
    for event in remaining_events:
        event_id = event['event_id']
        description = event['description'] or ''
        event_date = event['event_date'] or ''
        
        # Generate title from description
        if description:
            # Take first part of description as title (up to first sentence/50 chars)
            title_part = description.split('.')[0].split(',')[0].strip()
            if len(title_part) > 50:
                title_part = title_part[:47] + '...'
            
            # Add date if available
            date_part = event_date[:10] if event_date else ''
            if date_part:
                title = f"{title_part} – {date_part}"
            else:
                title = title_part
        else:
            # Last resort: use date or generic title
            title = event_date[:10] if event_date else 'Timeline Event'
            
        # Update this specific event
        try:
            db.execute("""
                UPDATE timeline_events 
                SET title = ?
                WHERE event_id = ?
            """, (title, event_id))
            updates += 1
        except Exception as e:
            logger.warning(f"Failed to update event {event_id}: {e}")
            
    print(f"Updated {len(remaining_events)} events using description analysis")
    
    # Final fallback: any remaining NULL titles get a generic title
    cursor = db.execute("""
        UPDATE timeline_events 
        SET title = 'Timeline Event'
        WHERE title IS NULL OR trim(title) = ''
    """)
    
    fallback_updates = cursor.rowcount
    updates += fallback_updates
    if fallback_updates > 0:
        print(f"Updated {fallback_updates} events with fallback title")
    
    # Verify completion
    cursor = db.execute("""
        SELECT COUNT(*) as count
        FROM timeline_events 
        WHERE title IS NULL OR trim(title) = ''
    """)
    
    remaining = cursor.fetchone()['count']
    
    if remaining == 0:
        print(f"✅ Successfully updated {updates} timeline event titles")
        
        # Add index for performance if it doesn't exist
        try:
            db.execute("""
                CREATE INDEX IF NOT EXISTS ix_timeline_events_message_id 
                ON timeline_events(json_extract(metadata, '$.message_id'))
            """)
            print("✅ Added timeline events message_id index")
        except Exception as e:
            logger.warning(f"Index creation failed (may already exist): {e}")
            
    else:
        print(f"⚠️  {remaining} events still missing titles after backfill")
        
    return updates


def verify_backfill():
    """Verify that the backfill was successful."""
    print("\n🔍 Verifying backfill results...")
    
    db = SimpleDB()
    
    # Check title distribution
    cursor = db.execute("""
        SELECT 
            COUNT(*) as total_events,
            COUNT(CASE WHEN title IS NOT NULL AND trim(title) != '' THEN 1 END) as with_titles,
            COUNT(CASE WHEN title IS NULL OR trim(title) = '' THEN 1 END) as missing_titles
        FROM timeline_events
    """)
    
    stats = cursor.fetchone()
    
    print(f"Total timeline events: {stats['total_events']}")
    print(f"Events with titles: {stats['with_titles']}")
    print(f"Events missing titles: {stats['missing_titles']}")
    
    if stats['missing_titles'] == 0:
        print("✅ All timeline events now have titles")
    else:
        print(f"❌ {stats['missing_titles']} events still missing titles")
        
    # Show sample titles
    cursor = db.execute("""
        SELECT title, event_type, substr(event_date, 1, 10) as date
        FROM timeline_events 
        WHERE title IS NOT NULL 
        ORDER BY rowid 
        LIMIT 5
    """)
    
    samples = cursor.fetchall()
    if samples:
        print("\nSample generated titles:")
        for sample in samples:
            print(f"  • {sample['title']} ({sample['event_type']}, {sample['date']})")


if __name__ == "__main__":
    try:
        updated = backfill_timeline_titles()
        verify_backfill()
        
        print("\n" + "=" * 60)
        print("Timeline Title Backfill Complete")
        print("=" * 60)
        
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Backfill failed: {e}")
        sys.exit(1)