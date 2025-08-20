"""
Legal Intelligence Service - Core Module

Integrates entity extraction, timeline generation, knowledge graph,
and Legal BERT embeddings for comprehensive legal case analysis.
"""

from datetime import datetime
from typing import Any

from loguru import logger

# Service imports based on investigation
from knowledge_graph import get_knowledge_graph_service, get_similarity_analyzer
from shared.simple_db import SimpleDB
from entity.main import EntityService
from utilities.timeline.main import TimelineService
from utilities.embeddings import get_embedding_service

# Logger is now imported globally from loguru


class LegalIntelligenceService:
    """
    Unified legal intelligence service for case analysis, timeline generation,
    relationship mapping, and missing document prediction.
    """

    def __init__(self, db_path: str = "data/emails.db"):
        """
        Initialize Legal Intelligence Service with integrated services.
        """
        self.db_path = db_path
        self.db = SimpleDB(db_path)

        # Initialize integrated services
        self.entity_service = EntityService()
        self.timeline_service = TimelineService()
        self.knowledge_graph = get_knowledge_graph_service(db_path)
        self.similarity_analyzer = get_similarity_analyzer(db_path, similarity_threshold=0.7)
        self.embedding_service = get_embedding_service()

        # Cache for analysis results
        self._analysis_cache = {}

        # Standard legal document patterns
        self._legal_doc_patterns = {
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

        logger.info(f"Legal Intelligence Service initialized with database: {db_path}")

    def process_case(self, case_number: str) -> dict[str, Any]:
        """Process a complete legal case, coordinating all analysis components.

        Args:
            case_number: The case identifier (e.g., "24NNCV00555")

        Returns:
            Dict containing comprehensive case analysis results
        """
        logger.info(f"Processing case: {case_number}")

        # Check cache first
        if case_number in self._analysis_cache:
            logger.info(f"Returning cached results for case: {case_number}")
            return self._analysis_cache[case_number]

        try:
            # Get all documents for the case
            case_documents = self._get_case_documents(case_number)

            if not case_documents:
                return {"success": False, "error": f"No documents found for case {case_number}"}

            # Perform comprehensive analysis
            results = {
                "success": True,
                "case_number": case_number,
                "document_count": len(case_documents),
                "documents": case_documents,
                "entities": self._extract_case_entities(case_documents),
                "timeline": self._generate_case_timeline(case_documents),
                "relationships": self._build_case_relationships(case_documents),
                "patterns": self._analyze_document_patterns(case_documents),
                "missing_documents": self.predict_missing_documents(case_number),
                "analysis_timestamp": datetime.now().isoformat(),
            }

            # Cache results
            self._analysis_cache[case_number] = results

            logger.info(
                f"Case processing complete: {case_number} - {len(case_documents)} documents analyzed"
            )
            return results

        except Exception as e:
            logger.error(f"Error processing case {case_number}: {e}")
            return {"success": False, "error": str(e)}

    def analyze_document_patterns(self, case_id: str) -> dict[str, Any]:
        """Analyze document patterns using Legal BERT embeddings to identify
        document types, recurring themes, and anomalies.

        Args:
            case_id: Case identifier

        Returns:
            Dict containing pattern analysis results
        """
        logger.info(f"Analyzing document patterns for case: {case_id}")

        # Check cache
        if case_id in self._analysis_cache:
            cached = self._analysis_cache[case_id].get("patterns")
            if cached:
                return cached

        case_documents = self._get_case_documents(case_id)
        return self._analyze_document_patterns(case_documents)

    def predict_missing_documents(self, case_id: str) -> dict[str, Any]:
        """Predict potentially missing documents based on case type and typical
        legal proceedings patterns.

        Args:
            case_id: Case identifier

        Returns:
            Dict with predicted missing documents and confidence scores
        """
        logger.info(f"Predicting missing documents for case: {case_id}")

        case_documents = self._get_case_documents(case_id)

        if not case_documents:
            return {"success": False, "error": f"No documents found for case {case_id}"}

        # Analyze existing document types
        existing_types = self._identify_document_types(case_documents)

        # Determine case type from documents
        case_type = self._determine_case_type(case_documents)

        # Get expected document sequence for case type
        expected_sequence = self._get_expected_document_sequence(case_type)

        # Find gaps in sequence
        missing = []
        for doc_type in expected_sequence:
            if doc_type not in existing_types:
                confidence = self._calculate_missing_confidence(
                    doc_type, existing_types, case_documents
                )
                if confidence > 0.3:  # Threshold for reporting
                    missing.append(
                        {
                            "document_type": doc_type,
                            "confidence": confidence,
                            "reason": self._get_missing_reason(doc_type, existing_types),
                        }
                    )

        # Sort by confidence
        missing.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "success": True,
            "case_id": case_id,
            "case_type": case_type,
            "existing_documents": list(existing_types),
            "predicted_missing": missing,
            "total_missing": len(missing),
        }

    def generate_case_timeline(self, case_id: str) -> dict[str, Any]:
        """Generate comprehensive timeline of case events, integrating document
        dates, entity mentions, and procedural milestones.

        Args:
            case_id: Case identifier

        Returns:
            Dict containing chronological timeline of case events
        """
        logger.info(f"Generating timeline for case: {case_id}")

        case_documents = self._get_case_documents(case_id)

        if not case_documents:
            return {"success": False, "error": f"No documents found for case {case_id}"}

        return self._generate_case_timeline(case_documents)

    def build_relationship_graph(self, case_id: str) -> dict[str, Any]:
        """Build comprehensive relationship graph showing document connections,
        entity relationships, and case dependencies.

        Args:
            case_id: Case identifier

        Returns:
            Dict containing relationship graph data
        """
        logger.info(f"Building relationship graph for case: {case_id}")

        case_documents = self._get_case_documents(case_id)

        if not case_documents:
            return {"success": False, "error": f"No documents found for case {case_id}"}

        return self._build_case_relationships(case_documents)

    # Private helper methods

    def _get_case_documents(self, case_number: str) -> list[dict[str, Any]]:
        """
        Get all documents related to a case number.
        """
        # Search for documents containing the case number
        search_results = self.db.search_content(case_number, limit=100)

        # Filter to ensure relevance
        case_docs = []
        for doc in search_results:
            # Check if case number is in title or content
            if (
                case_number in doc.get("title", "").upper()
                or case_number in doc.get("content", "").upper()
            ):
                case_docs.append(doc)

        return case_docs

    def _extract_case_entities(self, documents: list[dict]) -> dict[str, Any]:
        """
        Extract and consolidate entities from case documents.
        """
        all_entities = []
        entity_relationships = []

        for doc in documents:
            content = doc.get("content", "")
            if content:
                # Extract entities using the entity service
                # Use extract_email_entities with a dummy message_id
                result = self.entity_service.extract_email_entities(
                    message_id=f"doc_{doc.get('id', 'unknown')}", content=content
                )
                if result.get("success"):
                    entities = result.get("entities", [])
                    all_entities.extend(entities)

                    # Get relationships if available
                    relationships = result.get("relationships", [])
                    entity_relationships.extend(relationships)

        # Consolidate entities by type
        consolidated = self._consolidate_entities(all_entities)

        return {
            "total_entities": len(all_entities),
            "unique_entities": len(consolidated),
            "by_type": self._group_entities_by_type(consolidated),
            "relationships": entity_relationships,
            "key_parties": self._identify_key_parties(consolidated),
        }

    def _generate_case_timeline(self, documents: list[dict]) -> dict[str, Any]:
        """
        Generate timeline from case documents.
        """
        events = []

        for doc in documents:
            # Extract dates from document
            dates = self._extract_dates_from_document(doc)

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

        # Identify timeline gaps
        gaps = self._identify_timeline_gaps(events)

        return {
            "success": True,
            "events": events,
            "total_events": len(events),
            "date_range": {
                "start": events[0]["date"] if events else None,
                "end": events[-1]["date"] if events else None,
            },
            "gaps": gaps,
            "milestones": self._identify_milestones(events),
        }

    def _build_case_relationships(self, documents: list[dict]) -> dict[str, Any]:
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
                    "content_type": doc.get("content_type"),
                    "date": doc.get("datetime_utc"),
                },
            }
            nodes.append(node)

            # Add to knowledge graph
            self.knowledge_graph.add_node(
                content_id=node["id"],
                content_type="legal_document",
                title=node["title"],
                metadata=node["metadata"],
            )

        # Find document similarities and create edges
        for i, doc1 in enumerate(documents):
            for doc2 in documents[i + 1 :]:
                similarity = self._calculate_document_similarity(doc1, doc2)

                if similarity > 0.5:  # Threshold for relationship
                    edge = {
                        "source": doc1.get("content_id"),
                        "target": doc2.get("content_id"),
                        "type": "similar_to",
                        "strength": similarity,
                    }
                    edges.append(edge)

                    # Add to knowledge graph
                    self.knowledge_graph.add_edge(
                        source_content_id=edge["source"],
                        target_content_id=edge["target"],
                        relationship_type=edge["type"],
                        strength=edge["strength"],
                    )

        return {
            "success": True,
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "graph_density": (
                len(edges) / (len(nodes) * (len(nodes) - 1) / 2) if len(nodes) > 1 else 0
            ),
        }

    def _analyze_document_patterns(self, documents: list[dict]) -> dict[str, Any]:
        """
        Analyze patterns in case documents.
        """
        if not documents:
            return {"success": False, "error": "No documents to analyze"}

        # Identify document types
        doc_types = self._identify_document_types(documents)

        # Find recurring themes using embeddings
        themes = self._extract_themes(documents)

        # Detect anomalies
        anomalies = self._detect_anomalies(documents)

        # Analyze document flow
        flow = self._analyze_document_flow(documents)

        return {
            "success": True,
            "document_types": doc_types,
            "themes": themes,
            "anomalies": anomalies,
            "document_flow": flow,
            "pattern_summary": self._summarize_patterns(doc_types, themes, anomalies),
        }

    def _identify_document_types(self, documents: list[dict]) -> set[str]:
        """
        Identify types of legal documents present.
        """
        identified_types = set()

        for doc in documents:
            title = doc.get("title", "").lower()
            content_preview = doc.get("content", "")[:500].lower()

            for doc_type, patterns in self._legal_doc_patterns.items():
                for pattern in patterns:
                    if pattern in title or pattern in content_preview:
                        identified_types.add(doc_type)
                        break

        return identified_types

    def _determine_case_type(self, documents: list[dict]) -> str:
        """
        Determine the type of legal case from documents.
        """
        # Simple heuristic based on document types and content
        doc_types = self._identify_document_types(documents)

        if "complaint" in doc_types:
            # Check for specific case type indicators
            for doc in documents:
                content = doc.get("content", "").lower()
                if "unlawful detainer" in content:
                    return "unlawful_detainer"
                elif "personal injury" in content:
                    return "personal_injury"
                elif "breach of contract" in content:
                    return "contract"
                elif "divorce" in content or "dissolution" in content:
                    return "family_law"

        return "civil_litigation"  # Default

    def _get_expected_document_sequence(self, case_type: str) -> list[str]:
        """
        Get expected document sequence for a case type.
        """
        sequences = {
            "unlawful_detainer": [
                "complaint",
                "summons",
                "answer",
                "motion",
                "order",
                "judgment",
                "notice",
            ],
            "civil_litigation": [
                "complaint",
                "summons",
                "answer",
                "discovery",
                "motion",
                "brief",
                "order",
                "judgment",
            ],
            "contract": [
                "complaint",
                "answer",
                "discovery",
                "motion",
                "brief",
                "settlement",
                "order",
            ],
            "family_law": [
                "petition",
                "response",
                "discovery",
                "motion",
                "order",
                "settlement",
                "judgment",
            ],
        }

        return sequences.get(case_type, sequences["civil_litigation"])

    def _calculate_missing_confidence(
        self, doc_type: str, existing: set[str], documents: list[dict]
    ) -> float:
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
            content = doc.get("content", "").lower()
            if doc_type in content:
                confidence += 0.2
                break

        return min(confidence, 1.0)

    def _get_missing_reason(self, doc_type: str, existing: set[str]) -> str:
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
            "transcript": "Hearing transcripts appear to be missing",
        }

        return reasons.get(doc_type, f"Expected {doc_type} not found in case documents")

    def _consolidate_entities(self, entities: list[dict]) -> list[dict]:
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

    def _group_entities_by_type(self, entities: list[dict]) -> dict[str, list]:
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

    def _identify_key_parties(self, entities: list[dict]) -> list[dict]:
        """
        Identify key parties in the case.
        """
        # Focus on PERSON and ORG entities with high frequency
        person_org = [e for e in entities if e.get("label") in ["PERSON", "ORG"]]

        # Sort by confidence
        person_org.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return person_org[:10]  # Top 10 key parties

    def _extract_dates_from_document(self, document: dict) -> list[dict]:
        """
        Extract dates and their context from a document.
        """
        dates = []
        content = document.get("content", "")

        # Simple date extraction (could be enhanced with regex or NLP)
        import re

        date_pattern = r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\w+ \d{1,2}, \d{4})\b"

        matches = re.finditer(date_pattern, content)
        for match in matches:
            date_str = match.group()
            context = content[max(0, match.start() - 50) : min(len(content), match.end() + 50)]

            dates.append(
                {
                    "date": date_str,
                    "type": self._classify_date_type(context),
                    "description": context.strip(),
                    "confidence": 0.8,
                }
            )

        return dates

    def _classify_date_type(self, context: str) -> str:
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

    def _identify_timeline_gaps(self, events: list[dict]) -> list[dict]:
        """
        Identify significant gaps in the timeline.
        """
        gaps = []

        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]

            # Parse dates (simplified - should use proper date parsing)
            # This is a placeholder - would need proper implementation
            gap_days = 30  # Placeholder

            if gap_days > 60:  # Significant gap
                gaps.append(
                    {
                        "start": current["date"],
                        "end": next_event["date"],
                        "duration_days": gap_days,
                        "significance": "high" if gap_days > 120 else "medium",
                    }
                )

        return gaps

    def _identify_milestones(self, events: list[dict]) -> list[dict]:
        """
        Identify key milestones in the case timeline.
        """
        milestones = []

        milestone_types = ["filing_date", "hearing_date", "judgment_date"]

        for event in events:
            if event.get("type") in milestone_types:
                milestones.append(event)

        return milestones

    def _calculate_document_similarity(self, doc1: dict, doc2: dict) -> float:
        """
        Calculate similarity between two documents using Legal BERT.
        """
        try:
            # Get embeddings
            text1 = doc1.get("content", "")[:2000]  # Limit for performance
            text2 = doc2.get("content", "")[:2000]

            if not text1 or not text2:
                return 0.0

            embedding1 = self.embedding_service.encode(text1)
            embedding2 = self.embedding_service.encode(text2)

            # Cosine similarity
            import numpy as np

            similarity = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            )

            return float(similarity)

        except Exception as e:
            logger.warning(f"Error calculating similarity: {e}")
            return 0.0

    def _extract_themes(self, documents: list[dict]) -> list[dict]:
        """
        Extract recurring themes from documents.
        """
        # Simplified theme extraction
        themes = []

        # Would implement more sophisticated theme extraction
        # using clustering on Legal BERT embeddings

        common_themes = {
            "procedural": ["motion", "hearing", "order", "filed"],
            "parties": ["plaintiff", "defendant", "petitioner", "respondent"],
            "claims": ["breach", "damage", "injury", "violation"],
            "relief": ["judgment", "settlement", "dismissal", "award"],
        }

        for theme_name, keywords in common_themes.items():
            count = 0
            for doc in documents:
                content = doc.get("content", "").lower()
                for keyword in keywords:
                    if keyword in content:
                        count += 1
                        break

            if count > 0:
                themes.append(
                    {
                        "theme": theme_name,
                        "prevalence": count / len(documents),
                        "document_count": count,
                    }
                )

        return themes

    def _detect_anomalies(self, documents: list[dict]) -> list[dict]:
        """
        Detect anomalies in document patterns.
        """
        anomalies = []

        # Check for unusual gaps, duplicates, or outliers
        # Simplified implementation

        # Check for duplicate-looking documents
        for i, doc1 in enumerate(documents):
            for j, doc2 in enumerate(documents[i + 1 :], i + 1):
                similarity = self._calculate_document_similarity(doc1, doc2)
                if similarity > 0.95:
                    anomalies.append(
                        {
                            "type": "potential_duplicate",
                            "documents": [doc1.get("title"), doc2.get("title")],
                            "confidence": similarity,
                        }
                    )

        return anomalies

    def _analyze_document_flow(self, documents: list[dict]) -> dict[str, Any]:
        """
        Analyze the flow and progression of documents.
        """
        # Sort documents by date if available
        sorted_docs = sorted(documents, key=lambda x: x.get("datetime_utc", ""))

        flow = {
            "total_documents": len(sorted_docs),
            "date_range": {
                "start": sorted_docs[0].get("datetime_utc") if sorted_docs else None,
                "end": sorted_docs[-1].get("datetime_utc") if sorted_docs else None,
            },
            "document_sequence": [
                {
                    "title": doc.get("title"),
                    "type": self._identify_single_doc_type(doc),
                    "date": doc.get("datetime_utc"),
                }
                for doc in sorted_docs
            ],
        }

        return flow

    def _identify_single_doc_type(self, document: dict) -> str:
        """
        Identify the type of a single document.
        """
        title = document.get("title", "").lower()

        for doc_type, patterns in self._legal_doc_patterns.items():
            for pattern in patterns:
                if pattern in title:
                    return doc_type

        return "unknown"

    def _summarize_patterns(
        self, doc_types: set[str], themes: list[dict], anomalies: list[dict]
    ) -> str:
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


def get_legal_intelligence_service(db_path: str = "emails.db") -> LegalIntelligenceService:
    """Factory function to create LegalIntelligenceService instance.
    
    Args:
        db_path: Path to the database file
        
    Returns:
        LegalIntelligenceService instance
    """
    return LegalIntelligenceService(db_path)
