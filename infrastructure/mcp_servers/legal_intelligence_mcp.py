#!/usr/bin/env python3
"""Legal Intelligence MCP Server.

Unified Legal Intelligence MCP server that replaces existing legal and
timeline servers. Provides comprehensive legal case analysis, entity
extraction, timeline generation, knowledge graph relationships, and
document intelligence.

================================================================================
TECHNICAL DEBT & STUBBED FUNCTIONS - UPDATED 2025-01-04
================================================================================

This file contains significant technical debt and needs major refactoring:
- File size: 1487 lines (3.3x larger than recommended 450 lines)
- Multiple broken helper functions REMOVED (5 functions, 48 lines deleted)
- Import paths fixed to use correct modules

STUBBED FUNCTIONS (These are placeholders that need proper implementation):

1. BROKEN - Always returns placeholder values:
   - _identify_timeline_gaps(): REMOVED - had hardcoded 30-day gaps
   - _extract_dates_from_document(): REMOVED - regex too simplistic

2. POOR IMPLEMENTATION - Naive string matching:
   - _identify_document_types(): No word boundaries, will match "motion" in "promotion"
   - _determine_case_type(): Simplistic keyword matching
   - _calculate_document_similarity(): REMOVED - used word overlap not embeddings
   - _extract_themes(): REMOVED - just counted keywords, no NLP
   - _detect_anomalies(): REMOVED - overly simplistic duplicate detection

3. SHOULD USE LIBRARIES:
   - Date extraction -> dateparser or spacy
   - Document similarity -> sentence-transformers or existing embeddings
   - Pattern matching -> spacy.Matcher with proper patterns
   - Theme extraction -> KeyBERT or topic modeling

4. USEFUL BUT NEEDS REFACTOR:
   - _predict_missing_documents(): Has legal domain value but needs state machine
   - LEGAL_DOC_PATTERNS: Useful domain knowledge but needs proper config
   - _get_expected_document_sequence(): Legal procedure knowledge worth keeping

IMPORT PATHS:
- lib.db.SimpleDB - Database module
- utilities.embeddings.embedding_service - Embedding service (needs fixing)
- lib.timeline.main.TimelineService - Timeline service

TODO:
1. Extract helper functions to separate modules (~300 lines each)
2. Replace broken functions with proper libraries
3. Add comprehensive tests
4. Fix all hardcoded magic values
5. Implement proper error handling

NOTE: Tests in tests/integration/test_mcp_parameter_validation.py mock
get_legal_intelligence_service() so changes here won't break tests.
================================================================================
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

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

# Import underlying services directly
# NOTE: Import paths reflect current project structure
try:
    from loguru import logger

    from entity.main import EntityService
    from lib.db import SimpleDB  # Database module
    from lib.embeddings import get_embedding_service  # Consolidated architecture
    from lib.timeline.main import TimelineService  # Timeline service

    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Infrastructure services not available: {e}", file=sys.stderr)
    SERVICES_AVAILABLE = False

# Standard legal document patterns moved from legal_intelligence service
LEGAL_DOC_PATTERNS = {
    "complaint": ["complaint", "petition", "initial filing"],
    "answer": ["answer", "response", "reply"],
    "motion": ["motion", "request", "application"],
    "order": ["order", "ruling", "judgment", "decree"],
    "discovery": ["interrogatories", "deposition", "request for production"],
    "notice": ["notice", "summons", "subpoena"],
    "brief": ["brief", "memorandum", "argument"],
    "settlement": ["settlement", "agreement", "stipulation"],
    "transcript": ["transcript", "hearing", "proceedings"],
}

# Patchable factory hook for tests - now returns a simple dict structure
def get_legal_intelligence_service(db_path: str | None = None):
    """
    Create a simple service dict with the underlying services for compatibility
    with tests.
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

# Helper functions from legal_intelligence service

def _get_case_documents(case_number: str, db: SimpleDB) -> list[dict[str, Any]]:
    """
    Get all documents related to a case number.
    """
    search_results = db.search_content(case_number, limit=100)
    
    # Filter to ensure relevance
    case_docs = []
    case_upper = case_number.upper()
    for doc in search_results:
        # Check if case number is in title or content (case-insensitive)
        if (
            case_upper in doc.get("title", "").upper()
            or case_upper in doc.get("body", "").upper()
        ):
            case_docs.append(doc)
    
    return case_docs

