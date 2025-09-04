"""Test fixtures for MCP server testing.

Provides reusable test data and mock configurations.
"""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

# Ensure project imports work
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def mock_search_service():
    """
    Mock SearchIntelligenceService with common test data.
    """
    service = Mock()

    # Default search results
    service.smart_search_with_preprocessing.return_value = [
        {
            "id": "1",
            "title": "Legal Document Test",
            "content": "This is a legal document about contracts and agreements.",
            "source_type": "email",
            "semantic_score": 0.95,
            "created_time": "2024-08-22T10:00:00",
        },
        {
            "id": "2",
            "title": "Contract Analysis",
            "content": "Analysis of contract terms and legal obligations.",
            "source_type": "pdf",
            "semantic_score": 0.87,
            "created_time": "2024-08-21T15:30:00",
        },
    ]

    # Query expansion
    service._expand_query.return_value = ["law", "judicial"]

    # Entity extraction
    service.extract_and_cache_entities.return_value = [
        {"text": "John Doe", "label": "PERSON", "confidence": 0.95},
        {"text": "24NNCV06082", "label": "CASE_NUMBER", "confidence": 0.90},
        {"text": "2024-08-22", "label": "DATE", "confidence": 0.85},
    ]

    # Document similarity
    service.analyze_document_similarity.return_value = [
        {
            "content_id": "similar_1",
            "title": "Similar Legal Document",
            "similarity_score": 0.88,
            "content_type": "email",
            "created_time": "2024-08-20T12:00:00",
        }
    ]

    # Clustering
    service.cluster_similar_content.return_value = [
        {
            "cluster_id": 0,
            "size": 3,
            "documents": [
                {"content_id": "doc_1", "title": "Doc 1", "content_type": "email"},
                {"content_id": "doc_2", "title": "Doc 2", "content_type": "email"},
                {"content_id": "doc_3", "title": "Doc 3", "content_type": "pdf"},
            ],
            "average_similarity": 0.82,
        }
    ]

    # Duplicate detection
    service.detect_duplicates.return_value = [
        {
            "type": "exact",
            "hash": "abc12345",
            "count": 2,
            "documents": [
                {
                    "content_id": "dup_1",
                    "title": "Duplicate 1",
                    "created_time": "2024-08-22T09:00:00",
                },
                {
                    "content_id": "dup_2",
                    "title": "Duplicate 2",
                    "created_time": "2024-08-22T10:00:00",
                },
            ],
        }
    ]

    return service


@pytest.fixture
def mock_legal_service():
    """
    Mock LegalIntelligenceService with common test data.
    """
    service = Mock()

    # Entity extraction
    service.extract_legal_entities.return_value = {
        "entities": [
            {"text": "Jennifer Burbank", "label": "PERSON", "confidence": 0.95},
            {"text": "24NNCV06082", "label": "CASE_NUMBER", "confidence": 0.90},
            {"text": "Notice to Enter", "label": "DOCUMENT_TYPE", "confidence": 0.85},
        ]
    }

    # Timeline generation
    service.generate_case_timeline.return_value = {
        "events": [
            {
                "date": "2024-06-08",
                "event": "Case filed",
                "document_id": "doc_123",
                "importance": "high",
                "source": "Court filing",
            },
            {
                "date": "2024-06-15",
                "event": "Notice to Enter sent",
                "document_id": "doc_124",
                "importance": "medium",
                "source": "Email",
            },
        ],
        "gaps": [
            {
                "start_date": "2024-06-16",
                "end_date": "2024-07-01",
                "gap_days": 15,
                "significance": "potential missing communications",
            }
        ],
        "summary": "Timeline contains 2 events with 1 gap",
    }

    # Knowledge graph
    service.build_relationship_graph.return_value = {
        "nodes": [
            {"id": "doc_1", "title": "Legal Notice", "type": "document"},
            {"id": "doc_2", "title": "Response Letter", "type": "document"},
            {"id": "person_1", "title": "Jennifer Burbank", "type": "person"},
        ],
        "edges": [
            {"source": "doc_1", "target": "doc_2", "weight": 0.8, "type": "references"},
            {"source": "person_1", "target": "doc_1", "weight": 0.9, "type": "authored"},
        ],
        "stats": {"node_count": 3, "edge_count": 2, "density": 0.67},
    }

    # Document analysis
    service.process_case.return_value = {
        "case_number": "24NNCV06082",
        "document_count": 27,
        "entities_extracted": 156,
        "patterns_detected": [
            "Repeated notice violations",
            "Email thread escalation",
            "Legal deadline proximity",
        ],
        "risk_assessment": "medium",
        "key_findings": [
            "Multiple failed contact attempts",
            "Escalating tenant disputes",
            "Potential harassment pattern",
        ],
    }

    # Case tracking
    service.track_case_status.return_value = {
        "case_number": "24NNCV06082",
        "status": "active",
        "next_deadline": "2024-09-15",
        "days_until_deadline": 24,
        "required_actions": [
            "File response to motion",
            "Gather additional evidence",
            "Schedule mediation",
        ],
        "completion_percentage": 65,
    }

    # Relationship discovery
    service.discover_relationships.return_value = {
        "entity_relationships": [
            {
                "entity1": "Jennifer Burbank",
                "entity2": "518 Stoneman St",
                "relationship": "tenant_at",
                "confidence": 0.95,
                "evidence_count": 8,
            }
        ],
        "document_clusters": [
            {
                "cluster_id": "communication_thread",
                "documents": ["doc_1", "doc_2", "doc_3"],
                "theme": "Notice violations",
            }
        ],
        "timeline_patterns": [
            {"pattern": "escalation", "frequency": "weekly", "significance": "high"}
        ],
    }

    return service


