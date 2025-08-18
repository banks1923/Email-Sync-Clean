"""
EmailThreadProcessor - Converts Gmail threads to chronological markdown files.

Simple, direct implementation following CLAUDE.md principles.
Integrates with existing Gmail service and HTML cleaner.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import frontmatter
from loguru import logger

# Import existing services (avoid circular import)
try:
    from shared.html_cleaner import clean_html_content
    from shared.analog_db import AnalogDBManager
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False
    logger.warning("Dependencies not available - EmailThreadProcessor disabled")


class EmailThreadProcessor:
    """Processes Gmail threads into chronological markdown files."""

    def __init__(self, gmail_service = None, base_path: Optional[Path] = None):
        """Initialize thread processor with analog DB.
        
        Args:
            gmail_service: Optional Gmail service instance (avoids circular import)
            base_path: Base path for analog database
        """
        if not DEPENDENCIES_AVAILABLE:
            raise ImportError("Dependencies required for EmailThreadProcessor")
        
        self.gmail_service = gmail_service  # Set externally to avoid circular import
        self.analog_db = AnalogDBManager(base_path)
        self.max_emails_per_file = 100
        logger.info("EmailThreadProcessor initialized")

    def process_thread(
        self,
        thread_id: str,
        include_metadata: bool = True,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Process a Gmail thread into markdown format.
        
        Args:
            thread_id: Gmail thread ID
            include_metadata: Whether to include YAML frontmatter
            save_to_db: Whether to save to analog database
            
        Returns:
            Processing result with success status and file paths
        """
        try:
            # Fetch thread messages
            thread_result = self._fetch_thread_messages(thread_id)
            if not thread_result["success"]:
                return thread_result

            messages = thread_result["messages"]
            if not messages:
                return {"success": False, "error": "No messages found in thread"}

            # Sort chronologically
            sorted_messages = self._sort_chronologically(messages)
            
            # Generate metadata
            metadata = self._generate_thread_metadata(sorted_messages, thread_id)
            
            # Check if thread needs splitting
            if len(sorted_messages) > self.max_emails_per_file:
                return self._process_large_thread(
                    sorted_messages, metadata, include_metadata, save_to_db
                )
            else:
                return self._process_single_thread(
                    sorted_messages, metadata, include_metadata, save_to_db
                )

        except Exception as e:
            logger.error(f"Thread processing failed for {thread_id}: {e}")
            return {"success": False, "error": f"Processing failed: {str(e)}"}

    def _fetch_thread_messages(self, thread_id: str) -> Dict[str, Any]:
        """Fetch all messages in a Gmail thread."""
        try:
            # Connect to Gmail if not already connected
            if not self.gmail_service.gmail_api.service:
                connect_result = self.gmail_service.gmail_api.connect()
                if not connect_result["success"]:
                    return connect_result

            # Get thread details
            service = self.gmail_service.gmail_api.service
            thread_request = service.users().threads().get(userId="me", id=thread_id)
            thread_data = self.gmail_service.gmail_api._execute_with_timeout(thread_request)

            if "messages" not in thread_data:
                return {"success": False, "error": "No messages found in thread"}

            # Parse each message in the thread
            messages = []
            for message_data in thread_data["messages"]:
                parsed_message = self.gmail_service.gmail_api.parse_message(message_data)
                # Add threadId to parsed message
                parsed_message["thread_id"] = thread_id
                parsed_message["internal_date"] = message_data.get("internalDate", "0")
                messages.append(parsed_message)

            logger.info(f"Fetched {len(messages)} messages from thread {thread_id}")
            return {"success": True, "messages": messages}

        except Exception as e:
            logger.error(f"Failed to fetch thread {thread_id}: {e}")
            return {"success": False, "error": f"Failed to fetch thread: {str(e)}"}

    def _sort_chronologically(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort messages chronologically by internal date."""
        try:
            # Sort by internal date (Gmail's timestamp in milliseconds)
            sorted_messages = sorted(
                messages,
                key=lambda msg: int(msg.get("internal_date", "0"))
            )
            
            logger.debug(f"Sorted {len(messages)} messages chronologically")
            return sorted_messages

        except Exception as e:
            logger.warning(f"Chronological sorting failed: {e}")
            # Fallback: return original order
            return messages

    def _generate_thread_metadata(
        self, 
        messages: List[Dict[str, Any]], 
        thread_id: str
    ) -> Dict[str, Any]:
        """Generate comprehensive metadata for thread."""
        try:
            if not messages:
                return {"thread_id": thread_id, "processed_at": datetime.now().isoformat()}

            # Extract participants (unique senders and recipients)
            participants = set()
            senders = set()
            
            for msg in messages:
                if msg.get("sender"):
                    sender_email = self._extract_email_address(msg["sender"])
                    participants.add(sender_email)
                    senders.add(sender_email)
                
                if msg.get("recipient_to"):
                    recipients = msg["recipient_to"].split(",")
                    for recipient in recipients:
                        recipient_email = self._extract_email_address(recipient.strip())
                        participants.add(recipient_email)

            # Get date range
            first_message = messages[0]
            last_message = messages[-1]
            
            # Get subject (from first message, cleaned)
            subject = first_message.get("subject", "").strip()
            subject = re.sub(r'^(Re|Fwd?):\s*', '', subject, flags=re.IGNORECASE)

            metadata = {
                "thread_id": thread_id,
                "subject": subject,
                "message_count": len(messages),
                "participant_count": len(participants),
                "participants": sorted(list(participants)),
                "senders": sorted(list(senders)),
                "date_range": {
                    "start": first_message.get("datetime_utc"),
                    "end": last_message.get("datetime_utc")
                },
                "processed_at": datetime.now().isoformat(),
                "document_type": "email_thread"
            }

            return metadata

        except Exception as e:
            logger.warning(f"Metadata generation failed for thread {thread_id}: {e}")
            return {
                "thread_id": thread_id,
                "processed_at": datetime.now().isoformat(),
                "message_count": len(messages) if messages else 0
            }

    def _extract_email_address(self, email_field: str) -> str:
        """Extract email address from sender/recipient field."""
        if not email_field:
            return ""
        
        # Look for email in angle brackets
        match = re.search(r'<([^>]+)>', email_field)
        if match:
            return match.group(1).strip()
        
        # If no brackets, assume the whole string is an email
        return email_field.strip()

    def _process_single_thread(
        self,
        messages: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        include_metadata: bool,
        save_to_db: bool
    ) -> Dict[str, Any]:
        """Process a single thread (<=100 messages) into one markdown file."""
        try:
            # Format as markdown
            markdown_content = self._format_thread_to_markdown(
                messages, metadata if include_metadata else None
            )

            # Generate filename
            filename = self._generate_filename(metadata)
            
            # Save to analog database if requested
            if save_to_db:
                file_path = self._save_to_analog_db(markdown_content, filename)
            else:
                file_path = None

            return {
                "success": True,
                "thread_id": metadata["thread_id"],
                "message_count": len(messages),
                "files_created": 1,
                "file_paths": [str(file_path)] if file_path else [],
                "metadata": metadata
            }

        except Exception as e:
            logger.error(f"Single thread processing failed: {e}")
            return {"success": False, "error": f"Processing failed: {str(e)}"}

    def _process_large_thread(
        self,
        messages: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        include_metadata: bool,
        save_to_db: bool
    ) -> Dict[str, Any]:
        """Process a large thread (>100 messages) by splitting into multiple files."""
        try:
            # Split messages into chunks
            message_chunks = self._split_messages(messages)
            file_paths = []
            
            for i, chunk in enumerate(message_chunks):
                part_num = i + 1
                total_parts = len(message_chunks)
                
                # Create part-specific metadata
                part_metadata = metadata.copy()
                part_metadata.update({
                    "part_number": part_num,
                    "total_parts": total_parts,
                    "part_message_count": len(chunk),
                    "is_continuation": part_num > 1
                })

                # Format chunk as markdown
                markdown_content = self._format_thread_to_markdown(
                    chunk, part_metadata if include_metadata else None, part_num, total_parts
                )

                # Generate part filename
                filename = self._generate_filename(metadata, part_num)
                
                # Save to analog database if requested
                if save_to_db:
                    file_path = self._save_to_analog_db(markdown_content, filename)
                    if file_path:
                        file_paths.append(str(file_path))

            return {
                "success": True,
                "thread_id": metadata["thread_id"],
                "message_count": len(messages),
                "files_created": len(file_paths),
                "file_paths": file_paths,
                "metadata": metadata,
                "split_into_parts": True
            }

        except Exception as e:
            logger.error(f"Large thread processing failed: {e}")
            return {"success": False, "error": f"Processing failed: {str(e)}"}

    def _split_messages(self, messages: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Split messages into chunks of max_emails_per_file."""
        chunks = []
        for i in range(0, len(messages), self.max_emails_per_file):
            chunk = messages[i:i + self.max_emails_per_file]
            chunks.append(chunk)
        
        logger.info(f"Split {len(messages)} messages into {len(chunks)} chunks")
        return chunks

    def _format_thread_to_markdown(
        self,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        part_num: Optional[int] = None,
        total_parts: Optional[int] = None
    ) -> str:
        """Format messages as markdown with optional YAML frontmatter."""
        try:
            # Build markdown content
            content_lines = []
            
            # Add part navigation for multi-part threads
            if part_num and total_parts and total_parts > 1:
                content_lines.append(f"# Email Thread (Part {part_num} of {total_parts})")
                content_lines.append("")
                
                # Add navigation links
                nav_links = []
                if part_num > 1:
                    prev_filename = self._generate_filename(metadata, part_num - 1)
                    nav_links.append(f"← [Previous Part]({prev_filename})")
                if part_num < total_parts:
                    next_filename = self._generate_filename(metadata, part_num + 1)
                    nav_links.append(f"[Next Part]({next_filename}) →")
                
                if nav_links:
                    content_lines.append(" | ".join(nav_links))
                    content_lines.append("")
            
            # Add thread subject as main header
            if metadata and metadata.get("subject"):
                if not (part_num and total_parts):  # Don't duplicate if already added above
                    content_lines.append(f"# {metadata['subject']}")
                    content_lines.append("")

            # Add each message
            for i, message in enumerate(messages):
                content_lines.append(self._format_message_as_markdown(message, i + 1))
                content_lines.append("")

            # Join content
            markdown_text = "\n".join(content_lines).strip()

            # Add frontmatter if metadata provided
            if metadata:
                post = frontmatter.Post(markdown_text, **metadata)
                return frontmatter.dumps(post)
            else:
                return markdown_text

        except Exception as e:
            logger.warning(f"Markdown formatting failed: {e}")
            return f"Error formatting thread: {str(e)}"

    def _format_message_as_markdown(self, message: Dict[str, Any], message_num: int) -> str:
        """Format a single message as markdown."""
        try:
            lines = []
            
            # Message header
            lines.append(f"## Message {message_num}")
            lines.append("")
            
            # Message metadata
            if message.get("sender"):
                lines.append(f"**From:** {message['sender']}")
            if message.get("recipient_to"):
                lines.append(f"**To:** {message['recipient_to']}")
            if message.get("datetime_utc"):
                # Format datetime for readability
                try:
                    dt = datetime.fromisoformat(message["datetime_utc"].replace('Z', '+00:00'))
                    formatted_date = dt.strftime("%B %d, %Y at %I:%M %p")
                    lines.append(f"**Date:** {formatted_date}")
                except:
                    lines.append(f"**Date:** {message['datetime_utc']}")
            
            lines.append("")
            
            # Message content
            content = message.get("content", "")
            if content:
                # Clean HTML content
                cleaned_content = clean_html_content(content)
                if cleaned_content:
                    lines.append(cleaned_content)
                else:
                    lines.append("*(No content)*")
            else:
                lines.append("*(No content)*")
            
            return "\n".join(lines)

        except Exception as e:
            logger.warning(f"Message formatting failed: {e}")
            return f"*(Error formatting message: {str(e)})*"

    def _generate_filename(self, metadata: Dict[str, Any], part_num: Optional[int] = None) -> str:
        """Generate filename for thread markdown file."""
        try:
            # Get date for filename (from first message date or processing date)
            date_str = datetime.now().strftime("%Y-%m-%d")
            if metadata.get("date_range", {}).get("start"):
                try:
                    dt = datetime.fromisoformat(metadata["date_range"]["start"].replace('Z', '+00:00'))
                    date_str = dt.strftime("%Y-%m-%d")
                except:
                    pass

            # Create slug from subject
            subject = metadata.get("subject", "email_thread")
            slug = self._create_slug(subject)
            
            # Add thread ID for uniqueness
            thread_id = metadata.get("thread_id", "unknown")
            
            # Build filename
            if part_num:
                filename = f"{date_str}_{slug}_{thread_id}_part{part_num}.md"
            else:
                filename = f"{date_str}_{slug}_{thread_id}.md"
            
            return filename

        except Exception as e:
            logger.warning(f"Filename generation failed: {e}")
            thread_id = metadata.get("thread_id", "unknown")
            if part_num:
                return f"thread_{thread_id}_part{part_num}.md"
            else:
                return f"thread_{thread_id}.md"

    def _create_slug(self, text: str, max_length: int = 50) -> str:
        """Create URL-safe slug from text."""
        if not text:
            return "untitled"
        
        # Convert to lowercase and replace spaces/special chars with underscores
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '_', slug)
        
        # Truncate if too long
        if len(slug) > max_length:
            slug = slug[:max_length].rstrip('_')
        
        return slug or "untitled"

    def _save_to_analog_db(self, markdown_content: str, filename: str) -> Optional[Path]:
        """Save markdown content to analog database."""
        try:
            # Ensure email_threads directory exists
            self.analog_db.create_directory_structure()
            
            # Write file
            file_path = self.analog_db.directories["email_threads"] / filename
            file_path.write_text(markdown_content, encoding='utf-8')
            
            logger.info(f"Saved thread to {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to save thread to analog DB: {e}")
            return None

    def process_threads_by_query(
        self,
        query: str = "",
        max_threads: int = 10,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Process multiple threads based on Gmail search query.
        
        Args:
            query: Gmail search query
            max_threads: Maximum number of threads to process
            include_metadata: Whether to include YAML frontmatter
            
        Returns:
            Batch processing results
        """
        try:
            # Get thread IDs from Gmail
            messages_result = self.gmail_service.gmail_api.get_messages(
                query=query, max_results=max_threads
            )
            
            if not messages_result["success"]:
                return messages_result

            messages = messages_result["data"]
            if not messages:
                return {"success": True, "message": "No threads found", "processed": 0}

            # Extract unique thread IDs
            thread_ids = list(set(msg.get("threadId") for msg in messages if msg.get("threadId")))
            
            # Process each thread
            results = []
            success_count = 0
            error_count = 0

            for thread_id in thread_ids[:max_threads]:
                result = self.process_thread(thread_id, include_metadata, save_to_db=True)
                
                if result["success"]:
                    success_count += 1
                else:
                    error_count += 1

                results.append({
                    "thread_id": thread_id,
                    "success": result["success"],
                    "files_created": result.get("files_created", 0),
                    "error": result.get("error")
                })

            logger.info(f"Batch processing complete: {success_count} success, {error_count} errors")

            return {
                "success": True,
                "total_threads": len(thread_ids),
                "success_count": success_count,
                "error_count": error_count,
                "results": results
            }

        except Exception as e:
            logger.error(f"Batch thread processing failed: {e}")
            return {"success": False, "error": f"Batch processing failed: {str(e)}"}

    def validate_setup(self) -> Dict[str, Any]:
        """Validate EmailThreadProcessor setup and dependencies."""
        try:
            validation_result = {
                "gmail_available": GMAIL_AVAILABLE,
                "dependencies": {},
                "directories": {}
            }

            if GMAIL_AVAILABLE:
                validation_result["dependencies"] = {
                    "gmail_service": self.gmail_service is not None,
                    "analog_db": self.analog_db is not None,
                    "html_cleaner": True  # We imported it successfully
                }

                # Check directory access
                try:
                    self.analog_db.create_directory_structure()
                    email_threads_dir = self.analog_db.directories["email_threads"]
                    validation_result["directories"] = {
                        "email_threads_exists": email_threads_dir.exists(),
                        "email_threads_writable": email_threads_dir.exists() and os.access(email_threads_dir, os.W_OK)
                    }
                except Exception as e:
                    validation_result["directories"]["error"] = str(e)

            validation_result["ready"] = all([
                GMAIL_AVAILABLE,
                validation_result["dependencies"].get("gmail_service", False),
                validation_result["dependencies"].get("analog_db", False),
                validation_result["directories"].get("email_threads_writable", False)
            ])

            return validation_result

        except Exception as e:
            logger.error(f"Setup validation failed: {e}")
            return {"ready": False, "error": str(e)}


# Simple factory function following CLAUDE.md principles
def get_email_thread_processor(
    gmail_service=None,
    base_path: Optional[Path] = None
) -> Optional[EmailThreadProcessor]:
    """Get or create EmailThreadProcessor instance."""
    try:
        return EmailThreadProcessor(gmail_service, base_path)
    except ImportError as e:
        logger.warning(f"EmailThreadProcessor not available: {e}")
        return None