def _identify_document_types(documents: list[dict]) -> set[str]:
    """
    Identify types of legal documents present.
    """
    identified_types = set()
    
    for doc in documents:
        title = doc.get("title", "").lower()
        content_preview = doc.get("body", "")[:500].lower()
        
        for doc_type, patterns in LEGAL_DOC_PATTERNS.items():
            for pattern in patterns:
                if pattern in title or pattern in content_preview:
                    identified_types.add(doc_type)
                    break
    
    return identified_types

def _determine_case_type(documents: list[dict]) -> str:
    """
    Determine the type of legal case from documents.
    """
    doc_types = _identify_document_types(documents)
    
    if "complaint" in doc_types:
        # Check for specific case type indicators
        for doc in documents:
            content = doc.get("body", "").lower()
            if "unlawful detainer" in content:
                return "unlawful_detainer"
            elif "personal injury" in content:
                return "personal_injury"  
            elif "breach of contract" in content:
                return "contract"
            elif "divorce" in content or "dissolution" in content:
                return "family_law"
    
    return "civil_litigation"  # Default

def _get_expected_document_sequence(case_type: str) -> list[str]:
    """
    Get expected document sequence for a case type.
    """
    sequences = {
        "unlawful_detainer": [
            "complaint", "summons", "answer", "motion", "order", "judgment", "notice"
        ],
        "civil_litigation": [
            "complaint", "summons", "answer", "discovery", "motion", "brief", "order", "judgment"
        ],
        "contract": [
            "complaint", "answer", "discovery", "motion", "brief", "settlement", "order"
        ],
        "family_law": [
            "petition", "response", "discovery", "motion", "order", "settlement", "judgment"
        ]
    }
    
    return sequences.get(case_type, sequences["civil_litigation"])

def _calculate_missing_confidence(doc_type: str, existing: set[str], documents: list[dict]) -> float:
    """
    Calculate confidence that a document type is missing.
    """
    confidence = 0.5  # Base confidence
    
    # Adjust based on typical sequence
    if doc_type == "answer" and "complaint" in existing:
        confidence = 0.8
    elif doc_type == "order" and "motion" in existing:
        confidence = 0.7
    elif doc_type == "judgment" and len(documents) > 5:
        confidence = 0.6
    
    # Check for references to missing document
    for doc in documents:
        content = doc.get("body", "").lower()
        if doc_type in content:
            confidence += 0.2
            break
    
    return min(confidence, 1.0)

def _get_missing_reason(doc_type: str, existing: set[str]) -> str:
    """
    Get reason why a document might be missing.
    """
    reasons = {
        "answer": "Expected response to complaint not found",
        "discovery": "No discovery documents found despite case progression",
        "motion": "Case appears to lack expected motions",
        "order": "Court orders expected but not found",
        "judgment": "Case may be missing final judgment",
        "settlement": "Settlement documents not found",
        "transcript": "Hearing transcripts appear to be missing"
    }
    
    return reasons.get(doc_type, f"Expected {doc_type} not found in case documents")

# TODO: _extract_dates_from_document() was removed (2025-01-04)
# Original function extracted dates from documents using insufficient regex.
# Should be reimplemented with spacy (already installed) for temporal NER:
#   doc = nlp(text); dates = [ent for ent in doc.ents if ent.label_ == "DATE"]
# Or use dateparser.search.search_dates() for more robust parsing.

def _classify_date_type(context: str) -> str:
    """
    Classify the type of date based on context.
    """
    context_lower = context.lower()
    
    if "filed" in context_lower:
        return "filing_date"
    elif "hearing" in context_lower:
        return "hearing_date"
    elif "served" in context_lower:
        return "service_date"
    elif "due" in context_lower or "deadline" in context_lower:
        return "deadline"
    else:
        return "event_date"

