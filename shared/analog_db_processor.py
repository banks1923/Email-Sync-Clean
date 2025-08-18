"""
AnalogDBProcessor - Orchestration class for analog database operations.

Manages document processing, file organization, and coordination with existing services.
Uses dependency injection for testability and integrates with SimpleDB for metadata tracking.
"""

import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from shared.analog_db import AnalogDBManager
from shared.file_operations import FileOperations
from shared.retry_helper import retry_on_failure, retry_database
from shared.simple_db import SimpleDB

# Optional integration with EnhancedArchiveManager for better deduplication
try:
    from utilities.enhanced_archive_manager import get_enhanced_archive_manager
    ENHANCED_ARCHIVE_AVAILABLE = True
except ImportError:
    ENHANCED_ARCHIVE_AVAILABLE = False


class AnalogDBError(Exception):
    """Base exception for AnalogDB operations."""
    pass


class FileOperationError(AnalogDBError):
    """Exception for file operation failures."""
    pass


class MetadataError(AnalogDBError):
    """Exception for metadata processing failures."""
    pass


class AnalogDBProcessor:
    """Main orchestration class for analog database operations."""
    
    def __init__(
        self, 
        base_path: Optional[Path] = None,
        db_path: str = "emails.db",
        db_client: Optional[SimpleDB] = None,
        file_ops: Optional[FileOperations] = None,
        retry_helper: Optional[callable] = None,
        use_enhanced_archiving: bool = True
    ):
        """
        Initialize AnalogDBProcessor with dependency injection.
        
        Args:
            base_path: Base directory for analog database
            db_path: Path to SQLite database
            db_client: SimpleDB instance (injected for testing)
            file_ops: File operations handler (injected for testing)
            retry_helper: Retry decorator (injected for testing)
            use_enhanced_archiving: Use EnhancedArchiveManager for deduplication
        """
        self.manager = AnalogDBManager(base_path)
        self.db = db_client or SimpleDB(db_path)
        self.file_ops = file_ops or FileOperations()
        self.retry_helper = retry_helper or retry_on_failure
        
        # Optional enhanced archiving for deduplication
        self.enhanced_archive = None
        if use_enhanced_archiving and ENHANCED_ARCHIVE_AVAILABLE:
            try:
                originals_path = str(self.manager.base_path / "originals")
                archives_path = str(self.manager.base_path / "archives")
                self.enhanced_archive = get_enhanced_archive_manager(originals_path, archives_path)
                self.logger = logger.bind(component="AnalogDBProcessor+Enhanced")
            except Exception as e:
                self.logger.warning(f"Enhanced archiving initialization failed: {e}")
                self.logger = logger.bind(component="AnalogDBProcessor")
        else:
            self.logger = logger.bind(component="AnalogDBProcessor")
        
        # Circuit breaker state
        self._circuit_breaker_state = {}
        
        # Initialize the analog database structure
        self._ensure_setup()
    
    def _ensure_setup(self) -> None:
        """Ensure analog database structure is set up."""
        try:
            if not self.manager.setup():
                raise AnalogDBError("Failed to set up analog database structure")
            self.logger.info("Analog database structure verified")
        except Exception as e:
            self.logger.error(f"Failed to initialize analog database: {e}")
            raise AnalogDBError(f"Initialization failed: {e}")
    
    # Document Processing Methods (lines 50-150)
    
    def process_document(
        self, 
        file_path: str | Path, 
        doc_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for document processing.
        
        Args:
            file_path: Path to document file
            doc_type: Type of document (email, pdf, etc.)
            metadata: Additional metadata
            
        Returns:
            Processing result with document ID and status
        """
        file_path = Path(file_path)
        doc_id = str(uuid.uuid4())
        
        self.logger.bind(doc_id=doc_id).info(f"Starting document processing: {file_path}")
        
        try:
            # Validate document
            if not self.validate_document(file_path):
                raise FileOperationError(f"Document validation failed: {file_path}")
            
            # Extract metadata
            doc_metadata = self.extract_metadata(file_path, doc_type)
            if metadata:
                doc_metadata.update(metadata)
            
            # Create target path
            target_path = self.create_document_path(doc_type, file_path.stem, datetime.now())
            
            # Move to analog database
            if not self.move_to_analog_db(file_path, target_path):
                raise FileOperationError(f"Failed to move document to analog DB: {file_path}")
            
            # Register in SimpleDB
            self.register_document(doc_id, doc_metadata, target_path)
            
            self.logger.bind(doc_id=doc_id).success(f"Document processed successfully: {target_path}")
            
            return {
                "success": True,
                "doc_id": doc_id,
                "target_path": str(target_path),
                "metadata": doc_metadata
            }
            
        except Exception as e:
            self.logger.bind(doc_id=doc_id).error(f"Document processing failed: {e}")
            self.cleanup_on_error(doc_id, file_path)
            return {
                "success": False,
                "error": str(e),
                "doc_id": doc_id
            }
    
    def validate_document(self, file_path: Path) -> bool:
        """
        Validate document before processing.
        
        Args:
            file_path: Path to document
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not self.file_ops.file_exists(file_path):
                self.logger.error(f"File does not exist: {file_path}")
                return False
            
            file_size = self.file_ops.get_file_size(file_path)
            if file_size is None or file_size == 0:
                self.logger.error(f"File is empty: {file_path}")
                return False
            
            # Check if file is too large (> 100MB)
            if file_size > 100 * 1024 * 1024:
                self.logger.error(f"File too large: {file_path} ({file_size} bytes)")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Validation error for {file_path}: {e}")
            return False
    
    def extract_metadata(self, file_path: Path, doc_type: str) -> Dict[str, Any]:
        """
        Extract metadata from document.
        
        Args:
            file_path: Path to document
            doc_type: Type of document
            
        Returns:
            Metadata dictionary
        """
        try:
            # Calculate file hash
            content_hash = self._calculate_file_hash(file_path)
            
            metadata = {
                "doc_id": str(uuid.uuid4()),
                "doc_type": doc_type,
                "date_created": datetime.now().isoformat(),
                "title": file_path.name,
                "schema_version": "1.0.0",
                "file_hash": content_hash,
                "file_size": self.file_ops.get_file_size(file_path),
                "original_path": str(file_path),
                "extraction_method": "analog_processor",
                "processing_timestamp": datetime.now().isoformat()
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Metadata extraction failed for {file_path}: {e}")
            raise MetadataError(f"Failed to extract metadata: {e}")
    
    def chunk_document(self, content: str, chunk_size: int = 900) -> List[str]:
        """
        Split document content into chunks.
        
        Args:
            content: Document content
            chunk_size: Maximum chunk size
            
        Returns:
            List of content chunks
        """
        if not content:
            return []
        
        chunks = []
        words = content.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size > chunk_size and current_chunk:
                # Finalize current chunk
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_size = len(word)
            else:
                current_chunk.append(word)
                current_size += word_size
        
        # Add final chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks
    
    # File Organization Methods (lines 150-250)
    
    def create_document_path(self, doc_type: str, title: str, date: datetime) -> Path:
        """
        Create document path using YYYY-MM-DD naming convention.
        
        Args:
            doc_type: Type of document
            title: Document title
            date: Document date
            
        Returns:
            Target path for document
        """
        # Format date as YYYY-MM-DD
        date_str = date.strftime("%Y-%m-%d")
        
        # Sanitize title
        clean_title = self.file_ops.sanitize_path(title)
        
        # Create filename
        filename = f"{date_str}_{clean_title}.md"
        
        # Determine target directory based on doc_type
        if doc_type == "email":
            target_dir = self.manager.directories["email_threads"]
        else:
            target_dir = self.manager.directories["documents"]
        
        target_path = target_dir / filename
        
        # Handle duplicate names
        target_path = self.handle_duplicate_names(target_path)
        
        return target_path
    
    def organize_by_type(self, file_path: Path, doc_type: str) -> Path:
        """
        Categorize file based on type.
        
        Args:
            file_path: Source file path
            doc_type: Document type
            
        Returns:
            Organized file path
        """
        if doc_type == "email":
            return self.manager.directories["email_threads"] / file_path.name
        elif doc_type == "pdf":
            return self.manager.directories["documents"] / file_path.name
        else:
            return self.manager.directories["documents"] / file_path.name
    
    def move_to_analog_db(self, source_path: Path, target_path: Path) -> bool:
        """
        Move file to analog database with safety checks.
        
        Args:
            source_path: Source file path
            target_path: Target file path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure target directory exists
            if not self.file_ops.create_directory(target_path.parent):
                raise FileOperationError(f"Cannot create target directory: {target_path.parent}")
            
            # Perform the move
            if not self.file_ops.move_file(source_path, target_path):
                raise FileOperationError(f"File move failed: {source_path} -> {target_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Move operation failed: {e}")
            return False
    
    def validate_file_structure(self) -> Dict[str, bool]:
        """
        Validate analog database file structure integrity.
        
        Returns:
            Validation results for each directory
        """
        is_valid, status = self.manager.validate_directory_structure()
        
        results = {}
        for name, dir_status in status.items():
            results[name] = (
                dir_status["exists"] and 
                dir_status["is_directory"] and 
                dir_status["writable"]
            )
        
        return results
    
    def handle_duplicate_names(self, target_path: Path) -> Path:
        """
        Handle duplicate filenames by adding numeric suffix.
        
        Args:
            target_path: Proposed target path
            
        Returns:
            Unique target path
        """
        if not target_path.exists():
            return target_path
        
        base_path = target_path.parent
        stem = target_path.stem
        suffix = target_path.suffix
        
        counter = 1
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            new_path = base_path / new_name
            
            if not new_path.exists():
                return new_path
            
            counter += 1
            
            # Prevent infinite loop
            if counter > 1000:
                raise FileOperationError(f"Too many duplicates for {target_path}")
    
    # SimpleDB Integration Methods (lines 250-350)
    
    @retry_database
    def register_document(self, doc_id: str, metadata: Dict[str, Any], file_path: Path) -> bool:
        """
        Register document in SimpleDB with metadata tracking.
        
        Args:
            doc_id: Document ID
            metadata: Document metadata
            file_path: Path to document file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to content table
            content_id = self.db.add_content(
                content_type=metadata.get("doc_type", "document"),
                title=metadata.get("title", "Unknown"),
                content="",  # Will be populated later if needed
                metadata=metadata,
                source_path=str(file_path)
            )
            
            # Track processing status
            self.track_processing_status(doc_id, "registered")
            
            self.logger.info(f"Document registered: {doc_id} -> {content_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register document {doc_id}: {e}")
            return False
    
    @retry_database
    def update_metadata(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update document metadata in SimpleDB.
        
        Args:
            doc_id: Document ID
            updates: Metadata updates
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find content by doc_id in metadata
            results = self.db.search_content(doc_id, limit=1)
            
            if not results:
                self.logger.error(f"Document not found for update: {doc_id}")
                return False
            
            content = results[0]
            current_metadata = json.loads(content.get("metadata", "{}"))
            current_metadata.update(updates)
            current_metadata["last_updated"] = datetime.now().isoformat()
            
            success = self.db.update_content(
                content["content_id"],
                metadata=current_metadata
            )
            
            if success:
                self.logger.info(f"Metadata updated for document: {doc_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update metadata for {doc_id}: {e}")
            return False
    
    def query_documents(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query documents with optional filters.
        
        Args:
            filters: Query filters
            
        Returns:
            List of matching documents
        """
        try:
            # Build query based on filters
            query = ""
            limit = filters.get("limit", 100) if filters else 100
            
            if filters:
                if "doc_type" in filters:
                    # Search by content type
                    results = self.db.fetch(
                        "SELECT * FROM content WHERE content_type = ? ORDER BY created_at DESC LIMIT ?",
                        (filters["doc_type"], limit)
                    )
                    self.logger.info(f"Document query returned {len(results)} results")
                    return results
                elif "title" in filters:
                    query = filters["title"]
                elif "content" in filters:
                    query = filters["content"]
            
            # Fallback to search_content for general queries
            results = self.db.search_content(query, limit=limit, filters=filters)
            
            self.logger.info(f"Document query returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Document query failed: {e}")
            return []
    
    @retry_database
    def track_processing_status(self, doc_id: str, status: str) -> bool:
        """
        Track document processing status with atomic updates.
        
        Args:
            doc_id: Document ID
            status: Processing status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use a simple approach - just log the status for now
            # In a real implementation, this could be stored in a dedicated status table
            self.logger.info(f"Document {doc_id} status: {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track status for {doc_id}: {e}")
            return False
    
    def handle_transaction_rollback(self, doc_id: str) -> None:
        """
        Handle transaction rollback on failure.
        
        Args:
            doc_id: Document ID to rollback
        """
        try:
            # Try to remove from content table by searching for doc_id in metadata
            results = self.db.fetch("SELECT content_id FROM content WHERE metadata LIKE ?", (f'%{doc_id}%',))
            
            for result in results:
                content_id = result["content_id"]
                self.db.delete_content(content_id)
                self.logger.info(f"Removed content {content_id} during rollback")
            
            self.logger.info(f"Transaction rolled back for document: {doc_id}")
            
        except Exception as e:
            self.logger.error(f"Rollback failed for {doc_id}: {e}")
    
    # Error Handling & Retry Methods (lines 350-400)
    
    def process_with_retry(self, func: callable, *args, **kwargs) -> Any:
        """
        Wrapper for retry logic with exponential backoff.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
        """
        retry_decorator = self.retry_helper(
            max_attempts=3,
            delay=0.5,
            backoff=2.0,
            logger_instance=self.logger
        )
        
        return retry_decorator(func)(*args, **kwargs)
    
    def circuit_breaker_check(self, service_name: str) -> bool:
        """
        Check circuit breaker state for service.
        
        Args:
            service_name: Name of service to check
            
        Returns:
            True if service is available, False if circuit is open
        """
        if service_name not in self._circuit_breaker_state:
            self._circuit_breaker_state[service_name] = {
                "failures": 0,
                "last_failure": None,
                "state": "closed"  # closed, open, half-open
            }
        
        state = self._circuit_breaker_state[service_name]
        
        # If circuit is open, check if enough time has passed to try again
        if state["state"] == "open":
            if state["last_failure"]:
                time_since_failure = (datetime.now() - state["last_failure"]).seconds
                if time_since_failure > 60:  # 1 minute timeout
                    state["state"] = "half-open"
                    return True
            return False
        
        return True
    
    def cleanup_on_error(self, doc_id: str, file_path: Path) -> None:
        """
        Clean up resources on error to maintain consistency.
        
        Args:
            doc_id: Document ID
            file_path: Original file path
        """
        try:
            # Rollback database transaction
            self.handle_transaction_rollback(doc_id)
            
            # Log cleanup action
            self.logger.info(f"Cleaned up after error for document: {doc_id}")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed for {doc_id}: {e}")
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.error(f"Hash calculation failed for {file_path}: {e}")
            return ""