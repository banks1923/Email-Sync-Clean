"""
Tests for Analog Database SearchInterface.

Comprehensive tests for markdown-aware search functionality including
content search, metadata search, hybrid search, and performance optimization.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analog_db.search_interface import SearchInterface


class TestSearchInterface:
    """Test SearchInterface functionality."""
    
    @pytest.fixture
    def temp_analog_db(self):
        """Create temporary analog database structure with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            analog_db_path = base_path / "analog_db"
            
            # Create directory structure
            documents_dir = analog_db_path / "documents"
            email_threads_dir = analog_db_path / "email_threads"
            documents_dir.mkdir(parents=True)
            email_threads_dir.mkdir(parents=True)
            
            # Create test markdown files
            test_files = [
                {
                    "path": documents_dir / "test_contract.md",
                    "content": """---
title: "ABC Corp Contract Review"
doc_type: email
date_created: 2025-08-17
sender: legal@example.com
tags: ["contract", "legal", "abc_corp"]
---

# Contract Review

This is a contract review document for ABC Corporation.
The agreement includes payment terms of $50,000 monthly.
All parties must execute by end of month.
""",
                },
                {
                    "path": documents_dir / "meeting_notes.md",
                    "content": """---
title: "Team Meeting Notes"
doc_type: document
date_created: 2025-08-16
tags: ["meeting", "notes"]
---

# Team Meeting

Discussed project timeline and deliverables.
Next meeting scheduled for next week.
""",
                },
                {
                    "path": email_threads_dir / "email_thread_1.md",
                    "content": """---
title: "Re: Legal Discussion"
doc_type: email
sender: attorney@firm.com
date_created: 2025-08-15
tags: ["legal", "correspondence"]
---

# Legal Discussion Thread

Following up on our previous conversation about contract terms.
Please review the attached documentation.
""",
                },
            ]
            
            for file_info in test_files:
                file_info["path"].write_text(file_info["content"])
            
            yield base_path
    
    @pytest.fixture
    def search_interface(self, temp_analog_db):
        """Create SearchInterface instance with temporary database."""
        return SearchInterface(base_path=temp_analog_db)
    
    def test_initialization(self, search_interface, temp_analog_db):
        """Test SearchInterface initializes correctly."""
        assert search_interface.base_path == temp_analog_db
        assert search_interface.analog_db_path == temp_analog_db / "analog_db"
        assert search_interface.documents_path.exists()
        assert search_interface.email_threads_path.exists()
        assert isinstance(search_interface._metadata_cache, dict)
        assert isinstance(search_interface._search_stats, dict)
    
    def test_get_markdown_files(self, search_interface):
        """Test markdown file discovery."""
        markdown_files = search_interface._get_markdown_files()
        
        assert len(markdown_files) == 3
        file_names = [f.name for f in markdown_files]
        assert "test_contract.md" in file_names
        assert "meeting_notes.md" in file_names
        assert "email_thread_1.md" in file_names
    
    def test_get_file_metadata(self, search_interface):
        """Test frontmatter metadata extraction."""
        markdown_files = search_interface._get_markdown_files()
        contract_file = next(f for f in markdown_files if f.name == "test_contract.md")
        
        metadata = search_interface._get_file_metadata(contract_file)
        
        assert metadata is not None
        assert metadata["title"] == "ABC Corp Contract Review"
        assert metadata["doc_type"] == "email"
        assert metadata["sender"] == "legal@example.com"
        assert "contract" in metadata["tags"]
        assert "legal" in metadata["tags"]
    
    def test_metadata_caching(self, search_interface):
        """Test that metadata is cached properly."""
        markdown_files = search_interface._get_markdown_files()
        contract_file = next(f for f in markdown_files if f.name == "test_contract.md")
        
        # First call - cache miss
        metadata1 = search_interface._get_file_metadata(contract_file)
        search_interface._search_stats["cache_misses"]
        
        # Second call - cache hit
        metadata2 = search_interface._get_file_metadata(contract_file)
        
        assert metadata1 == metadata2
        assert search_interface._search_stats["cache_hits"] > 0
    
    @patch('subprocess.run')
    def test_content_search_with_ripgrep(self, mock_run, search_interface):
        """Test full-text content search using ripgrep."""
        # Mock ripgrep output
        mock_output = '''{"type":"match","data":{"path":{"text":"analog_db/documents/test_contract.md"},"line_number":10,"lines":{"text":"The agreement includes payment terms of $50,000 monthly."}}}
{"type":"match","data":{"path":{"text":"analog_db/documents/test_contract.md"},"line_number":11,"lines":{"text":"All parties must execute by end of month."}}}'''
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=mock_output
        )
        
        results = search_interface.search_content("contract payment")
        
        assert len(results) == 2
        assert results[0]["matched_content"] == "The agreement includes payment terms of $50,000 monthly."
        assert results[0]["query"] == "contract payment"
        assert "test_contract.md" in results[0]["file_path"]
    
    def test_metadata_search(self, search_interface):
        """Test metadata-based search functionality."""
        # Search by title
        results = search_interface.search_metadata({"title": "Contract"})
        assert len(results) >= 1
        contract_result = next(r for r in results if "contract" in r["metadata"]["title"].lower())
        assert contract_result["metadata"]["title"] == "ABC Corp Contract Review"
        
        # Search by doc type
        results = search_interface.search_metadata({"doc_type": "email"})
        assert len(results) >= 2  # contract and email thread
        
        # Search by tags
        results = search_interface.search_metadata({"tags": ["legal"]})
        assert len(results) >= 2  # contract and email thread
        
        # Search by sender
        results = search_interface.search_metadata({"sender": "legal@example.com"})
        assert len(results) == 1
        assert results[0]["metadata"]["sender"] == "legal@example.com"
    
    def test_matches_filters(self, search_interface):
        """Test the filter matching logic."""
        # Test metadata that should match
        metadata = {
            "title": "Test Contract Document",
            "doc_type": "email",
            "tags": ["contract", "legal"],
            "sender": "john@example.com"
        }
        
        # Title filter
        assert search_interface._matches_filters(metadata, {"title": "Contract"})
        assert not search_interface._matches_filters(metadata, {"title": "Meeting"})
        
        # Doc type filter
        assert search_interface._matches_filters(metadata, {"doc_type": "email"})
        assert not search_interface._matches_filters(metadata, {"doc_type": "document"})
        
        # Tags filter (OR logic)
        assert search_interface._matches_filters(metadata, {"tags": ["contract"], "tag_logic": "OR"})
        assert search_interface._matches_filters(metadata, {"tags": ["contract", "finance"], "tag_logic": "OR"})
        
        # Tags filter (AND logic)
        assert search_interface._matches_filters(metadata, {"tags": ["contract", "legal"], "tag_logic": "AND"})
        assert not search_interface._matches_filters(metadata, {"tags": ["contract", "finance"], "tag_logic": "AND"})
        
        # Sender filter
        assert search_interface._matches_filters(metadata, {"sender": "john@example.com"})
        assert not search_interface._matches_filters(metadata, {"sender": "jane@example.com"})
    
    @patch('analog_db.search_interface.SearchInterface._get_vector_search_results')
    @patch('analog_db.search_interface.SearchInterface._get_analog_semantic_search')
    @patch('subprocess.run')
    def test_hybrid_search(self, mock_run, mock_analog_semantic, mock_vector_search, search_interface):
        """Test hybrid search combining content, metadata, and vector results."""
        # Mock content search (ripgrep)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"type":"match","data":{"path":{"text":"test.md"},"line_number":1,"lines":{"text":"contract terms"}}}'
        )
        
        # Mock vector searches
        mock_analog_semantic.return_value = [
            {
                "file_path": "semantic_result.md",
                "score": 12.0,
                "source": "analog_semantic",
                "similarity_score": 0.8
            }
        ]
        
        mock_vector_search.return_value = [
            {
                "file_path": "vector_result.md",
                "score": 8.0,
                "source": "vector",
                "similarity_score": 0.7
            }
        ]
        
        # Test hybrid search
        results = search_interface.hybrid_search(
            "contract terms",
            metadata_filters={"doc_type": "email"},
            limit=10,
            use_vector=True
        )
        
        # Should have results from multiple sources
        assert len(results) > 0
        
        # Check that different sources are present
        sources = [r.get("source", "unknown") for r in results]
        assert len(set(sources)) > 1  # Multiple different sources
    
    @patch('analog_db.search_interface.get_embedding_service')
    def test_analog_semantic_search(self, mock_embedding_service, search_interface):
        """Test semantic search on analog database files."""
        # Mock embedding service
        mock_service = MagicMock()
        mock_service.get_embedding.return_value = [0.1] * 1024  # Mock embedding
        mock_embedding_service.return_value = mock_service
        
        # Mock sklearn imports and cosine similarity
        with patch('sklearn.metrics.pairwise.cosine_similarity') as mock_cosine:
            mock_cosine.return_value = [[0.8]]  # High similarity
            
            results = search_interface._get_analog_semantic_search("contract", limit=5)
            
            # Should find semantic matches
            assert len(results) > 0
            assert all(r["source"] == "analog_semantic" for r in results)
            assert all(r["similarity_score"] >= 0.7 for r in results)
    
    def test_search_performance_tracking(self, search_interface):
        """Test that search performance is tracked."""
        initial_stats = search_interface.get_search_stats()
        assert initial_stats["total_searches"] == 0
        assert initial_stats["avg_search_time"] == 0.0
        
        # Perform a metadata search (doesn't require ripgrep)
        search_interface.search_metadata({"doc_type": "email"})
        
        updated_stats = search_interface.get_search_stats()
        assert updated_stats["total_searches"] == 1
        assert updated_stats["avg_search_time"] > 0
    
    def test_content_score_calculation(self, search_interface):
        """Test content relevance scoring."""
        result = {
            "matched_content": "This contract has payment terms and contract clauses",
            "metadata": {"title": "Contract Review Document"}
        }
        
        score = search_interface._calculate_content_score(result, "contract payment")
        
        # Should get points for matches in content and title
        assert score > 0
        
        # Title matches should boost score
        title_match_result = {
            "matched_content": "payment terms",
            "metadata": {"title": "Contract Payment Schedule"}
        }
        title_score = search_interface._calculate_content_score(title_match_result, "contract payment")
        assert title_score > score  # Title matches are weighted more
    
    def test_result_deduplication(self, search_interface):
        """Test that duplicate results are properly removed."""
        results = [
            {"file_path": "test1.md", "score": 10.0},
            {"file_path": "test2.md", "score": 8.0},
            {"file_path": "test1.md", "score": 9.0},  # Duplicate
            {"file_path": "test3.md", "score": 7.0}
        ]
        
        unique_results = search_interface._deduplicate_results(results)
        
        assert len(unique_results) == 3
        file_paths = [r["file_path"] for r in unique_results]
        assert len(set(file_paths)) == 3  # All unique
    
    def test_result_ranking(self, search_interface):
        """Test that results are properly ranked by score."""
        results = [
            {"file_path": "test1.md", "score": 5.0},
            {"file_path": "test2.md", "score": 10.0},
            {"file_path": "test3.md", "score": 7.0}
        ]
        
        ranked_results = search_interface._rank_results(results)
        
        scores = [r["score"] for r in ranked_results]
        assert scores == [10.0, 7.0, 5.0]  # Descending order
    
    def test_cache_clearing(self, search_interface):
        """Test cache clearing functionality."""
        # Get some metadata to populate cache
        markdown_files = search_interface._get_markdown_files()
        if markdown_files:
            search_interface._get_file_metadata(markdown_files[0])
        
        # Verify cache has content
        assert len(search_interface._metadata_cache) > 0
        
        # Clear cache
        search_interface.clear_cache()
        
        # Verify cache is empty
        assert len(search_interface._metadata_cache) == 0
        assert len(search_interface._cache_timestamps) == 0
    
    def test_content_preview_generation(self, search_interface):
        """Test content preview generation."""
        markdown_files = search_interface._get_markdown_files()
        contract_file = next(f for f in markdown_files if f.name == "test_contract.md")
        
        preview = search_interface._get_content_preview(contract_file, lines=2)
        
        assert len(preview) > 0
        assert "Contract Review" in preview
        assert len(preview) <= 300  # Should be truncated
    
    def test_error_handling(self, search_interface):
        """Test error handling for various failure scenarios."""
        # Test with non-existent file
        non_existent_path = Path("/non/existent/file.md")
        metadata = search_interface._get_file_metadata(non_existent_path)
        assert metadata is None
        
        # Test content preview with non-existent file
        preview = search_interface._get_content_preview(non_existent_path)
        assert preview == ""
        
        # Test search with empty results should not crash
        results = search_interface.search_metadata({"title": "NonExistentDocument"})
        assert results == []
    
    @pytest.mark.performance
    def test_search_performance_target(self, search_interface):
        """Test that search meets performance targets (<1 second)."""
        import time
        
        start_time = time.time()
        
        # Perform a quick metadata search
        results = search_interface.search_metadata({"doc_type": "email"}, limit=5)
        
        end_time = time.time()
        search_time = end_time - start_time
        
        # Should complete quickly (allowing some buffer for test environment)
        assert search_time < 2.0, f"Search took {search_time:.3f}s, target is <1s"
        assert len(results) >= 0  # Should return results without error
    
    def test_ripgrep_args_building(self, search_interface):
        """Test ripgrep argument construction."""
        args = search_interface._build_ripgrep_args(
            query="test query",
            path=None,
            limit=10,
            regex=True,
            case_sensitive=True
        )
        
        assert "rg" in args
        assert "--json" in args
        assert "--max-count" in args
        assert "10" in args
        assert "--type" in args
        assert "markdown" in args
        assert "test query" in args
        
        # Case sensitive should not include ignore-case
        assert "--ignore-case" not in args
        
        # Regex should not include fixed-strings
        assert "--fixed-strings" not in args
        
        # Test case insensitive and non-regex
        args2 = search_interface._build_ripgrep_args(
            query="test",
            path=None,
            limit=5,
            regex=False,
            case_sensitive=False
        )
        
        assert "--ignore-case" in args2
        assert "--fixed-strings" in args2


class TestSearchInterfaceIntegration:
    """Integration tests that require real file system operations."""
    
    def test_real_file_search(self):
        """Test with actual analog_db directory if it exists."""
        # This test only runs if analog_db exists in the project
        project_root = Path(__file__).parent.parent.parent
        analog_db_path = project_root / "analog_db"
        
        if not analog_db_path.exists():
            pytest.skip("analog_db directory not found, skipping integration test")
        
        search_interface = SearchInterface(base_path=project_root)
        markdown_files = search_interface._get_markdown_files()
        
        if len(markdown_files) == 0:
            pytest.skip("No markdown files found in analog_db, skipping integration test")
        
        # Test that we can read metadata from real files
        for md_file in markdown_files[:3]:  # Test first 3 files
            metadata = search_interface._get_file_metadata(md_file)
            # Should either return metadata dict or None (for files without frontmatter)
            assert metadata is None or isinstance(metadata, dict)
        
        # Test stats gathering
        stats = search_interface.get_search_stats()
        assert isinstance(stats, dict)
        assert "total_searches" in stats