#!/usr/bin/env python3
"""Entity Handler for CLI.

Handles entity extraction and management commands. Integrates with
unified entity processing system.
"""

import sys
from pathlib import Path
from typing import Any

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from loguru import logger

from shared.processors.unified_entity_processor import UnifiedEntityProcessor


class EntityHandler:
    """
    Handle entity extraction and management commands.
    """

    def __init__(self):
        self.processor = UnifiedEntityProcessor()

    def extract_entities_unified(self, args) -> dict[str, Any]:
        """
        Extract entities from unified content pipeline.
        """
        max_content = getattr(args, "limit", None)
        missing_only = getattr(args, "missing_only", False)

        try:
            if missing_only:
                logger.info("🔍 Processing only content without entity mappings...")
                result = self.processor.process_missing_entities_only(
                    max_content=max_content or 100
                )
            else:
                logger.info("🔬 Processing entities from unified content...")
                result = self.processor.process_content_entities(max_content=max_content)

            if result.get("success"):
                print("\n✅ Entity Extraction Results:")
                print(f"  Processed: {result['processed']:,} content items")
                print(f"  Entities extracted: {result['entities_extracted']:,}")
                print(f"  Entity mappings created: {result['entities_mapped']:,}")
                print(f"  Processing time: {result.get('elapsed_seconds', 0):.1f}s")

                if "content_types_processed" in result:
                    print("\n📊 Content Types Processed:")
                    for content_type, count in result["content_types_processed"].items():
                        print(f"  - {content_type}: {count:,}")

                if result.get("errors", 0) > 0:
                    print(f"\n⚠️  Errors: {result['errors']}")

            else:
                print(f"❌ Entity extraction failed: {result.get('error', 'Unknown error')}")

            return result

        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            print(f"❌ Entity extraction failed: {e}")
            return {"success": False, "error": str(e)}

    def entity_status(self, args) -> dict[str, Any]:
        """
        Show entity extraction status for unified content.
        """
        try:
            status = self.processor.get_processing_status()

            print("\n📊 Unified Entity Processing Status:")
            print(f"Generated: {status['timestamp']}")

            # Content statistics
            print("\n📄 Content Statistics:")
            total_content = 0
            total_with_entities = 0
            total_mappings = 0

            for stat in status["content_statistics"]:
                content_type = stat["source_type"]
                content_count = stat["total_content"]
                entities_count = stat["content_with_entities"]
                mappings_count = stat["total_entity_mappings"]

                coverage = (entities_count / content_count * 100) if content_count > 0 else 0

                print(f"  {content_type}:")
                print(f"    Content items: {content_count:,}")
                print(f"    With entities: {entities_count:,} ({coverage:.1f}%)")
                print(f"    Total mappings: {mappings_count:,}")

                total_content += content_count
                total_with_entities += entities_count
                total_mappings += mappings_count

            overall_coverage = (
                (total_with_entities / total_content * 100) if total_content > 0 else 0
            )
            print("\n📈 Overall:")
            print(f"  Total content: {total_content:,}")
            print(f"  With entities: {total_with_entities:,} ({overall_coverage:.1f}%)")
            print(f"  Total mappings: {total_mappings:,}")

            # Entity type distribution
            if status["entity_type_distribution"]:
                print("\n🏷️  Entity Types (Top 10):")
                sorted_types = sorted(
                    status["entity_type_distribution"].items(), key=lambda x: x[1], reverse=True
                )[:10]

                for entity_type, count in sorted_types:
                    print(f"  {entity_type}: {count:,}")

            # Recent activity
            recent = status.get("recent_mappings_24h", 0)
            print("\n⏱️  Recent Activity:")
            print(f"  Entity mappings (24h): {recent:,}")

            # Identify gaps
            missing_entities = total_content - total_with_entities
            if missing_entities > 0:
                print("\n⚠️  Missing Entity Extraction:")
                print(f"  {missing_entities:,} content items need entity processing")
                print("  Run: tools/scripts/vsearch extract-entities --missing-only")

            return status

        except Exception as e:
            logger.error(f"Error getting entity status: {e}")
            print(f"❌ Failed to get entity status: {e}")
            return {"error": str(e)}

    def search_by_entity(self, args):
        """
        Search content by entity type and value.
        """
        entity_type = getattr(args, "entity_type", None)
        entity_value = getattr(args, "entity_value", None)
        limit = getattr(args, "limit", 10)

        if not entity_type or not entity_value:
            print("❌ Both --entity-type and --entity-value are required")
            return {"error": "Missing required parameters"}

        try:
            # Search for content containing the entity (using entity_text column)
            query = """
                SELECT DISTINCT cu.id, cu.source_type, cu.title, cu.body, 
                       ecm.entity_type, ecm.entity_text, ecm.confidence
                FROM content_unified cu
                JOIN entity_content_mapping ecm ON cu.id = ecm.content_id
                WHERE ecm.entity_type = ? 
                AND ecm.entity_text LIKE ?
                ORDER BY ecm.confidence DESC, cu.created_at DESC
                LIMIT ?
            """

            results = self.processor.db.fetch(
                query, (entity_type.upper(), f"%{entity_value}%", limit)
            )

            print(f"\n🔍 Search Results for {entity_type}: '{entity_value}'")
            print(f"Found {len(results)} matching content items:\n")

            for i, result in enumerate(results, 1):
                title = result["title"] or "Untitled"
                source_type = result["source_type"]
                confidence = result["confidence"]

                # Truncate body for display
                body_preview = (
                    result["body"][:200] + "..." if len(result["body"]) > 200 else result["body"]
                )

                print(f"{i}. [{source_type.upper()}] {title}")
                print(f"   Entity: {result['entity_text']} (confidence: {confidence:.2f})")
                print(f"   Preview: {body_preview}")
                print(f"   Content ID: {result['id']}")
                print()

            return {"results": results, "count": len(results)}

        except Exception as e:
            logger.error(f"Entity search error: {e}")
            print(f"❌ Entity search failed: {e}")
            return {"error": str(e)}


def handle_entity_command(command: str, args) -> dict[str, Any]:
    """
    Route entity commands to appropriate handlers.
    """
    handler = EntityHandler()

    if command == "extract-entities":
        return handler.extract_entities_unified(args)
    elif command == "entity-status":
        return handler.entity_status(args)
    elif command == "search-entities":
        return handler.search_by_entity(args)
    else:
        print(f"❌ Unknown entity command: {command}")
        return {"error": f"Unknown command: {command}"}


if __name__ == "__main__":
    # Test the handler directly
    import argparse

    parser = argparse.ArgumentParser(description="Test entity handler")
    parser.add_argument("command", choices=["extract-entities", "entity-status", "search-entities"])
    parser.add_argument("--limit", type=int, help="Limit number of items to process")
    parser.add_argument("--missing-only", action="store_true", help="Process only missing entities")
    parser.add_argument("--entity-type", help="Entity type for search")
    parser.add_argument("--entity-value", help="Entity value for search")

    args = parser.parse_args()
    handle_entity_command(args.command, args)
