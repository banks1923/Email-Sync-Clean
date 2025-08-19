"""Comprehensive tests for snippet utilities."""

import pytest

from shared.snippet_utils import (
    _calculate_snippet_score,
    extract_snippet,
    format_search_result,
    get_cached_snippet,
    highlight_keywords,
    rank_snippets,
)


class TestExtractSnippet:
    """Test snippet extraction functionality."""
    
    def test_extract_snippet_basic(self):
        """Test basic snippet extraction."""
        text = "The quick brown fox jumps over the lazy dog. This is a test sentence."
        query = "fox"
        snippet = extract_snippet(text, query, window_size=30)
        
        assert "fox" in snippet
        assert len(snippet) <= 60  # Window on both sides
        
    def test_extract_snippet_empty_text(self):
        """Test snippet extraction with empty text."""
        snippet = extract_snippet("", "query", window_size=50)
        assert snippet == ""
        
    def test_extract_snippet_empty_query(self):
        """Test snippet extraction with empty query."""
        text = "This is some text content."
        snippet = extract_snippet(text, "", window_size=20)
        assert snippet == "This is some text co"
        
    def test_extract_snippet_short_text(self):
        """Test snippet extraction with text shorter than window."""
        text = "Short text"
        snippet = extract_snippet(text, "text", window_size=50)
        assert snippet == "Short text"
        
    def test_extract_snippet_multiple_matches(self):
        """Test snippet extraction with multiple query matches."""
        text = "Python is great. I love Python programming. Python is versatile."
        snippet = extract_snippet(text, "Python", window_size=40)
        
        # Should get first match
        assert "Python" in snippet
        assert snippet.startswith("Python is great")
        
    def test_extract_snippet_case_insensitive(self):
        """Test case-insensitive snippet extraction."""
        text = "The QUICK brown FOX jumps over the lazy dog."
        snippet = extract_snippet(text, "quick fox", window_size=30)
        
        assert "QUICK" in snippet or "FOX" in snippet
        
    def test_extract_snippet_with_ellipsis(self):
        """Test snippet with ellipsis for truncated text."""
        text = "Start " + "word " * 50 + " end"
        snippet = extract_snippet(text, "word", window_size=20)
        
        # Should have ellipsis since text is truncated
        assert "..." in snippet
        
    def test_extract_snippet_no_match(self):
        """Test snippet when query not found."""
        text = "This is a sample text without the search term."
        snippet = extract_snippet(text, "missing", window_size=30)
        
        # Should return beginning of text
        assert snippet.startswith("This is a sample")
        
    def test_extract_snippet_whitespace_normalization(self):
        """Test snippet with normalized whitespace."""
        text = "This    has     extra     spaces     between     words."
        snippet = extract_snippet(text, "extra", window_size=30)
        
        # Whitespace should be normalized
        assert "  " not in snippet
        assert "extra spaces" in snippet
        
    def test_extract_snippet_skip_short_terms(self):
        """Test that very short query terms are skipped."""
        text = "The quick brown fox jumps over the lazy dog."
        snippet = extract_snippet(text, "a", window_size=30)
        
        # Should return beginning since single char is skipped
        assert snippet.startswith("The quick brown")


