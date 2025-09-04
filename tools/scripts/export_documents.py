#!/usr/bin/env python3
"""
Batch Document Export Script - Direct export using SimpleDB

Exports all documents from the database to clean text files.
Reimplemented to use SimpleDB directly after consolidation refactor.

Usage:
    python tools/scripts/export_documents.py [--output-dir DIR] [--content-type TYPE]
"""

import argparse
import sys
from pathlib import Path
from typing import Any, Dict

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lib.db import SimpleDB


def export_documents(db: SimpleDB, content_type: str = None, output_dir: Path = None, organize_by_type: bool = True) -> Dict[str, Any]:
    """
    Export documents from database to text files.
    """
    if output_dir is None:
        output_dir = Path("data/export")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build query based on content_type
    if content_type:
        # Map CLI choices to source_type values
        source_type_map = {
            "email": ["email_message", "email_summary"],
            "pdf": ["document", "document_chunk"],
            "upload": ["document", "document_chunk"]
        }
        source_types = source_type_map.get(content_type, [content_type])
        
        where_clause = "WHERE source_type IN ({})".format(",".join("?" * len(source_types)))
        query = f"SELECT source_type, source_id, title, body, substantive_text FROM content_unified {where_clause} ORDER BY source_type, title"
        params = source_types
    else:
        query = "SELECT source_type, source_id, title, body, substantive_text FROM content_unified ORDER BY source_type, title"
        params = []
    
    # Execute query
    try:
        documents = db.query(query, params)
    except Exception as e:
        return {"success": False, "error": f"Database query failed: {e}"}
    if not documents:
        return {"success": False, "error": "No documents found to export"}
    
    exported_count = 0
    source_counts = {}
    
    for doc in documents:
        source_type = doc["source_type"]
        source_id = doc["source_id"] 
        title = doc["title"] or f"untitled_{source_id}"
        
        # Use substantive_text if available, otherwise body
        content = doc.get("substantive_text") or doc.get("body", "")
        if not content:
            continue
        
        # Organize by type if requested
        if organize_by_type:
            type_dir = output_dir / source_type
            type_dir.mkdir(exist_ok=True)
            export_dir = type_dir
        else:
            export_dir = output_dir
        
        # Create safe filename
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:100]  # Limit length
        filename = f"{safe_title}_{source_id[:8]}.txt"
        file_path = export_dir / filename
        
        # Write content to file
        try:
            file_path.write_text(content, encoding="utf-8")
            exported_count += 1
            source_counts[source_type] = source_counts.get(source_type, 0) + 1
        except Exception as e:
            print(f"⚠️  Failed to write {filename}: {e}")
    
    return {
        "success": True,
        "exported_count": exported_count,
        "source_counts": source_counts,
        "target_directory": str(output_dir)
    }


def main():
    parser = argparse.ArgumentParser(
        description="Export all documents to clean text files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/scripts/export_documents.py
  python tools/scripts/export_documents.py --output-dir /path/to/export
  python tools/scripts/export_documents.py --content-type email
  python tools/scripts/export_documents.py --no-organize
        """,
    )

    parser.add_argument(
        "--output-dir",
        default="data/export",
        help="Output directory for exported files (default: data/export)",
    )

    parser.add_argument(
        "--content-type",
        choices=["email", "pdf", "upload"],
        help="Export only specific content type",
    )

    parser.add_argument(
        "--no-organize",
        action="store_true",
        help="Don't organize files into subdirectories by type",
    )

    args = parser.parse_args()

    try:
        # Initialize database
        db = SimpleDB()
        
        if args.content_type:
            # Export specific content type
            print(f"📄 Exporting {args.content_type} documents to {args.output_dir}")
            result = export_documents(db, args.content_type, Path(args.output_dir), not args.no_organize)
        else:
            # Export all documents
            print(f"📁 Exporting all documents to {args.output_dir}")
            result = export_documents(db, None, Path(args.output_dir), not args.no_organize)

        if result["success"]:
            print("\n✅ Export completed successfully!")
            print(f"   Exported: {result['exported_count']} documents")

            if "source_counts" in result:
                print("\n📊 Export breakdown by type:")
                for source_type, count in sorted(result["source_counts"].items()):
                    print(f"   - {source_type}: {count}")

            print(f"\n📁 Files exported to: {result.get('target_directory', args.output_dir)}")
        else:
            print(f"\n❌ Export failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Export error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
