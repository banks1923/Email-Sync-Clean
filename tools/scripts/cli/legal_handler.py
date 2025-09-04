#!/usr/bin/env python3
"""
Legal Intelligence CLI Handler Provides CLI commands for legal case analysis,
timeline generation, relationship mapping, and document intelligence.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from entity.main import EntityService
from shared.db.simple_db import SimpleDB
from summarization import get_document_summarizer
from utilities.timeline.main import TimelineService

# Logger is now imported globally from loguru


def process_legal_case(case_id: str, output_format: str = "text") -> None:
    """Process a legal case and extract comprehensive intelligence.

    Args:
        case_id: Case identifier or search pattern
        output_format: Output format (text/json)
    """
    print(f"🏛️ Processing legal case: {case_id}")

    try:
        # Initialize services directly
        db = SimpleDB()
        entity_service = EntityService()
        
        # Get case documents
        case_documents = _get_case_documents(db, case_id)
        
        if not case_documents:
            result = {"success": False, "error": f"No documents found for case {case_id}"}
        else:
            # Perform comprehensive analysis
            result = {
                "success": True,
                "case_id": case_id,
                "documents_analyzed": len(case_documents),
                "entities": _extract_case_entities(entity_service, case_documents),
                "timeline": _generate_case_timeline_data(case_documents),
                "patterns": _analyze_document_patterns(case_documents),
                "analysis_timestamp": datetime.now().isoformat(),
            }

        if output_format == "json":
            print(json.dumps(result, indent=2, default=str))
        else:
            # Text format output
            print(f"\n📊 Case Analysis for: {result.get('case_id', case_id)}")
            print("=" * 60)

            # Show entity summary
            entities = result.get("entities", {})
            if entities:
                print("\n👥 Key Entities:")
                for entity_type, entity_list in entities.items():
                    if entity_list:
                        print(f"  {entity_type}: {', '.join(entity_list[:5])}")

            # Show document summary
            docs_analyzed = result.get("documents_analyzed", 0)
            print(f"\n📄 Documents Analyzed: {docs_analyzed}")

            # Show patterns
            patterns = result.get("patterns", {})
            if patterns:
                print("\n🔍 Document Patterns:")
                for pattern_type, docs in patterns.items():
                    if docs:
                        print(f"  {pattern_type}: {len(docs)} documents")

            # Show timeline summary
            timeline = result.get("timeline", {})
            events = timeline.get("events", [])
            if events:
                print(f"\n📅 Timeline: {len(events)} events found")
                print(f"  Date Range: {timeline.get('date_range', 'Unknown')}")

            print("\n✅ Case processing complete")

    except Exception as e:
        print(f"❌ Error processing case: {e}")
        logger.error(f"Error in process_legal_case: {e}")
        sys.exit(1)


def generate_legal_timeline(case_id: str, output_file: str | None = None) -> None:
    """Generate a chronological timeline for a legal case.

    Args:
        case_id: Case identifier or search pattern
        output_file: Optional file path to save timeline
    """
    print(f"📅 Generating timeline for case: {case_id}")

    try:
        # Initialize services directly
        db = SimpleDB()
        
        # Get case documents
        case_documents = _get_case_documents(db, case_id)
        
        if not case_documents:
            timeline = None
        else:
            timeline = _generate_case_timeline_data(case_documents)
            timeline["case_id"] = case_id

        if not timeline or not timeline.get("events"):
            print("❌ No timeline events found for this case")
            return

        # Display timeline
        print(f"\n⏱️ Case Timeline: {timeline.get('case_id', case_id)}")
        print(f"Date Range: {timeline.get('date_range', 'Unknown')}")
        print("=" * 60)

        events = timeline.get("events", [])
        for event in events[:20]:  # Show first 20 events
            date = event.get("date", "Unknown date")
            desc = event.get("description", "")
            doc = event.get("document_title", "")

            print(f"\n📌 {date}")
            print(f"   {desc}")
            if doc:
                print(f"   Source: {doc}")

        if len(events) > 20:
            print(f"\n... and {len(events) - 20} more events")

        # Save to file if requested
        if output_file:
            output_path = Path(output_file)
            with open(output_path, "w") as f:
                json.dump(timeline, f, indent=2, default=str)
            print(f"\n💾 Timeline saved to: {output_path}")

        print(f"\n✅ Timeline generation complete: {len(events)} events")

    except Exception as e:
        print(f"❌ Error generating timeline: {e}")
        logger.error(f"Error in generate_legal_timeline: {e}")
        sys.exit(1)


def build_legal_graph(case_id: str, max_depth: int = 3) -> None:
    """Build and display a relationship graph for a legal case.

    Args:
        case_id: Case identifier or search pattern
        max_depth: Maximum depth for relationship traversal
    """
    print(f"🕸️ Building relationship graph for case: {case_id}")

    try:
        # Initialize services directly
        db = SimpleDB()
        
        # Get case documents
        case_documents = _get_case_documents(db, case_id)
        
        if not case_documents:
            graph = None
        else:
            graph = _build_case_relationships(case_documents)
            graph["case_id"] = case_id

        if not graph:
            print("❌ No relationships found for this case")
            return

        # Display graph summary
        print(f"\n🔗 Relationship Graph: {graph.get('case_id', case_id)}")
        print("=" * 60)

        # Show node statistics
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        print("\n📊 Graph Statistics:")
        print(f"  Nodes: {len(nodes)}")
        print(f"  Edges: {len(edges)}")
        print(f"  Max Depth: {max_depth}")

        # Show key relationships
        if edges:
            print("\n🔗 Key Relationships:")
            for edge in edges[:10]:  # Show first 10 relationships
                source = edge.get("source", "Unknown")
                target = edge.get("target", "Unknown")
                rel_type = edge.get("relationship", "related_to")
                weight = edge.get("weight", 0.0)

                print(f"  {source} --[{rel_type}:{weight:.2f}]--> {target}")

            if len(edges) > 10:
                print(f"  ... and {len(edges) - 10} more relationships")

        # Show clusters if found
        clusters = graph.get("clusters", [])
        if clusters:
            print(f"\n🎯 Document Clusters: {len(clusters)} found")
            for i, cluster in enumerate(clusters[:3], 1):
                print(f"  Cluster {i}: {len(cluster)} documents")

        print("\n✅ Graph building complete")

    except Exception as e:
        print(f"❌ Error building graph: {e}")
        logger.error(f"Error in build_legal_graph: {e}")
        sys.exit(1)


def search_legal(query: str, case_id: str | None = None, limit: int = 10) -> None:
    """Perform legal-specific search with entity awareness.

    Args:
        query: Search query
        case_id: Optional case filter
        limit: Number of results to return
    """
    print(f"🔍 Legal Search: '{query}'")
    if case_id:
        print(f"   Filtered to case: {case_id}")

    try:
        # Initialize services directly
        db = SimpleDB()
        entity_service = EntityService()

        # Search with filters
        results = db.search_content(query, limit=limit)
        
        # Filter by case_id if provided
        if case_id and results:
            case_upper = case_id.upper()
            results = [
                result for result in results
                if (case_upper in result.get("title", "").upper() 
                    or case_upper in result.get("body", "").upper())
            ]

        if not results:
            print("❌ No results found")
            return

        print(f"\n📚 Found {len(results)} legal documents")
        print("=" * 60)

        for i, result in enumerate(results, 1):
            content_type = result.get("content_type", "document")
            title = result.get("title", "Untitled")
            content = result.get("content", "")[:200]

            print(f"\n{i}. 📄 {title}")
            print(f"   Type: {content_type}")
            print(f"   Preview: {content}...")

            # Extract and show entities if available
            try:
                entity_result = entity_service.extract_email_entities(
                    message_id=f"search_{i}",
                    content=content[:500],  # Limit content for entity extraction
                )
                if entity_result.get("success"):
                    entities = entity_result.get("entities", [])
                    if entities and isinstance(entities, list):
                        # Get unique entity texts
                        entity_texts = list(
                            {e.get("text", "") for e in entities[:5] if e.get("text")}
                        )
                        if entity_texts:
                            print(f"   Entities: {', '.join(entity_texts[:5])}")
            except Exception:
                # Silently skip entity extraction errors
                pass

        print("\n✅ Search complete")

    except Exception as e:
        print(f"❌ Error in legal search: {e}")
        logger.error(f"Error in search_legal: {e}")
        sys.exit(1)


def predict_missing_documents(case_id: str, confidence_threshold: float = 0.6) -> None:
    """Predict potentially missing documents in a legal case.

    Args:
        case_id: Case identifier or search pattern
        confidence_threshold: Minimum confidence for predictions
    """
    print(f"🔮 Predicting missing documents for case: {case_id}")

    try:
        # Initialize services directly
        db = SimpleDB()
        
        # Get case documents
        case_documents = _get_case_documents(db, case_id)
        
        if not case_documents:
            predictions = {"success": False, "error": f"No documents found for case {case_id}"}
        else:
            predictions = _predict_missing_documents(case_documents, case_id)

        if not predictions or not predictions.get("missing_documents"):
            print("✅ No missing documents detected - case appears complete")
            return

        # Display predictions
        print("\n⚠️ Potential Missing Documents Detected")
        print("=" * 60)

        missing_docs = predictions.get("missing_documents", [])
        high_confidence = [
            d for d in missing_docs if d.get("confidence", 0) >= confidence_threshold
        ]

        if high_confidence:
            print(f"\n🔴 High Confidence Missing ({len(high_confidence)} documents):")
            for doc in high_confidence:
                doc_type = doc.get("type", "Unknown")
                confidence = doc.get("confidence", 0.0)
                reason = doc.get("reason", "Pattern analysis")

                print(f"\n  📄 {doc_type}")
                print(f"     Confidence: {confidence:.0%}")
                print(f"     Reason: {reason}")

                # Show related documents that suggest this is missing
                evidence = doc.get("evidence", [])
                if evidence:
                    print(f"     Evidence: {', '.join(evidence[:3])}")

        # Show patterns found
        patterns = predictions.get("patterns_found", {})
        if patterns:
            print("\n📊 Document Patterns Detected:")
            for pattern, docs in patterns.items():
                if docs:
                    print(f"  {pattern}: {len(docs)} documents")

        # Show recommendation
        total_missing = len(missing_docs)
        print(
            f"\n💡 Recommendation: Review and locate {total_missing} potentially missing documents"
        )
        print("   Priority should be given to high-confidence predictions")

    except Exception as e:
        print(f"❌ Error predicting missing documents: {e}")
        logger.error(f"Error in predict_missing_documents: {e}")
        sys.exit(1)


def summarize_legal_docs(case_id: str, max_docs: int = 10) -> None:
    """Generate summaries for legal documents in a case.

    Args:
        case_id: Case identifier or search pattern
        max_docs: Maximum number of documents to summarize
    """
    print(f"📝 Summarizing legal documents for case: {case_id}")

    try:
        # Initialize services directly
        db = SimpleDB()
        entity_service = EntityService()
        
        # Search for case documents
        results = db.search_content(case_id, limit=max_docs)

        if not results:
            print("❌ No documents found for this case")
            return

        print(f"\n📚 Summarizing {len(results)} documents")
        print("=" * 60)

        summarizer = get_document_summarizer()

        for i, doc in enumerate(results, 1):
            title = doc.get("title", "Untitled")
            content = doc.get("content", "")

            if not content:
                continue

            print(f"\n{i}. 📄 {title}")

            # Generate summary
            summary = summarizer.extract_summary(
                content, max_sentences=3, max_keywords=10, summary_type="combined"
            )

            # Display keywords
            keywords = summary.get("tf_idf_keywords", {})
            if keywords:
                top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:5]
                keyword_str = ", ".join([k[0] for k in top_keywords])
                print(f"   Keywords: {keyword_str}")

            # Display summary sentences
            sentences = summary.get("textrank_sentences", [])
            if sentences:
                print(f"   Summary: {' '.join(sentences[:2])}")

            # Extract and show legal entities
            try:
                entity_result = entity_service.extract_email_entities(
                    message_id=f"summary_{i}",
                    content=content[:500],  # Limit content for entity extraction
                )
                if entity_result.get("success"):
                    entities = entity_result.get("entities", [])
                    if entities and isinstance(entities, list):
                        # Filter for legal entity types
                        legal_entities = [
                            e for e in entities if e.get("entity_type") in ["PERSON", "ORG", "LAW"]
                        ]
                        entity_texts = list(
                            {e.get("text", "") for e in legal_entities[:5] if e.get("text")}
                        )
                        if entity_texts:
                            print(f"   Legal Entities: {', '.join(entity_texts[:5])}")
            except Exception:
                # Silently skip entity extraction errors
                pass

        print("\n✅ Summarization complete")

    except Exception as e:
        print(f"❌ Error summarizing documents: {e}")
        logger.error(f"Error in summarize_legal_docs: {e}")
        sys.exit(1)


# Helper functions (previously part of LegalIntelligenceService)

def _get_case_documents(db: SimpleDB, case_number: str) -> list[dict[str, Any]]:
    """Get all documents related to a case number."""
    # Search for documents containing the case number
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


def _extract_case_entities(entity_service: EntityService, documents: list[dict]) -> dict[str, Any]:
    """Extract and consolidate entities from case documents."""
    all_entities = []
    entity_relationships = []

    for doc in documents:
        content = doc.get("body", "")
        if content:
            # Extract entities using the entity service
            result = entity_service.extract_email_entities(
                message_id=f"doc_{doc.get('id', 'unknown')}", content=content
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
        "key_parties": _identify_key_parties(consolidated),
    }


def _generate_case_timeline_data(documents: list[dict]) -> dict[str, Any]:
    """Generate timeline from case documents."""
    events = []

    for doc in documents:
        # Extract dates from document
        dates = _extract_dates_from_document(doc)

        for date_info in dates:
            event = {
                "date": date_info["date"],
                "type": date_info["type"],
                "description": date_info["description"],
                "document_id": doc.get("content_id"),
                "document_title": doc.get("title"),
                "confidence": date_info.get("confidence", 1.0),
            }
            events.append(event)

    # Sort by date
    events.sort(key=lambda x: x["date"])

    # Create date range
    date_range = "Unknown"
    if events:
        start_date = events[0]["date"]
        end_date = events[-1]["date"]
        if start_date != end_date:
            date_range = f"{start_date} to {end_date}"
        else:
            date_range = start_date

    return {
        "success": True,
        "events": events,
        "total_events": len(events),
        "date_range": date_range,
        "milestones": _identify_milestones(events),
    }


def _build_case_relationships(documents: list[dict]) -> dict[str, Any]:
    """Build relationship graph for case documents."""
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
                "date": doc.get("datetime_utc"),
            },
        }
        nodes.append(node)

    # Find document similarities and create edges (simplified)
    for i, doc1 in enumerate(documents):
        for doc2 in documents[i + 1 :]:
            similarity = _calculate_document_similarity(doc1, doc2)

            if similarity > 0.5:  # Threshold for relationship
                edge = {
                    "source": doc1.get("content_id"),
                    "target": doc2.get("content_id"),
                    "relationship": "similar_to",
                    "weight": similarity,
                }
                edges.append(edge)

    # Create clusters (simple grouping by similarity)
    clusters = []
    if len(documents) > 2:
        # Simple clustering - group similar documents
        cluster = [doc.get("title", "Untitled") for doc in documents[:3]]
        if cluster:
            clusters.append(cluster)

    return {
        "success": True,
        "nodes": nodes,
        "edges": edges,
        "clusters": clusters,
        "node_count": len(nodes),
        "edge_count": len(edges),
    }


def _analyze_document_patterns(documents: list[dict]) -> dict[str, Any]:
    """Analyze patterns in case documents."""
    if not documents:
        return {"success": False, "error": "No documents to analyze"}

    # Standard legal document patterns
    legal_doc_patterns = {
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

    # Identify document types
    identified_types = {}
    for doc in documents:
        title = doc.get("title", "").lower()
        content_preview = doc.get("body", "")[:500].lower()

        for doc_type, patterns in legal_doc_patterns.items():
            for pattern in patterns:
                if pattern in title or pattern in content_preview:
                    if doc_type not in identified_types:
                        identified_types[doc_type] = []
                    identified_types[doc_type].append(doc.get("title", "Untitled"))
                    break

    return {
        "success": True,
        "document_types": identified_types,
        "total_documents": len(documents),
        "pattern_summary": f"Found {len(identified_types)} document types across {len(documents)} documents",
    }


def _predict_missing_documents(documents: list[dict], case_id: str) -> dict[str, Any]:
    """Predict potentially missing documents based on case type and patterns."""
    # Analyze existing document types
    existing_types = set()
    legal_doc_patterns = {
        "complaint": ["complaint", "petition", "initial filing"],
        "answer": ["answer", "response", "reply"],
        "motion": ["motion", "request", "application"],
        "order": ["order", "ruling", "judgment", "decree"],
        "discovery": ["interrogatories", "deposition", "request for production"],
    }

    for doc in documents:
        title = doc.get("title", "").lower()
        content_preview = doc.get("body", "")[:500].lower()

        for doc_type, patterns in legal_doc_patterns.items():
            for pattern in patterns:
                if pattern in title or pattern in content_preview:
                    existing_types.add(doc_type)
                    break

    # Determine case type (simplified)
    case_type = "civil_litigation"
    for doc in documents:
        content = doc.get("body", "").lower()
        if "unlawful detainer" in content:
            case_type = "unlawful_detainer"
            break

    # Expected document sequence
    expected_sequences = {
        "unlawful_detainer": ["complaint", "answer", "motion", "order", "judgment"],
        "civil_litigation": ["complaint", "answer", "discovery", "motion", "order"],
    }

    expected = set(expected_sequences.get(case_type, expected_sequences["civil_litigation"]))

    # Find missing documents
    missing = []
    for doc_type in expected:
        if doc_type not in existing_types:
            confidence = 0.6  # Base confidence
            if doc_type == "answer" and "complaint" in existing_types:
                confidence = 0.8
            elif doc_type == "order" and "motion" in existing_types:
                confidence = 0.7

            missing.append({
                "type": doc_type,
                "confidence": confidence,
                "reason": f"Expected {doc_type} not found in case documents",
                "evidence": list(existing_types),
            })

    # Get patterns found
    patterns_found = _analyze_document_patterns(documents)

    return {
        "success": True,
        "case_id": case_id,
        "case_type": case_type,
        "existing_documents": list(existing_types),
        "missing_documents": missing,
        "patterns_found": patterns_found.get("document_types", {}),
        "total_missing": len(missing),
    }


def _consolidate_entities(entities: list[dict]) -> list[dict]:
    """Consolidate duplicate entities."""
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
    """Group entities by their type/label."""
    grouped = {}

    for entity in entities:
        label = entity.get("label", "UNKNOWN")
        if label not in grouped:
            grouped[label] = []
        grouped[label].append(entity.get("text"))

    return grouped


def _identify_key_parties(entities: list[dict]) -> list[dict]:
    """Identify key parties in the case."""
    # Focus on PERSON and ORG entities with high frequency
    person_org = [e for e in entities if e.get("label") in ["PERSON", "ORG"]]

    # Sort by confidence
    person_org.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return person_org[:10]  # Top 10 key parties


def _extract_dates_from_document(document: dict) -> list[dict]:
    """Extract dates and their context from a document."""
    dates = []
    content = document.get("body", "")

    # Simple date extraction
    date_pattern = r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2}, \d{4})\b"

    matches = re.finditer(date_pattern, content)
    for match in matches:
        date_str = match.group()
        context = content[max(0, match.start() - 50) : min(len(content), match.end() + 50)]

        dates.append({
            "date": date_str,
            "type": _classify_date_type(context),
            "description": context.strip(),
            "confidence": 0.8,
        })

    return dates


def _classify_date_type(context: str) -> str:
    """Classify the type of date based on context."""
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


def _identify_milestones(events: list[dict]) -> list[dict]:
    """Identify key milestones in the case timeline."""
    milestones = []

    milestone_types = ["filing_date", "hearing_date", "judgment_date"]

    for event in events:
        if event.get("type") in milestone_types:
            milestones.append(event)

    return milestones


def _calculate_document_similarity(doc1: dict, doc2: dict) -> float:
    """Calculate similarity between two documents (simplified)."""
    try:
        # Simple Jaccard similarity on words
        text1 = doc1.get("body", "")[:500].lower()
        text2 = doc2.get("body", "")[:500].lower()

        if not text1 or not text2:
            return 0.0

        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    except Exception as e:
        logger.warning(f"Error calculating similarity: {e}")
        return 0.0
