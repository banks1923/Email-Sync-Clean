#!/usr/bin/env python3
"""Search Intelligence MCP Server.

Unified Search Intelligence MCP server that provides comprehensive
search and document intelligence capabilities including smart search,
similarity analysis, entity extraction, summarization, clustering, and
batch processing.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path - flexible path resolution
try:
    # Use Pydantic config for path management if available
    from config.settings import settings

    project_root = Path(settings.paths.data_root).parent
except ImportError:
    # Fallback to path calculation (3 levels deep: infrastructure/mcp_servers/*.py)
    project_root = Path(__file__).parent.parent.parent

sys.path.insert(0, str(project_root))

# MCP imports
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Import only infrastructure layer dependencies
try:
    from shared.simple_db import SimpleDB

    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Infrastructure services not available: {e}", file=sys.stderr)
    SERVICES_AVAILABLE = False

def search_smart(
    query: str, limit: int = 10, use_expansion: bool = True, content_type: str | None = None
) -> str:
    """Semantic search - pure vector similarity search.
    
    Note: use_expansion parameter is kept for compatibility but ignored
    (semantic embeddings capture meaning without needing expansion).
    """
    if not SERVICES_AVAILABLE:
        return "Search intelligence services not available"

    try:
        from search_intelligence import search
        
        # Add content type filter if specified
        filters = {}
        if content_type:
            filters["source_type"] = content_type

        # Perform semantic search
        results = search(query=query, limit=limit, filters=filters)

        if not results:
            return f"📭 No results found for: {query}"

        # Format results
        output = f"🔍 Semantic Search Results for '{query}':\n\n"

        # Format results
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            content_type = result.get("content_type", "unknown")
            score = result.get("relevance_score", 0)
            snippet = result.get("content", "")[:200] + "..."

            output += f"{i}. [{content_type}] {title} (score: {score:.2f})\n"
            output += f"   {snippet}\n\n"

            # Show entities if available
            if "entities" in result:
                entities = result["entities"][:5]  # Top 5 entities
                if entities:
                    entity_texts = [e.get("text", "") for e in entities]
                    output += f"   🏷️ Entities: {', '.join(entity_texts)}\n\n"

        output += f"\n📊 Total Results: {len(results)}"
        return output

    except Exception as e:
        return f"❌ Error in smart search: {str(e)}"


def find_literal_patterns(
    pattern: str, limit: int = 50, fields: list | None = None
) -> str:
    """Find documents with exact pattern matches.
    
    Perfect for finding specific identifiers like BATES numbers,
    section codes, email addresses, etc.
    """
    if not SERVICES_AVAILABLE:
        return "Search intelligence services not available"
    
    try:
        from search_intelligence import find_literal
        
        # Perform literal search
        results = find_literal(pattern=pattern, limit=limit, fields=fields)
        
        if not results:
            return f"📭 No exact matches found for pattern: {pattern}"
        
        # Format results
        output = f"🔤 Literal Pattern Matches for '{pattern}':\n\n"
        output += f"Found {len(results)} documents containing the pattern\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "Untitled")
            source_type = result.get("source_type", "unknown")
            content_id = result.get("content_id", "unknown")
            
            # Find and highlight the pattern in content
            content_preview = result.get("content", "")[:200]
            if pattern.lower() in content_preview.lower():
                content_preview += "..."
            
            output += f"{i}. [{source_type}] {title}\n"
            output += f"   🆔 ID: {content_id}\n"
            output += f"   📄 Preview: {content_preview}\n\n"
        
        return output
        
    except Exception as e:
        return f"❌ Error in literal pattern search: {str(e)}"


def search_similar(document_id: str, threshold: float = 0.7, limit: int = 10) -> str:
    """
    Find documents similar to a given document.
    """
    if not SERVICES_AVAILABLE:
        return "Search intelligence services not available"

    try:
        from search_intelligence import get_search_intelligence_service
        service = get_search_intelligence_service()

        # Find similar documents
        similar_docs = service.analyze_document_similarity(
            doc_id=document_id, threshold=threshold, limit=limit
        )

        if not similar_docs:
            return f"📭 No similar documents found for: {document_id} (threshold: {threshold})"

        # Format results
        output = f"🔄 Similar Documents to '{document_id}':\n\n"
        output += f"📈 Similarity Threshold: {threshold:.2f}\n\n"

        for i, doc in enumerate(similar_docs, 1):
            doc_id = doc.get("document_id", "unknown")
            similarity = doc.get("similarity_score", 0)
            title = doc.get("title", "Untitled")
            content_type = doc.get("content_type", "unknown")

            output += f"{i}. [{content_type}] {title}\n"
            output += f"   📊 Similarity: {similarity:.2%}\n"
            output += f"   🆔 ID: {doc_id}\n"

            # Show common entities if available
            if "common_entities" in doc:
                entities = doc["common_entities"][:3]
                if entities:
                    output += f"   🏷️ Common Entities: {', '.join(entities)}\n"

            output += "\n"

        output += f"📊 Found {len(similar_docs)} similar documents"
        return output

    except Exception as e:
        return f"❌ Error finding similar documents: {str(e)}"


def search_entities(
    document_id: str | None = None, text: str | None = None, cache_results: bool = True
) -> str:
    """
    Extract entities from a document or text.
    """
    if not SERVICES_AVAILABLE:
        return "Search intelligence services not available"

    try:
        service = get_search_intelligence_service()

        if document_id:
            # Extract from existing document
            entities = service.extract_and_cache_entities(
                doc_id=document_id, force_refresh=not cache_results
            )
            source = f"document '{document_id}'"
        elif text:
            # Extract from provided text
            # Direct import following clean architecture pattern
            from entity import EntityService

            entity_service = EntityService()

            result = entity_service.extract_email_entities("temp_doc", text)
            entities = result.get("entities", [])
            source = "provided text"
        else:
            return "❌ Either document_id or text must be provided"

        if not entities:
            return f"📭 No entities found in {source}"

        # Format results
        output = f"🏷️ Entity Extraction from {source}:\n\n"

        # Group entities by type
        entity_by_type = {}
        for entity in entities:
            etype = entity.get("label", "UNKNOWN")
            if etype not in entity_by_type:
                entity_by_type[etype] = []
            entity_by_type[etype].append(
                {"text": entity.get("text", ""), "confidence": entity.get("confidence", 0)}
            )

        # Sort and display by type
        output += "📊 Entities by Type:\n"
        for etype, items in sorted(entity_by_type.items()):
            # Get unique entities with highest confidence
            unique_items = {}
            for item in items:
                text = item["text"]
                if (
                    text not in unique_items
                    or item["confidence"] > unique_items[text]["confidence"]
                ):
                    unique_items[text] = item

            # Display top entities for this type
            sorted_items = sorted(
                unique_items.values(), key=lambda x: x["confidence"], reverse=True
            )[:5]
            entity_list = [f"{item['text']} ({item['confidence']:.2f})" for item in sorted_items]
            output += f"  • {etype}: {', '.join(entity_list)}\n"

        # Statistics
        output += "\n📈 Statistics:\n"
        output += f"  • Total entities: {len(entities)}\n"
        output += f"  • Unique types: {len(entity_by_type)}\n"

        if cache_results and document_id:
            output += f"  • ✅ Results cached for document '{document_id}'"

        return output

    except Exception as e:
        return f"❌ Error extracting entities: {str(e)}"


def search_summarize(
    document_id: str | None = None,
    text: str | None = None,
    max_sentences: int = 3,
    max_keywords: int = 10,
) -> str:
    """
    Summarize a document or text.
    """
    if not SERVICES_AVAILABLE:
        return "Search intelligence services not available"

    try:
        if document_id:
            # Get document from database
            db = SimpleDB()
            doc = db.get_content(document_id)
            if not doc:
                return f"❌ Document not found: {document_id}"

            text = doc.get("content", "")
            source = f"document '{document_id}'"
            title = doc.get("title", "Untitled")
        elif text:
            source = "provided text"
            title = "User Text"
        else:
            return "❌ Either document_id or text must be provided"

        if not text:
            return f"📭 No content to summarize in {source}"

        # Get summarizer and extract summary
        # Direct import following clean architecture pattern
        from summarization import get_document_summarizer

        summarizer = get_document_summarizer()
        summary = summarizer.extract_summary(
            text=text,
            max_sentences=max_sentences,
            max_keywords=max_keywords,
            summary_type="combined",
        )

        # Format results
        output = f"📝 Document Summary for {title}:\n\n"

        # Key sentences
        output += "🔑 Key Sentences:\n"
        sentences = summary.get("sentences", [])
        for i, sentence in enumerate(sentences, 1):
            output += f"{i}. {sentence}\n"

        # Keywords
        output += "\n🏷️ Top Keywords:\n"
        keywords = summary.get("keywords", {})
        sorted_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:max_keywords]
        for keyword, score in sorted_keywords:
            output += f"  • {keyword}: {score:.3f}\n"

        # Statistics
        output += "\n📊 Statistics:\n"
        output += f"  • Method: {summary.get('method', 'combined')}\n"
        output += f"  • Word count: {summary.get('word_count', 0)}\n"

        return output

    except Exception as e:
        return f"❌ Error summarizing document: {str(e)}"


def search_cluster(threshold: float = 0.7, limit: int = 100, min_cluster_size: int = 2) -> str:
    """
    Cluster similar documents.
    """
    if not SERVICES_AVAILABLE:
        return "Search intelligence services not available"

    try:
        # Direct import following clean architecture pattern
        from search_intelligence import get_search_intelligence_service

        service = get_search_intelligence_service()

        # Perform clustering
        clusters = service.cluster_similar_content(threshold=threshold, limit=limit)

        if not clusters:
            return f"📭 No clusters found (threshold: {threshold})"

        # Filter by minimum cluster size
        filtered_clusters = [c for c in clusters if len(c.get("documents", [])) >= min_cluster_size]

        if not filtered_clusters:
            return f"📭 No clusters with {min_cluster_size}+ documents found"

        # Format results
        output = f"🗂️ Document Clusters (threshold: {threshold}):\n\n"

        for i, cluster in enumerate(filtered_clusters[:10], 1):  # Show top 10 clusters
            docs = cluster.get("documents", [])
            cluster_type = cluster.get("dominant_type", "mixed")
            avg_similarity = cluster.get("average_similarity", 0)

            output += f"📁 Cluster {i} ({len(docs)} documents, type: {cluster_type}):\n"
            output += f"   📊 Average Similarity: {avg_similarity:.2%}\n"

            # Show sample documents
            output += "   📄 Sample Documents:\n"
            for doc in docs[:3]:  # Show first 3 documents
                title = doc.get("title", "Untitled")
                doc_id = doc.get("document_id", "unknown")
                output += f"      • {title} (ID: {doc_id})\n"

            if len(docs) > 3:
                output += f"      ... and {len(docs) - 3} more\n"

            # Show common themes if available
            if "common_keywords" in cluster:
                keywords = cluster["common_keywords"][:5]
                if keywords:
                    output += f"   🏷️ Common Themes: {', '.join(keywords)}\n"

            output += "\n"

        # Statistics
        output += "📊 Clustering Statistics:\n"
        output += f"  • Total clusters: {len(filtered_clusters)}\n"
        output += f"  • Documents clustered: {sum(len(c.get('documents', [])) for c in filtered_clusters)}\n"
        output += f"  • Average cluster size: {sum(len(c.get('documents', [])) for c in filtered_clusters) / len(filtered_clusters):.1f}\n"

        return output

    except Exception as e:
        return f"❌ Error clustering documents: {str(e)}"


def search_process_all(operation: str, content_type: str | None = None, limit: int = 100) -> str:
    """
    Batch process documents with specified operation.
    """
    if not SERVICES_AVAILABLE:
        return "Search intelligence services not available"

    try:
        # Direct import following clean architecture pattern
        from search_intelligence import get_search_intelligence_service

        service = get_search_intelligence_service()
        db = SimpleDB()

        # Get documents to process
        filters = {}
        if content_type:
            filters["content_types"] = [content_type]

        documents = db.search_content("", limit=limit, filters=filters)

        if not documents:
            return "📭 No documents found to process"

        # Process based on operation
        output = f"⚙️ Batch Processing: {operation}\n\n"
        processed = 0
        errors = 0

        if operation == "extract_entities":
            output += f"🏷️ Extracting entities from {len(documents)} documents...\n\n"

            for doc in documents:
                try:
                    doc_id = doc.get("content_id")
                    service.extract_and_cache_entities(doc_id)
                    processed += 1
                except Exception:
                    errors += 1

        elif operation == "generate_summaries":
            output += f"📝 Generating summaries for {len(documents)} documents...\n\n"

            # Direct import following clean architecture pattern
            from summarization import get_document_summarizer

            summarizer = get_document_summarizer()

            for doc in documents:
                try:
                    text = doc.get("content", "")
                    if text:
                        summarizer.extract_summary(text)
                        processed += 1
                except Exception:
                    errors += 1

        elif operation == "find_duplicates":
            output += f"🔍 Detecting duplicates among {len(documents)} documents...\n\n"

            duplicates = service.detect_duplicates(similarity_threshold=0.95)

            for dup_group in duplicates[:10]:  # Show first 10 groups
                output += "  • Duplicate Group:\n"
                for doc in dup_group:
                    title = doc.get("title", "Untitled")
                    doc_id = doc.get("document_id", "unknown")
                    output += f"    - {title} (ID: {doc_id})\n"
                output += "\n"

            processed = len(duplicates)

        else:
            return f"❌ Unknown operation: {operation}. Valid options: extract_entities, generate_summaries, find_duplicates"

        # Statistics
        output += "📊 Processing Statistics:\n"
        output += f"  • Documents processed: {processed}\n"
        output += f"  • Errors: {errors}\n"
        output += f"  • Success rate: {(processed / len(documents) * 100):.1f}%\n"

        return output

    except Exception as e:
        return f"❌ Error in batch processing: {str(e)}"


class SearchIntelligenceMCPServer:
    """
    Search Intelligence MCP Server.
    """

    def __init__(self):
        self.server = Server("search-intelligence")
        self.setup_tools()

    def setup_tools(self):
        """
        Register search intelligence tools.
        """

        @self.server.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="search_smart",
                    description="Semantic search using Legal BERT embeddings",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                            "use_expansion": {
                                "type": "boolean",
                                "description": "Ignored - kept for compatibility",
                                "default": True,
                            },
                            "content_type": {
                                "type": "string",
                                "description": "Filter by content type",
                                "enum": ["email", "pdf", "transcript", "note"],
                            },
                        },
                        "required": ["query"],
                    },
                ),
                Tool(
                    name="find_literal",
                    description="Find documents with exact pattern matches (BATES IDs, section codes, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Exact pattern to search for"},
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 50,
                            },
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Fields to search in",
                                "default": ["body", "metadata"],
                            },
                        },
                        "required": ["pattern"],
                    },
                ),
                Tool(
                    name="search_similar",
                    description="Find documents similar to a given document",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Document ID to find similar to",
                            },
                            "threshold": {
                                "type": "number",
                                "description": "Similarity threshold (0-1)",
                                "default": 0.7,
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                        },
                        "required": ["document_id"],
                    },
                ),
                Tool(
                    name="search_entities",
                    description="Extract entities from a document or text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Document ID to extract from",
                            },
                            "text": {
                                "type": "string",
                                "description": "Text to extract entities from",
                            },
                            "cache_results": {
                                "type": "boolean",
                                "description": "Cache extraction results",
                                "default": True,
                            },
                        },
                    },
                ),
                Tool(
                    name="search_summarize",
                    description="Summarize a document or text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "document_id": {
                                "type": "string",
                                "description": "Document ID to summarize",
                            },
                            "text": {"type": "string", "description": "Text to summarize"},
                            "max_sentences": {
                                "type": "integer",
                                "description": "Maximum sentences",
                                "default": 3,
                            },
                            "max_keywords": {
                                "type": "integer",
                                "description": "Maximum keywords",
                                "default": 10,
                            },
                        },
                    },
                ),
                Tool(
                    name="search_cluster",
                    description="Cluster similar documents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "threshold": {
                                "type": "number",
                                "description": "Similarity threshold",
                                "default": 0.7,
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum documents to cluster",
                                "default": 100,
                            },
                            "min_cluster_size": {
                                "type": "integer",
                                "description": "Minimum cluster size",
                                "default": 2,
                            },
                        },
                    },
                ),
                Tool(
                    name="search_process_all",
                    description="Batch process documents with specified operation",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "Operation to perform",
                                "enum": [
                                    "extract_entities",
                                    "generate_summaries",
                                    "find_duplicates",
                                ],
                            },
                            "content_type": {
                                "type": "string",
                                "description": "Filter by content type",
                                "enum": ["email", "pdf", "transcript", "note"],
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum documents",
                                "default": 100,
                            },
                        },
                        "required": ["operation"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            try:
                if name == "search_smart":
                    result = search_smart(
                        query=arguments["query"],
                        limit=arguments.get("limit", 10),
                        use_expansion=arguments.get("use_expansion", True),
                        content_type=arguments.get("content_type"),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "find_literal":
                    result = find_literal_patterns(
                        pattern=arguments["pattern"],
                        limit=arguments.get("limit", 50),
                        fields=arguments.get("fields"),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "search_similar":
                    result = search_similar(
                        document_id=arguments["document_id"],
                        threshold=arguments.get("threshold", 0.7),
                        limit=arguments.get("limit", 10),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "search_entities":
                    result = search_entities(
                        document_id=arguments.get("document_id"),
                        text=arguments.get("text"),
                        cache_results=arguments.get("cache_results", True),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "search_summarize":
                    result = search_summarize(
                        document_id=arguments.get("document_id"),
                        text=arguments.get("text"),
                        max_sentences=arguments.get("max_sentences", 3),
                        max_keywords=arguments.get("max_keywords", 10),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "search_cluster":
                    result = search_cluster(
                        threshold=arguments.get("threshold", 0.7),
                        limit=arguments.get("limit", 100),
                        min_cluster_size=arguments.get("min_cluster_size", 2),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "search_process_all":
                    result = search_process_all(
                        operation=arguments["operation"],
                        content_type=arguments.get("content_type"),
                        limit=arguments.get("limit", 100),
                    )
                    return [TextContent(type="text", text=result)]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """
    Run the search intelligence server.
    """
    server = SearchIntelligenceMCPServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="search-intelligence",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(NotificationOptions(), {}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
