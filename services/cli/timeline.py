#!/usr/bin/env python3
"""
Timeline Handler - Modular CLI component for timeline operations
Handles: timeline command
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def show_timeline(start_date=None, end_date=None, event_types=None, limit=20):
    """
    Show chronological timeline of content.
    """
    print("📅 Content Timeline")
    print("=" * 40)

    try:
        from lib.timeline import TimelineService

        timeline_service = TimelineService()

        # Sync recent content to timeline
        print("🔄 Syncing content to timeline...")
        sync_result = timeline_service.sync_emails_to_timeline(limit=100)
        doc_sync_result = timeline_service.sync_documents_to_timeline(limit=50)

        print(f"   📧 Synced {sync_result.get('synced_events', 0)} email events")
        print(f"   📄 Synced {doc_sync_result.get('synced_events', 0)} document events")

        # Get timeline view
        result = timeline_service.get_timeline_view(
            start_date=start_date,
            end_date=end_date,
            event_types=event_types or ["email", "document"],
            limit=limit,
        )

        if result["success"]:
            events = result.get("timeline", [])
            if events:
                print(f"\n📋 Showing {len(events)} events:\n")

                for i, event in enumerate(events, 1):
                    event_type = event.get("event_type", "unknown")
                    title = event.get("title", "No title")
                    date = event.get("event_date", "Unknown date")
                    description = event.get("description", "")

                    # Event type icons
                    icons = {"email": "📧", "document": "📄", "transcript": "🎙️"}
                    icon = icons.get(event_type, "📋")

                    print(f"{icon} {i}. {title}")
                    print(f"   📅 {date}")
                    if description:
                        print(f"   📝 {description}")
                    print()

                    if i >= limit:
                        break
            else:
                print("📋 No events found for the specified criteria")

            return True
        else:
            print(f"❌ Timeline error: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Timeline error: {e}")
        return False
