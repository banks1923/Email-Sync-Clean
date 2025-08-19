#!/usr/bin/env python3
"""
Simple Legal MCP Server - DEPRECATED

⚠️ DEPRECATION NOTICE ⚠️
This server is deprecated and will be removed in a future version.
Please use the unified Legal Intelligence MCP Server instead:
- File: legal_intelligence_mcp.py
- Provides all legal functionality in a single, more powerful server

Provides legal document analysis tools using EntityService and SimpleDB
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

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
    print(f"Infrastructure services not available: {e}")
    SERVICES_AVAILABLE = False

# Service factory - to be injected from higher layers
_entity_service_factory = None

def set_entity_service_factory(factory):
    """Inject entity service factory from higher layer."""
    global _entity_service_factory
    _entity_service_factory = factory


def tag_evidence(text: str, doc_id: str = None) -> str:
    """Auto-tag documents with legal categories using EntityService"""
    deprecation_warning = """
⚠️ DEPRECATION WARNING ⚠️
This tool is deprecated. Please use the unified Legal Intelligence MCP Server:
- Tool: legal_extract_entities (provides enhanced entity extraction)
- Tool: legal_document_analysis (provides comprehensive document analysis)

"""

    if not SERVICES_AVAILABLE:
        return deprecation_warning + "Legal services not available"

    try:
        # Extract entities
        if not _entity_service_factory:
            return "Entity service not configured - must be injected from higher layer"
        entity_service = _entity_service_factory()
        doc_id = doc_id or f"legal_{len(text)}"
        result = entity_service.extract_email_entities(doc_id, text)

        if not result["success"]:
            return f"Error: {result['error']}"

        # Categorize based on entities and keywords
        tags = []
        entities = result.get("entities", [])

        # Check for case numbers
        case_numbers = [e for e in entities if e.get("type") == "CASE_NUMBER"]
        if case_numbers:
            tags.append("case_document")

        # Check for legal entity types
        legal_types = ["COURT", "JUDGE", "ATTORNEY", "LAW_FIRM"]
        for entity in entities:
            if entity.get("type") in legal_types:
                tags.append(f"involves_{entity['type'].lower()}")

        # Check document type keywords
        text_lower = text.lower()
        doc_types = {
            "motion": ["motion to", "motion for", "plaintiff's motion", "defendant's motion"],
            "opposition": ["opposition to", "opposing", "opposes"],
            "reply": ["reply to", "reply brief", "reply in support"],
            "order": ["court order", "order granting", "order denying", "it is ordered"],
            "complaint": ["complaint for", "first amended complaint", "complaint alleging"],
            "answer": ["answer to complaint", "defendant's answer", "affirmative defenses"],
        }

        for doc_type, keywords in doc_types.items():
            if any(keyword in text_lower for keyword in keywords):
                tags.append(doc_type)

        # Format output
        output = deprecation_warning + "📋 Legal Document Analysis:\n\n"
        output += f"🏷️ Tags: {', '.join(tags) if tags else 'No specific tags'}\n\n"

        output += "📊 Entities Found:\n"
        entity_summary = {}
        for entity in entities:
            etype = entity.get("type", "UNKNOWN")
            if etype not in entity_summary:
                entity_summary[etype] = []
            entity_summary[etype].append(entity.get("text", ""))

        for etype, texts in entity_summary.items():
            output += f"  • {etype}: {', '.join(set(texts[:5]))}\n"

        # Store tags in database if doc_id provided
        if doc_id and tags:
            db = SimpleDB()
            metadata = {"tags": tags, "entity_count": len(entities)}
            db.execute(
                "UPDATE content SET metadata = ? WHERE id = ?",
                (json.dumps(metadata), doc_id),
            )
            output += f"\n✅ Tags saved to document: {doc_id}"

        return output

    except Exception as e:
        return f"Error tagging evidence: {str(e)}"


def find_case_documents(case_number: str, limit: int = 20) -> str:
    """Search for documents by case number"""
    deprecation_warning = """
⚠️ DEPRECATION WARNING ⚠️
This tool is deprecated. Please use the unified Legal Intelligence MCP Server:
- Tool: legal_case_tracking (provides enhanced case document tracking)
- Tool: legal_document_analysis (provides comprehensive case analysis)

