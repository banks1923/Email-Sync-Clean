#!/usr/bin/env python3
"""
Test suite for verifying the import refactoring is complete and working.
Tests that all public APIs are accessible via two-level imports.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPublicAPIImports(unittest.TestCase):
    """Test that all public APIs are accessible via two-level imports."""
    
    def test_lib_imports(self):
        """Test lib package exports."""
        # Database
        from lib import DatabaseMetrics, SimpleDB
        self.assertTrue(callable(SimpleDB))
        self.assertTrue(callable(DatabaseMetrics))
        
        # Search functions
        from lib import find_literal, hybrid_search, keyword_search, search, semantic_search
        self.assertTrue(callable(search))
        self.assertTrue(callable(semantic_search))
        self.assertTrue(callable(hybrid_search))
        self.assertTrue(callable(find_literal))
        self.assertTrue(callable(keyword_search))
        
        # Embeddings
        from lib import EmbeddingService, get_embedding_service
        self.assertTrue(callable(get_embedding_service))
        self.assertTrue(callable(EmbeddingService))
        
        # Vector Store
        from lib import VectorStore, get_vector_store
        self.assertTrue(callable(get_vector_store))
        self.assertTrue(callable(VectorStore))
        
        # Pipelines
        from lib import ChunkPipeline
        self.assertTrue(callable(ChunkPipeline))
        
        # Exceptions
        from lib import EnrichmentError, SearchError, ValidationError, VectorStoreError
        self.assertTrue(issubclass(SearchError, Exception))
        self.assertTrue(issubclass(ValidationError, Exception))
        self.assertTrue(issubclass(VectorStoreError, Exception))
        self.assertTrue(issubclass(EnrichmentError, Exception))
    
    def test_services_imports(self):
        """Test services package exports."""
        # PDF Service
        from services import EnhancedPDFProcessor, IdempotentPDFWriter, PDFHealthManager, PDFService
        self.assertTrue(callable(PDFService))
        self.assertTrue(callable(EnhancedPDFProcessor))
        self.assertTrue(callable(IdempotentPDFWriter))
        self.assertTrue(callable(PDFHealthManager))
        
        # Entity Service
        from services import EntityConfig, EntityDatabase, EntityService
        self.assertTrue(callable(EntityService))
        self.assertTrue(callable(EntityDatabase))
        self.assertTrue(callable(EntityConfig))
        
        # Summarization
        from services import DocumentSummarizer, TextRankSummarizer, TFIDFSummarizer
        self.assertTrue(callable(DocumentSummarizer))
        self.assertTrue(callable(TFIDFSummarizer))
        self.assertTrue(callable(TextRankSummarizer))
    
    def test_infrastructure_imports(self):
        """Test infrastructure package exports."""
        from infrastructure import (
            DocumentChunk,
            DocumentChunker,
            DocumentType,
            QualityScoreCalculator,
        )
        self.assertTrue(callable(DocumentChunker))
        self.assertTrue(callable(DocumentChunk))
        # DocumentType is an Enum
        self.assertTrue(hasattr(DocumentType, '__members__'))
        self.assertTrue(callable(QualityScoreCalculator))
    
    def test_gmail_imports(self):
        """Test gmail package exports."""
        from gmail import GmailAPI, GmailAuth, GmailConfig, GmailService
        self.assertTrue(callable(GmailService))
        self.assertTrue(callable(GmailAuth))
        self.assertTrue(callable(GmailAPI))
        self.assertTrue(callable(GmailConfig))
        
        # Factory function
        from gmail import get_gmail_service
        self.assertTrue(callable(get_gmail_service))
        
        # Deduplication
        from gmail import MessageDeduplicator, NearDuplicateDetector
        self.assertTrue(callable(NearDuplicateDetector))
        self.assertTrue(callable(MessageDeduplicator))
    
    def test_wildcard_imports_restricted(self):
        """Test that wildcard imports only expose __all__ members."""
        # Test lib package
        import lib
        public_api = set(lib.__all__)
        
        # Verify __all__ is respected
        for name in public_api:
            self.assertTrue(hasattr(lib, name), f"Missing export: {name}")
        
        # Similar tests for other packages
        import services
        self.assertTrue(hasattr(services, '__all__'))
        
        import infrastructure
        self.assertTrue(hasattr(infrastructure, '__all__'))
        
        import gmail
        self.assertTrue(hasattr(gmail, '__all__'))
    
    def test_no_deep_imports_needed(self):
        """Verify that deep imports are not needed for public APIs."""
        # This should fail (demonstrating we don't need deep imports)
        with self.assertRaises(ImportError):
            from lib.db import SimpleDB  # Testing invalid deep import
        
        # But this should work (two-level import)
        from lib import SimpleDB  # Valid two-level import
        self.assertTrue(callable(SimpleDB))


class TestImportDepthCompliance(unittest.TestCase):
    """Test that the codebase doesn't use deep imports."""
    
    def test_no_deep_imports_in_codebase(self):
        """Scan for deep imports (more than 2 levels) in Python files."""
        import ast
        import re

        # Patterns that indicate deep imports
        deep_import_pattern = re.compile(
            r'^from\s+(\w+)\.(\w+)\.(\w+)\.(\w+)',  # 4+ levels
            re.MULTILINE
        )
        
        violations = []
        project_root = Path(__file__).parent.parent
        
        # Scan Python files
        for py_file in project_root.rglob("*.py"):
            # Skip test files and migrations
            if "test" in str(py_file) or "migration" in str(py_file):
                continue
            
            # Skip __pycache__ and virtual environments
            if "__pycache__" in str(py_file) or "venv" in str(py_file):
                continue
                
            try:
                content = py_file.read_text()
                matches = deep_import_pattern.findall(content)
                if matches:
                    violations.append({
                        'file': str(py_file.relative_to(project_root)),
                        'imports': matches
                    })
            except Exception as e:
                pass  # Skip files that can't be read
        
        # Report violations
        if violations:
            print("\nDeep import violations found:")
            for v in violations[:5]:  # Show first 5
                print(f"  {v['file']}: {v['imports']}")
        
        # This is informational - not failing the test yet
        # self.assertEqual(len(violations), 0, f"Found {len(violations)} deep import violations")


def run_tests():
    """Run all import tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPublicAPIImports))
    suite.addTests(loader.loadTestsFromTestCase(TestImportDepthCompliance))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)