"""Document Summarization Engine implementation.

Uses TF-IDF for keyword extraction and TextRank for sentence extraction.
"""

import re
import sys
from pathlib import Path

import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Add parent to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger

# Logger is now imported globally from loguru


class TFIDFSummarizer:
    """
    Extract keywords using TF-IDF algorithm.
    """

    def __init__(self, max_features: int = 100, ngram_range: tuple[int, int] = (1, 3)) -> None:
        """Initialize TF-IDF summarizer.

        Args:
            max_features: Maximum number of features to extract
            ngram_range: Range of n-grams to consider (min, max)
        """
        self.max_features = max_features
        self.ngram_range = ngram_range
        self.vectorizer = None

    def preprocess_text(self, text: str) -> str:
        """Preprocess text for TF-IDF analysis.

        Args:
            text: Raw text to preprocess

        Returns:
            Cleaned text
        """
        # Convert to lowercase
        text = text.lower()

        # Remove special characters but keep spaces and alphanumeric
        text = re.sub(r"[^a-z0-9\s\-]", " ", text)

        # Remove extra whitespace
        text = " ".join(text.split())

        return text

    def extract_keywords(self, text: str, max_keywords: int = 10) -> dict[str, float]:
        """Extract top keywords with TF-IDF scores.

        Args:
            text: Document text
            max_keywords: Maximum number of keywords to return

        Returns:
            Dictionary of keyword -> score
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for keyword extraction")
            return {}

        try:
            # Preprocess text
            processed_text = self.preprocess_text(text)

            # Create and fit TF-IDF vectorizer
            # For single document, don't use min_df/max_df
            self.vectorizer = TfidfVectorizer(
                max_features=self.max_features, ngram_range=self.ngram_range, stop_words="english"
            )

            # Fit and transform the text
            tfidf_matrix = self.vectorizer.fit_transform([processed_text])

            # Get feature names and scores
            feature_names = self.vectorizer.get_feature_names_out()
            scores = tfidf_matrix.toarray()[0]

            # Create keyword-score pairs
            keyword_scores = list(zip(feature_names, scores))

            # Sort by score and get top keywords
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            top_keywords = keyword_scores[:max_keywords]

            # Convert to dictionary
            result = {keyword: float(score) for keyword, score in top_keywords}

            logger.debug(f"Extracted {len(result)} keywords from text of length {len(text)}")
            return result

        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            return {}

    def extract_keywords_batch(
        self, texts: list[str], max_keywords: int = 10
    ) -> list[dict[str, float]]:
        """Extract keywords from multiple documents.

        Args:
            texts: List of document texts
            max_keywords: Maximum keywords per document

        Returns:
            List of keyword dictionaries
        """
        if not texts:
            return []

        try:
            # Preprocess all texts
            processed_texts = [self.preprocess_text(text) for text in texts]

            # Create and fit TF-IDF vectorizer on all documents
            self.vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                ngram_range=self.ngram_range,
                stop_words="english",
                min_df=1,
                max_df=0.95,
            )

            # Fit and transform all texts
            tfidf_matrix = self.vectorizer.fit_transform(processed_texts)
            feature_names = self.vectorizer.get_feature_names_out()

            # Extract keywords for each document
            results = []
            for i in range(len(texts)):
                scores = tfidf_matrix[i].toarray()[0]
                keyword_scores = list(zip(feature_names, scores))
                keyword_scores.sort(key=lambda x: x[1], reverse=True)
                top_keywords = keyword_scores[:max_keywords]
                result = {keyword: float(score) for keyword, score in top_keywords if score > 0}
                results.append(result)

            logger.info(f"Batch extracted keywords from {len(texts)} documents")
            return results

        except Exception as e:
            logger.error(f"Error in batch keyword extraction: {e}")
            return [{}] * len(texts)


class TextRankSummarizer:
    """
    Extract key sentences using TextRank algorithm with Legal BERT embeddings.
    """

    def __init__(self, similarity_threshold: float = 0.3) -> None:
        """Initialize TextRank summarizer.

        Args:
            similarity_threshold: Minimum similarity to create edge in graph
        """
        self.similarity_threshold = similarity_threshold
        self.embedding_service = None

    def _get_embedding_service(self):
        """
        Lazy load embedding service.
        """
        if self.embedding_service is None:
            try:
                from utilities.embeddings import get_embedding_service

                self.embedding_service = get_embedding_service()
                logger.debug("Loaded Legal BERT embedding service")
            except Exception as e:
                logger.warning(f"Could not load embedding service: {e}")
        return self.embedding_service

    def split_sentences(self, text: str) -> list[str]:
        """Split text into sentences.

        Args:
            text: Document text

        Returns:
            List of sentences
        """
        # Split on sentence delimiters but don't remove trailing text
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())

        # Clean and filter sentences
        cleaned = []
        for s in sentences:
            s = s.strip()
            # Remove trailing punctuation if sentence already has internal punctuation
            if s and len(s) > 10:
                cleaned.append(s.rstrip(".!?"))
            elif s and not cleaned:  # Keep short first sentence
                cleaned.append(s.rstrip(".!?"))

        return cleaned

    def extract_sentences(self, text: str, max_sentences: int = 3) -> list[str]:
        """Extract key sentences using TextRank.

        Args:
            text: Document text
            max_sentences: Maximum number of sentences to return

        Returns:
            List of key sentences
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for sentence extraction")
            return []

        try:
            # Split into sentences
            sentences = self.split_sentences(text)

            if len(sentences) <= max_sentences:
                return sentences

            # Try to use Legal BERT embeddings
            embedding_service = self._get_embedding_service()

            if embedding_service:
                # Get embeddings for each sentence
                embeddings = []
                for sentence in sentences:
                    try:
                        embedding = embedding_service.encode(sentence)
                        embeddings.append(embedding)
                    except Exception as e:
                        logger.warning(f"Error encoding sentence: {e}")
                        # Use basic vectorization as fallback
                        embeddings = None
                        break

                if embeddings:
                    embeddings = np.array(embeddings)
                    # Calculate similarity matrix
                    similarity_matrix = cosine_similarity(embeddings)
                else:
                    # Fallback to TF-IDF for similarity
                    similarity_matrix = self._tfidf_similarity(sentences)
            else:
                # Fallback to TF-IDF for similarity
                similarity_matrix = self._tfidf_similarity(sentences)

            # Create graph from similarity matrix
            nx_graph = nx.from_numpy_array(similarity_matrix)

            # Apply TextRank (PageRank on the graph)
            scores = nx.pagerank(nx_graph, max_iter=100)

            # Sort sentences by score
            ranked_sentences = sorted(
                [(sentences[i], scores[i]) for i in range(len(sentences))],
                key=lambda x: x[1],
                reverse=True,
            )

            # Return top sentences in original order
            top_sentences = ranked_sentences[:max_sentences]
            top_sentences_text = [s[0] for s in top_sentences]

            # Maintain original order
            result = []
            for sentence in sentences:
                if sentence in top_sentences_text:
                    result.append(sentence)
                if len(result) >= max_sentences:
                    break

            logger.debug(f"Extracted {len(result)} key sentences from {len(sentences)} total")
            return result

        except Exception as e:
            logger.error(f"Error extracting sentences: {e}")
            # Return first few sentences as fallback
            sentences = self.split_sentences(text)
            return sentences[:max_sentences]

    def _tfidf_similarity(self, sentences: list[str]) -> np.ndarray:
        """Calculate sentence similarity using TF-IDF (fallback method).

        Args:
            sentences: List of sentences

        Returns:
            Similarity matrix
        """
        try:
            vectorizer = TfidfVectorizer(stop_words="english", min_df=1, max_df=0.95)
            tfidf_matrix = vectorizer.fit_transform(sentences)
            similarity_matrix = cosine_similarity(tfidf_matrix)

            # Apply threshold
            similarity_matrix[similarity_matrix < self.similarity_threshold] = 0

            return similarity_matrix
        except Exception as e:
            logger.error(f"Error calculating TF-IDF similarity: {e}")
            # Return identity matrix as fallback
            return np.eye(len(sentences))


