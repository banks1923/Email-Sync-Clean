#!/usr/bin/env python3
"""
Unified Ingestion Service - Manual processing for emails and documents.

Provides single interface for ingesting content through the unified pipeline:
- Emails via GmailService
- Documents via SimpleUploadProcessor 
- Both via unified interface

Follows CLAUDE.md principles: Simple > Complex, Direct > Indirect.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from loguru import logger

from .simple_upload_processor import SimpleUploadProcessor


class UnifiedIngestionService:
    """Manual ingestion service for emails and documents through unified pipeline."""

    def __init__(self):
        self.document_processor = SimpleUploadProcessor()

    def ingest_documents(
        self, 
        directory: str = "data/Stoneman_dispute/user_data",
        extensions: list[str] = None
    ) -> Dict[str, Any]:
        """
        Process documents from directory recursively through unified pipeline.
        
        Args:
            directory: Directory to scan recursively
            extensions: File extensions to process (default: pdf, txt, docx, md)
            
        Returns:
            Processing results with counts and file details
        """
        if extensions is None:
            extensions = ['.pdf', '.txt', '.docx', '.md']
        
        directory_path = Path(directory)
        if not directory_path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {directory}",
                "processed": 0,
                "duplicates": 0,
                "errors": 0,
                "files": []
            }

        logger.info(f"📄 Starting document ingestion from: {directory}")
        start_time = time.time()
        
        # Use the recursive processor directly with explicit document source type
        result = self.document_processor.process_directory_recursive(directory_path, extensions)
        
        if not result.get("total_files", 0):
            logger.info("No documents found to process")
            return {
                "success": True,
                "processed": 0,
                "duplicates": 0,
                "errors": 0,
                "files": [],
                "message": "No documents found"
            }

        logger.info(f"Found {result['total_files']} documents to process")
        
        # Print progress as files are processed
        for processed_file in result.get("processed_files", []):
            print(f"✅ {processed_file['file']} → content_id: {processed_file['content_id']}")
        
        for failed_file in result.get("failed_files", []):
            print(f"❌ {failed_file['file']}: {failed_file['error']}")

        elapsed = time.time() - start_time
        
        # Summary
        logger.info(f"Document ingestion complete in {elapsed:.1f}s")
        logger.info(f"Processed: {result['success_count']}, Errors: {result['failed_count']}")
        
        # Convert SimpleUploadProcessor format to our format
        processed_results = {
            "success": result["success"],
            "processed": result["success_count"],
            "duplicates": 0,  # Duplicates are handled transparently by SimpleDB
            "errors": result["failed_count"],
            "files": result["processed_files"] + result["failed_files"],
            "elapsed_seconds": elapsed,
            "directory": directory,
            "total_files": result["total_files"]
        }
        
        return processed_results

    def ingest_emails(self, since: str = None) -> Dict[str, Any]:
        """
        Process emails via GmailService.
        
        Args:
            since: Date filter (e.g., '2024-01-01', 'last week')
            
        Returns:
            Processing results from email sync
        """
        try:
            from gmail.main import GmailService
            
            logger.info("📧 Starting email ingestion...")
            
            gmail_service = GmailService()
            if since:
                logger.info(f"Filtering emails since: {since}")
                # TODO: Implement date filtering in GmailService if needed
                result = gmail_service.sync_emails()
            else:
                result = gmail_service.sync_emails()
            
            logger.info(f"Email sync complete: {result.get('message', 'Done')}")
            return result
            
        except ImportError as e:
            error_msg = f"Gmail service not available: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "processed": 0
            }
        except Exception as e:
            error_msg = f"Email ingestion failed: {e}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "processed": 0
            }

    def ingest_all(
        self, 
        document_directory: str = "data/Stoneman_dispute/user_data",
        email_since: str = None
    ) -> Dict[str, Any]:
        """
        Process both emails and documents.
        
        Args:
            document_directory: Directory for document processing
            email_since: Date filter for emails
            
        Returns:
            Combined results from both operations
        """
        logger.info("🔄 Starting unified ingestion (emails + documents)")
        start_time = time.time()
        
        # Process emails first
        print("\n📧 Processing Emails...")
        email_results = self.ingest_emails(since=email_since)
        
        # Process documents
        print("\n📄 Processing Documents...")
        doc_results = self.ingest_documents(directory=document_directory)
        
        elapsed = time.time() - start_time
        
        # Combined summary
        total_processed = email_results.get('processed', 0) + doc_results.get('processed', 0)
        total_errors = email_results.get('errors', 0) + doc_results.get('errors', 0)
        
        logger.info(f"✅ Unified ingestion complete in {elapsed:.1f}s")
        logger.info(f"Total processed: {total_processed}, Total errors: {total_errors}")
        
        return {
            "success": True,
            "elapsed_seconds": elapsed,
            "emails": email_results,
            "documents": doc_results,
            "totals": {
                "processed": total_processed,
                "errors": total_errors
            }
        }


def get_ingestion_service() -> UnifiedIngestionService:
    """Get ingestion service instance. Simple factory following CLAUDE.md principles."""
    return UnifiedIngestionService()