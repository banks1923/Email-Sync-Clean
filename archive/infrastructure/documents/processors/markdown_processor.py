"""Markdown document processor for MD files.

Handles Markdown files with YAML frontmatter support.
"""

import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from .base_processor import BaseProcessor


class MarkdownProcessor(BaseProcessor):
    """
    Processes Markdown documents with frontmatter support.
    """

    def __init__(self):
        """
        Initialize markdown processor.
        """
        super().__init__()
        self.format_type = "md"

    def extract_text(self, file_path: Path) -> str:
        """Extract text from Markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            Extracted text content (without frontmatter)
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Separate frontmatter and content
            frontmatter, body = self._parse_frontmatter(content)

            # Store frontmatter for metadata extraction
            self._frontmatter = frontmatter

            return body.strip()

        except Exception as e:
            logger.error(f"Failed to extract markdown text: {e}")
            raise

    def _parse_frontmatter(self, content: str) -> tuple[dict | None, str]:
        """Parse YAML frontmatter from markdown content.

        Args:
            content: Full markdown content

        Returns:
            Tuple of (frontmatter dict, body text)
        """
        # Check for YAML frontmatter (---\n...\n---)
        pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
        match = re.match(pattern, content, re.DOTALL)

        if match:
            try:
                frontmatter_text = match.group(1)
                body = match.group(2)
                frontmatter = yaml.safe_load(frontmatter_text)
                return frontmatter, body
            except yaml.YAMLError as e:
                logger.warning(f"Failed to parse YAML frontmatter: {e}")
                return None, content

        return None, content

    def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from markdown file including frontmatter.

        Args:
            file_path: Path to markdown file

        Returns:
            Enhanced metadata including frontmatter
        """
        # Get base metadata
        metadata = super().extract_metadata(file_path)

        # Add frontmatter if available
        if hasattr(self, "_frontmatter") and self._frontmatter:
            metadata["frontmatter"] = self._frontmatter

            # Extract common fields
            if isinstance(self._frontmatter, dict):
                for key in ["title", "author", "date", "tags", "categories", "description"]:
                    if key in self._frontmatter:
                        metadata[key] = self._frontmatter[key]

        # Extract structure metadata
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            structure = self._analyze_structure(content)
            metadata.update(structure)

        except Exception as e:
            logger.error(f"Failed to analyze markdown structure: {e}")

        return metadata

    def _analyze_structure(self, content: str) -> dict[str, Any]:
        """Analyze markdown document structure.

        Args:
            content: Markdown content

        Returns:
            Structure analysis
        """
        structure = {
            "heading_count": {},
            "link_count": 0,
            "image_count": 0,
            "code_block_count": 0,
            "table_count": 0,
            "list_count": 0,
        }

        # Count headings by level
        for level in range(1, 7):
            pattern = f'^{"#" * level} .+$'
            matches = re.findall(pattern, content, re.MULTILINE)
            if matches:
                structure["heading_count"][f"h{level}"] = len(matches)

        # Count links [text](url) - exclude images which start with !
        link_pattern = r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)"
        structure["link_count"] = len(re.findall(link_pattern, content))

        # Count images ![alt](url)
        image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
        structure["image_count"] = len(re.findall(image_pattern, content))

        # Count code blocks ```...```
        code_block_pattern = r"```[\s\S]*?```"
        structure["code_block_count"] = len(re.findall(code_block_pattern, content))

        # Count tables (simple detection)
        table_pattern = r"^\|.*\|.*\|.*$"
        structure["table_count"] = len(re.findall(table_pattern, content, re.MULTILINE)) // 2

        # Count lists (bullets and numbered)
        bullet_pattern = r"^[\*\-\+] .+$"
        numbered_pattern = r"^\d+\. .+$"
        bullet_count = len(re.findall(bullet_pattern, content, re.MULTILINE))
        numbered_count = len(re.findall(numbered_pattern, content, re.MULTILINE))
        structure["list_count"] = bullet_count + numbered_count

        return {"structure": structure}

    def process_to_plain_text(self, content: str) -> str:
        """Convert markdown to plain text.

        Args:
            content: Markdown content

        Returns:
            Plain text version
        """
        # Remove frontmatter
        _, body = self._parse_frontmatter(content)

        # Remove markdown syntax
        text = body

        # Remove code blocks
        text = re.sub(r"```[\s\S]*?```", "", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Remove images
        text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", "", text)

        # Convert links to text
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Remove heading markers
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Remove emphasis markers
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # Bold
        text = re.sub(r"\*([^*]+)\*", r"\1", text)  # Italic
        text = re.sub(r"__([^_]+)__", r"\1", text)  # Bold
        text = re.sub(r"_([^_]+)_", r"\1", text)  # Italic

        # Remove blockquotes
        text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)

        # Remove horizontal rules
        text = re.sub(r"^[\*\-_]{3,}$", "", text, flags=re.MULTILINE)

        # Clean up excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def extract_links(self, content: str) -> list:
        """Extract all links from markdown.

        Args:
            content: Markdown content

        Returns:
            List of (text, url) tuples
        """
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        links = re.findall(link_pattern, content)
        return links

    def extract_headings(self, content: str) -> list:
        """Extract document outline from headings.

        Args:
            content: Markdown content

        Returns:
            List of (level, text) tuples
        """
        headings = []

        for line in content.split("\n"):
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append((level, text))

        return headings
