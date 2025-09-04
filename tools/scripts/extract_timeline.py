#!/usr/bin/env python3
"""
Timeline Extraction Script - Simplified version using TimelineService

Processes documents and generates timeline from content in database.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utilities.timeline import TimelineService


def extract_timeline_from_database(_ = "MEDIUM") -> dict:
    """
    Extract timeline events from database content.
    """

    # Get timeline service
    service = TimelineService()

    # Get all timeline events from database
    events = service.get_all_events()

    if not events:
        logger.warning("No timeline events found in database")
        return {"total_events": 0, "events": [], "date_range": None}

    # Filter by confidence if needed (simplified for now)
    # In real implementation, would need confidence scoring

    # Sort events by date
    sorted_events = sorted(events, key=lambda x: x.get("date", ""))

    # Generate summary
    summary = {
        "total_events": len(events),
        "events": sorted_events,
        "date_range": {
            "start": sorted_events[0].get("date") if sorted_events else None,
            "end": sorted_events[-1].get("date") if sorted_events else None,
        },
    }

    return summary


def generate_markdown_timeline(events: list, output_path: str) -> str:
    """
    Generate markdown timeline from events.
    """

    lines = []
    lines.append("# Timeline of Events")
    lines.append(f"\nGenerated: {datetime.now().isoformat()}")
    lines.append(f"Total Events: {len(events)}\n")
    lines.append("---\n")

    # Group events by date
    events_by_date = {}
    for event in events:
        date = event.get("date", "Unknown")
        if date not in events_by_date:
            events_by_date[date] = []
        events_by_date[date].append(event)

    # Generate timeline
    for date in sorted(events_by_date.keys()):
        lines.append(f"\n## {date}\n")
        for event in events_by_date[date]:
            lines.append(
                f"- **{event.get('type', 'Event')}**: {event.get('description', 'No description')}"
            )
            if event.get("content_id"):
                lines.append(f"  - Source: Document ID {event['content_id']}")

    timeline_content = "\n".join(lines)

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(timeline_content)

    return timeline_content


def main():
    """
    Main timeline extraction function.
    """
    parser = argparse.ArgumentParser(
        description="Extract timeline from database content",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/extract_timeline.py
  python scripts/extract_timeline.py --output timeline.md
  python scripts/extract_timeline.py --confidence HIGH
        """,
    )

    parser.add_argument(
        "--output",
        default="data/export/timeline.md",
        help="Output timeline file (default: data/export/timeline.md)",
    )

    parser.add_argument(
        "--confidence",
        choices=["LOW", "MEDIUM", "HIGH"],
        default="MEDIUM",
        help="Minimum confidence level for events (default: MEDIUM)",
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only show statistics, don't generate timeline file",
    )

    args = parser.parse_args()

    # Extract timeline from database
    logger.info("Extracting timeline events from database...")
    timeline_data = extract_timeline_from_database(args.confidence)

    # Print statistics
    print("\n" + "=" * 60)
    print("TIMELINE EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Total events found: {timeline_data['total_events']}")

    if timeline_data["date_range"]:
        print(
            f"Date range: {timeline_data['date_range']['start']} to {timeline_data['date_range']['end']}"
        )

    if args.stats_only or timeline_data["total_events"] == 0:
        print("\nStats-only mode or no events found. Timeline file not generated.")
        return

    # Generate timeline file
    try:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        generate_markdown_timeline(timeline_data["events"], str(output_path))

        print(f"\n✅ Timeline generated: {output_path}")
        print(f"   Events included: {timeline_data['total_events']}")

    except Exception as e:
        logger.error(f"Error generating timeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
