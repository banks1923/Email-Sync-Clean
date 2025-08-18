"""
Document Exporter - Sequential file export with markdown formatting

Architecture:
- Simple counter management via .counter file
- YAML frontmatter + markdown content formatting
- Sequential numbering: 0001_filename.md, 0002_filename.md, etc.
- Service independent, never breaks calling services
"""

import json
import os
import re
from datetime import datetime
from typing import Any

from shared.simple_db import SimpleDB
from shared.html_cleaner import extract_email_content


class DocumentExporter:
    """Export documents to markdown files with sequential numbering"""

    def __init__(self, export_dir: str = "data/export"):
        self.export_dir = export_dir
        self.counter_file = os.path.join(export_dir, ".counter")
        self.db = SimpleDB()

        # Ensure export directory exists
        os.makedirs(export_dir, exist_ok=True)

    def get_next_counter(self) -> int:
        """Get next sequential counter number"""
        try:
            if os.path.exists(self.counter_file):
                with open(self.counter_file) as f:
                    current = int(f.read().strip())
            else:
                current = 0

            next_counter = current + 1

            # Write new counter value
            with open(self.counter_file, "w") as f:
                f.write(str(next_counter))

            return next_counter
        except Exception:
            # If anything fails, start from 1
            with open(self.counter_file, "w") as f:
                f.write("1")
            return 1

    def format_as_markdown(
        self, content_dict: dict[str, Any], summary_dict: dict | None = None
    ) -> str:
        """Format content as markdown with YAML frontmatter"""
        # Extract basic info
        content_type = content_dict.get("content_type", "document")
        title = content_dict.get("title", "Untitled Document")
        content = content_dict.get("content", "")
        created_at = content_dict.get(
            "created_time", content_dict.get("created_at", datetime.now().isoformat())
        )

        # Parse metadata if it's a JSON string
        metadata = content_dict.get("metadata", {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}

        # Extract email metadata if this is HTML email content
        email_metadata = {}
        if content_type == "email" and content and "<" in content and ">" in content:
            _, email_metadata = extract_email_content(content)

        # Create YAML frontmatter with all metadata
        yaml_front = f"""---
doc_id: {content_dict.get("content_id", "unknown")}
doc_type: {content_type}
date_created: {created_at}
title: "{title}"
schema_version: "1.0.0"
export_timestamp: "{datetime.now().isoformat()}"
"""

        # Add original metadata fields
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, str):
                    yaml_front += f'{key}: "{value}"\n'
                else:
                    yaml_front += f"{key}: {json.dumps(value)}\n"

        # Add extracted email metadata
        if email_metadata:
            for key, value in email_metadata.items():
                if key not in metadata:  # Don't override existing metadata
                    yaml_front += f'{key}: "{value}"\n'

        yaml_front += "---\n\n"

        # Format content sections
        markdown_content = f"# {title}\n\n"

        # Add summary if available
        if summary_dict:
            markdown_content += "## Summary\n\n"
            if summary_dict.get("summary_text"):
                markdown_content += f"{summary_dict['summary_text']}\n\n"

            if summary_dict.get("tf_idf_keywords"):
                keywords = summary_dict["tf_idf_keywords"]
                if isinstance(keywords, dict):
                    keyword_list = [
                        k for k, v in sorted(keywords.items(), key=lambda x: x[1], reverse=True)
                    ]
                    markdown_content += f"**Keywords**: {', '.join(keyword_list[:10])}\n\n"

        # Add main content
        markdown_content += "## Content\n\n"
        
        # Clean content if it's HTML (common for emails)
        if content_type == "email" and content and "<" in content and ">" in content:
            # This looks like HTML email content - extract clean text
            cleaned_content, _ = extract_email_content(content)  # Metadata already extracted above
            markdown_content += cleaned_content
        else:
            # Regular content or already clean
            markdown_content += content

        return yaml_front + markdown_content

    def generate_filename(self, title: str, counter: int) -> str:
        """Generate sequential filename: 0001_title.md"""
        # Clean title for filename
        clean_title = re.sub(r"[^\w\s-]", "", title)
        clean_title = re.sub(r"[-\s]+", "_", clean_title)
        clean_title = clean_title[:50]  # Limit length

        # Format counter with leading zeros
        counter_str = f"{counter:04d}"

        return f"{counter_str}_{clean_title}.md"

    def save_to_export(self, content_id: str, filename_hint: str = "") -> dict[str, Any]:
        """Export content to markdown file with sequential numbering"""
        try:
            # Get content from database
            content_dict = self.db.get_content(content_id=content_id)
            if not content_dict:
                return {"success": False, "error": f"Content not found: {content_id}"}

            # Get summary if available
            summary_dict = None
            summaries = self.db.get_document_summaries(content_id)
            if summaries:
                summary_dict = summaries[0]  # Use first summary

            # Generate filename
            counter = self.get_next_counter()
            title = filename_hint or content_dict.get("title", "document")
            filename = self.generate_filename(title, counter)
            filepath = os.path.join(self.export_dir, filename)

            # Format content as markdown
            markdown_content = self.format_as_markdown(content_dict, summary_dict)

            # Write file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            # Update manifest.txt
            self._update_manifest(counter, filename, content_id, title)

            return {"success": True, "filepath": filepath, "filename": filename, "counter": counter}

        except Exception as e:
            return {"success": False, "error": f"Export failed: {str(e)}"}

    def _update_manifest(self, counter: int, filename: str, content_id: str, title: str) -> None:
        """Update manifest.txt with exported document mapping"""
        try:
            manifest_path = os.path.join(self.export_dir, "manifest.txt")
            timestamp = datetime.now().isoformat()

            # Append to manifest
            with open(manifest_path, "a", encoding="utf-8") as f:
                f.write(f"{counter:04d}\t{filename}\t{content_id}\t{title[:100]}\t{timestamp}\n")

        except Exception:
            # Don't fail export if manifest update fails
            pass