class TestHighlightKeywords:
    """Test keyword highlighting functionality."""
    
    def test_highlight_keywords_ansi(self):
        """Test highlighting with ANSI color codes."""
        text = "The quick brown fox"
        highlighted = highlight_keywords(text, "quick", use_ansi=True)
        
        assert "\033[93m\033[1m" in highlighted  # Yellow bold
        assert "\033[0m" in highlighted  # Reset
        assert "quick" in highlighted
        
    def test_highlight_keywords_brackets(self):
        """Test highlighting with brackets."""
        text = "The quick brown fox"
        highlighted = highlight_keywords(text, "quick", use_ansi=False)
        
        assert "[quick]" in highlighted
        
    def test_highlight_multiple_keywords(self):
        """Test highlighting multiple keywords."""
        text = "The quick brown fox jumps"
        highlighted = highlight_keywords(text, "quick fox", use_ansi=False)
        
        assert "[quick]" in highlighted
        assert "[fox]" in highlighted
        
    def test_highlight_case_insensitive(self):
        """Test case-insensitive highlighting."""
        text = "The QUICK brown FOX"
        highlighted = highlight_keywords(text, "quick fox", use_ansi=False)
        
        assert "[QUICK]" in highlighted
        assert "[FOX]" in highlighted
        
    def test_highlight_empty_text(self):
        """Test highlighting with empty text."""
        highlighted = highlight_keywords("", "query")
        assert highlighted == ""
        
    def test_highlight_empty_query(self):
        """Test highlighting with empty query."""
        text = "Some text"
        highlighted = highlight_keywords(text, "")
        assert highlighted == text
        
    def test_highlight_word_boundaries(self):
        """Test highlighting respects word boundaries."""
        text = "The quickly quick quickest"
        highlighted = highlight_keywords(text, "quick", use_ansi=False)
        
        # Should only highlight the exact word "quick"
        assert "[quick]" in highlighted
        assert "quickly" in highlighted  # Not highlighted
        assert "quickest" in highlighted  # Not highlighted
        
    def test_highlight_special_characters(self):
        """Test highlighting with special regex characters."""
        text = "Price is $10.50 (plus tax)"
        highlighted = highlight_keywords(text, "$10.50", use_ansi=False)
        
        # Special characters should be escaped
        assert "[$10.50]" in highlighted
        
    def test_highlight_skip_short_terms(self):
        """Test that single character terms are skipped."""
        text = "A quick brown fox"
        highlighted = highlight_keywords(text, "a", use_ansi=False)
        
        # Single char should be skipped
        assert highlighted == text


class TestRankSnippets:
    """Test snippet ranking functionality."""
    
    def test_rank_snippets_basic(self):
        """Test basic snippet ranking."""
        snippets = [
            "Python programming is fun",
            "Java programming tutorial",
            "Python is the best language"
        ]
        
        ranked = rank_snippets(snippets, "Python")
        
        assert len(ranked) == 3
        # Python snippets should rank higher
        assert "Python" in ranked[0][0]
        assert ranked[0][1] > ranked[-1][1]  # First has higher score than last
        
    def test_rank_snippets_empty_list(self):
        """Test ranking empty snippet list."""
        ranked = rank_snippets([], "query")
        assert ranked == []
        
    def test_rank_snippets_empty_query(self):
        """Test ranking with empty query."""
        snippets = ["Text 1", "Text 2"]
        ranked = rank_snippets(snippets, "")
        
        assert len(ranked) == 2
        # All should have default score
        for snippet, score in ranked:
            assert score == 1.0
            
    def test_rank_snippets_multiple_terms(self):
        """Test ranking with multiple query terms."""
        snippets = [
            "Python and Java programming",
            "Only Python here",
            "Only Java here",
            "Neither language mentioned"
        ]
        
        ranked = rank_snippets(snippets, "Python Java")
        
        # First snippet with both terms should rank highest
        assert "Python and Java" in ranked[0][0]
        assert ranked[0][1] > ranked[1][1]
        
    def test_rank_snippets_position_bonus(self):
        """Test that earlier matches get position bonus."""
        snippets = [
            "End of text has Python",
            "Python at the beginning"
        ]
        
        ranked = rank_snippets(snippets, "Python")
        
        # Earlier position should rank higher
        assert "beginning" in ranked[0][0]