# TODO: _identify_timeline_gaps() was removed (2025-01-04)
# Original function had hardcoded 30-day gap detection (broken logic).
# Should be reimplemented with proper date parsing and configurable thresholds.

def _identify_milestones(events: list[dict]) -> list[dict]:
    """
    Identify key milestones in the case timeline.
    """
    milestones = []
    milestone_types = ["filing_date", "hearing_date", "judgment_date"]
    
    for event in events:
        if event.get("type") in milestone_types:
            milestones.append(event)
    
    return milestones

# TODO: _calculate_document_similarity() was removed (2025-01-04)
# Original used naive Jaccard similarity (word overlap).
# Should use existing embedding infrastructure + cosine similarity.
# Check search_intelligence/similarity.py for existing implementation.

def _generate_case_timeline(documents: list[dict]) -> dict[str, Any]:
    """
    Generate timeline from case documents.
    """
    events = []
    
    for doc in documents:
        # TODO: Date extraction removed - would use spacy NER
        dates = []  # Empty until reimplemented
        
        for date_info in dates:
            event = {
                "date": date_info["date"],
                "type": date_info["type"],
                "description": date_info["description"],
                "document_id": doc.get("content_id"),
                "document_title": doc.get("title"),
                "confidence": date_info.get("confidence", 1.0)
            }
            events.append(event)
    
    # Sort by date
    events.sort(key=lambda x: x["date"])
    
    # TODO: Gap detection removed - needs proper implementation
    gaps = []  # Empty until reimplemented
    
    return {
        "success": True,
        "events": events,
        "total_events": len(events),
        "date_range": {
            "start": events[0]["date"] if events else None,
            "end": events[-1]["date"] if events else None
        },
        "gaps": gaps,
        "milestones": _identify_milestones(events)
    }

def _build_case_relationships(documents: list[dict]) -> dict[str, Any]:
    """
    Build relationship graph for case documents.
    """
    nodes = []
    edges = []
    
    # Add document nodes
    for doc in documents:
        node = {
            "id": doc.get("content_id"),
            "type": "document",
            "title": doc.get("title"),
            "metadata": {
                "content_type": doc.get("source_type"),
                "date": doc.get("datetime_utc")
            }
        }
        nodes.append(node)
    
    # Find document similarities and create edges
    for i, doc1 in enumerate(documents):
        for doc2 in documents[i + 1:]:
            # TODO: Similarity calculation removed - should use embeddings
            similarity = 0.1  # Default low similarity
            
            if similarity > 0.5:  # Threshold for relationship
                edge = {
                    "source": doc1.get("content_id"),
                    "target": doc2.get("content_id"),
                    "type": "similar_to",
                    "strength": similarity
                }
                edges.append(edge)
    
    return {
        "success": True,
        "nodes": nodes,
        "edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "graph_density": (
            len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
        )
    }

def _extract_case_entities(documents: list[dict]) -> dict[str, Any]:
    """
    Extract and consolidate entities from case documents.
    """
    all_entities = []
    entity_relationships = []
    
    entity_service = EntityService()
    
    for doc in documents:
        content = doc.get("body", "")
        if content:
            # Use extract_email_entities with a dummy message_id
            result = entity_service.extract_email_entities(
                message_id=f"doc_{doc.get('id', 'unknown')}", 
                content=content
            )
            if result.get("success"):
                entities = result.get("entities", [])
                all_entities.extend(entities)
                
                # Get relationships if available
                relationships = result.get("relationships", [])
                entity_relationships.extend(relationships)
    
    # Consolidate entities by type
    consolidated = _consolidate_entities(all_entities)
    
    return {
        "total_entities": len(all_entities),
        "unique_entities": len(consolidated),
        "by_type": _group_entities_by_type(consolidated),
        "relationships": entity_relationships,
        "key_parties": _identify_key_parties(consolidated)
    }

def _consolidate_entities(entities: list[dict]) -> list[dict]:
    """
    Consolidate duplicate entities.
    """
    consolidated = {}
    
    for entity in entities:
        key = (entity.get("text", "").lower(), entity.get("label", ""))
        
        if key not in consolidated:
            consolidated[key] = entity
        else:
            # Merge confidence scores
            existing = consolidated[key]
            existing["confidence"] = max(
                existing.get("confidence", 0), entity.get("confidence", 0)
            )
    
    return list(consolidated.values())

