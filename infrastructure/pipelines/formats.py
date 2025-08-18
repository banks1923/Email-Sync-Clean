"""Unified Document Output Formats

Provides formatters for consistent document representation:
- Markdown with YAML frontmatter
- JSON companion files with structured metadata
"""

import json
from datetime import datetime
from typing import Any

import yaml
from loguru import logger

# Logger is now imported globally from loguru


class MarkdownFormatter:
    """Format documents as Markdown with YAML frontmatter."""

    @staticmethod
    def format(pipeline_id: str, title: str, content: str, metadata: dict[str, Any]) -> str:
        """Format document as Markdown with YAML frontmatter.

        Args:
            pipeline_id: Document pipeline identifier
            title: Document title
            content: Main document content
            metadata: Additional metadata for frontmatter

        Returns:
            str: Formatted Markdown document
        """
        # Build frontmatter
        frontmatter = {
            "pipeline_id": pipeline_id,
            "title": title,
            "date": metadata.get("date", datetime.utcnow().isoformat()),
            "content_type": metadata.get("content_type", "document"),
            "tags": metadata.get("tags", []),
            "summary": metadata.get("summary", ""),
        }

        # Add custom metadata
        for key, value in metadata.items():
            if key not in frontmatter:
                frontmatter[key] = value

        # Format as YAML frontmatter
        yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

        # Build final document
        markdown = f"---\n{yaml_str}---\n\n"
        markdown += f"# {title}\n\n"
        markdown += content

        return markdown

    @staticmethod
    def parse(markdown_content: str) -> dict[str, Any]:
        """Parse Markdown document with YAML frontmatter.

        Args:
            markdown_content: Markdown document string

        Returns:
            Dict with 'frontmatter' and 'content' keys
        """
        if not markdown_content.startswith("---"):
            return {"frontmatter": {}, "content": markdown_content}

        # Find end of frontmatter
        end_marker = markdown_content.find("\n---\n", 4)
        if end_marker == -1:
            return {"frontmatter": {}, "content": markdown_content}

        # Extract and parse frontmatter
        frontmatter_str = markdown_content[4:end_marker]
        try:
            frontmatter = yaml.safe_load(frontmatter_str)
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML frontmatter: {e}")
            frontmatter = {}

        # Extract content
        content = markdown_content[end_marker + 5 :].strip()

        return {"frontmatter": frontmatter, "content": content}


class JSONCompanionFormatter:
    """Format structured metadata as JSON companion files."""

    @staticmethod
    def format(
        pipeline_id: str,
        intelligence: dict[str, Any],
        embeddings: dict[str, Any] | None = None,
        search_index: dict[str, Any] | None = None,
    ) -> str:
        """Format document intelligence as JSON.

        Args:
            pipeline_id: Document pipeline identifier
            intelligence: Extracted intelligence data
            embeddings: Optional embedding information
            search_index: Optional search index information

        Returns:
            str: JSON-formatted string
        """
        companion = {
            "pipeline_id": pipeline_id,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "intelligence": intelligence,
        }

        if embeddings:
            companion["embeddings"] = embeddings

        if search_index:
            companion["search_index"] = search_index

        return json.dumps(companion, indent=2, default=str)

    @staticmethod
    def parse(json_content: str) -> dict[str, Any]:
        """Parse JSON companion file.

        Args:
            json_content: JSON string

        Returns:
            Dict: Parsed JSON data
        """
        try:
            return json.loads(json_content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {}


class UnifiedDocumentFormatter:
    """Combines Markdown and JSON formatters for complete document output."""

    def __init__(self):
        """Initialize the unified formatter."""
        self.markdown = MarkdownFormatter()
        self.json_companion = JSONCompanionFormatter()

    def format_document(
        self,
        pipeline_id: str,
        title: str,
        content: str,
        metadata: dict[str, Any],
        intelligence: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Format document in both Markdown and JSON formats.

        Args:
            pipeline_id: Document pipeline identifier
            title: Document title
            content: Main document content
            metadata: Document metadata
            intelligence: Optional extracted intelligence

        Returns:
            Dict with 'markdown' and 'json' keys containing formatted content
        """
        # Format Markdown
        markdown_content = self.markdown.format(
            pipeline_id=pipeline_id, title=title, content=content, metadata=metadata
        )

        # Format JSON companion
        json_content = None
        if intelligence:
            json_content = self.json_companion.format(
                pipeline_id=pipeline_id,
                intelligence=intelligence,
                embeddings=metadata.get("embeddings"),
                search_index=metadata.get("search_index"),
            )

        result = {"markdown": markdown_content}
        if json_content:
            result["json"] = json_content

        return result

    def save_formatted_document(
        self, pipeline_id: str, output_dir: str, formatted_content: dict[str, str]
    ) -> dict[str, str]:
        """Save formatted document to files.

        Args:
            pipeline_id: Document pipeline identifier
            output_dir: Directory to save files
            formatted_content: Dict with 'markdown' and optional 'json' content

        Returns:
            Dict with paths to saved files
        """
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        saved_files = {}

        # Save Markdown
        md_path = output_path / f"{pipeline_id}.md"
        with open(md_path, "w") as f:
            f.write(formatted_content["markdown"])
        saved_files["markdown"] = str(md_path)
        logger.info(f"Saved Markdown: {md_path}")

        # Save JSON companion if present
        if "json" in formatted_content and formatted_content["json"]:
            json_path = output_path / f"{pipeline_id}.json"
            with open(json_path, "w") as f:
                f.write(formatted_content["json"])
            saved_files["json"] = str(json_path)
            logger.info(f"Saved JSON companion: {json_path}")

        return saved_files


# Export main formatter
def get_document_formatter() -> UnifiedDocumentFormatter:
    """Get unified document formatter instance.

    Returns:
        UnifiedDocumentFormatter: Formatter instance
    """
    return UnifiedDocumentFormatter()