class TestCalculateSnippetScore:
    """Test snippet score calculation."""
    
    def test_calculate_score_all_terms_match(self):
        """Test score when all query terms match."""
        query_terms = {"python", "programming"}
        snippet = "Python programming is great"
        
        score = _calculate_snippet_score(snippet, query_terms)
        assert score > 0
        
    def test_calculate_score_partial_match(self):
        """Test score with partial term match."""
        query_terms = {"python", "java", "programming"}
        snippet = "Python programming tutorial"
        
        score = _calculate_snippet_score(snippet, query_terms)
        assert 0 < score < 1  # Partial match
        
    def test_calculate_score_no_match(self):
        """Test score with no matching terms."""
        query_terms = {"python", "java"}
        snippet = "JavaScript and TypeScript"
        
        score = _calculate_snippet_score(snippet, query_terms)
        assert score == 0
        
    def test_calculate_score_empty_snippet(self):
        """Test score with empty snippet."""
        query_terms = {"python"}
        score = _calculate_snippet_score("", query_terms)
        assert score == 0
        
    def test_calculate_score_empty_query(self):
        """Test score with empty query terms."""
        snippet = "Some text"
        score = _calculate_snippet_score(snippet, set())
        assert score == 0
        
    def test_calculate_score_position_matters(self):
        """Test that position affects score."""
        query_terms = {"python"}
        snippet1 = "Python is first"
        snippet2 = "Last word is Python"
        
        score1 = _calculate_snippet_score(snippet1, query_terms)
        score2 = _calculate_snippet_score(snippet2, query_terms)
        
        # Earlier position should score higher
        assert score1 > score2
        
    def test_calculate_score_length_penalty(self):
        """Test that longer snippets get penalized."""
        query_terms = {"python"}
        short = "Python rocks"
        long = "Python " + "word " * 100 + "rocks"
        
        score_short = _calculate_snippet_score(short, query_terms)
        score_long = _calculate_snippet_score(long, query_terms)
        
        # Shorter snippet should score higher
        assert score_short > score_long


class TestGetCachedSnippet:
    """Test cached snippet extraction."""
    
    def test_get_cached_snippet_basic(self):
        """Test basic cached snippet extraction."""
        text = "The quick brown fox jumps over the lazy dog."
        snippet1 = get_cached_snippet(text, "fox", 30)
        snippet2 = get_cached_snippet(text, "fox", 30)
        
        assert snippet1 == snippet2
        assert "fox" in snippet1
        
    def test_get_cached_snippet_empty(self):
        """Test cached snippet with empty text."""
        snippet = get_cached_snippet("", "query", 50)
        assert snippet == ""
        
    def test_get_cached_snippet_different_params(self):
        """Test that different parameters create different results."""
        text = "The quick brown fox jumps over the lazy dog."
        
        snippet1 = get_cached_snippet(text, "fox", 20)
        snippet2 = get_cached_snippet(text, "fox", 40)
        
        # Different window sizes should give different results
        assert len(snippet2) >= len(snippet1)


class TestFormatSearchResult:
    """Test search result formatting."""
    
    def test_format_search_result_dict(self):
        """Test formatting dictionary search result."""
        content = {
            "content": "The quick brown fox jumps over the lazy dog.",
            "title": "Test Document"
        }
        
        result = format_search_result(content, "fox", snippet_length=30)
        
        assert "snippet" in result
        assert "highlighted_snippet" in result
        assert "snippet_length" in result
        assert "fox" in result["snippet"]
        
    def test_format_search_result_body_field(self):
        """Test formatting with body field instead of content."""
        content = {
            "body": "Email body with search term.",
            "subject": "Test Email"
        }
        
        result = format_search_result(content, "search", snippet_length=30)
        
        assert "snippet" in result
        assert "search" in result["snippet"]
        
    def test_format_search_result_title_fallback(self):
        """Test formatting falls back to title if no content/body."""
        content = {
            "title": "Document with search term"
        }
        
        result = format_search_result(content, "search", snippet_length=30)
        
        assert "snippet" in result
        assert "search" in result["snippet"]
        
    def test_format_search_result_string_content(self):
        """Test formatting string content instead of dict."""
        content = "Plain text content with search term"
        
        result = format_search_result(content, "search", snippet_length=30)
        
        assert isinstance(result, dict)
        assert "snippet" in result
        assert "content" in result
        assert result["content"] == content
        
    def test_format_search_result_empty_content(self):
        """Test formatting empty content."""
        result = format_search_result({}, "query", snippet_length=30)
        assert result == {}
        
        result2 = format_search_result(None, "query", snippet_length=30)
        assert result2 is None
        
    def test_format_search_result_ansi_highlighting(self):
        """Test that highlighted snippet includes ANSI codes."""
        content = {"content": "Text with keyword here"}
        result = format_search_result(content, "keyword", snippet_length=50)
        
        # Should have ANSI codes in highlighted snippet
        assert "\033[93m" in result["highlighted_snippet"] or "[keyword]" in result["highlighted_snippet"]
        
    def test_format_search_result_preserves_original(self):
        """Test that original content is preserved."""
        content = {
            "content": "Original content",
            "id": 123,
            "metadata": {"key": "value"}
        }
        
        result = format_search_result(content, "content", snippet_length=50)
        
        # Original fields should be preserved
        assert result["id"] == 123
        assert result["metadata"] == {"key": "value"}
        assert result["content"] == "Original content"


