"""Pipeline Orchestrator for Document Processing

Manages document lifecycle through stages:
raw → staged → processed → quarantine/export
"""

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

# Logger is now imported globally from loguru


class PipelineOrchestrator:
    """Orchestrates document processing through pipeline stages."""

    STAGES = ["raw", "staged", "processed", "quarantine", "export"]

    def __init__(self, data_dir: str = "data"):
        """Initialize the pipeline orchestrator.

        Args:
            data_dir: Root directory for pipeline data
        """
        self.data_dir = Path(data_dir)
        self._validate_and_create_folders()
        logger.info(f"Pipeline orchestrator initialized with data_dir: {self.data_dir}")

    def _validate_and_create_folders(self) -> None:
        """Ensure all pipeline stage directories exist."""
        for stage in self.STAGES:
            stage_dir = self.data_dir / stage
            stage_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Validated stage directory: {stage_dir}")

    def generate_pipeline_id(self) -> str:
        """Generate unique pipeline ID for document tracking.

        Returns:
            str: UUID-based pipeline identifier
        """
        pipeline_id = str(uuid.uuid4())
        logger.debug(f"Generated pipeline_id: {pipeline_id}")
        return pipeline_id

    def move_to_stage(self, pipeline_id: str, from_stage: str, to_stage: str) -> bool:
        """Move document between pipeline stages.

        Args:
            pipeline_id: Document pipeline identifier
            from_stage: Current stage (e.g., 'raw')
            to_stage: Target stage (e.g., 'staged')

        Returns:
            bool: True if successful, False otherwise
        """
        if from_stage not in self.STAGES or to_stage not in self.STAGES:
            logger.error(f"Invalid stage: from={from_stage}, to={to_stage}")
            return False

        from_dir = self.data_dir / from_stage
        to_dir = self.data_dir / to_stage

        # Find all files with this pipeline_id
        moved_count = 0
        for file_path in from_dir.glob(f"{pipeline_id}*"):
            dest_path = to_dir / file_path.name
            try:
                shutil.move(str(file_path), str(dest_path))
                moved_count += 1
                logger.debug(f"Moved {file_path.name} from {from_stage} to {to_stage}")
            except Exception as e:
                logger.error(f"Failed to move {file_path.name}: {e}")
                return False

        if moved_count > 0:
            logger.info(
                f"Moved {moved_count} files for {pipeline_id} from {from_stage} to {to_stage}"
            )
            return True
        else:
            logger.warning(f"No files found for {pipeline_id} in {from_stage}")
            return False

    def create_metadata(self, pipeline_id: str, stage: str, metadata: dict[str, Any]) -> str:
        """Create metadata file for document.

        Args:
            pipeline_id: Document pipeline identifier
            stage: Current pipeline stage
            metadata: Metadata dictionary to save

        Returns:
            str: Path to created metadata file
        """
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}")

        # Add timestamp and pipeline info
        metadata.update(
            {
                "pipeline_id": pipeline_id,
                "stage": stage,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "updated_at": datetime.utcnow().isoformat() + "Z",
            }
        )

        # Save metadata file
        meta_path = self.data_dir / stage / f"{pipeline_id}.meta.json"
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"Created metadata for {pipeline_id} in {stage}")
        return str(meta_path)

    def update_metadata(self, pipeline_id: str, stage: str, updates: dict[str, Any]) -> bool:
        """Update existing metadata file.

        Args:
            pipeline_id: Document pipeline identifier
            stage: Current pipeline stage
            updates: Dictionary of updates to apply

        Returns:
            bool: True if successful, False otherwise
        """
        meta_path = self.data_dir / stage / f"{pipeline_id}.meta.json"

        if not meta_path.exists():
            logger.error(f"Metadata not found: {meta_path}")
            return False

        try:
            # Load existing metadata
            with open(meta_path) as f:
                metadata = json.load(f)

            # Apply updates
            metadata.update(updates)
            metadata["updated_at"] = datetime.utcnow().isoformat() + "Z"

            # Save updated metadata
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)

            logger.info(f"Updated metadata for {pipeline_id} in {stage}")
            return True

        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return False

    def get_metadata(self, pipeline_id: str, stage: str) -> dict[str, Any] | None:
        """Retrieve metadata for a document.

        Args:
            pipeline_id: Document pipeline identifier
            stage: Pipeline stage to check

        Returns:
            Dict or None: Metadata if found, None otherwise
        """
        meta_path = self.data_dir / stage / f"{pipeline_id}.meta.json"

        if not meta_path.exists():
            return None

        try:
            with open(meta_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metadata: {e}")
            return None

    def list_documents(self, stage: str) -> list[str]:
        """List all pipeline IDs in a given stage.

        Args:
            stage: Pipeline stage to list

        Returns:
            List[str]: List of pipeline IDs in the stage
        """
        if stage not in self.STAGES:
            logger.error(f"Invalid stage: {stage}")
            return []

        stage_dir = self.data_dir / stage
        pipeline_ids = set()

        for meta_file in stage_dir.glob("*.meta.json"):
            pipeline_id = meta_file.stem.replace(".meta", "")
            pipeline_ids.add(pipeline_id)

        return sorted(list(pipeline_ids))

    def quarantine_document(
        self, pipeline_id: str, current_stage: str, error_info: dict[str, Any]
    ) -> bool:
        """Move document to quarantine with error information.

        Args:
            pipeline_id: Document pipeline identifier
            current_stage: Current stage of document
            error_info: Error details to log

        Returns:
            bool: True if quarantined successfully
        """
        # First move the document
        if not self.move_to_stage(pipeline_id, current_stage, "quarantine"):
            return False

        # Update metadata with error info
        metadata_updates = {
            "quarantined_at": datetime.utcnow().isoformat() + "Z",
            "quarantined_from": current_stage,
            "error_info": error_info,
            "status": "quarantined",
        }

        return self.update_metadata(pipeline_id, "quarantine", metadata_updates)

    def get_stage_stats(self) -> dict[str, int]:
        """Get document count for each stage.

        Returns:
            Dict[str, int]: Count of documents in each stage
        """
        stats = {}
        for stage in self.STAGES:
            docs = self.list_documents(stage)
            stats[stage] = len(docs)

        return stats

    def process_raw_document(self, pipeline_id: str, document_type: str) -> bool:
        """Process a document from raw stage through the pipeline.

        Args:
            pipeline_id: Document pipeline identifier
            document_type: Type of document (email, pdf, transcription)

        Returns:
            bool: True if processing successful
        """
        from infrastructure.pipelines.processors import get_processor

        try:
            # Get the appropriate processor
            processor = get_processor(document_type)

            # Load raw document and metadata
            raw_metadata = self.get_metadata(pipeline_id, "raw")
            if not raw_metadata:
                logger.error(f"No metadata found for {pipeline_id} in raw")
                return False

            # Find and read the document file
            raw_dir = self.data_dir / "raw"
            doc_files = list(raw_dir.glob(f"{pipeline_id}_*"))
            if not doc_files:
                logger.error(f"No document file found for {pipeline_id} in raw")
                return False

            doc_file = doc_files[0]
            with open(doc_file) as f:
                content = f.read()

            # Validate document
            is_valid, error_msg = processor.validate(content, raw_metadata)
            if not is_valid:
                logger.error(f"Validation failed for {pipeline_id}: {error_msg}")
                self.quarantine_document(
                    pipeline_id, "raw", {"error": "validation_failed", "message": error_msg}
                )
                return False

            # Process document
            processed_content, updated_metadata = processor.process(content, raw_metadata)

            # Stage the processed document
            return self.stage_document(
                pipeline_id,
                processed_content,
                doc_file.name.replace(f"{pipeline_id}_", ""),
                updated_metadata,
            )

        except Exception as e:
            logger.error(f"Failed to process raw document {pipeline_id}: {e}")
            self.quarantine_document(
                pipeline_id, "raw", {"error": "processing_failed", "message": str(e)}
            )
            return False

    def stage_document(
        self, pipeline_id: str, content: str, filename: str, metadata: dict[str, Any]
    ) -> bool:
        """Stage a document for further processing.

        Args:
            pipeline_id: Document pipeline identifier
            content: Processed document content
            filename: Original filename
            metadata: Document metadata

        Returns:
            bool: True if staging successful
        """
        try:
            # Save to staged directory
            staged_path = self.data_dir / "staged" / f"{pipeline_id}_{filename}"
            with open(staged_path, "w") as f:
                f.write(content)

            # Update metadata
            metadata.update(
                {
                    "stage": "staged",
                    "staged_at": datetime.utcnow().isoformat() + "Z",
                    "staged_file": staged_path.name,
                }
            )

            # Create/update metadata in staged
            self.create_metadata(pipeline_id, "staged", metadata)

            # Move from raw to staged
            self.move_to_stage(pipeline_id, "raw", "staged")

            logger.info(f"Staged document {pipeline_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to stage document {pipeline_id}: {e}")
            return False

    def process_staged_document(self, pipeline_id: str) -> bool:
        """Process staged document with intelligence extraction.

        Args:
            pipeline_id: Document pipeline identifier

        Returns:
            bool: True if processing successful
        """
        from infrastructure.pipelines.formats import get_document_formatter
        from infrastructure.pipelines.intelligence import DocumentIntelligence

        try:
            # Load staged document
            staged_metadata = self.get_metadata(pipeline_id, "staged")
            if not staged_metadata:
                logger.error(f"No metadata found for {pipeline_id} in staged")
                return False

            staged_dir = self.data_dir / "staged"
            doc_files = list(staged_dir.glob(f"{pipeline_id}_*"))
            if not doc_files:
                logger.error(f"No document file found for {pipeline_id} in staged")
                return False

            doc_file = doc_files[0]
            with open(doc_file) as f:
                content = f.read()

            # Extract intelligence
            intelligence = DocumentIntelligence()
            intel_data = intelligence.extract_all(content, staged_metadata)

            # Format document
            formatter = get_document_formatter()
            formatted = formatter.format_document(
                pipeline_id=pipeline_id,
                title=staged_metadata.get("title", staged_metadata.get("subject", "Document")),
                content=content,
                metadata=staged_metadata,
                intelligence=intel_data,
            )

            # Save formatted documents to processed
            saved_files = formatter.save_formatted_document(
                pipeline_id=pipeline_id,
                output_dir=str(self.data_dir / "processed"),
                formatted_content=formatted,
            )

            # Update metadata
            staged_metadata.update(
                {
                    "stage": "processed",
                    "processed_at": datetime.utcnow().isoformat() + "Z",
                    "output_files": saved_files,
                    "intelligence_extracted": True,
                }
            )

            # Create metadata in processed
            self.create_metadata(pipeline_id, "processed", staged_metadata)

            # Move from staged to processed
            self.move_to_stage(pipeline_id, "staged", "processed")

            logger.info(f"Processed document {pipeline_id} with intelligence extraction")
            return True

        except Exception as e:
            logger.error(f"Failed to process staged document {pipeline_id}: {e}")
            self.quarantine_document(
                pipeline_id,
                "staged",
                {"error": "intelligence_extraction_failed", "message": str(e)},
            )
            return False

    def export_document(self, pipeline_id: str, export_format: str = "markdown") -> bool:
        """Export processed document to final format.

        Args:
            pipeline_id: Document pipeline identifier
            export_format: Export format (markdown, json, both)

        Returns:
            bool: True if export successful
        """
        try:
            # Load processed document
            processed_dir = self.data_dir / "processed"

            # Determine which files to export
            files_to_export = []
            if export_format in ["markdown", "both"]:
                md_file = processed_dir / f"{pipeline_id}.md"
                if md_file.exists():
                    files_to_export.append(md_file)

            if export_format in ["json", "both"]:
                json_file = processed_dir / f"{pipeline_id}.json"
                if json_file.exists():
                    files_to_export.append(json_file)

            if not files_to_export:
                logger.error(f"No files found for export: {pipeline_id}")
                return False

            # Copy files to export directory
            export_dir = self.data_dir / "export"
            for file_path in files_to_export:
                dest_path = export_dir / file_path.name
                shutil.copy2(str(file_path), str(dest_path))
                logger.info(f"Exported {file_path.name} to export directory")

            # Update metadata
            metadata = self.get_metadata(pipeline_id, "processed")
            if metadata:
                metadata.update(
                    {
                        "exported_at": datetime.utcnow().isoformat() + "Z",
                        "export_format": export_format,
                        "exported_files": [f.name for f in files_to_export],
                    }
                )
                self.create_metadata(pipeline_id, "export", metadata)

            logger.info(f"Exported document {pipeline_id} as {export_format}")
            return True

        except Exception as e:
            logger.error(f"Failed to export document {pipeline_id}: {e}")
            return False

    def save_document_to_stage(
        self,
        content: str,
        filename: str,
        stage: str,
        pipeline_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Save a document directly to a stage.

        Args:
            content: Document content to save
            filename: Original filename
            stage: Target stage
            pipeline_id: Optional pipeline ID (generates if not provided)
            metadata: Optional metadata to save

        Returns:
            str: Pipeline ID of saved document
        """
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}")

        # Generate pipeline ID if not provided
        if pipeline_id is None:
            pipeline_id = self.generate_pipeline_id()

        # Save the document
        doc_path = self.data_dir / stage / f"{pipeline_id}_{filename}"
        with open(doc_path, "w") as f:
            f.write(content)

        # Create metadata
        if metadata is None:
            metadata = {}

        metadata.update(
            {
                "original_filename": filename,
                "content_size": len(content),
                "saved_at": datetime.utcnow().isoformat() + "Z",
            }
        )

        self.create_metadata(pipeline_id, stage, metadata)

        logger.info(f"Saved document {pipeline_id} to {stage}")
        return pipeline_id