@pytest.fixture
def mock_simple_db():
    """
    Mock SimpleDB with test data.
    """
    db = Mock()

    # Content retrieval
    db.get_content.return_value = {
        "id": "test_doc_123",
        "title": "Test Legal Document",
        "body": "This is a test legal document containing contract terms and legal language.",
        "source_type": "email",
        "created_at": "2024-08-22T10:00:00",
        "sha256": "abc123def456",
    }

    # Search results
    db.search_content.return_value = [
        {
            "id": "search_result_1",
            "title": "Search Result 1",
            "body": "Content matching search query",
            "source_type": "email",
            "created_at": "2024-08-22T09:00:00",
        }
    ]

    # Fetch results (for direct SQL queries)
    db.fetch.return_value = [
        {
            "id": "fetch_result_1",
            "title": "Fetch Result 1",
            "body": "Content from direct SQL query",
            "source_type": "pdf",
            "created_at": "2024-08-22T08:00:00",
        }
    ]

    return db


@pytest.fixture
def mock_document_summarizer():
    """
    Mock DocumentSummarizer with test data.
    """
    summarizer = Mock()

    summarizer.extract_summary.return_value = {
        "sentences": [
            "This document contains important legal information.",
            "The contract specifies terms and conditions.",
            "All parties must comply with stated obligations.",
        ],
        "keywords": {
            "legal": 0.95,
            "contract": 0.87,
            "terms": 0.82,
            "obligations": 0.78,
            "parties": 0.71,
        },
        "method": "combined",
        "word_count": 150,
        "summary_text": "Legal document outlining contract terms and party obligations.",
    }

    return summarizer


# Test data constants
TEST_CASE_NUMBERS = ["24NNCV06082", "23CV12345", "24NNCV99999"]

TEST_DOCUMENTS = [
    {
        "id": "doc_1",
        "title": "Notice to Enter Dwelling Unit",
        "content": "Legal notice regarding property access for inspection purposes.",
        "source_type": "email",
        "case_number": "24NNCV06082",
    },
    {
        "id": "doc_2",
        "title": "Response to Notice",
        "content": "Tenant response expressing concerns about notice validity.",
        "source_type": "email",
        "case_number": "24NNCV06082",
    },
    {
        "id": "doc_3",
        "title": "Court Filing Motion",
        "content": "Motion filed with court regarding tenant dispute.",
        "source_type": "pdf",
        "case_number": "24NNCV06082",
    },
]

TEST_ENTITIES = [
    {"text": "Jennifer Burbank", "label": "PERSON", "confidence": 0.95},
    {"text": "518 Stoneman Street", "label": "ADDRESS", "confidence": 0.90},
    {"text": "24NNCV06082", "label": "CASE_NUMBER", "confidence": 0.88},
    {"text": "Notice to Enter", "label": "DOCUMENT_TYPE", "confidence": 0.85},
    {"text": "2024-06-08", "label": "DATE", "confidence": 0.82},
]

TEST_QUERY_EXPANSIONS = {
    "legal": ["law", "judicial"],
    "contract": ["agreement", "deal"],
    "attorney": ["lawyer", "counsel"],
    "case": ["matter", "lawsuit"],
}
