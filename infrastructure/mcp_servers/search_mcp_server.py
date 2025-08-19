#!/usr/bin/env python3
"""
Simple Search MCP Server - DEPRECATED

This server is deprecated and will be removed in a future version.
Please use the unified Search Intelligence MCP Server instead:
- Server name: search-intelligence
- File: search_intelligence_mcp.py
- Migration: Run scripts/migrate_mcp_servers.py

Provides search tools for Email Sync using SearchService and SimpleDB
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# MCP imports
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Import services
try:
    from search import get_search_service

    from shared.simple_db import SimpleDB

    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Services not available: {e}")
    SERVICES_AVAILABLE = False


def search_content(query: str, limit: int = 10, content_type: str = None) -> str:
    """Basic keyword search using SimpleDB"""
    if not SERVICES_AVAILABLE:
        return "Search services not available"

    try:
        db = SimpleDB()

        # Build filters if content_type specified
        filters = {}
        if content_type:
            filters["content_types"] = [content_type]

        results = db.search_content(query, limit=limit, filters=filters)

        if not results:
            return f"No results found for: {query}"

        output = f"🔍 Found {len(results)} results for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            content_type = result.get("content_type", "unknown")
            snippet = result.get("content", "")[:200] + "..."

            output += f"{i}. [{content_type}] {title}\n"
            output += f"   {snippet}\n\n"

        return output

    except Exception as e:
        return f"Error searching content: {str(e)}"


def hybrid_search(query: str, limit: int = 10) -> str:
    """Semantic + keyword search using SearchService"""
    if not SERVICES_AVAILABLE:
        return "Search services not available"

    try:
        search = get_search_service()
        results = search.search(query, limit=limit)

        if not results:
            return f"No results found for: {query}"

        output = f"🔍 Hybrid Search Results for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            score = result.get("score", 0)
            content = result.get("content", {})
            metadata = result.get("metadata", {})

            title = content.get("subject") or content.get("title", "Untitled")
            content_type = metadata.get("content_type", "unknown")

            output += f"{i}. [{content_type}] {title} (score: {score:.2f})\n"

            # Show snippet if available
            if "snippet" in content:
                output += f"   {content['snippet']}\n"

        return output

    except Exception as e:
        return f"Error in hybrid search: {str(e)}"


def search_by_type(content_type: str, query: str = "", limit: int = 10) -> str:
    """Search filtered by content type"""
    if not SERVICES_AVAILABLE:
        return "Search services not available"

    try:
        db = SimpleDB()

        # If no query, get recent items of that type
        if not query:
            query_sql = """
                SELECT id, title, content, content_type, created_date
                FROM content
                WHERE content_type = ?
                ORDER BY created_date DESC
                LIMIT ?
            """
            results = db.fetch(query_sql, (content_type, limit))
        else:
            filters = {"content_types": [content_type]}
            results = db.search_content(query, limit=limit, filters=filters)

        if not results:
            return f"No {content_type} items found"

        output = f"📂 {content_type.capitalize()} Search Results:\n\n"
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            content_snippet = (
                (result.get("content", "")[:150] + "...") if result.get("content") else "No content"
            )

            output += f"{i}. {title}\n"
            output += f"   {content_snippet}\n\n"

        return output

    except Exception as e:
        return f"Error searching by type: {str(e)}"


def get_search_stats() -> str:
    """Get search and vector statistics"""
    if not SERVICES_AVAILABLE:
        return "Search services not available"

    try:
        search = get_search_service()
        stats = search.get_stats()

        db = SimpleDB()
        content_stats = db.get_content_stats()

        output = "📊 Search System Statistics:\n\n"

        # Vector stats
        output += "🔢 Vector Store:\n"
        output += f"  • Vectors indexed: {stats.get('vector_count', 0)}\n"
        output += f"  • Collection: {stats.get('collection', 'unknown')}\n"
        output += f"  • Model: {stats.get('embedding_model', 'unknown')}\n"
        output += f"  • Dimensions: {stats.get('dimensions', 0)}\n\n"

        # Content stats
        output += "📄 Content Database:\n"
        output += f"  • Total items: {content_stats.get('total_content', 0)}\n"

        by_type = content_stats.get("content_by_type", {})
        if by_type:
            output += "  • By type:\n"
            for ctype, count in by_type.items():
                output += f"    - {ctype}: {count}\n"

        # Entity stats if available
        entity_stats = stats.get("entity_service", {})
        if entity_stats.get("available"):
            output += "\n🏷️ Entity Service:\n"
            output += f"  • Raw entities: {entity_stats.get('raw_entities', 0)}\n"
            output += f"  • Consolidated: {entity_stats.get('consolidated_entities', 0)}\n"
            output += f"  • Relationships: {entity_stats.get('relationships', 0)}\n"

        return output

    except Exception as e:
        return f"Error getting stats: {str(e)}"


class SearchServer:
    """Simple search MCP server"""

    def __init__(self):
        self.server = Server("search-server")
        self.setup_tools()

    def setup_tools(self):
        """Register search tools"""

        @self.server.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="search_content",
                    description="Basic keyword search across all content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                            "content_type": {
                                "type": "string",
                                "description": "Filter by type (email, pdf, transcript)",
                                "enum": ["email", "pdf", "transcript", "note"],
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="hybrid_search",
                    description="Semantic + keyword search using Legal BERT embeddings",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="search_by_type",
                    description="Search or list content filtered by type",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content_type": {
                                "type": "string",
                                "description": "Content type to filter",
                                "enum": ["email", "pdf", "transcript", "note"],
                            },
                            "query": {"type": "string", "description": "Optional search query"},
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                        },
                        "required": ["content_type"],
                    },
                ),
                Tool(
                    name="search_stats",
                    description="Get search system and vector statistics",
                    inputSchema={"type": "object", "properties": {}},
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            try:
                if name == "search_content":
                    result = search_content(
                        query=arguments["query"],
                        limit=arguments.get("limit", 10),
                        content_type=arguments.get("content_type"),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "hybrid_search":
                    result = hybrid_search(
                        query=arguments["query"], limit=arguments.get("limit", 10)
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "search_by_type":
                    result = search_by_type(
                        content_type=arguments["content_type"],
                        query=arguments.get("query", ""),
                        limit=arguments.get("limit", 10),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "search_stats":
                    result = get_search_stats()
                    return [TextContent(type="text", text=result)]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the search server"""
    server = SearchServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="search",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(NotificationOptions(), {}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