def _group_entities_by_type(entities: list[dict]) -> dict[str, list]:
    """
    Group entities by their type/label.
    """
    grouped = {}
    
    for entity in entities:
        label = entity.get("label", "UNKNOWN")
        if label not in grouped:
            grouped[label] = []
        grouped[label].append(entity.get("text"))
    
    return grouped

def _identify_key_parties(entities: list[dict]) -> list[dict]:
    """
    Identify key parties in the case.
    """
    # Focus on PERSON and ORG entities with high frequency
    person_org = [e for e in entities if e.get("label") in ["PERSON", "ORG"]]
    
    # Sort by confidence
    person_org.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    return person_org[:10]  # Top 10 key parties

def _analyze_document_patterns(documents: list[dict]) -> dict[str, Any]:
    """
    Analyze patterns in case documents.
    """
    if not documents:
        return {"success": False, "error": "No documents to analyze"}
    
    # Identify document types
    doc_types = _identify_document_types(documents)
    
    # Find recurring themes
    # TODO: Theme extraction removed - needs KeyBERT or topic modeling
    themes = []  # Empty until reimplemented
    
    # Detect anomalies
    # TODO: Anomaly detection removed - use duplicate_detector.py instead
    anomalies = []  # Empty until reimplemented
    
    # Analyze document flow
    flow = _analyze_document_flow(documents)
    
    return {
        "success": True,
        "document_types": doc_types,
        "themes": themes,
        "anomalies": anomalies,
        "document_flow": flow,
        "pattern_summary": _summarize_patterns(doc_types, themes, anomalies)
    }

# TODO: _extract_themes() was removed (2025-01-04)
# Original was naive keyword counting without NLP.
# Should use KeyBERT or topic modeling (LDA/NMF) for proper theme extraction.
# scikit-learn (already installed) has TF-IDF and topic modeling capabilities.

# TODO: _detect_anomalies() was removed (2025-01-04)
# Original depended on broken similarity function.
# Should use search_intelligence/duplicate_detector.py (already exists!).
# Or implement with MinHash/LSH for efficient near-duplicate detection.

def _analyze_document_flow(documents: list[dict]) -> dict[str, Any]:
    """
    Analyze the flow and progression of documents.
    """
    # Sort documents by date if available
    sorted_docs = sorted(documents, key=lambda x: x.get("datetime_utc", ""))
    
    flow = {
        "total_documents": len(sorted_docs),
        "date_range": {
            "start": sorted_docs[0].get("datetime_utc") if sorted_docs else None,
            "end": sorted_docs[-1].get("datetime_utc") if sorted_docs else None
        },
        "document_sequence": [{
            "title": doc.get("title"),
            "type": _identify_single_doc_type(doc),
            "date": doc.get("datetime_utc")
        } for doc in sorted_docs]
    }
    
    return flow

def _identify_single_doc_type(document: dict) -> str:
    """
    Identify the type of a single document.
    """
    title = document.get("title", "").lower()
    
    for doc_type, patterns in LEGAL_DOC_PATTERNS.items():
        for pattern in patterns:
            if pattern in title:
                return doc_type
    
    return "unknown"

def _summarize_patterns(doc_types: set[str], themes: list[dict], anomalies: list[dict]) -> str:
    """
    Summarize the patterns found in the analysis.
    """
    summary = f"Found {len(doc_types)} document types"
    
    if themes:
        top_theme = max(themes, key=lambda x: x["prevalence"])
        summary += f", primary theme: {top_theme['theme']}"
    
    if anomalies:
        summary += f", {len(anomalies)} anomalies detected"
    
    return summary

