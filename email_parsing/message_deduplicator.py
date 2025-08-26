#!/usr/bin/env python3
"""
Advanced Email Message Deduplication Service Implements message-level parsing
and deduplication for legal evidence integrity.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


@dataclass
class MessageBoundary:
    """
    Represents a detected message boundary in email content.
    """

    start: int
    end: int
    boundary_type: str  # 'header', 'quote', 'forward', 'timestamp'
    confidence: float
    marker: str


@dataclass
class ParsedMessage:
    """
    Individual message extracted from email thread.
    """

    content: str
    subject: str | None
    sender: str | None
    recipients: list[str] | None
    date: datetime | None
    message_id: str | None
    parent_id: str | None
    position_in_email: int
    context_type: str  # 'original', 'quoted', 'forwarded'
    quote_depth: int


class MessageDeduplicator:
    """
    Advanced email message parsing and deduplication.
    """

    # Common email headers and markers
    FORWARD_MARKERS = [
        r"^\s*----+\s*Forwarded [Mm]essage\s*----+",
        r"^\s*----+\s*Original [Mm]essage\s*----+",
        r"^\s*Begin forwarded message:",
        r"^\s*---------- Forwarded message ---------",
    ]

    REPLY_MARKERS = [
        r"^\s*On .+ wrote:$",
        r"^\s*On .+, .+ wrote:$",
        r"^\s*.+ wrote on .+:$",
        r"^\s*From:\s*.+\s*Sent:\s*.+\s*To:\s*.+\s*Subject:\s*.+",
    ]

    QUOTE_PATTERN = re.compile(r"^(>+)\s*(.*)$")

    def __init__(self):
        """
        Initialize the deduplicator.
        """
        self.unique_messages: dict[str, dict] = {}
        self.message_registry: dict[str, list[dict]] = {}

    def parse_email_thread(
        self, email_content: str, email_id: str, thread_id: str | None = None
    ) -> list[ParsedMessage]:
        """Parse an email thread into individual messages.

        Args:
            email_content: Full email content including quotes
            email_id: Unique identifier for this email
            thread_id: Thread identifier if available

        Returns:
            List of parsed messages found in the email
        """
        logger.debug(
            f"Parsing email {email_id}: {len(email_content)} chars, {email_content.count(chr(10))} lines"
        )
        messages = []

        # Find message boundaries
        boundaries = self._find_message_boundaries(email_content)
        logger.debug(f"Email {email_id}: Found {len(boundaries)} boundaries")

        # Extract messages between boundaries
        lines = email_content.split("\n")
        for i, boundary in enumerate(boundaries):
            logger.debug(
                f"Email {email_id}: Processing boundary {i+1}: {boundary.boundary_type} lines {boundary.start}-{boundary.end}"
            )

            # Extract the correct line range for this boundary
            content_slice = "\n".join(lines[boundary.start : boundary.end])
            logger.debug(f"Email {email_id}: Boundary {i+1} content: {len(content_slice)} chars")

            message = self._parse_message_segment(content_slice, boundary.boundary_type, i)

            if message:
                if self._is_substantial_content(message.content):
                    messages.append(message)
                    logger.debug(
                        f"Email {email_id}: ✅ Added message {i+1}: {message.context_type}, {len(message.content)} chars"
                    )
                else:
                    logger.debug(
                        f"Email {email_id}: ❌ Filtered message {i+1}: Not substantial ({len(message.content)} chars)"
                    )
            else:
                logger.debug(f"Email {email_id}: ❌ No message created for boundary {i+1}")

        # If no boundaries found, treat entire email as single message
        if not messages and self._is_substantial_content(email_content):
            logger.debug(f"Email {email_id}: No boundaries found, creating single message fallback")
            messages.append(
                ParsedMessage(
                    content=self._normalize_content(email_content),
                    subject=None,
                    sender=None,
                    recipients=None,
                    date=None,
                    message_id=None,
                    parent_id=None,
                    position_in_email=0,
                    context_type="original",
                    quote_depth=0,
                )
            )

        logger.info(
            f"Email {email_id}: Extracted {len(messages)} messages from {len(boundaries)} boundaries"
        )
        return messages

    def _find_message_boundaries(self, content: str) -> list[MessageBoundary]:
        """
        Detect message boundaries using multiple strategies.
        """
        boundaries = []
        lines = content.split("\n")
        logger.debug(f"Finding boundaries in {len(lines)} lines")

        # Strategy 1: Detect forward markers
        forward_boundaries = self._detect_forward_boundaries(lines)
        boundaries.extend(forward_boundaries)
        logger.debug(f"Forward detection: {len(forward_boundaries)} boundaries")

        # Strategy 2: Detect reply markers
        reply_boundaries = self._detect_reply_boundaries(lines)
        boundaries.extend(reply_boundaries)
        logger.debug(f"Reply detection: {len(reply_boundaries)} boundaries")

        # Strategy 3: Detect quote level changes
        quote_boundaries = self._detect_quote_boundaries(lines)
        boundaries.extend(quote_boundaries)
        logger.debug(f"Quote detection: {len(quote_boundaries)} boundaries")

        logger.debug(f"Total boundaries before merge: {len(boundaries)}")

        # Merge overlapping boundaries and sort
        boundaries = self._merge_boundaries(boundaries, len(lines))
        logger.debug(f"Final boundaries after merge: {len(boundaries)}")

        return boundaries

    def _detect_forward_boundaries(self, lines: list[str]) -> list[MessageBoundary]:
        """
        Detect forwarded message boundaries.
        """
        boundaries = []

        for i, line in enumerate(lines):
            for pattern in self.FORWARD_MARKERS:
                if re.match(pattern, line, re.IGNORECASE):
                    # Find end of forwarded section (next marker or end)
                    end = self._find_section_end(lines, i)
                    boundaries.append(
                        MessageBoundary(
                            start=i,
                            end=end,
                            boundary_type="forward",
                            confidence=0.9,
                            marker=line.strip(),
                        )
                    )
                    break

        return boundaries

    def _detect_reply_boundaries(self, lines: list[str]) -> list[MessageBoundary]:
        """
        Detect reply message boundaries.
        """
        boundaries = []

        for i, line in enumerate(lines):
            for pattern in self.REPLY_MARKERS:
                if re.match(pattern, line, re.IGNORECASE):
                    # Reply boundary typically starts after the marker
                    end = self._find_section_end(lines, i)
                    boundaries.append(
                        MessageBoundary(
                            start=i + 1,
                            end=end,
                            boundary_type="reply",
                            confidence=0.8,
                            marker=line.strip(),
                        )
                    )
                    break

        return boundaries

    def _detect_quote_boundaries(self, lines: list[str]) -> list[MessageBoundary]:
        """
        Detect boundaries based on quote depth changes.
        """
        boundaries = []
        current_depth = 0
        section_start = 0

        for i, line in enumerate(lines):
            match = self.QUOTE_PATTERN.match(line)
            depth = len(match.group(1)) if match else 0

            if depth != current_depth:
                # Only create boundaries for actual quoted sections (depth > 0)
                if i > section_start and current_depth > 0:
                    boundaries.append(
                        MessageBoundary(
                            start=section_start,
                            end=i,
                            boundary_type="quote",
                            confidence=0.7,
                            marker=f"Quote depth: {current_depth}",
                        )
                    )
                section_start = i
                current_depth = depth

        # Add final section only if it's a quoted section
        if section_start < len(lines) and current_depth > 0:
            boundaries.append(
                MessageBoundary(
                    start=section_start,
                    end=len(lines),
                    boundary_type="quote",
                    confidence=0.7,
                    marker=f"Quote depth: {current_depth}",
                )
            )

        return boundaries

    def _find_section_end(self, lines: list[str], start: int) -> int:
        """
        Find where a message section ends.
        """
        # Look for next boundary marker or significant quote depth change
        for i in range(start + 1, len(lines)):
            line = lines[i]

            # Check for new boundary markers
            for patterns in [self.FORWARD_MARKERS, self.REPLY_MARKERS]:
                for pattern in patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        return i

            # Check for quote depth changes (start of quoted section)
            match = self.QUOTE_PATTERN.match(line)
            if match and len(match.group(1)) > 0:  # Found quoted line
                return i

        return len(lines)

    def _merge_boundaries(
        self, boundaries: list[MessageBoundary], total_lines: int
    ) -> list[MessageBoundary]:
        """
        Merge overlapping boundaries and fill gaps.
        """
        if not boundaries:
            return [
                MessageBoundary(
                    start=0,
                    end=total_lines,
                    boundary_type="original",
                    confidence=1.0,
                    marker="Full content",
                )
            ]

        # Sort by start position
        boundaries.sort(key=lambda b: b.start)

        # Create final boundary list including gaps
        final_boundaries = []
        current_pos = 0

        for boundary in boundaries:
            # Add gap before this boundary as 'original' content
            if boundary.start > current_pos:
                final_boundaries.append(
                    MessageBoundary(
                        start=current_pos,
                        end=boundary.start,
                        boundary_type="original",
                        confidence=1.0,
                        marker="Original content",
                    )
                )

            # Add the boundary (skip if it would be empty or overlapping)
            if boundary.end > boundary.start and boundary.start >= current_pos:
                # Adjust start if it overlaps with previous boundary
                adjusted_start = max(boundary.start, current_pos)
                if boundary.end > adjusted_start:
                    final_boundaries.append(
                        MessageBoundary(
                            start=adjusted_start,
                            end=boundary.end,
                            boundary_type=boundary.boundary_type,
                            confidence=boundary.confidence,
                            marker=boundary.marker,
                        )
                    )
                    current_pos = boundary.end

        # Add final gap if needed
        if current_pos < total_lines:
            final_boundaries.append(
                MessageBoundary(
                    start=current_pos,
                    end=total_lines,
                    boundary_type="original",
                    confidence=1.0,
                    marker="Final content",
                )
            )

        return final_boundaries

    def _parse_message_segment(
        self, content: str, boundary_type: str, position: int
    ) -> ParsedMessage | None:
        """
        Parse a message segment into structured data.
        """
        if not content.strip():
            logger.debug(f"Segment {position}: Empty content, skipping")
            return None

        # Remove quote markers if present
        cleaned_lines = []
        quote_depth = 0

        for line in content.split("\n"):
            match = self.QUOTE_PATTERN.match(line)
            if match:
                quote_depth = max(quote_depth, len(match.group(1)))
                cleaned_lines.append(match.group(2))
            else:
                cleaned_lines.append(line)

        cleaned_content = "\n".join(cleaned_lines)

        # Extract metadata if available
        subject = self._extract_subject(cleaned_content)
        sender = self._extract_sender(cleaned_content)
        date = self._extract_date(cleaned_content)

        # Determine context type
        context_type = "quoted" if quote_depth > 0 else "original"
        if boundary_type == "forward":
            context_type = "forwarded"

        return ParsedMessage(
            content=self._normalize_content(cleaned_content),
            subject=subject,
            sender=sender,
            recipients=None,  # Could be extracted if needed
            date=date,
            message_id=None,  # Would need email headers
            parent_id=None,
            position_in_email=position,
            context_type=context_type,
            quote_depth=quote_depth,
        )

    def _normalize_content(self, content: str) -> str:
        """
        Normalize message content for consistent hashing.
        """
        # Remove signatures
        content = self._remove_signatures(content)

        # Remove disclaimers
        content = self._remove_disclaimers(content)

        # Normalize whitespace
        content = " ".join(content.split())

        # Remove common variations
        content = self._remove_temporal_variations(content)

        return content.strip()

    def _remove_signatures(self, content: str) -> str:
        """
        Remove email signatures.
        """
        # Common signature markers
        sig_markers = [
            r"^--\s*$",
            r"^Best regards,",
            r"^Sincerely,",
            r"^Thanks,",
            r"^Sent from my iPhone",
            r"^Sent from my Android",
        ]

        lines = content.split("\n")
        for i, line in enumerate(lines):
            for marker in sig_markers:
                if re.match(marker, line, re.IGNORECASE):
                    return "\n".join(lines[:i])

        return content

    def _remove_disclaimers(self, content: str) -> str:
        """
        Remove legal disclaimers.
        """
        disclaimer_patterns = [
            r"This email and any attachments are confidential",
            r"CONFIDENTIALITY NOTICE",
            r"This message is intended only for",
            r"If you are not the intended recipient",
        ]

        for pattern in disclaimer_patterns:
            content = re.sub(pattern + r".*", "", content, flags=re.IGNORECASE | re.DOTALL)

        return content

    def _remove_temporal_variations(self, content: str) -> str:
        """
        Remove temporal variations that don't affect meaning.
        """
        # Remove timestamps in various formats
        content = re.sub(r"\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?", "", content, flags=re.IGNORECASE)

        # Remove message IDs
        content = re.sub(r"Message-ID:\s*<[^>]+>", "", content, flags=re.IGNORECASE)

        return content

    def _is_substantial_content(self, content: str) -> bool:
        """
        Check if content is substantial enough to keep.
        """
        if not content:
            return False

        # Remove whitespace and check length
        cleaned = content.strip()
        if len(cleaned) < 10:  # Too short
            return False

        # Check if it's just quotes or markers
        if cleaned.startswith(">") and not any(c.isalnum() for c in cleaned):
            return False

        return True

    def _extract_subject(self, content: str) -> str | None:
        """
        Extract subject from content if present.
        """
        match = re.search(r"^Subject:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_sender(self, content: str) -> str | None:
        """
        Extract sender from content if present.
        """
        match = re.search(r"^From:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if match:
            sender = match.group(1).strip()
            # Extract email if in format "Name <email>"
            email_match = re.search(r"<([^>]+)>", sender)
            return email_match.group(1) if email_match else sender
        return None

    def _extract_date(self, content: str) -> datetime | None:
        """
        Extract date from content if present.
        """
        match = re.search(r"^Date:\s*(.+)$", content, re.MULTILINE | re.IGNORECASE)
        if match:
            date_str = match.group(1).strip()
            # Try common date formats (including the test format)
            for fmt in [
                "%a, %d %b %Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y %H:%M",
                "Mon, %d Jan %Y %H:%M:%S",
                "%a, %d %b %Y %H:%M:%S",
            ]:
                try:
                    # Handle various date string lengths
                    if len(date_str) > 19:
                        # Try full string first, then truncated
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            return datetime.strptime(date_str[:19], fmt)
                    else:
                        return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        return None

    def create_message_hash(self, content: str, subject: str | None = None) -> str:
        """Create deterministic hash for message content.

        Args:
            content: Normalized message content
            subject: Optional subject for additional uniqueness

        Returns:
            SHA256 hash of the message
        """
        # Normalize content
        normalized = self._normalize_content(content)

        # Include subject for additional uniqueness
        hash_input = f"{normalized}|{subject or ''}".encode()

        return hashlib.sha256(hash_input).hexdigest()

    def deduplicate_messages(self, messages: list[ParsedMessage]) -> dict[str, dict]:
        """Deduplicate parsed messages and track occurrences.

        Args:
            messages: List of parsed messages

        Returns:
            Dictionary of unique messages with occurrence tracking
        """
        unique = {}

        for message in messages:
            # Generate hash
            msg_hash = self.create_message_hash(message.content, message.subject)

            if msg_hash not in unique:
                unique[msg_hash] = {
                    "content": message.content,
                    "subject": message.subject,
                    "sender": message.sender,
                    "date": message.date,
                    "context_type": message.context_type,
                    "occurrences": [],
                    "quote_depths": set(),
                }

            # Track occurrence
            unique[msg_hash]["occurrences"].append(
                {
                    "position": message.position_in_email,
                    "context_type": message.context_type,
                    "quote_depth": message.quote_depth,
                }
            )
            unique[msg_hash]["quote_depths"].add(message.quote_depth)

        return unique


def process_email_file(email_content: str, email_id: str) -> tuple[list[dict], dict]:
    """Process a single email file and extract unique messages.

    Args:
        email_content: Full email content
        email_id: Unique identifier for the email

    Returns:
        Tuple of (unique_messages, processing_stats)
    """
    deduplicator = MessageDeduplicator()

    # Parse messages
    messages = deduplicator.parse_email_thread(email_content, email_id)

    # Deduplicate
    unique = deduplicator.deduplicate_messages(messages)

    # Prepare results
    results = []
    for msg_hash, msg_data in unique.items():
        results.append(
            {
                "message_hash": msg_hash,
                "content": msg_data["content"],
                "subject": msg_data["subject"],
                "sender": msg_data["sender"],
                "date": msg_data["date"],
                "occurrences": msg_data["occurrences"],
            }
        )

    stats = {
        "total_messages": len(messages),
        "unique_messages": len(unique),
        "deduplication_rate": 1 - (len(unique) / len(messages)) if messages else 0,
    }

    logger.info(
        f"Processed email {email_id}: {stats['total_messages']} messages, "
        f"{stats['unique_messages']} unique ({stats['deduplication_rate']:.1%} dedup rate)"
    )

    return results, stats
