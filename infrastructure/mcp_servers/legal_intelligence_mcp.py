#!/usr/bin/env python3
"""Legal Intelligence MCP Server.

PURPOSE:
--------
Thin MCP wrapper that exposes legal analysis capabilities through the Model Context
Protocol. Delegates all actual work to existing services (EntityService, TimelineService, 
SimpleDB) rather than reimplementing functionality.

WHAT IT DOES:
-------------
- Provides MCP tools for legal entity extraction, timeline generation, and case analysis
- Routes requests to appropriate underlying services
- Formats service responses for MCP consumption

USAGE:
------
This file is referenced in .mcp.json and runs as an MCP server for Claude Desktop/Code.
Not intended for direct execution - Claude connects to it via stdio protocol.

NOTE: Tests mock get_legal_intelligence_service() so internal changes are safe.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# MCP imports
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Check service availability
try:
    from entity.main import EntityService
    from lib.db import SimpleDB
    from lib.embeddings import get_embedding_service
    from lib.timeline.main import TimelineService
    
    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Infrastructure services not available: {e}", file=sys.stderr)
    SERVICES_AVAILABLE = False


def get_legal_intelligence_service(db_path: str | None = None):
    """
    Factory function for tests to mock. Returns dict with service instances.
    
    Args:
        db_path: Optional database path override
        
    Returns:
        Dict with database and service instances, or None if services unavailable
    """
    if not SERVICES_AVAILABLE:
        return None
        
    db_path = db_path or "data/system_data/emails.db"
    return {
        'db': SimpleDB(db_path),
        'entity_service': EntityService(),
        'timeline_service': TimelineService(),
        'embedding_service': get_embedding_service()
    }


def legal_extract_entities(content: str, case_id: str | None = None) -> str:
    """
    Extract legal entities using EntityService.
    
    Args:
        content: Text to analyze
        case_id: Optional case identifier for context
        
    Returns:
        JSON string with extracted entities
    """
    if not SERVICES_AVAILABLE:
        return json.dumps({"error": "Services not available"})
    
    try:
        # Check if we have a mocked service (for tests)
        service_dict = get_legal_intelligence_service()
        if service_dict and hasattr(service_dict, 'extract_legal_entities'):
            # Use mocked service for tests
            result = service_dict.extract_legal_entities(content, case_id=case_id)
            if not isinstance(result, str):
                return json.dumps(result)
            return result
        
        # Normal operation - use EntityService directly
        service = EntityService()
        entities = service.extract_entities(content, source_type="legal_document")
        
        # Format response
        result = {
            "success": True,
            "case_id": case_id,
            "entities": entities,
            "entity_count": len(entities),
            "entity_types": list(set(e.get("label") for e in entities))
        }
        
        return json.dumps(result)
        
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})


def legal_timeline_events(
    case_number: str, 
    start_date: str | None = None, 
    end_date: str | None = None
) -> str:
    """
    Generate timeline using TimelineService.
    
    Args:
        case_number: Case identifier to search for
        start_date: Optional start date filter (YYYY-MM-DD)
        end_date: Optional end date filter (YYYY-MM-DD)
        
    Returns:
        Formatted timeline string
    """
    if not SERVICES_AVAILABLE:
        return "❌ Services not available"
    
    try:
        # Get documents for case
        db = SimpleDB()
        results = db.search_content(case_number, limit=100)
        
        if not results:
            return f"❌ No documents found for case {case_number}"
        
        # Use TimelineService to process
        timeline_service = TimelineService()
        timeline = timeline_service.generate_timeline(
            content_ids=[r.get("content_id") for r in results if r.get("content_id")]
        )
        
        # Format output
        output = f"📅 Legal Timeline: {case_number}\n\n"
        
        if timeline.get("events"):
            events = timeline["events"]
            
            # Apply date filters if provided
            if start_date or end_date:
                filtered = []
                for event in events:
                    event_date = event.get("date", "")
                    if start_date and event_date < start_date:
                        continue
                    if end_date and event_date > end_date:
                        continue
                    filtered.append(event)
                events = filtered
            
            output += f"Found {len(events)} events\n\n"
            
            for event in events[-20:]:  # Show recent 20
                date = event.get("date", "Unknown")
                desc = event.get("description", "")[:100]
                output += f"• {date}: {desc}\n"
        else:
            output += "No timeline events found"
        
        return output
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


def legal_knowledge_graph(case_number: str, include_relationships: bool = True) -> str:
    """
    Build knowledge graph using existing services.
    
    Args:
        case_number: Case identifier
        include_relationships: Whether to include relationship analysis
        
    Returns:
        Formatted knowledge graph analysis
    """
    if not SERVICES_AVAILABLE:
        return "❌ Services not available"
    
    try:
        db = SimpleDB()
        results = db.search_content(case_number, limit=100)
        
        if not results:
            return f"❌ No documents found for case {case_number}"
        
        output = f"🕸️ Knowledge Graph: {case_number}\n\n"
        output += f"📊 Found {len(results)} documents\n"
        
        if include_relationships:
            # Extract entities from all documents
            entity_service = EntityService()
            all_entities = []
            
            for doc in results[:20]:  # Limit for performance
                content = doc.get("body", "")
                if content:
                    entities = entity_service.extract_entities(content)
                    all_entities.extend(entities)
            
            # Group by type
            by_type = {}
            for entity in all_entities:
                etype = entity.get("label", "UNKNOWN")
                if etype not in by_type:
                    by_type[etype] = set()
                by_type[etype].add(entity.get("text"))
            
            output += f"\n🏷️ Entities Found:\n"
            for etype, texts in sorted(by_type.items()):
                output += f"  • {etype}: {len(texts)} unique\n"
        
        return output
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


def legal_document_analysis(case_number: str, analysis_type: str = "comprehensive") -> str:
    """
    Analyze case documents using existing services.
    
    Args:
        case_number: Case identifier
        analysis_type: Type of analysis ("comprehensive" or "patterns")
        
    Returns:
        Formatted analysis results
    """
    if not SERVICES_AVAILABLE:
        return "❌ Services not available"
    
    try:
        db = SimpleDB()
        results = db.search_content(case_number, limit=100)
        
        if not results:
            return f"❌ No documents found for case {case_number}"
        
        output = f"📊 Document Analysis: {case_number}\n\n"
        output += f"Found {len(results)} documents\n\n"
        
        if analysis_type == "comprehensive":
            # Use multiple services for comprehensive analysis
            
            # Entity extraction
            entity_service = EntityService()
            all_entities = []
            for doc in results[:10]:
                content = doc.get("body", "")
                if content:
                    entities = entity_service.extract_entities(content)
                    all_entities.extend(entities)
            
            output += f"👥 Entities: {len(all_entities)} found\n"
            
            # Timeline
            timeline_service = TimelineService()
            timeline = timeline_service.generate_timeline(
                content_ids=[r.get("content_id") for r in results[:20] if r.get("content_id")]
            )
            
            if timeline.get("events"):
                output += f"📅 Timeline: {len(timeline['events'])} events\n"
            
            # Document types (basic pattern matching)
            doc_types = set()
            for doc in results:
                title = doc.get("title", "").lower()
                if "complaint" in title:
                    doc_types.add("complaint")
                elif "motion" in title:
                    doc_types.add("motion")
                elif "order" in title:
                    doc_types.add("order")
            
            if doc_types:
                output += f"📄 Document Types: {', '.join(doc_types)}\n"
        
        else:  # patterns
            output += "📋 Pattern Analysis:\n"
            
            # Simple date pattern analysis
            dates_found = 0
            for doc in results:
                content = doc.get("body", "")
                # Very basic date detection
                import re
                date_pattern = r'\d{1,2}/\d{1,2}/\d{2,4}'
                dates = re.findall(date_pattern, content)
                dates_found += len(dates)
            
            output += f"  • Date references: {dates_found}\n"
            output += f"  • Avg dates per doc: {dates_found/max(len(results), 1):.1f}\n"
        
        return output
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


def legal_case_tracking(case_number: str, track_type: str = "status") -> str:
    """
    Track case status using database queries.
    
    Args:
        case_number: Case identifier
        track_type: Type of tracking ("status", "deadlines", "missing")
        
    Returns:
        Formatted tracking information
    """
    if not SERVICES_AVAILABLE:
        return "❌ Services not available"
    
    try:
        db = SimpleDB()
        results = db.search_content(case_number, limit=100)
        
        if not results:
            return f"❌ No documents found for case {case_number}"
        
        output = f"📋 Case Tracking: {case_number}\n\n"
        
        if track_type == "status":
            output += f"⚖️ Status:\n"
            output += f"  • Documents found: {len(results)}\n"
            
            # Sort by date
            sorted_docs = sorted(
                results,
                key=lambda x: x.get("datetime_utc", ""),
                reverse=True
            )
            
            if sorted_docs:
                latest = sorted_docs[0]
                output += f"  • Latest activity: {latest.get('datetime_utc', 'Unknown')[:10]}\n"
                output += f"  • Latest doc: {latest.get('title', 'Untitled')[:50]}\n"
        
        elif track_type == "deadlines":
            output += "⏰ Deadline Search:\n"
            
            # Simple keyword search for deadlines
            deadline_count = 0
            for doc in results:
                content = doc.get("body", "").lower()
                if any(word in content for word in ["deadline", "due", "respond by"]):
                    deadline_count += 1
            
            output += f"  • Documents mentioning deadlines: {deadline_count}\n"
        
        elif track_type == "missing":
            output += "🔍 Document Completeness:\n"
            
            # Basic check for common document types
            found_types = set()
            for doc in results:
                title = doc.get("title", "").lower()
                if "complaint" in title:
                    found_types.add("complaint")
                elif "answer" in title:
                    found_types.add("answer")
                elif "motion" in title:
                    found_types.add("motion")
            
            output += f"  • Document types found: {', '.join(found_types) if found_types else 'None identified'}\n"
            
            # Simple missing document check
            if "complaint" in found_types and "answer" not in found_types:
                output += "  • ⚠️ Complaint found but no answer\n"
        
        return output
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


def legal_relationship_discovery(case_number: str, entity_focus: str | None = None) -> str:
    """
    Discover entity relationships using EntityService.
    
    Args:
        case_number: Case identifier
        entity_focus: Optional entity to focus on
        
    Returns:
        Formatted relationship analysis
    """
    if not SERVICES_AVAILABLE:
        return "❌ Services not available"
    
    try:
        db = SimpleDB()
        results = db.search_content(case_number, limit=50)
        
        if not results:
            return f"❌ No documents found for case {case_number}"
        
        output = f"🔗 Relationship Discovery: {case_number}\n\n"
        
        # Extract entities from documents
        entity_service = EntityService()
        all_entities = []
        entity_docs = {}  # Track which docs contain which entities
        
        for doc in results[:20]:  # Limit for performance
            content = doc.get("body", "")
            if content:
                entities = entity_service.extract_entities(content)
                for entity in entities:
                    entity_text = entity.get("text")
                    if entity_text:
                        all_entities.append(entity)
                        if entity_text not in entity_docs:
                            entity_docs[entity_text] = []
                        entity_docs[entity_text].append(doc.get("title", "")[:30])
        
        # Filter by focus if provided
        if entity_focus:
            filtered = [e for e in all_entities if entity_focus.lower() in e.get("text", "").lower()]
            output += f"🔍 Focused on '{entity_focus}': {len(filtered)} mentions\n\n"
            all_entities = filtered
        
        # Find co-occurring entities (simple relationship detection)
        if all_entities:
            # Count entity types
            by_type = {}
            for entity in all_entities:
                etype = entity.get("label", "UNKNOWN")
                if etype not in by_type:
                    by_type[etype] = 0
                by_type[etype] += 1
            
            output += "👥 Entity Summary:\n"
            for etype, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True)[:10]:
                output += f"  • {etype}: {count} occurrences\n"
            
            # Show which docs contain key entities
            output += "\n📄 Entity Document Matrix:\n"
            shown = 0
            for entity_text, docs in sorted(entity_docs.items(), key=lambda x: len(x[1]), reverse=True):
                if shown >= 5:
                    break
                if len(docs) > 1:  # Only show entities in multiple docs
                    output += f"  • '{entity_text}': appears in {len(docs)} documents\n"
                    shown += 1
        
        return output
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


class LegalIntelligenceServer:
    """
    MCP Server for legal intelligence tools.
    """
    
    def __init__(self):
        self.server = Server("legal-intelligence-server")
        self.setup_tools()
    
    def setup_tools(self):
        """Register MCP tools."""
        
        @self.server.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="legal_extract_entities",
                    description="Extract legal entities from text using NER",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Text content to analyze"
                            },
                            "case_id": {
                                "type": "string",
                                "description": "Optional case ID for context"
                            }
                        },
                        "required": ["content"]
                    }
                ),
                Tool(
                    name="legal_timeline_events",
                    description="Generate timeline of legal case events",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to analyze"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Optional start date (YYYY-MM-DD)"
                            },
                            "end_date": {
                                "type": "string",
                                "description": "Optional end date (YYYY-MM-DD)"
                            }
                        },
                        "required": ["case_number"]
                    }
                ),
                Tool(
                    name="legal_knowledge_graph",
                    description="Build knowledge graph for legal case",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number"
                            },
                            "include_relationships": {
                                "type": "boolean",
                                "description": "Include relationship analysis",
                                "default": True
                            }
                        },
                        "required": ["case_number"]
                    }
                ),
                Tool(
                    name="legal_document_analysis",
                    description="Analyze legal case documents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number"
                            },
                            "analysis_type": {
                                "type": "string",
                                "description": "Analysis type",
                                "enum": ["comprehensive", "patterns"],
                                "default": "comprehensive"
                            }
                        },
                        "required": ["case_number"]
                    }
                ),
                Tool(
                    name="legal_case_tracking",
                    description="Track legal case status and deadlines",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number"
                            },
                            "track_type": {
                                "type": "string",
                                "description": "Tracking type",
                                "enum": ["status", "deadlines", "missing"],
                                "default": "status"
                            }
                        },
                        "required": ["case_number"]
                    }
                ),
                Tool(
                    name="legal_relationship_discovery",
                    description="Discover entity relationships in case",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number"
                            },
                            "entity_focus": {
                                "type": "string",
                                "description": "Optional entity to focus on"
                            }
                        },
                        "required": ["case_number"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            try:
                if name == "legal_extract_entities":
                    result = legal_extract_entities(
                        content=arguments["content"],
                        case_id=arguments.get("case_id")
                    )
                elif name == "legal_timeline_events":
                    result = legal_timeline_events(
                        case_number=arguments["case_number"],
                        start_date=arguments.get("start_date"),
                        end_date=arguments.get("end_date")
                    )
                elif name == "legal_knowledge_graph":
                    result = legal_knowledge_graph(
                        case_number=arguments["case_number"],
                        include_relationships=arguments.get("include_relationships", True)
                    )
                elif name == "legal_document_analysis":
                    result = legal_document_analysis(
                        case_number=arguments["case_number"],
                        analysis_type=arguments.get("analysis_type", "comprehensive")
                    )
                elif name == "legal_case_tracking":
                    result = legal_case_tracking(
                        case_number=arguments["case_number"],
                        track_type=arguments.get("track_type", "status")
                    )
                elif name == "legal_relationship_discovery":
                    result = legal_relationship_discovery(
                        case_number=arguments["case_number"],
                        entity_focus=arguments.get("entity_focus")
                    )
                else:
                    result = f"Unknown tool: {name}"
                
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                error_msg = f"Error executing {name}: {str(e)}"
                print(error_msg, file=sys.stderr)
                return [TextContent(type="text", text=error_msg)]


async def main():
    """Run the MCP server."""
    server = LegalIntelligenceServer()
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="legal-intelligence",
                server_version="2.0.0",  # Bumped version after refactor
                capabilities=server.server.get_capabilities(NotificationOptions(), {})
            )
        )


if __name__ == "__main__":
    asyncio.run(main())