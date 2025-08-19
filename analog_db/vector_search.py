"""
Vector search integration for analog database.

Handles semantic search using Legal BERT embeddings and integration
with existing search_intelligence services.
"""

from pathlib import Path
from typing import Any, Dict, List

import frontmatter
from loguru import logger


class VectorSearcher:
    """Handles semantic vector search integration."""
    
    def __init__(self, base_path: Path):
        """Initialize vector searcher."""
        self.base_path = base_path
        self.analog_db_path = base_path / "analog_db"
    
    def get_database_vector_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Get vector search results from existing search_intelligence service."""
        try:
            from search_intelligence import get_search_intelligence_service
            
            search_service = get_search_intelligence_service()
            vector_results = search_service.smart_search_with_preprocessing(
                query=query,
                limit=limit,
                use_expansion=True,
                filters=None
            )
            
            formatted_results = []
            for result in vector_results:
                formatted_result = {
                    "file_path": result.get("file_path", ""),
                    "content": result.get("content", ""),
                    "metadata": {
                        "title": result.get("subject", result.get("title", "")),
                        "doc_type": "vector_match",
                        "similarity_score": result.get("similarity_score", 0.0)
                    },
                    "score": result.get("similarity_score", 0.0) * 10,
                    "source": "vector",
                    "match_type": "semantic"
                }
                formatted_results.append(formatted_result)
            
            logger.debug(f"Database vector search returned {len(formatted_results)} results")
            return formatted_results
            
        except ImportError:
            logger.debug("Search intelligence service not available")
            return []
        except Exception as e:
            logger.debug(f"Database vector search failed: {e}")
            return []
    
    def get_analog_semantic_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Perform semantic search on analog database markdown files."""
        try:
            from utilities.embeddings import get_embedding_service
            
            embedding_service = get_embedding_service()
            query_embedding = embedding_service.get_embedding(query)
            if query_embedding is None or len(query_embedding) == 0:
                return []
            
            markdown_files = self._get_markdown_files()
            semantic_results = []
            
            # Process files (limit for performance - increased from 50 to 100)
            for file_path in markdown_files[:100]:
                try:
                    similarity_score = self._calculate_similarity(
                        file_path, query_embedding, embedding_service
                    )
                    
                    if similarity_score is not None and float(similarity_score) > 0.4:
                        result = self._create_semantic_result(file_path, similarity_score)
                        semantic_results.append(result)
                        
                except Exception as e:
                    logger.debug(f"Failed to process file {file_path} for semantic search: {e}")
                    continue
            
            # Sort by similarity and return top results
            semantic_results.sort(key=lambda x: x["similarity_score"], reverse=True)
            final_results = semantic_results[:limit]
            
            logger.debug(f"Analog semantic search returned {len(final_results)} results")
            return final_results
            
        except ImportError:
            logger.debug("Embedding services not available for semantic search")
            return []
        except Exception as e:
            logger.debug(f"Analog semantic search failed: {e}")
            return []
    
    def _get_markdown_files(self) -> List[Path]:
        """Get all markdown files in analog database."""
        markdown_files = []
        documents_path = self.analog_db_path / "documents"
        email_threads_path = self.analog_db_path / "email_threads"
        
        for search_dir in [documents_path, email_threads_path]:
            if search_dir.exists():
                markdown_files.extend(search_dir.rglob("*.md"))
        
        return markdown_files
    
    def _calculate_similarity(self, file_path: Path, query_embedding, embedding_service):
        """Calculate similarity between query and file content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # Create combined text from title and content
            title = post.metadata.get('title', '')
            content_sample = post.content[:1000]  # First 1000 chars
            combined_text = f"{title} {content_sample}"
            
            # Skip empty content
            if not combined_text.strip():
                return None
            
            # Get embedding for file content
            content_embedding = embedding_service.get_embedding(combined_text)
            if content_embedding is None or len(content_embedding) == 0:
                return None
            
            # Ensure embeddings are numpy arrays with proper shape
            import numpy as np
            
            query_emb = np.array(query_embedding).flatten()
            content_emb = np.array(content_embedding).flatten()
            
            # Check dimensions match
            if len(query_emb) != len(content_emb):
                return None
            
            # Calculate cosine similarity manually to avoid array truth value error
            dot_product = np.dot(query_emb, content_emb)
            query_norm = np.linalg.norm(query_emb)
            content_norm = np.linalg.norm(content_emb)
            
            if query_norm == 0 or content_norm == 0:
                return 0.0
            
            similarity = dot_product / (query_norm * content_norm)
            return float(similarity)
            
        except Exception as e:
            logger.debug(f"Error calculating similarity for {file_path}: {e}")
            return None
    
    def _create_semantic_result(self, file_path: Path, similarity_score: float) -> Dict[str, Any]:
        """Create semantic search result dictionary."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            return {
                "file_path": str(file_path),
                "metadata": post.metadata,
                "content_preview": post.content[:200] + "...",
                "similarity_score": similarity_score,
                "score": similarity_score * 15,  # High boost for semantic matches
                "source": "analog_semantic",
                "match_type": "semantic"
            }
        except Exception:
            return {
                "file_path": str(file_path),
                "similarity_score": similarity_score,
                "score": similarity_score * 15,
                "source": "analog_semantic",
                "match_type": "semantic"
            }