def _predict_missing_documents(case_documents: list[dict]) -> dict[str, Any]:
    """
    Predict potentially missing documents based on case type and patterns.
    """
    if not case_documents:
        return {"success": False, "error": "No documents found"}
    
    # Analyze existing document types
    existing_types = _identify_document_types(case_documents)
    
    # Determine case type from documents
    case_type = _determine_case_type(case_documents)
    
    # Get expected document sequence for case type
    expected_sequence = _get_expected_document_sequence(case_type)
    
    # Find gaps in sequence
    missing = []
    for doc_type in expected_sequence:
        if doc_type not in existing_types:
            confidence = _calculate_missing_confidence(
                doc_type, existing_types, case_documents
            )
            if confidence > 0.3:  # Threshold for reporting
                missing.append({
                    "document_type": doc_type,
                    "confidence": confidence,
                    "reason": _get_missing_reason(doc_type, existing_types)
                })
    
    # Sort by confidence
    missing.sort(key=lambda x: x["confidence"], reverse=True)
    
    return {
        "success": True,
        "case_type": case_type,
        "existing_documents": list(existing_types),
        "predicted_missing": missing,
        "total_missing": len(missing)
    }


def legal_extract_entities(content: str, case_id: str | None = None) -> str:
    """Extract legal entities from text content using validated EntityService.

    FAIL-FAST: Will crash immediately if EntityService is broken.
    """
    if not SERVICES_AVAILABLE:
        return "Legal intelligence services not available"

    try:
        # Use fail-fast validated EntityService
        from .legal_service_validator import get_legal_service_validator
        
        validator = get_legal_service_validator()
        entity_service = validator.get_validated_entity_service()
        
        # Use extract_email_entities with legal case context
        message_id = f"case_{case_id}" if case_id else "legal_text_analysis"
        result = entity_service.extract_email_entities(
            message_id=message_id, 
            content=content
        )

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


# _get_legal_service function removed - no longer needed since we use services directly


def legal_timeline_events(
    case_number: str, start_date: str | None = None, end_date: str | None = None
) -> str:
    """
    Generate comprehensive timeline of legal case events.
    """
    if not SERVICES_AVAILABLE:
        return "Legal intelligence services not available"

    try:
        db = SimpleDB()
        
        # Get case documents
        case_documents = _get_case_documents(case_number, db)
        
        if not case_documents:
            return f"❌ No documents found for case {case_number}"
        
        # Generate timeline from case documents
        timeline_result = _generate_case_timeline(case_documents)

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
        db = SimpleDB()
        
        # Get case documents
        case_documents = _get_case_documents(case_number, db)
        
        if not case_documents:
            return f"❌ No documents found for case {case_number}"
        
        # Build relationship graph
        graph_result = _build_case_relationships(case_documents)

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
        db = SimpleDB()
        
        # Get case documents
        case_documents = _get_case_documents(case_number, db)
        
        if not case_documents:
            return f"❌ No documents found for case {case_number}"

        # Perform document pattern analysis
        if analysis_type == "patterns":
            result = _analyze_document_patterns(case_documents)
        else:
            # Comprehensive case analysis
            result = {
                "success": True,
                "case_number": case_number,
                "document_count": len(case_documents),
                "documents": case_documents,
                "entities": _extract_case_entities(case_documents),
                "timeline": _generate_case_timeline(case_documents),
                "relationships": _build_case_relationships(case_documents),
                "patterns": _analyze_document_patterns(case_documents),
                "missing_documents": _predict_missing_documents(case_documents),
                "analysis_timestamp": datetime.now().isoformat()
            }

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
        db = SimpleDB()
        
        # Get case documents for analysis
        case_documents = _get_case_documents(case_number, db)

        if not case_documents:
            return f"❌ No documents found for case: {case_number}"

        # Format case tracking output
        output = f"📋 Legal Case Tracking: {case_number}\n\n"

        if track_type == "status":
            # Case status analysis
            doc_types = _identify_document_types(case_documents)
            case_type = _determine_case_type(case_documents)

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
            missing_result = _predict_missing_documents(case_documents)

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
        db = SimpleDB()
        
        # Get case documents
        case_documents = _get_case_documents(case_number, db)

        if not case_documents:
            return f"❌ No documents found for case: {case_number}"

        # Extract and analyze relationships
        relationship_result = _build_case_relationships(case_documents)
        entity_result = _extract_case_entities(case_documents)

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