"""

    if not SERVICES_AVAILABLE:
        return deprecation_warning + "Legal services not available"

    try:
        db = SimpleDB()

        # Search in content and metadata
        results = db.search_content(case_number, limit=limit)

        # Also search in documents table
        doc_results = db.fetch(
            """
            SELECT * FROM documents
            WHERE text_content LIKE ? OR file_name LIKE ?
            ORDER BY upload_date DESC
            LIMIT ?
            """,
            (f"%{case_number}%", f"%{case_number}%", limit),
        )

        # Combine and deduplicate results
        all_results = list(results) + list(doc_results)
        seen_ids = set()
        unique_results = []

        for result in all_results:
            result_id = result.get("content_id") or result.get("chunk_id")
            if result_id and result_id not in seen_ids:
                seen_ids.add(result_id)
                unique_results.append(result)

        if not unique_results:
            return f"No documents found for case: {case_number}"

        output = deprecation_warning + f"⚖️ Case Documents for {case_number}:\n\n"

        # Group by document type if possible
        by_type = {}
        for doc in unique_results[:limit]:
            # Try to determine document type
            title = doc.get("title") or doc.get("file_name", "Unknown")
            title_lower = title.lower()

            doc_type = "other"
            if "motion" in title_lower:
                doc_type = "motion"
            elif "opposition" in title_lower:
                doc_type = "opposition"
            elif "order" in title_lower:
                doc_type = "order"
            elif "complaint" in title_lower:
                doc_type = "complaint"

            if doc_type not in by_type:
                by_type[doc_type] = []
            by_type[doc_type].append(doc)

        for doc_type, docs in sorted(by_type.items()):
            output += f"\n📁 {doc_type.upper()}:\n"
            for doc in docs:
                title = doc.get("title") or doc.get("file_name", "Unknown")
                date = doc.get("created_date") or doc.get("upload_date", "")
                output += f"  • {title}"
                if date:
                    output += f" ({date[:10]})"
                output += "\n"

        return output

    except Exception as e:
        return f"Error finding case documents: {str(e)}"


def detect_missing_documents(case_number: str) -> str:
    """Identify procedural gaps in case documents"""
    if not SERVICES_AVAILABLE:
        return "Legal services not available"

    try:
        db = SimpleDB()

        # Get all documents for the case
        case_docs = db.search_content(case_number, limit=100)

        # Analyze document types and dates
        motions = []
        oppositions = []
        orders = []

        for doc in case_docs:
            title = (doc.get("title") or "").lower()
            content = (doc.get("content") or "").lower()
            date = doc.get("created_date", "")

            if "motion" in title or "motion to" in content[:500]:
                motions.append(
                    {"title": doc.get("title"), "date": date, "id": doc.get("content_id")}
                )
            elif "opposition" in title or "opposition to" in content[:500]:
                oppositions.append(
                    {"title": doc.get("title"), "date": date, "id": doc.get("content_id")}
                )
            elif "order" in title or "court order" in content[:500]:
                orders.append(
                    {"title": doc.get("title"), "date": date, "id": doc.get("content_id")}
                )

        # Detect missing oppositions
        missing = []

        for motion in motions:
            motion_date = motion.get("date", "")
            if not motion_date:
                continue

            # Look for opposition within 20 days
            has_opposition = False
            for opp in oppositions:
                opp_date = opp.get("date", "")
                if opp_date and motion["title"]:
                    # Simple date comparison
                    if motion["title"].split()[0] in opp.get("title", ""):
                        has_opposition = True
                        break

            if not has_opposition:
                missing.append(
                    {
                        "type": "Opposition",
                        "expected_for": motion["title"],
                        "motion_date": motion_date[:10] if motion_date else "unknown",
                        "urgency": "high",
                    }
                )

        # Check for missing orders on motions
        for motion in motions:
            has_order = False
            for order in orders:
                if motion["title"] and motion["title"].split()[0] in order.get("title", ""):
                    has_order = True
                    break

            if not has_order:
                missing.append(
                    {"type": "Court Order", "expected_for": motion["title"], "urgency": "medium"}
                )

        # Format output
        output = f"🔍 Procedural Gap Analysis for Case {case_number}:\n\n"

        output += "📊 Document Summary:\n"
        output += f"  • Motions filed: {len(motions)}\n"
        output += f"  • Oppositions filed: {len(oppositions)}\n"
        output += f"  • Orders issued: {len(orders)}\n\n"

        if missing:
            output += f"⚠️ Missing Documents ({len(missing)}):\n"
            for item in missing:
                output += f"\n  • Missing: {item['type']}\n"
                output += f"    For: {item['expected_for']}\n"
                if item.get("motion_date"):
                    output += f"    Motion filed: {item['motion_date']}\n"
                output += f"    Urgency: {item['urgency']}\n"
        else:
            output += "✅ No procedural gaps detected\n"

        # Suggest searches
        if missing:
            output += "\n📝 Suggested Searches:\n"
            for item in missing[:3]:  # Limit to 3 suggestions
                if item["type"] == "Opposition":
                    output += f"  • Search: 'opposition {item['expected_for']} {case_number}'\n"
                elif item["type"] == "Court Order":
                    output += f"  • Search: 'order {item['expected_for']} {case_number}'\n"

        return output

    except Exception as e:
        return f"Error detecting missing documents: {str(e)}"


def analyze_case_relationships(case_number: str) -> str:
    """Analyze relationships between legal documents"""
    if not SERVICES_AVAILABLE:
        return "Legal services not available"

    try:
        db = SimpleDB()
        if not _entity_service_factory:
            return "Entity service not configured - must be injected from higher layer"
        entity_service = _entity_service_factory()

        # Get case documents
        case_docs = db.search_content(case_number, limit=50)

        if not case_docs:
            return f"No documents found for case: {case_number}"

        # Extract entities from each document
        doc_entities = {}
        relationships = []

        for doc in case_docs[:20]:  # Limit for performance
            doc_id = doc.get("content_id")
            content = doc.get("content", "")

            if content:
                entity_result = entity_service.extract_email_entities(doc_id, content[:5000])
                if entity_result["success"]:
                    doc_entities[doc_id] = {
                        "title": doc.get("title"),
                        "entities": entity_result.get("entities", []),
                        "date": doc.get("created_date", ""),
                    }

        # Find relationships based on shared entities
        doc_ids = list(doc_entities.keys())
        for i, doc1_id in enumerate(doc_ids):
            doc1_data = doc_entities[doc1_id]
            doc1_entities = {e.get("text") for e in doc1_data["entities"]}

            for doc2_id in doc_ids[i + 1 :]:
                doc2_data = doc_entities[doc2_id]
                doc2_entities = {e.get("text") for e in doc2_data["entities"]}

                # Find shared entities
                shared = doc1_entities & doc2_entities
                if len(shared) > 2:  # Significant overlap
                    relationships.append(
                        {
                            "doc1": doc1_data["title"],
                            "doc2": doc2_data["title"],
                            "shared_entities": list(shared)[:5],
                            "strength": min(len(shared) / 5, 1.0),  # Normalize strength
                        }
                    )

        # Format output
        output = f"🔗 Document Relationships for Case {case_number}:\n\n"

        output += f"📄 Documents Analyzed: {len(doc_entities)}\n"
        output += f"🔗 Relationships Found: {len(relationships)}\n\n"

        if relationships:
            # Sort by strength
            relationships.sort(key=lambda x: x["strength"], reverse=True)

            output += "Strong Relationships:\n"
            for rel in relationships[:10]:  # Top 10
                output += f"\n  • {rel['doc1'][:50]}\n"
                output += f"    ↔️ {rel['doc2'][:50]}\n"
                output += f"    Shared: {', '.join(rel['shared_entities'][:3])}\n"
                output += f"    Strength: {rel['strength']:.0%}\n"
        else:
            output += "No significant relationships found between documents.\n"

        # Summary of key entities
        all_entities = {}
        for doc_data in doc_entities.values():
            for entity in doc_data["entities"]:
                etype = entity.get("type", "UNKNOWN")
                etext = entity.get("text", "")
                if etype not in all_entities:
                    all_entities[etype] = set()
                all_entities[etype].add(etext)

        output += "\n📊 Key Entities in Case:\n"
        for etype, texts in sorted(all_entities.items()):
            if texts:
                output += f"  • {etype}: {', '.join(list(texts)[:5])}\n"

        return output

    except Exception as e:
        return f"Error analyzing relationships: {str(e)}"


class LegalServer:
    """Simple legal MCP server"""

    def __init__(self):
        self.server = Server("legal-server")
        self.setup_tools()

    def setup_tools(self):
        """Register legal tools"""

        @self.server.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="tag_evidence",
                    description="Auto-tag documents with legal categories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Document text to analyze"},
                            "doc_id": {
                                "type": "string",
                                "description": "Optional document ID for saving tags",
                            },
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="find_case_documents",
                    description="Search for documents by case number",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to search",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 20,
                            },
                        },
                        "required": ["case_number"],
                    },
                ),
                Tool(
                    name="detect_missing_documents",
                    description="Identify procedural gaps in case documents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to analyze",
                            }
                        },
                        "required": ["case_number"],
                    },
                ),
                Tool(
                    name="analyze_case_relationships",
                    description="Analyze relationships between legal documents",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to analyze",
                            }
                        },
                        "required": ["case_number"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            try:
                if name == "tag_evidence":
                    result = tag_evidence(text=arguments["text"], doc_id=arguments.get("doc_id"))
                    return [TextContent(type="text", text=result)]

                elif name == "find_case_documents":
                    result = find_case_documents(
                        case_number=arguments["case_number"], limit=arguments.get("limit", 20)
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "detect_missing_documents":
                    result = detect_missing_documents(case_number=arguments["case_number"])
                    return [TextContent(type="text", text=result)]

                elif name == "analyze_case_relationships":
                    result = analyze_case_relationships(case_number=arguments["case_number"])
                    return [TextContent(type="text", text=result)]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the legal server"""
    server = LegalServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="legal",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(NotificationOptions(), {}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
