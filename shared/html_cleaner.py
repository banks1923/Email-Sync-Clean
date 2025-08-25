"""Simple HTML cleaning utilities for email content.

Uses only standard library to avoid external dependencies.
"""

import html
import re


def clean_html_content(html_content: str) -> str:
    """Clean HTML content to readable text.

    Args:
        html_content: Raw HTML content

    Returns:
        Clean text content suitable for markdown
    """
    if not html_content or not isinstance(html_content, str):
        return ""
    
    text = html_content
    
    # Remove script and style tags completely
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Convert common block elements to line breaks
    block_elements = ['div', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']
    for element in block_elements:
        text = re.sub(f'<{element}[^>]*>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(f'</{element}>', '\n', text, flags=re.IGNORECASE)
    
    # Convert list items to bullet points
    text = re.sub(r'<li[^>]*>', '\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '', text, flags=re.IGNORECASE)
    
    # Remove all remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decode HTML entities after removing tags (so decoded < > don't get treated as tags)
    text = html.unescape(text)
    
    # Clean up whitespace
    # Replace multiple whitespace with single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Replace multiple newlines with max 2
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Remove leading/trailing whitespace on each line and filter empty lines
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if line:  # Only keep non-empty lines
            lines.append(line)
    
    return '\n'.join(lines)


def extract_email_content(email_html: str) -> tuple[str, dict]:
    """Extract meaningful content from email HTML.

    Args:
        email_html: Raw email HTML content

    Returns:
        Tuple of (cleaned_content, metadata)
    """
    metadata = {}
    
    # Extract email headers from HTML patterns (before cleaning HTML)
    sender_match = re.search(r'[Ff]rom:?\s*([^<\n]+?)(?:\s*<|</|$)', email_html)
    if sender_match:
        metadata['sender'] = sender_match.group(1).strip()
    
    subject_match = re.search(r'[Ss]ubject:?\s*([^<\n]+?)(?:\s*<|</|$)', email_html)
    if subject_match:
        metadata['subject'] = subject_match.group(1).strip()
    
    date_match = re.search(r'[Dd]ate:?\s*([^<\n]+?)(?:\s*<|</|$)', email_html)
    if date_match:
        metadata['date'] = date_match.group(1).strip()
    
    # Clean the content
    cleaned_content = clean_html_content(email_html)
    
    # Remove email signature boilerplate
    cleaned_content = remove_email_boilerplate(cleaned_content)
    
    return cleaned_content, metadata


def remove_email_boilerplate(content: str) -> str:
    """
    Remove common email boilerplate and quoted content.
    """
    if not content:
        return ""
    
    lines = content.split('\n')
    clean_lines = []
    
    skip_patterns = [
        r'^>.*',  # Quoted lines
        r'^\s*On .+wrote:.*',  # Gmail quote headers
        r'^\s*From:.*',  # Email headers in body
        r'^\s*To:.*',
        r'^\s*Cc:.*',
        r'^\s*Sent:.*',
        r'^\s*Subject:.*',
        r'^\s*\[image\d*\.\w+\]',  # Image placeholders
        r'^\s*<image\d*\.\w+>',
        r'alt="[^"]*"',  # Alt text
        r'src="[^"]*"',  # Image sources
        r'cid:[^"]*',  # Email content IDs
    ]
    
    for line in lines:
        # Skip boilerplate patterns
        skip_line = False
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                skip_line = True
                break
        
        if not skip_line and line.strip():
            clean_lines.append(line)
    
    return '\n'.join(clean_lines)


def format_as_clean_markdown(content: str, title: str | None = None) -> str:
    """Format cleaned content as markdown.

    Args:
        content: Cleaned text content
        title: Optional title for the document

    Returns:
        Formatted markdown content
    """
    if not content:
        return ""
    
    markdown = ""
    
    if title:
        markdown += f"# {title}\n\n"
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    for paragraph in paragraphs:
        # Handle bullet points
        if paragraph.startswith('•'):
            lines = paragraph.split('\n')
            for line in lines:
                if line.strip().startswith('•'):
                    markdown += f"- {line.strip()[1:].strip()}\n"
                else:
                    markdown += f"  {line.strip()}\n"
            markdown += "\n"
        else:
            markdown += f"{paragraph}\n\n"
    
    return markdown.strip()