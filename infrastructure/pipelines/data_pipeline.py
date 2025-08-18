"""
Data Pipeline Orchestrator - Manages file movement through pipeline stages

Pipeline Stages:
1. raw/ - Incoming unprocessed documents
2. staged/ - Documents being processed
3. processed/ - Successfully processed documents
4. quarantine/ - Failed processing documents
5. export/ - Documents ready for external systems
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger


class DataPipelineOrchestrator:
    """Manages document movement through processing pipeline stages"""

    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.stages = {
            "raw": self.base_path / "raw",
            "staged": self.base_path / "staged",
            "processed": self.base_path / "processed",
            "quarantine": self.base_path / "quarantine",
            "export": self.base_path / "export",
        }
        # Logger is now imported globally from loguru
        self._validate_directories()

    def _validate_directories(self):
        """Ensure all pipeline directories exist"""
        for stage, path in self.stages.items():
            path.mkdir(parents=True, exist_ok=True)

    def add_to_raw(self, file_path: str, copy: bool = False) -> dict[str, Any]:
        """Add file to raw stage for processing"""
        try:
            source = Path(file_path)
            if not source.exists():
                return {"success": False, "error": f"File not found: {file_path}"}

            dest = self.stages["raw"] / source.name

            # Handle duplicate filenames
            if dest.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = source.stem, timestamp, source.suffix
                dest = self.stages["raw"] / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"

            if copy:
                shutil.copy2(source, dest)
            else:
                shutil.move(str(source), str(dest))

            logger.info(f"Added {source.name} to raw stage")
            return {"success": True, "path": str(dest), "stage": "raw"}

        except Exception as e:
            logger.error(f"Failed to add file to raw: {e}")
            return {"success": False, "error": str(e)}

    def move_to_staged(self, filename: str) -> dict[str, Any]:
        """Move file from raw to staged for processing"""
        return self._move_between_stages(filename, "raw", "staged")

    def move_to_processed(self, filename: str, metadata: dict | None = None) -> dict[str, Any]:
        """Move file from staged to processed after successful processing"""
        result = self._move_between_stages(filename, "staged", "processed")

        if result["success"] and metadata:
            # Save metadata alongside processed file
            meta_path = Path(result["path"]).with_suffix(".meta.json")
            with open(meta_path, "w") as f:
                json.dump(metadata, f, indent=2)

        return result

    def move_to_quarantine(
        self, filename: str, error: str, from_stage: str = "staged"
    ) -> dict[str, Any]:
        """Move file to quarantine after processing failure"""
        result = self._move_between_stages(filename, from_stage, "quarantine")

        if result["success"]:
            # Save error information
            error_path = Path(result["path"]).with_suffix(".error.json")
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "from_stage": from_stage,
                "error": error,
                "filename": filename,
            }
            with open(error_path, "w") as f:
                json.dump(error_data, f, indent=2)

        return result

    def prepare_for_export(self, filename: str, from_stage: str = "processed") -> dict[str, Any]:
        """Move file to export stage for external systems"""
        return self._move_between_stages(filename, from_stage, "export")

    def _move_between_stages(self, filename: str, from_stage: str, to_stage: str) -> dict[str, Any]:
        """Generic method to move files between pipeline stages"""
        try:
            if from_stage not in self.stages or to_stage not in self.stages:
                return {"success": False, "error": f"Invalid stage: {from_stage} or {to_stage}"}

            source = self.stages[from_stage] / filename
            if not source.exists():
                return {"success": False, "error": f"File not found in {from_stage}: {filename}"}

            dest = self.stages[to_stage] / filename

            # Handle duplicate filenames in destination
            if dest.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = Path(filename).stem, timestamp, Path(filename).suffix
                dest = self.stages[to_stage] / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"

            shutil.move(str(source), str(dest))

            logger.info(f"Moved {filename} from {from_stage} to {to_stage}")
            return {"success": True, "path": str(dest), "stage": to_stage}

        except Exception as e:
            logger.error(f"Failed to move file: {e}")
            return {"success": False, "error": str(e)}

    def get_stage_files(self, stage: str) -> list[str]:
        """List all files in a given stage"""
        if stage not in self.stages:
            return []

        path = self.stages[stage]
        return [f.name for f in path.iterdir() if f.is_file() and not f.name.startswith(".")]

    def get_pipeline_stats(self) -> dict[str, int]:
        """Get count of files in each pipeline stage"""
        stats = {}
        for stage in self.stages:
            files = self.get_stage_files(stage)
            # Exclude metadata and error files from count
            stats[stage] = len(
                [f for f in files if not (f.endswith(".meta.json") or f.endswith(".error.json"))]
            )
        return stats

    def cleanup_export(self, older_than_days: int = 7) -> int:
        """Remove exported files older than specified days"""
        count = 0
        export_path = self.stages["export"]
        cutoff = datetime.now().timestamp() - (older_than_days * 86400)

        for file in export_path.iterdir():
            if file.is_file() and file.stat().st_mtime < cutoff:
                file.unlink()
                count += 1

        logger.info(f"Cleaned up {count} exported files older than {older_than_days} days")
        return count
