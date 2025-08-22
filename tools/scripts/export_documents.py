#!/usr/bin/env python3
"""
Batch Document Export Script - Uses SimpleExportManager for direct export

Exports all documents from the database to clean text files.

Usage:
    python scripts/export_documents.py [--output-dir DIR] [--content-type TYPE]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.simple_export_manager import get_export_manager


def main():
    parser = argparse.ArgumentParser(
        description="Export all documents to clean text files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/export_documents.py
  python scripts/export_documents.py --output-dir /path/to/export
  python scripts/export_documents.py --content-type email
  python scripts/export_documents.py --no-organize
        """
    )
    
    parser.add_argument(
        "--output-dir",
        default="data/export",
        help="Output directory for exported files (default: data/export)"
    )
    
    parser.add_argument(
        "--content-type",
        choices=["email", "pdf", "upload"],
        help="Export only specific content type"
    )
    
    parser.add_argument(
        "--no-organize",
        action="store_true",
        help="Don't organize files into subdirectories by type"
    )
    
    args = parser.parse_args()
    
    # Get export manager
    export_manager = get_export_manager()
    
    try:
        if args.content_type:
            # Export specific content type
            print(f"📄 Exporting {args.content_type} documents to {args.output_dir}")
            result = export_manager.export_by_content_type(
                args.content_type,
                Path(args.output_dir)
            )
        else:
            # Export all documents
            print(f"📁 Exporting all documents to {args.output_dir}")
            result = export_manager.export_all_documents(
                Path(args.output_dir),
                organize_by_type=not args.no_organize
            )
        
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