#!/usr/bin/env python3
"""
Legal Intelligence CLI Handler
Provides CLI commands for legal case analysis, timeline generation,
relationship mapping, and document intelligence.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from loguru import logger

from legal_intelligence.main import get_legal_intelligence_service

# Logger is now imported globally from loguru


def process_legal_case(case_id: str, output_format: str = "text") -> None:
    """
    Process a legal case and extract comprehensive intelligence.

    Args:
        case_id: Case identifier or search pattern
        output_format: Output format (text/json)
    """
    print(f"🏛️ Processing legal case: {case_id}")

    try:
        service = LegalIntelligenceService()
        result = service.process_case(case_id)

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
    """
    Generate a chronological timeline for a legal case.

    Args:
        case_id: Case identifier or search pattern
        output_file: Optional file path to save timeline
    """
    print(f"📅 Generating timeline for case: {case_id}")

    try:
        service = LegalIntelligenceService()
        timeline = service.generate_case_timeline(case_id)

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
    """
    Build and display a relationship graph for a legal case.

    Args:
        case_id: Case identifier or search pattern
        max_depth: Maximum depth for relationship traversal (currently unused by service)
    """
    print(f"🕸️ Building relationship graph for case: {case_id}")

    try:
        service = LegalIntelligenceService()
        # Note: max_depth is not currently used by the service
        graph = service.build_relationship_graph(case_id)

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
    """
    Perform legal-specific search with entity awareness.

    Args:
        query: Search query
        case_id: Optional case filter
        limit: Number of results to return
    """
    print(f"🔍 Legal Search: '{query}'")
    if case_id:
        print(f"   Filtered to case: {case_id}")

    try:
        service = LegalIntelligenceService()

        # Build search context
        filters = {}
        if case_id:
            filters["case_id"] = case_id

        # Use analyze_document_patterns for search
        # This is a workaround since there's no direct search method
        from shared.simple_db import SimpleDB

        db = SimpleDB()

        # Search with filters
        results = db.search_content(query, limit=limit)

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
                entity_result = service.entity_service.extract_email_entities(
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
    """
    Predict potentially missing documents in a legal case.

    Args:
        case_id: Case identifier or search pattern
        confidence_threshold: Minimum confidence for predictions
    """
    print(f"🔮 Predicting missing documents for case: {case_id}")

    try:
        service = LegalIntelligenceService()
        predictions = service.predict_missing_documents(case_id)

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
    """
    Generate summaries for legal documents in a case.

    Args:
        case_id: Case identifier or search pattern
        max_docs: Maximum number of documents to summarize
    """
    print(f"📝 Summarizing legal documents for case: {case_id}")

    try:
        service = LegalIntelligenceService()

        # Get case documents
        from shared.simple_db import SimpleDB

        db = SimpleDB()

        # Search for case documents
        results = db.search_content(case_id, limit=max_docs)

        if not results:
            print("❌ No documents found for this case")
            return

        print(f"\n📚 Summarizing {len(results)} documents")
        print("=" * 60)

        from summarization import get_document_summarizer

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
                entity_result = service.entity_service.extract_email_entities(
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