class DocumentSummarizer:
    """
    Orchestrates both TF-IDF and TextRank summarization.
    """

    def __init__(self) -> None:
        """
        Initialize document summarizer with both algorithms.
        """
        self.tfidf_summarizer = TFIDFSummarizer()
        self.textrank_summarizer = TextRankSummarizer()

    def extract_summary(
        self,
        text: str,
        max_sentences: int = 3,
        max_keywords: int = 10,
        summary_type: str = "combined",
    ) -> dict:
        """Extract comprehensive summary from document.

        Args:
            text: Document text
            max_sentences: Maximum number of key sentences
            max_keywords: Maximum number of keywords
            summary_type: Type of summary ('tfidf', 'textrank', 'combined')

        Returns:
            Dictionary with summary components
        """
        result = {
            "summary_type": summary_type,
            "summary_text": None,
            "tf_idf_keywords": None,
            "textrank_sentences": None,
        }

        if not text or not text.strip():
            logger.warning("Empty text provided for summarization")
            return result

        try:
            # Extract based on type
            if summary_type in ["tfidf", "combined"]:
                keywords = self.tfidf_summarizer.extract_keywords(text, max_keywords)
                result["tf_idf_keywords"] = keywords

            if summary_type in ["textrank", "combined"]:
                sentences = self.textrank_summarizer.extract_sentences(text, max_sentences)
                result["textrank_sentences"] = sentences

            # Generate combined summary text
            if summary_type == "combined" and result["textrank_sentences"]:
                result["summary_text"] = " ".join(result["textrank_sentences"])
            elif summary_type == "textrank" and result["textrank_sentences"]:
                result["summary_text"] = " ".join(result["textrank_sentences"])
            elif summary_type == "tfidf":
                if result["tf_idf_keywords"]:
                    # Create a simple summary from keywords
                    top_keywords = list(result["tf_idf_keywords"].keys())[:5]
                    result["summary_text"] = f"Key topics: {', '.join(top_keywords)}"
                else:
                    result["summary_text"] = "Unable to extract keywords from document."

            logger.info(f"Generated {summary_type} summary for text of length {len(text)}")
            return result

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return result

    def summarize_batch(
        self,
        texts: list[str],
        max_sentences: int = 3,
        max_keywords: int = 10,
        summary_type: str = "combined",
    ) -> list[dict]:
        """Summarize multiple documents.

        Args:
            texts: List of document texts
            max_sentences: Maximum sentences per document
            max_keywords: Maximum keywords per document
            summary_type: Type of summary

        Returns:
            List of summary dictionaries
        """
        results = []

        # Batch process TF-IDF if needed
        if summary_type in ["tfidf", "combined"]:
            all_keywords = self.tfidf_summarizer.extract_keywords_batch(texts, max_keywords)
        else:
            all_keywords = [None] * len(texts)

        # Process each document
        for i, text in enumerate(texts):
            result = {
                "summary_type": summary_type,
                "summary_text": None,
                "tf_idf_keywords": all_keywords[i] if all_keywords[i] else None,
                "textrank_sentences": None,
            }

            # Extract TextRank sentences if needed
            if summary_type in ["textrank", "combined"] and text:
                sentences = self.textrank_summarizer.extract_sentences(text, max_sentences)
                result["textrank_sentences"] = sentences
                result["summary_text"] = " ".join(sentences) if sentences else None
            elif summary_type == "tfidf" and result["tf_idf_keywords"]:
                top_keywords = list(result["tf_idf_keywords"].keys())[:5]
                result["summary_text"] = f"Key topics: {', '.join(top_keywords)}"

            results.append(result)

        logger.info(f"Batch summarized {len(texts)} documents")
        return results


# Singleton instance
_document_summarizer = None


def get_document_summarizer() -> DocumentSummarizer:
    """
    Get singleton document summarizer instance.
    """
    global _document_summarizer
    if _document_summarizer is None:
        _document_summarizer = DocumentSummarizer()
    return _document_summarizer