@pytest.mark.integration
class TestSnippetUtilsIntegration:
    """Integration tests for snippet utilities."""
    
    def test_full_pipeline(self):
        """Test complete snippet processing pipeline."""
        # Sample search results
        results = [
            {
                "id": 1,
                "title": "Python Programming Guide",
                "content": "Python is a versatile programming language. Learn Python basics here."
            },
            {
                "id": 2,
                "title": "Java Tutorial",
                "body": "Java is an object-oriented programming language used for enterprise."
            },
            {
                "id": 3,
                "title": "JavaScript Basics",
                "content": "JavaScript runs in browsers and Node.js. It's essential for web dev."
            }
        ]
        
        query = "Python programming"
        
        # Format all results
        formatted = []
        for result in results:
            formatted.append(format_search_result(result, query, snippet_length=50))
            
        # Extract just snippets for ranking
        snippets = [r.get("snippet", "") for r in formatted]
        ranked = rank_snippets(snippets, query)
        
        # Python results should rank higher
        assert "Python" in ranked[0][0]
        
        # All results should be enhanced
        for result in formatted:
            if result.get("snippet"):
                assert "snippet" in result
                assert "highlighted_snippet" in result
                assert "snippet_length" in result
                
    def test_real_world_text(self):
        """Test with realistic text content."""
        legal_text = """
        WHEREAS, the parties have entered into a mutual agreement dated January 1, 2024,
        for the provision of software development services; and WHEREAS, the Client requires
        modifications to the original scope of work as outlined in Exhibit A; NOW THEREFORE,
        in consideration of the mutual covenants and agreements contained herein, the parties
        agree to amend the original agreement as follows: The development timeline shall be
        extended by thirty (30) days to accommodate the additional features requested by the
        Client. The total compensation shall be increased by $10,000 to reflect the expanded
        scope of work.
        """
        
        # Extract snippet
        snippet = extract_snippet(legal_text, "development timeline", window_size=100)
        assert "development timeline" in snippet
        assert "extended" in snippet
        
        # Highlight terms
        highlighted = highlight_keywords(snippet, "development timeline extended", use_ansi=False)
        assert "[development]" in highlighted
        assert "[timeline]" in highlighted
        assert "[extended]" in highlighted
        
    def test_performance_large_text(self):
        """Test performance with large text."""
        # Create large text
        large_text = " ".join([f"Sentence {i} with some content." for i in range(1000)])
        large_text += " Important keyword appears here. "
        large_text += " ".join([f"More content {i}." for i in range(1000)])
        
        # Should handle large text efficiently
        snippet = extract_snippet(large_text, "keyword", window_size=50)
        assert "keyword" in snippet
        assert len(snippet) <= 110  # Window + ellipsis
        
        # Highlighting should also work
        highlighted = highlight_keywords(snippet, "keyword")
        assert highlighted is not None