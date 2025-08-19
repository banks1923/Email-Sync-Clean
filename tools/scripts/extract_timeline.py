#!/usr/bin/env python3
"""
Timeline Extraction Script

Processes all documents in data/export/ and generates comprehensive timeline.md.
Follows CLAUDE.md principles: simple, direct implementation under 200 lines.
"""

import argparse
import os
import sys
from pathlib import Path

from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.pipelines.timeline_extractor import TimelineExtractor

# Configure logging
# logging.basicConfig(  # Now configured in shared/loguru_config.pylevel="INFO", format="%(asctime)s - %(levelname)s - %(message)s")
# Logger is now imported globally from loguru


def find_exported_documents(export_dir: str) -> list[str]:
    """Find all markdown documents in export directory."""
    export_path = Path(export_dir)

    if not export_path.exists():
        logger.error(f"Export directory does not exist: {export_dir}")
        return []

    # Find all .md files
    md_files = list(export_path.glob("*.md"))

    # Filter out timeline.md if it exists (don't process our own output)
    md_files = [f for f in md_files if f.name != "timeline.md"]

    logger.info(f"Found {len(md_files)} documents in {export_dir}")
    return [str(f) for f in md_files]


def process_documents(document_paths: list[str], extractor: TimelineExtractor) -> list[dict]:
    """Process all documents and extract timeline events."""
    all_events = []

    for doc_path in document_paths:
        try:
            logger.info(f"Processing: {Path(doc_path).name}")
            events = extractor.extract_dates_from_file(doc_path)
            all_events.extend(events)
            logger.info(f"  Found {len(events)} events")
        except Exception as e:
            logger.error(f"Error processing {doc_path}: {e}")

    return all_events


def main():
    """Main timeline extraction function."""
    parser = argparse.ArgumentParser(
        description="Extract timeline from exported documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/extract_timeline.py
  python scripts/extract_timeline.py --export-dir /custom/path
  python scripts/extract_timeline.py --confidence HIGH --output custom_timeline.md
  python scripts/extract_timeline.py --verbose --stats-only
        """,
    )

    parser.add_argument(
        "--export-dir",
        default="data/export",
        help="Directory containing exported documents (default: data/export)",
    )

    parser.add_argument(
        "--output", default="timeline.md", help="Output timeline file (default: timeline.md)"
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

    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "--store-db", action="store_true", help="Store extracted events in timeline database"
    )

    parser.add_argument(
        "--db-path",
        default="emails.db",
        help="Database path for storing timeline events (default: emails.db)",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.level("DEBUG")

    # Find documents
    document_paths = find_exported_documents(args.export_dir)

    if not document_paths:
        logger.error("No documents found to process")
        sys.exit(1)

    # Initialize extractor
    extractor = TimelineExtractor()

    # Process documents
    logger.info("Starting timeline extraction...")
    all_events = process_documents(document_paths, extractor)

    if not all_events:
        logger.warning("No timeline events found in any documents")
        sys.exit(0)

    # Generate statistics
    summary = extractor.generate_timeline_summary(all_events)

    # Print statistics
    print("\n" + "=" * 60)
    print("TIMELINE EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Documents processed: {len(document_paths)}")
    print(f"Total events found: {summary['total_events']}")
    print(f"Date range: {summary['date_range']['start']} to {summary['date_range']['end']}")
    print(f"Timeline span: {summary['timeline_span_days']} days")
    print("\nConfidence distribution:")
    print(f"  🟢 High: {summary['high_confidence_events']}")
    print(f"  🟡 Medium: {summary['medium_confidence_events']}")
    print(f"  🔴 Low: {summary['low_confidence_events']}")
    print("\nEvent types:")
    for event_type, count in sorted(summary["event_types"].items()):
        print(f"  {event_type.title()}: {count}")

    # Filter by confidence level
    filtered_events = extractor.filter_events_by_confidence(all_events, args.confidence)
    print(f"\nEvents with {args.confidence}+ confidence: {len(filtered_events)}")

    if args.stats_only:
        print("\nStats-only mode enabled. Timeline file not generated.")
        return

    # Generate timeline
    if not filtered_events:
        logger.warning(f"No events meet the {args.confidence} confidence threshold")
        return

    try:
        # Determine output path
        if not os.path.isabs(args.output):
            # Make relative to export directory
            output_path = os.path.join(args.export_dir, args.output)
        else:
            output_path = args.output

        # Generate markdown timeline
        timeline_content = extractor.generate_markdown_timeline(
            all_events, output_path, args.confidence
        )

        print(f"\n✅ Timeline generated: {output_path}")
        print(f"   Events included: {len(filtered_events)}")
        print(f"   Minimum confidence: {args.confidence}")

        # Show preview of timeline content
        lines = timeline_content.split("\n")
        if len(lines) > 10:
            print("\nPreview (first 10 lines):")
            for i, line in enumerate(lines[:10]):
                print(f"  {line}")
            print(f"  ... ({len(lines) - 10} more lines)")

    except Exception as e:
        logger.error(f"Error generating timeline: {e}")
        sys.exit(1)

    # Store in database if requested
    if args.store_db:
        print(f"\n📊 Storing events in database: {args.db_path}")

        try:
            storage_result = extractor.store_events_in_database(filtered_events, args.db_path)

            if storage_result.get("success"):
                print(
                    f"   ✅ Stored {storage_result['stored_count']}/{storage_result['total_events']} events"
                )
                if storage_result["error_count"] > 0:
                    print(f"   ⚠️  {storage_result['error_count']} errors occurred")
                    if args.verbose:
                        for error in storage_result["errors"][:5]:  # Show first 5 errors
                            print(f"      {error}")
            else:
                print(
                    f"   ❌ Database storage failed: {storage_result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error storing events in database: {e}")
            print(f"   ❌ Database storage failed: {e}")


if __name__ == "__main__":
    main()
