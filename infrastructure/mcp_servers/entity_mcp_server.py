#!/usr/bin/env python3
"""
Simple Entity Extraction MCP Server - DEPRECATED

This server is deprecated and will be removed in a future version.
Please use the unified intelligence MCP servers instead:
- For legal entities: legal-intelligence (legal_intelligence_mcp.py)
- For general entities: search-intelligence (search_intelligence_mcp.py)
- Migration: Run scripts/migrate_mcp_servers.py

Leverages Task #8 entity extraction and relationship mapping
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# MCP imports
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from entity.main import EntityService

# Entity service factory - to be injected from higher layers
_entity_service_factory = None
ENTITY_SERVICE_AVAILABLE = True

def set_entity_service_factory(factory):
    """Inject entity service factory from higher layer."""
    global _entity_service_factory
    _entity_service_factory = factory


def extract_entities(text: str, message_id: str = None) -> str:
    """Extract entities from text using Task #8 system"""
    if not ENTITY_SERVICE_AVAILABLE:
        return "Entity service not available"
    
    if not _entity_service_factory:
        return "Entity service not configured - must be injected from higher layer"

    try:
        service = _entity_service_factory()
        msg_id = message_id or f"mcp_{len(text)}"
        result = service.extract_email_entities(msg_id, text)

        if not result["success"]:
            return f"Error: {result['error']}"

        # Format results
        output = f"🔍 Found {result['entity_count']} entities:\n"
        output += f"🔗 Found {result['relationship_count']} relationships\n"
        output += f"⚙️  Extractor: {result['extractor_used']}\n\n"

        # Show entities by type
        entities_by_type = {}
        for entity in result["entities"]:
            entity_type = entity.get("type", "UNKNOWN")
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity["text"])

        for entity_type, texts in sorted(entities_by_type.items()):
            output += f"📂 {entity_type}: {', '.join(texts)}\n"

        # Show relationships if any
        if result["relationships"]:
            output += "\n🔗 Relationships:\n"
            for rel in result["relationships"][:5]:  # Limit to 5
                output += f"  • {rel['source_entity_text']} → {rel['target_entity_text']} ({rel['relationship_type']})\n"

        return output

    except Exception as e:
        return f"Error extracting entities: {str(e)}"


def search_entities(entity_type: str = None, name_pattern: str = None, limit: int = 10) -> str:
    """Search entities using Task #8 system"""
    if not ENTITY_SERVICE_AVAILABLE:
        return "Entity service not available"

    try:
        service = EntityService()
        result = service.search_entities(entity_type, name_pattern, limit)

        if not result["success"]:
            return f"Error: {result['error']}"

        entities = result.get("data", [])
        if not entities:
            return "No entities found matching criteria"

        output = f"🔍 Found {len(entities)} entities:\n\n"
        for entity in entities:
            output += f"• {entity['primary_name']} ({entity['entity_type']})\n"
            if entity.get("total_mentions", 0) > 1:
                output += f"  Mentioned {entity['total_mentions']} times\n"

        return output

    except Exception as e:
        return f"Error searching entities: {str(e)}"


def get_knowledge_graph(entity_ids: list[str] = None, max_depth: int = 2) -> str:
    """Get knowledge graph using Task #8 system"""
    if not ENTITY_SERVICE_AVAILABLE:
        return "Entity service not available"

    try:
        service = EntityService()
        result = service.get_knowledge_graph(entity_ids, max_depth)

        if not result["success"]:
            return f"Error: {result['error']}"

        relationships = result.get("data", [])
        if not relationships:
            return "No relationships found"

        output = f"🕸️  Knowledge Graph ({len(relationships)} relationships):\n\n"
        for rel in relationships[:10]:  # Limit display
            source = rel.get("source_name", "Unknown")
            target = rel.get("target_name", "Unknown")
            rel_type = rel.get("relationship_type", "unknown")
            confidence = rel.get("confidence", 0)
            output += f"• {source} → {target}\n"
            output += f"  Type: {rel_type}, Confidence: {confidence:.2f}\n"

        return output

    except Exception as e:
        return f"Error getting knowledge graph: {str(e)}"


def get_entity_stats() -> str:
    """Get entity statistics using Task #8 system"""
    if not ENTITY_SERVICE_AVAILABLE:
        return "Entity service not available"

    try:
        service = EntityService()
        result = service.get_entity_stats()

        if not result["success"]:
            return f"Error: {result['error']}"

        output = "📊 Entity Statistics:\n\n"
        output += f"Raw entities: {result.get('raw_entities', 0)}\n"
        output += f"Consolidated entities: {result.get('consolidated_entities', 0)}\n"
        output += f"Relationships: {result.get('relationships', 0)}\n\n"

        # Entity types breakdown
        entity_types = result.get("entity_types", [])
        if entity_types:
            output += "📂 Entity Types:\n"
            for et in entity_types:
                output += f"  • {et['type']}: {et['count']}\n"

        # Relationship types breakdown
        rel_types = result.get("relationship_types", [])
        if rel_types:
            output += "\n🔗 Relationship Types:\n"
            for rt in rel_types:
                output += f"  • {rt['type']}: {rt['count']}\n"

        return output

    except Exception as e:
        return f"Error getting entity stats: {str(e)}"


class EntityServer:
    """Simple entity MCP server leveraging Task #8"""

    def __init__(self):
        self.server = Server("entity-server")
        self.setup_tools()

    def setup_tools(self):
        """Register entity tools"""

        @self.server.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="extract_entities",
                    description="Extract entities and relationships from text using Legal BERT + spaCy",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to extract entities from",
                            },
                            "message_id": {
                                "type": "string",
                                "description": "Optional message identifier",
                            },
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="search_entities",
                    description="Search consolidated entities by type or name pattern",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entity_type": {
                                "type": "string",
                                "description": "Filter by entity type (PERSON, ORG, CASE_NUMBER, etc.)",
                            },
                            "name_pattern": {
                                "type": "string",
                                "description": "Search pattern for entity names",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results to return",
                                "default": 10,
                            },
                        },
                    },
                ),
                Tool(
                    name="knowledge_graph",
                    description="Get entity knowledge graph with relationships",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "entity_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific entity IDs to include",
                            },
                            "max_depth": {
                                "type": "integer",
                                "description": "Maximum relationship depth",
                                "default": 2,
                            },
                        },
                    },
                ),
                Tool(
                    name="entity_stats",
                    description="Get comprehensive entity extraction statistics",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            try:
                if name == "extract_entities":
                    result = extract_entities(
                        text=arguments["text"], message_id=arguments.get("message_id")
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "search_entities":
                    result = search_entities(
                        entity_type=arguments.get("entity_type"),
                        name_pattern=arguments.get("name_pattern"),
                        limit=arguments.get("limit", 10),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "knowledge_graph":
                    result = get_knowledge_graph(
                        entity_ids=arguments.get("entity_ids"),
                        max_depth=arguments.get("max_depth", 2),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "entity_stats":
                    result = get_entity_stats()
                    return [TextContent(type="text", text=result)]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the entity server"""
    server = EntityServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="entity",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(NotificationOptions(), {}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
