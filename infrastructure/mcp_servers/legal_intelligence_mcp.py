#!/usr/bin/env python3
"""Legal Intelligence MCP Server.

Unified Legal Intelligence MCP server that replaces existing legal and
timeline servers. Provides comprehensive legal case analysis, entity
extraction, timeline generation, knowledge graph relationships, and
document intelligence.
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

# Note: Do not cache patched class at import-time; tests patch it dynamically.

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

# Patchable factory hook for tests
def get_legal_intelligence_service(db_path: str | None = None):
    from legal_intelligence import get_legal_intelligence_service as _factory

    return _factory(db_path) if db_path else _factory()


def legal_extract_entities(content: str, case_id: str | None = None) -> str:
    """
    Extract legal entities from text content using Legal BERT and NER.
    """
    # Honor patched availability flag from test shim if present
    try:
        from mcp_servers.legal_intelligence_mcp import SERVICES_AVAILABLE as _SERVICES_AVAILABLE  # type: ignore
        if not _SERVICES_AVAILABLE:
            return "Legal intelligence services not available"
    except Exception:
        if not SERVICES_AVAILABLE:
            return "Legal intelligence services not available"

    try:
        service = get_legal_intelligence_service()
        # Extract entities using the legal intelligence service
        result = service.extract_legal_entities(content, case_id=case_id)

        # Treat missing 'success' as success to allow simple mocks in tests
        if result.get("success") is False:
            return f"❌ Entity extraction failed: {result.get('error', 'Unknown error')}"

        entities = result.get("entities", [])
        relationships = result.get("relationships", [])

        # Format comprehensive output
        output = "🏷️ Legal Entity Extraction:\n\n"

        # Entity summary
        entity_by_type = {}
        for entity in entities:
            etype = entity.get("label", "UNKNOWN")
            if etype not in entity_by_type:
                entity_by_type[etype] = []
            entity_by_type[etype].append(entity.get("text", ""))

        output += "📊 Entities by Type:\n"
        for etype, texts in sorted(entity_by_type.items()):
            unique_texts = list(set(texts))[:5]  # Top 5 unique
            output += f"  • {etype}: {', '.join(unique_texts)}\n"

        output += "\n📈 Statistics:\n"
        output += f"  • Total entities: {len(entities)}\n"
        output += f"  • Unique types: {len(entity_by_type)}\n"
        output += f"  • Relationships: {len(relationships)}\n"

        # Highlight legal-specific entities
        legal_entities = [
            e for e in entities if e.get("label") in ["COURT", "JUDGE", "ATTORNEY", "CASE_NUMBER"]
        ]
        if legal_entities:
            output += "\n⚖️ Legal Entities:\n"
            for entity in legal_entities[:10]:
                output += f"  • {entity.get('label')}: {entity.get('text')} (conf: {entity.get('confidence', 0):.2f})\n"

        # Relationship summary
        if relationships:
            output += "\n🔗 Entity Relationships:\n"
            for rel in relationships[:5]:
                output += f"  • {rel.get('source')} → {rel.get('target')} ({rel.get('type')})\n"

        return output

    except Exception as e:
        return f"❌ Error extracting entities: {str(e)}"


def _get_legal_service():
    """Return a legal service instance via patchable factory."""
    return get_legal_intelligence_service()


def legal_timeline_events(
    case_number: str, start_date: str | None = None, end_date: str | None = None
) -> str:
    """
    Generate comprehensive timeline of legal case events.
    """
    if not SERVICES_AVAILABLE:
        return "Legal intelligence services not available"

    try:
        legal_service = get_legal_intelligence_service()

        # Generate case timeline using the legal intelligence service
        timeline_result = legal_service.generate_case_timeline(case_number)

        if not timeline_result.get("success"):
            return f"❌ Timeline generation failed: {timeline_result.get('error', 'No timeline data found')}"

        events = timeline_result.get("events", [])
        gaps = timeline_result.get("gaps", [])
        milestones = timeline_result.get("milestones", [])
        date_range = timeline_result.get("date_range", {})

        # Filter by date range if provided
        if start_date or end_date:
            filtered_events = []
            for event in events:
                event_date = event.get("date", "")
                if start_date and event_date < start_date:
                    continue
                if end_date and event_date > end_date:
                    continue
                filtered_events.append(event)
            events = filtered_events

        # Format comprehensive timeline output
        output = f"📅 Legal Case Timeline: {case_number}\n\n"

        # Date range info
        if date_range.get("start") and date_range.get("end"):
            output += f"📊 Date Range: {date_range['start']} to {date_range['end']}\n"

        output += f"📈 Total Events: {len(events)}\n"

        if start_date or end_date:
            output += f"🔍 Filtered by: {start_date or 'beginning'} to {end_date or 'now'}\n"

        output += "\n"

        # Key milestones
        if milestones:
            output += "⭐ Key Milestones:\n"
            for milestone in milestones[:5]:
                output += f"  • {milestone.get('date')}: {milestone.get('description', milestone.get('type'))}\n"
            output += "\n"

        # Chronological events
        output += "📋 Chronological Events:\n"

        # Group events by date
        events_by_date = {}
        for event in events[-20:]:  # Show recent 20 events
            event_date = event.get("date", "")[:10]  # Just date part
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append(event)

        for date in sorted(events_by_date.keys(), reverse=True):
            output += f"\n📌 {date}:\n"
            for event in events_by_date[date]:
                event_type = event.get("type", "event")
                description = event.get("description", "")[:80]
                doc_title = event.get("document_title", "")

                # Icon based on event type
                icon = (
                    "📧"
                    if "email" in event_type
                    else (
                        "📄" if "filing" in event_type else "⚖️" if "hearing" in event_type else "📝"
                    )
                )

                output += f"  {icon} {description}"
                if doc_title:
                    output += f" (from: {doc_title[:40]})"
                output += "\n"

        # Timeline gaps analysis
        if gaps:
            output += f"\n⚠️ Timeline Gaps Detected ({len(gaps)}):\n"
            for gap in gaps[:3]:  # Top 3 gaps
                output += f"  • Gap: {gap.get('start')} to {gap.get('end')} ({gap.get('duration_days', 0)} days)\n"
                output += f"    Significance: {gap.get('significance', 'unknown')}\n"

        return output

    except Exception as e:
        return f"❌ Error generating timeline: {str(e)}"


def legal_knowledge_graph(case_number: str, include_relationships: bool = True) -> str:
    """
    Build and analyze knowledge graph relationships for legal case.
    """
    if not SERVICES_AVAILABLE:
        return "Legal intelligence services not available"

    try:
        legal_service = get_legal_intelligence_service()

        # Build relationship graph using the legal intelligence service
        graph_result = legal_service.build_relationship_graph(case_number)

        if not graph_result.get("success"):
            return f"❌ Knowledge graph generation failed: {graph_result.get('error', 'No graph data found')}"

        nodes = graph_result.get("nodes", [])
        edges = graph_result.get("edges", [])
        node_count = graph_result.get("node_count", 0)
        edge_count = graph_result.get("edge_count", 0)
        graph_density = graph_result.get("graph_density", 0)

        # Format knowledge graph output
        output = f"🕸️ Legal Knowledge Graph: {case_number}\n\n"

        output += "📊 Graph Statistics:\n"
        output += f"  • Nodes (documents): {node_count}\n"
        output += f"  • Edges (relationships): {edge_count}\n"
        output += f"  • Graph density: {graph_density:.3f}\n"
        output += f"  • Avg connections per document: {edge_count / max(node_count, 1):.1f}\n\n"

        # Document nodes
        output += "📄 Document Nodes:\n"
        for node in nodes[:10]:  # Show first 10 nodes
            node_type = node.get("metadata", {}).get("content_type", "unknown")
            title = node.get("title", "Untitled")[:50]
            output += f"  • {title} ({node_type})\n"

        if len(nodes) > 10:
            output += f"  ... and {len(nodes) - 10} more documents\n"

        # Relationship analysis
        if include_relationships and edges:
            output += "\n🔗 Document Relationships:\n"

            # Group relationships by type
            relationships_by_type = {}
            for edge in edges:
                rel_type = edge.get("type", "unknown")
                if rel_type not in relationships_by_type:
                    relationships_by_type[rel_type] = []
                relationships_by_type[rel_type].append(edge)

            for rel_type, rels in relationships_by_type.items():
                output += f"\n  {rel_type.replace('_', ' ').title()} ({len(rels)}):\n"
                for rel in rels[:5]:  # Show first 5 relationships of each type
                    strength = rel.get("strength", 0)
                    output += f"    • Document similarity: {strength:.3f}\n"

            # Strongest relationships
            if edges:
                strongest_edges = sorted(edges, key=lambda x: x.get("strength", 0), reverse=True)
                output += "\n💪 Strongest Relationships:\n"
                for edge in strongest_edges[:5]:
                    strength = edge.get("strength", 0)
                    output += f"  • Similarity score: {strength:.3f}\n"

        # Network insights
        if node_count > 1:
            output += "\n🧠 Network Insights:\n"
            if graph_density > 0.5:
                output += "  • High document interconnectedness - comprehensive case file\n"
            elif graph_density > 0.2:
                output += "  • Moderate document relationships - typical case structure\n"
            else:
                output += "  • Low connectivity - possible missing documents or isolated filings\n"

            if edge_count == 0:
                output += (
                    "  • No document relationships found - consider document similarity analysis\n"
                )

        return output

    except Exception as e:
        return f"❌ Error building knowledge graph: {str(e)}"


def legal_document_analysis(case_number: str, analysis_type: str = "comprehensive") -> str:
    """
    Perform comprehensive document analysis using Legal BERT embeddings.
    """
    if not SERVICES_AVAILABLE:
        return "Legal intelligence services not available"

    try:
        legal_service = _get_legal_service()

        # Perform document pattern analysis
        if analysis_type == "patterns":
            result = legal_service.analyze_document_patterns(case_number)
        else:
            # Comprehensive case analysis
            result = legal_service.process_case(case_number)

        if not result.get("success"):
            return f"❌ Document analysis failed: {result.get('error', 'Analysis error')}"

        # Format comprehensive analysis output
        output = f"📊 Legal Document Analysis: {case_number}\n\n"

        if analysis_type == "comprehensive":
            # Full case analysis
            output += "📈 Case Summary:\n"
            output += f"  • Total documents: {result.get('document_count', 0)}\n"
            output += f"  • Analysis timestamp: {result.get('analysis_timestamp', '')[:19]}\n\n"

            # Entity analysis
            entities = result.get("entities", {})
            if entities:
                output += "👥 Entity Analysis:\n"
                output += f"  • Total entities: {entities.get('total_entities', 0)}\n"
                output += f"  • Unique entities: {entities.get('unique_entities', 0)}\n"

                by_type = entities.get("by_type", {})
                for etype, items in sorted(by_type.items()):
                    output += f"  • {etype}: {len(items)} found\n"

                key_parties = entities.get("key_parties", [])
                if key_parties:
                    output += "\n🔑 Key Parties:\n"
                    for party in key_parties[:5]:
                        output += f"  • {party.get('text')} ({party.get('label')})\n"

            # Timeline summary
            timeline = result.get("timeline", {})
            if timeline.get("success"):
                events = timeline.get("events", [])
                output += "\n📅 Timeline Summary:\n"
                output += f"  • Total events: {len(events)}\n"

                date_range = timeline.get("date_range", {})
                if date_range.get("start"):
                    output += f"  • Date range: {date_range['start']} to {date_range['end']}\n"

                gaps = timeline.get("gaps", [])
                if gaps:
                    output += f"  • Timeline gaps: {len(gaps)} detected\n"

            # Missing documents prediction
            missing = result.get("missing_documents", {})
            if missing.get("success") and missing.get("predicted_missing"):
                predicted = missing.get("predicted_missing", [])
                output += "\n⚠️ Predicted Missing Documents:\n"
                for doc in predicted[:5]:
                    doc_type = doc.get("document_type", "unknown")
                    confidence = doc.get("confidence", 0)
                    reason = doc.get("reason", "")
                    output += (
                        f"  • {doc_type.replace('_', ' ').title()}: {confidence:.0%} confidence\n"
                    )
                    output += f"    Reason: {reason}\n"

        else:
            # Pattern-specific analysis
            patterns = result
            output += "📋 Document Pattern Analysis:\n\n"

            doc_types = patterns.get("document_types", set())
            output += f"📄 Document Types Found: {', '.join(sorted(doc_types))}\n\n"

            themes = patterns.get("themes", [])
            if themes:
                output += "🎯 Recurring Themes:\n"
                for theme in themes:
                    name = theme.get("theme", "unknown")
                    prevalence = theme.get("prevalence", 0)
                    count = theme.get("document_count", 0)
                    output += f"  • {name.title()}: {prevalence:.0%} prevalence ({count} docs)\n"

            anomalies = patterns.get("anomalies", [])
            if anomalies:
                output += "\n🚨 Anomalies Detected:\n"
                for anomaly in anomalies:
                    atype = anomaly.get("type", "unknown")
                    confidence = anomaly.get("confidence", 0)
                    output += (
                        f"  • {atype.replace('_', ' ').title()}: {confidence:.0%} confidence\n"
                    )

            flow = patterns.get("document_flow", {})
            if flow:
                output += "\n📈 Document Flow:\n"
                output += f"  • Total documents: {flow.get('total_documents', 0)}\n"
                date_range = flow.get("date_range", {})
                if date_range.get("start"):
                    output += (
                        f"  • Date span: {date_range['start'][:10]} to {date_range['end'][:10]}\n"
                    )

        return output

    except Exception as e:
        return f"❌ Error in document analysis: {str(e)}"


def legal_case_tracking(case_number: str, track_type: str = "status") -> str:
    """
    Track legal case status, deadlines, and procedural requirements.
    """
    if not SERVICES_AVAILABLE:
        return "Legal intelligence services not available"

    try:
        legal_service = _get_legal_service()

        # Get case documents for analysis
        case_documents = legal_service._get_case_documents(case_number)

        if not case_documents:
            return f"❌ No documents found for case: {case_number}"

        # Format case tracking output
        output = f"📋 Legal Case Tracking: {case_number}\n\n"

        if track_type == "status":
            # Case status analysis
            doc_types = legal_service._identify_document_types(case_documents)
            case_type = legal_service._determine_case_type(case_documents)

            output += "⚖️ Case Status:\n"
            output += f"  • Case type: {case_type.replace('_', ' ').title()}\n"
            output += f"  • Documents filed: {len(case_documents)}\n"
            output += f"  • Document types: {', '.join(sorted(doc_types))}\n"

            # Determine case stage
            if "judgment" in doc_types:
                stage = "Concluded"
            elif "motion" in doc_types:
                stage = "Active litigation"
            elif "answer" in doc_types:
                stage = "Responsive pleadings"
            elif "complaint" in doc_types:
                stage = "Initial filing"
            else:
                stage = "Unknown"

            output += f"  • Current stage: {stage}\n\n"

            # Recent activity
            sorted_docs = sorted(
                case_documents, key=lambda x: x.get("datetime_utc", ""), reverse=True
            )
            output += "📅 Recent Activity:\n"
            for doc in sorted_docs[:5]:
                title = doc.get("title", "Untitled")[:50]
                date = doc.get("datetime_utc", "")[:10]
                output += f"  • {date}: {title}\n"

        elif track_type == "deadlines":
            # Extract potential deadlines from documents
            output += "⏰ Deadline Tracking:\n"

            deadlines = []
            for doc in case_documents:
                content = doc.get("content", "").lower()

                # Simple deadline detection
                import re

                deadline_patterns = [
                    r"due.*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                    r"deadline.*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                    r"respond.*?by.*?(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                ]

                for pattern in deadline_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        deadline_date = match.group(1)
                        context = content[max(0, match.start() - 30) : match.end() + 30]
                        deadlines.append(
                            {
                                "date": deadline_date,
                                "context": context.strip(),
                                "document": doc.get("title", "Unknown"),
                            }
                        )

            if deadlines:
                output += f"Found {len(deadlines)} potential deadlines:\n"
                for deadline in deadlines[:10]:
                    output += f"  • {deadline['date']}: {deadline['context'][:60]}...\n"
                    output += f"    (from: {deadline['document'][:40]})\n"
            else:
                output += "No explicit deadlines found in case documents\n"

        elif track_type == "missing":
            # Missing document analysis
            missing_result = legal_service.predict_missing_documents(case_number)

            if missing_result.get("success"):
                predicted = missing_result.get("predicted_missing", [])
                case_type = missing_result.get("case_type", "unknown")
                existing = missing_result.get("existing_documents", [])

                output += "🔍 Missing Document Analysis:\n"
                output += f"  • Case type: {case_type.replace('_', ' ').title()}\n"
                output += f"  • Existing document types: {len(existing)}\n"
                output += f"  • Predicted missing: {len(predicted)}\n\n"

                if predicted:
                    output += "⚠️ Likely Missing Documents:\n"
                    for doc in predicted:
                        doc_type = doc.get("document_type", "unknown")
                        confidence = doc.get("confidence", 0)
                        reason = doc.get("reason", "")
                        output += f"  • {doc_type.replace('_', ' ').title()}: {confidence:.0%} confidence\n"
                        output += f"    {reason}\n\n"
                else:
                    output += "✅ No missing documents predicted for this case type\n"
            else:
                output += f"❌ Could not analyze missing documents: {missing_result.get('error', 'Unknown error')}\n"

        return output

    except Exception as e:
        return f"❌ Error in case tracking: {str(e)}"


def legal_relationship_discovery(case_number: str, entity_focus: str | None = None) -> str:
    """
    Discover relationships between entities, documents, and cases.
    """
    if not SERVICES_AVAILABLE:
        return "Legal intelligence services not available"

    try:
        legal_service = _get_legal_service()

        # Get case documents
        case_documents = legal_service._get_case_documents(case_number)

        if not case_documents:
            return f"❌ No documents found for case: {case_number}"

        # Extract and analyze relationships
        relationship_result = legal_service._build_case_relationships(case_documents)
        entity_result = legal_service._extract_case_entities(case_documents)

        # Format relationship discovery output
        output = f"🔗 Legal Relationship Discovery: {case_number}\n\n"

        # Entity relationships
        if entity_result.get("relationships"):
            relationships = entity_result.get("relationships", [])
            output += f"👥 Entity Relationships ({len(relationships)}):\n"

            # Filter by entity focus if provided
            if entity_focus:
                relationships = [
                    r
                    for r in relationships
                    if entity_focus.lower() in r.get("source", "").lower()
                    or entity_focus.lower() in r.get("target", "").lower()
                ]
                output += f"Filtered by '{entity_focus}': {len(relationships)} relationships\n"

            # Group relationships by type
            rel_by_type = {}
            for rel in relationships:
                rel_type = rel.get("type", "unknown")
                if rel_type not in rel_by_type:
                    rel_by_type[rel_type] = []
                rel_by_type[rel_type].append(rel)

            for rel_type, rels in sorted(rel_by_type.items()):
                output += f"\n  {rel_type.replace('_', ' ').title()} ({len(rels)}):\n"
                for rel in rels[:5]:  # Show first 5 of each type
                    source = rel.get("source", "unknown")
                    target = rel.get("target", "unknown")
                    confidence = rel.get("confidence", 0)
                    output += f"    • {source} → {target} (conf: {confidence:.2f})\n"

        # Document relationships
        if relationship_result.get("success"):
            edges = relationship_result.get("edges", [])
            nodes = relationship_result.get("nodes", [])

            output += "\n📄 Document Relationships:\n"
            output += f"  • Documents analyzed: {len(nodes)}\n"
            output += f"  • Relationships found: {len(edges)}\n"

            if edges:
                # Find document clusters (highly connected documents)
                doc_connections = {}
                for edge in edges:
                    source = edge.get("source")
                    target = edge.get("target")
                    strength = edge.get("strength", 0)

                    if source not in doc_connections:
                        doc_connections[source] = []
                    if target not in doc_connections:
                        doc_connections[target] = []

                    doc_connections[source].append((target, strength))
                    doc_connections[target].append((source, strength))

                # Find most connected documents
                most_connected = sorted(
                    doc_connections.items(), key=lambda x: len(x[1]), reverse=True
                )

                if most_connected:
                    output += "\n🎯 Most Connected Documents:\n"
                    for doc_id, connections in most_connected[:5]:
                        # Find document title
                        doc_title = "Unknown"
                        for node in nodes:
                            if node.get("id") == doc_id:
                                doc_title = node.get("title", "Unknown")[:40]
                                break

                        avg_strength = sum(c[1] for c in connections) / len(connections)
                        output += f"  • {doc_title}: {len(connections)} connections (avg strength: {avg_strength:.3f})\n"

        # Cross-case relationships (if knowledge graph has data)
        try:
            # Search for related documents across cases
            output += "\n🌐 Cross-Case Analysis:\n"

            # Get entities for similarity search
            entities = entity_result.get("by_type", {})
            key_entities = []

            for entity_type in ["PERSON", "ORG", "ATTORNEY", "JUDGE"]:
                if entity_type in entities:
                    key_entities.extend(entities[entity_type][:3])  # Top 3 of each type

            if key_entities:
                output += f"  • Searching for cross-case connections using {len(key_entities)} key entities\n"

                # Search for documents containing these entities in other cases
                db = SimpleDB()
                related_cases = set()

                for entity in key_entities[:5]:  # Limit search
                    search_results = db.search_content(entity, limit=20)
                    for result in search_results:
                        content = result.get("content", "")
                        # Look for other case numbers
                        import re

                        case_pattern = r"\b\d{2}[A-Z]{2,4}\d{5,8}\b"
                        found_cases = re.findall(case_pattern, content)
                        for found_case in found_cases:
                            if found_case != case_number:
                                related_cases.add(found_case)

                if related_cases:
                    output += f"  • Found {len(related_cases)} potentially related cases\n"
                    for related_case in list(related_cases)[:5]:
                        output += f"    - {related_case}\n"
                else:
                    output += "  • No cross-case relationships found\n"
            else:
                output += "  • Insufficient entity data for cross-case analysis\n"

        except Exception as e:
            output += f"  • Cross-case analysis unavailable: {str(e)}\n"

        return output

    except Exception as e:
        return f"❌ Error in relationship discovery: {str(e)}"


class LegalIntelligenceServer:
    """
    Unified Legal Intelligence MCP Server.
    """

    def __init__(self):
        self.server = Server("legal-intelligence-server")
        self.setup_tools()

    def setup_tools(self):
        """
        Register legal intelligence tools.
        """

        @self.server.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="legal_extract_entities",
                    description="Extract legal entities from text using Legal BERT and NER",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "Text content to analyze for legal entities",
                            },
                            "case_id": {
                                "type": "string",
                                "description": "Optional case ID for context",
                            },
                        },
                        "required": ["content"],
                    },
                ),
                Tool(
                    name="legal_timeline_events",
                    description="Generate comprehensive timeline of legal case events",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to analyze",
                            },
                            "start_date": {
                                "type": "string",
                                "description": "Optional start date filter (YYYY-MM-DD)",
                            },
                            "end_date": {
                                "type": "string",
                                "description": "Optional end date filter (YYYY-MM-DD)",
                            },
                        },
                        "required": ["case_number"],
                    },
                ),
                Tool(
                    name="legal_knowledge_graph",
                    description="Build and analyze knowledge graph relationships for legal case",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to analyze",
                            },
                            "include_relationships": {
                                "type": "boolean",
                                "description": "Include detailed relationship analysis",
                                "default": True,
                            },
                        },
                        "required": ["case_number"],
                    },
                ),
                Tool(
                    name="legal_document_analysis",
                    description="Perform comprehensive document analysis using Legal BERT",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to analyze",
                            },
                            "analysis_type": {
                                "type": "string",
                                "description": "Type of analysis to perform",
                                "enum": ["comprehensive", "patterns"],
                                "default": "comprehensive",
                            },
                        },
                        "required": ["case_number"],
                    },
                ),
                Tool(
                    name="legal_case_tracking",
                    description="Track legal case status, deadlines, and procedural requirements",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to track",
                            },
                            "track_type": {
                                "type": "string",
                                "description": "Type of tracking to perform",
                                "enum": ["status", "deadlines", "missing"],
                                "default": "status",
                            },
                        },
                        "required": ["case_number"],
                    },
                ),
                Tool(
                    name="legal_relationship_discovery",
                    description="Discover relationships between entities, documents, and cases",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to analyze",
                            },
                            "entity_focus": {
                                "type": "string",
                                "description": "Optional entity name to focus relationship discovery on",
                            },
                        },
                        "required": ["case_number"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            try:
                if name == "legal_extract_entities":
                    result = legal_extract_entities(
                        content=arguments["content"], case_id=arguments.get("case_id")
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "legal_timeline_events":
                    result = legal_timeline_events(
                        case_number=arguments["case_number"],
                        start_date=arguments.get("start_date"),
                        end_date=arguments.get("end_date"),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "legal_knowledge_graph":
                    result = legal_knowledge_graph(
                        case_number=arguments["case_number"],
                        include_relationships=arguments.get("include_relationships", True),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "legal_document_analysis":
                    result = legal_document_analysis(
                        case_number=arguments["case_number"],
                        analysis_type=arguments.get("analysis_type", "comprehensive"),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "legal_case_tracking":
                    result = legal_case_tracking(
                        case_number=arguments["case_number"],
                        track_type=arguments.get("track_type", "status"),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "legal_relationship_discovery":
                    result = legal_relationship_discovery(
                        case_number=arguments["case_number"],
                        entity_focus=arguments.get("entity_focus"),
                    )
                    return [TextContent(type="text", text=result)]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                error_msg = f"Error executing {name}: {str(e)}"
                print(error_msg, file=sys.stderr)  # Log to stderr for stdio servers
                return [TextContent(type="text", text=error_msg)]


async def main():
    """
    Run the legal intelligence server.
    """
    server = LegalIntelligenceServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="legal-intelligence",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(NotificationOptions(), {}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
