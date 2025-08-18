"""
PDF validation and resource checking
"""

import os
from typing import Any

import psutil

# Resource protection constants
MAX_PDF_SIZE = 100 * 1024 * 1024  # 100MB file size limit
MIN_MEMORY_THRESHOLD = 512 * 1024 * 1024  # 512MB minimum available memory


class PDFValidator:
    """Handles PDF validation and resource checking"""

    def validate_pdf_file(self, pdf_path: str) -> dict[str, Any]:
        """Validate PDF file exists and is valid"""
        if not os.path.exists(pdf_path):
            return {"success": False, "error": f"File not found: {pdf_path}"}

        if not pdf_path.lower().endswith(".pdf"):
            return {"success": False, "error": "File must be a PDF"}

        return {"success": True}

    def check_resource_limits(self, pdf_path: str) -> dict[str, Any]:
        """Check resource limits before processing"""
        try:
            # Check file size limit
            file_size = os.path.getsize(pdf_path)
            if file_size > MAX_PDF_SIZE:
                size_mb = file_size / (1024 * 1024)
                max_mb = MAX_PDF_SIZE / (1024 * 1024)
                return {
                    "success": False,
                    "error": f"File size {size_mb:.1f}MB exceeds maximum limit of {max_mb}MB",
                }

            # Check available memory
            available_memory = psutil.virtual_memory().available
            if available_memory < MIN_MEMORY_THRESHOLD:
                available_mb = available_memory / (1024 * 1024)
                min_mb = MIN_MEMORY_THRESHOLD / (1024 * 1024)
                return {
                    "success": False,
                    "error": f"Insufficient memory: {available_mb:.1f}MB available, {min_mb}MB required",
                }

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": f"Resource check failed: {str(e)}"}

    def check_system_health(self) -> dict[str, Any]:
        """System health monitoring"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "success": True,
                "resources": {
                    "memory_available_mb": memory.available / (1024 * 1024),
                    "memory_percent_used": memory.percent,
                    "disk_free_gb": disk.free / (1024 * 1024 * 1024),
                    "disk_percent_used": (disk.used / disk.total) * 100,
                },
            }

        except Exception as e:
            return {"success": False, "error": f"Health check failed: {str(e)}"}

    def get_resource_constants(self) -> dict[str, Any]:
        """Get resource protection constants"""
        return {
            "max_file_size_mb": MAX_PDF_SIZE / (1024 * 1024),
            "memory_threshold_mb": MIN_MEMORY_THRESHOLD / (1024 * 1024),
        }
