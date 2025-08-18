#!/usr/bin/env python3
"""
Batch Document Export Script

Exports all documents from the database to markdown files with sequential numbering.
Useful for creating backups or exporting existing documents.

Usage:
    python scripts/export_documents.py [--limit N] [--content-type TYPE]
"""

import argparse

# Add project root to path for imports
import os
import sys
import time
from typing import Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.pipelines.document_exporter import DocumentExporter
from shared.simple_db import SimpleDB


def export_all_documents(limit: int = None, content_type: str = None) -> dict[str, Any]:
    """Export all documents to markdown files"""
    try:
        db = SimpleDB()
        exporter = DocumentExporter()

        # Get all content
        print("Fetching documents from database...")
        if content_type:
            content_list = db.search_content("", content_type=content_type, limit=limit or 1000)
        else:
            content_list = db.search_content("", limit=limit or 1000)

        if not content_list:
            print("No documents found to export")
            return {"success": True, "exported": 0, "errors": 0}

        print(f"Found {len(content_list)} documents to export")

        exported_count = 0
        error_count = 0

        for i, content in enumerate(content_list, 1):
            content_id = content["content_id"]
            title = content.get("title", "untitled")

            print(f"Exporting {i}/{len(content_list)}: {title[:50]}...")

            try:
                # Use title as filename hint
                result = exporter.save_to_export(content_id, title)

                if result["success"]:
                    exported_count += 1
                    print(f"  ✓ Exported to {result['filename']}")
                else:
                    error_count += 1
                    print(f"  ✗ Export failed: {result.get('error', 'Unknown error')}")

            except Exception as e:
                error_count += 1
                print(f"  ✗ Export failed with exception: {str(e)}")

            # Small delay to avoid overwhelming the system
            if i % 10 == 0:
                time.sleep(0.1)

        print(f"\nExport completed: {exported_count} exported, {error_count} errors")

        return {
            "success": True,
            "exported": exported_count,
            "errors": error_count,
            "total_processed": len(content_list),
        }

    except Exception as e:
        error_msg = f"Batch export failed: {str(e)}"
        print(f"\nERROR: {error_msg}")
        return {"success": False, "error": error_msg}


def main():
    parser = argparse.ArgumentParser(description="Export all documents to markdown files")
    parser.add_argument("--limit", type=int, help="Limit number of documents to export")
    parser.add_argument(
        "--content-type",
        choices=["email", "pdf", "transcript"],
        help="Export only specific content type",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be exported without actually exporting",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No files will be created")
        # Just count documents
        db = SimpleDB()
        if args.content_type:
            content_list = db.search_content(
                "", content_type=args.content_type, limit=args.limit or 1000
            )
        else:
            content_list = db.search_content("", limit=args.limit or 1000)

        print(f"Would export {len(content_list)} documents")
        for i, content in enumerate(content_list[:10], 1):  # Show first 10
            title = content.get("title", "untitled")
            content_type_str = content.get("content_type", "document")
            print(f"  {i}. [{content_type_str}] {title[:60]}")

        if len(content_list) > 10:
            print(f"  ... and {len(content_list) - 10} more")

        return

    print("Starting batch document export...")
    print("Target directory: data/export/")

    # Create export directory if it doesn't exist
    os.makedirs("data/export", exist_ok=True)

    result = export_all_documents(limit=args.limit, content_type=args.content_type)

    if result["success"]:
        print("\n✓ Export completed successfully!")
        if "exported" in result:
            print(f"  Documents exported: {result['exported']}")
            print(f"  Errors encountered: {result['errors']}")
    else:
        print(f"\n✗ Export failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
