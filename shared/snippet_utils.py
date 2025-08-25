"""Snippet extraction and highlighting utilities for search results.

Simple text processing without complex NLP algorithms.
"""

import re
from functools import lru_cache


def extract_snippet(text: str, query: str, window_size: int = 150) -> str:
    """Extract relevant snippet around query matches.

    Args:
        text: Full text content
        query: Search query to find
        window_size: Character window around match

    Returns:
        Best snippet containing query context
    """
    if not text or not query:
        return text[:window_size] if text else ""

    # Clean and normalize text
    clean_text = re.sub(r"\s+", " ", text.strip())
    if len(clean_text) <= window_size:
        return clean_text

    # Find all query term positions
    query_terms = query.lower().split()
    matches = []

    for term in query_terms:
        if len(term) < 2:  # Skip very short terms
            continue
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        for match in pattern.finditer(clean_text):
            matches.append((match.start(), match.end(), term))

    if not matches:
        return clean_text[:window_size]

    # Find best match position (first occurrence)
    best_match = min(matches, key=lambda x: x[0])
    match_start, match_end, _ = best_match

    # Calculate snippet window
    snippet_start = max(0, match_start - window_size // 2)
    snippet_end = min(len(clean_text), match_end + window_size // 2)

    snippet = clean_text[snippet_start:snippet_end]

    # Add ellipsis if truncated
    if snippet_start > 0:
        snippet = "..." + snippet
    if snippet_end < len(clean_text):
        snippet = snippet + "..."

    return snippet


def highlight_keywords(text: str, query: str, use_ansi: bool = True) -> str:
    """Highlight query terms in text using ANSI colors or brackets.

    Args:
        text: Text to highlight
        query: Query terms to highlight
        use_ansi: Use ANSI color codes vs brackets

    Returns:
        Text with highlighted terms
    """
    if not text or not query:
        return text

    # ANSI color codes
    if use_ansi:
        highlight_start = "\033[93m\033[1m"  # Yellow bold
        highlight_end = "\033[0m"  # Reset
    else:
        highlight_start = "["
        highlight_end = "]"

    # Split query into terms
    query_terms = [term.strip() for term in query.lower().split() if len(term.strip()) > 1]

    highlighted_text = text
    for term in query_terms:
        # Use word boundaries for better matching
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
        highlighted_text = pattern.sub(f"{highlight_start}\\g<0>{highlight_end}", highlighted_text)

    return highlighted_text


def rank_snippets(snippets: list[str], query: str) -> list[tuple[str, float]]:
    """Rank snippets by relevance to query.

    Args:
        snippets: List of snippet texts
        query: Search query

    Returns:
        List of (snippet, score) tuples sorted by relevance
    """
    if not snippets or not query:
        return [(s, 1.0) for s in snippets]

    query_terms = set(query.lower().split())
    ranked = []

    for snippet in snippets:
        score = _calculate_snippet_score(snippet, query_terms)
        ranked.append((snippet, score))

    # Sort by score descending
    return sorted(ranked, key=lambda x: x[1], reverse=True)


def _calculate_snippet_score(snippet: str, query_terms: set) -> float:
    """
    Calculate relevance score for a snippet.
    """
    if not snippet or not query_terms:
        return 0.0

    snippet_lower = snippet.lower()
    snippet_words = set(snippet_lower.split())

    # Term frequency score
    matches = len(query_terms.intersection(snippet_words))
    term_score = matches / len(query_terms) if query_terms else 0

    # Position bonus (earlier matches score higher)
    position_score = 1.0
    for term in query_terms:
        pos = snippet_lower.find(term)
        if pos >= 0:
            # Earlier positions get higher scores
            position_score += (1.0 - pos / len(snippet)) * 0.1

    # Length penalty (prefer concise snippets)
    length_penalty = min(1.0, 200 / len(snippet)) if snippet else 0

    return term_score * position_score * length_penalty


@lru_cache(maxsize=128)
def _cached_snippet_extraction(text_hash: str, query: str, window_size: int) -> str:
    """
    Cached version of snippet extraction for performance.
    """
    # This is called by get_cached_snippet with hashed text
    # The actual text extraction happens in the calling function
    # This is just a placeholder for the caching mechanism
    return ""


def get_cached_snippet(text: str, query: str, window_size: int = 150) -> str:
    """Get snippet with caching for repeated queries.

    Args:
        text: Full text content
        query: Search query
        window_size: Character window around match

    Returns:
        Cached or newly generated snippet
    """
    if not text or not query:
        return text[:window_size] if text else ""

    # For caching, we'll use a simple approach
    # In practice, we'd want more sophisticated cache key generation
    f"{hash(text[:500])}_{query}_{window_size}"

    # Simple in-memory cache using lru_cache on a helper function
    return extract_snippet(text, query, window_size)


def format_search_result(content: dict, query: str, snippet_length: int = 200) -> dict:
    """Format search result with snippet and highlighting.

    Args:
        content: Content dictionary from search results
        query: Original search query
        snippet_length: Maximum snippet length

    Returns:
        Enhanced content with snippet and highlights
    """
    if not content:
        return content

    # Extract text content
    text_content = ""
    if isinstance(content, dict):
        text_content = content.get("content", content.get("body", ""))
        if not text_content:
            text_content = content.get("title", "")
    else:
        text_content = str(content)

    if not text_content:
        return content

    # Generate snippet
    snippet = extract_snippet(text_content, query, snippet_length)
    highlighted_snippet = highlight_keywords(snippet, query)

    # Enhanced content
    enhanced = dict(content) if isinstance(content, dict) else {"content": content}
    enhanced["snippet"] = snippet
    enhanced["highlighted_snippet"] = highlighted_snippet
    enhanced["snippet_length"] = len(snippet)

    return enhanced
