#!/usr/bin/env python3
"""
Simple Export Manager - Direct database to file export.

Replaces complex pipeline export with direct SimpleDB -> clean files export.
Combines functionality from the improved export script we created earlier.
"""

import html
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List

from loguru import logger
from .simple_db import SimpleDB


class SimpleExportManager:
    """Direct export from database to organized file structure."""

    def __init__(self):
        self.db = SimpleDB()

    def export_all_documents(self, target_dir: Path, organize_by_type: bool = True) -> Dict[str, Any]:
        """
        Export all documents as clean text files.
        
        Args:
            target_dir: Directory to export files to
            organize_by_type: Whether to organize files into subdirectories by type
            
        Returns:
            Export results with counts and file paths
        """
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)

        # Create organized subdirectories if requested
        if organize_by_type:
            (target_path / "emails").mkdir(exist_ok=True)
            (target_path / "pdfs").mkdir(exist_ok=True)
            (target_path / "uploads").mkdir(exist_ok=True)

        logger.info(f"Starting export to {target_dir}")

        # Get all content from database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, source_type, title, body, created_at, sha256, chunk_index
                FROM content_unified
                WHERE body IS NOT NULL AND body != ''
                ORDER BY source_type, created_at, chunk_index
            ''')
            content_items = cursor.fetchall()

        logger.info(f"Found {len(content_items)} content items to export")

        # Group PDF chunks and process
        pdf_chunks_by_sha, other_content = self._group_pdf_chunks(content_items)
        combined_pdfs = self._combine_pdf_chunks(pdf_chunks_by_sha)

        # Process all content
        all_content = combined_pdfs + other_content
        
        exported_count = 0
        source_counts = {}
        exported_files = []

        for item in all_content:
            content_id, source_type, title, body, created_at, sha256, chunk_info = item
            
            # Count by source type
            source_counts[source_type] = source_counts.get(source_type, 0) + 1
            
            # Clean content based on type
            if source_type == 'email':
                cleaned_body = self._clean_html_content(body)
            else:
                cleaned_body = body
            
            # Generate filename and path
            file_info = self._create_export_file(
                target_path, content_id, source_type, title, cleaned_body,
                created_at, sha256, chunk_info, organize_by_type
            )
            
            if file_info["success"]:
                exported_count += 1
                exported_files.append(file_info["file_path"])
                
                if exported_count % 50 == 0:
                    logger.info(f"Exported {exported_count} files...")

        # Summary
        logger.info(f"Export complete: {exported_count} files exported")
        for source_type, count in sorted(source_counts.items()):
            logger.info(f"  {source_type}: {count} files")

        return {
            "success": True,
            "exported_count": exported_count,
            "source_counts": source_counts,
            "exported_files": exported_files,
            "target_directory": str(target_path)
        }

    def export_by_content_type(self, content_type: str, target_dir: Path) -> Dict[str, Any]:
        """Export only files of a specific content type."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, source_type, title, body, created_at, sha256, chunk_index
                FROM content_unified
                WHERE source_type = ? AND body IS NOT NULL AND body != ''
                ORDER BY created_at, chunk_index
            ''', (content_type,))
            content_items = cursor.fetchall()

        logger.info(f"Exporting {len(content_items)} {content_type} documents to {target_dir}")
        
        target_path = Path(target_dir)
        target_path.mkdir(parents=True, exist_ok=True)
        
        exported_files = []
        for item in content_items:
            content_id, source_type, title, body, created_at, sha256, chunk_info = item
            
            # Clean content if needed
            if source_type == 'email':
                cleaned_body = self._clean_html_content(body)
            else:
                cleaned_body = body
                
            file_info = self._create_export_file(
                target_path, content_id, source_type, title, cleaned_body,
                created_at, sha256, chunk_info, organize_by_type=False
            )
            
            if file_info["success"]:
                exported_files.append(file_info["file_path"])

        return {
            "success": True,
            "exported_count": len(exported_files),
            "content_type": content_type,
            "exported_files": exported_files
        }

    def _group_pdf_chunks(self, content_items: List) -> tuple:
        """Group PDF chunks by SHA256 hash for combining."""
        chunks_by_sha = defaultdict(list)
        other_content = []
        
        for item in content_items:
            content_id, source_type, title, body, created_at, sha256, chunk_index = item
            
            if source_type == 'pdf' and sha256 and chunk_index is not None:
                chunks_by_sha[sha256].append(item)
            else:
                other_content.append(item)
        
        # Sort chunks within each document by chunk_index
        for sha256_hash in chunks_by_sha:
            chunks_by_sha[sha256_hash].sort(key=lambda x: x[6])  # Sort by chunk_index
        
        return dict(chunks_by_sha), other_content

    def _combine_pdf_chunks(self, chunks_by_sha: Dict) -> List:
        """Combine PDF chunks into complete documents."""
        combined_pdfs = []
        
        for sha256_hash, chunks in chunks_by_sha.items():
            if not chunks:
                continue
                
            # Use first chunk for metadata, combine all content
            first_chunk = chunks[0]
            content_id, source_type, title, _, created_at, sha256, _ = first_chunk
            
            # Combine all chunk content
            combined_content = []
            for chunk in chunks:
                if chunk[3]:  # If body content exists
                    combined_content.append(chunk[3])
            
            full_content = '\n\n'.join(combined_content)
            chunk_info = f"combined_{len(chunks)}_chunks"
            
            combined_pdfs.append((content_id, source_type, title, full_content, created_at, sha256, chunk_info))
        
        return combined_pdfs

    def _clean_html_content(self, html_content: str) -> str:
        """Enhanced HTML cleaning for email content."""
        if not html_content or not isinstance(html_content, str):
            return ""
        
        text = html_content
        
        # Remove script and style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove Microsoft Office XML
        text = re.sub(r'<o:[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</o:[^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<!--\[if[^>]*>.*?<!\[endif\]-->', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<xml>.*?</xml>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Convert block elements to line breaks
        block_elements = ['div', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']
        for element in block_elements:
            text = re.sub(f'<{element}[^>]*>', '\n', text, flags=re.IGNORECASE)
            text = re.sub(f'</{element}>', '\n', text, flags=re.IGNORECASE)
        
        # Convert list items
        text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
        text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)
        
        # Remove remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = html.unescape(text)
        
        # Clean up whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r'&nbsp;', ' ', text)
        
        # Clean email artifacts
        text = re.sub(r'^\s*>', '', text, flags=re.MULTILINE)
        text = re.sub(r'\n\s*\n\s*On.*wrote:\s*\n', '\n\n[Previous email content]\n', text, flags=re.IGNORECASE)
        
        return text.strip()

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for filesystem safety."""
        if not filename:
            return "untitled"
        
        filename = re.sub(r'<[^>]+>', '', filename)  # Remove HTML
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Replace problematic chars
        filename = re.sub(r'\s+', ' ', filename).strip()  # Normalize whitespace
        
        if len(filename) > 100:
            filename = filename[:97] + "..."
        
        return filename or "untitled"

    def _create_export_file(self, target_path: Path, content_id: int, source_type: str, 
                           title: str, content: str, created_at: str, sha256: str, 
                           chunk_info: Any, organize_by_type: bool) -> Dict[str, Any]:
        """Create export file with proper naming and organization."""
        try:
            # Generate safe filename
            safe_title = self._sanitize_filename(title) if title else f"content_{content_id}"
            
            # Add chunk info for PDFs
            if isinstance(chunk_info, str) and chunk_info.startswith('combined_'):
                safe_title += f"_{chunk_info}"
            
            # Determine file location
            if organize_by_type:
                if source_type == 'email':
                    subdir = target_path / "emails"
                    filename = f"email_{content_id:04d}_{safe_title}.txt"
                elif source_type == 'pdf':
                    subdir = target_path / "pdfs"
                    filename = f"pdf_{content_id:04d}_{safe_title}.txt"
                elif source_type == 'upload':
                    subdir = target_path / "uploads"
                    filename = f"upload_{content_id:04d}_{safe_title}.txt"
                else:
                    subdir = target_path
                    filename = f"{source_type}_{content_id:04d}_{safe_title}.txt"
            else:
                subdir = target_path
                filename = f"{source_type}_{content_id:04d}_{safe_title}.txt"
            
            filepath = subdir / filename
            
            # Create file header
            header = f"""Document ID: {content_id}
Source Type: {source_type}
Title: {title or 'Untitled'}
Created: {created_at}
SHA256: {sha256 or 'N/A'}
Chunk Info: {chunk_info if chunk_info is not None else 'N/A'}
Content Length: {len(content):,} characters

{'=' * 80}

"""
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(header)
                f.write(content)
            
            return {
                "success": True,
                "file_path": str(filepath),
                "filename": filename
            }
            
        except Exception as e:
            logger.error(f"Failed to create export file for content {content_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def get_export_manager() -> SimpleExportManager:
    """Get export manager instance."""
    return SimpleExportManager()