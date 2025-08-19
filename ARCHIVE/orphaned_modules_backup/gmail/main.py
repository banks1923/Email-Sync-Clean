import os
from typing import Any

from loguru import logger

from infrastructure.pipelines.data_pipeline import DataPipelineOrchestrator
from infrastructure.pipelines.document_exporter import DocumentExporter
from shared.simple_db import SimpleDB
from summarization import get_document_summarizer

# Import EmailThreadProcessor
try:
    from infrastructure.documents.processors.email_thread_processor import (
        get_email_thread_processor,
    )
    THREAD_PROCESSOR_AVAILABLE = True
except ImportError:
    THREAD_PROCESSOR_AVAILABLE = False
    logger.warning("EmailThreadProcessor not available - using legacy email processing only")

from .config import GmailConfig
from .gmail_api import GmailAPI
from .storage import EmailStorage

# Logger is now imported globally from loguru


class GmailService:
    """Main Gmail service for email synchronization with batch processing support."""

    def __init__(self, gmail_timeout: int = 30, db_path: str = "emails.db") -> None:
        """Initialize Gmail service with API, storage, and processing components.

        Args:
            gmail_timeout: Timeout in seconds for Gmail API requests.
            db_path: Path to SQLite database file.
        """
        self.gmail_api = GmailAPI(timeout=gmail_timeout)
        self.storage = EmailStorage(db_path)
        self.config = GmailConfig()
        self.db = SimpleDB(db_path)
        self.summarizer = get_document_summarizer()
        self.pipeline = DataPipelineOrchestrator()  # Add pipeline orchestrator
        self.exporter = DocumentExporter()  # Add document exporter
        
        # Initialize EmailThreadProcessor if available
        if THREAD_PROCESSOR_AVAILABLE:
            self.thread_processor = get_email_thread_processor()
            logger.info("EmailThreadProcessor initialized for thread-based processing")
        else:
            self.thread_processor = None
            
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Set up log directory for Gmail service."""
        os.makedirs("logs", exist_ok=True)

    def sync_emails(
        self,
        use_config: bool = True,
        query: str = "",
        max_results: int = 100,
        batch_mode: bool = True,
    ) -> dict[str, Any]:
        """Synchronize emails from Gmail to local database.

        Args:
            use_config: Use configured sender filters if True.
            query: Gmail search query (overridden by use_config).
            max_results: Maximum number of emails to sync.
            batch_mode: Use streaming batch mode for large syncs.

        Returns:
            dict: Success status with processed/duplicate/error counts.
        """
        logger.info(
            f"Starting email sync - use_config={use_config}, max_results={max_results}, batch_mode={batch_mode}"
        )

        if use_config:
            query = self.config.build_query()
            max_results = self.config.max_results

        logger.info(f"Gmail query: {query}")
        messages_result = self.gmail_api.get_messages(query, max_results)
        if not messages_result["success"]:
            logger.error(f"Failed to get messages: {messages_result.get('error', 'Unknown error')}")
            return messages_result

        messages = messages_result["data"]
        logger.info(f"Retrieved {len(messages)} messages from Gmail")

        if batch_mode and len(messages) > 10:
            # Use batch mode for better performance with many emails
            return self._sync_emails_batch(messages)
        else:
            # Use original single-email mode for small batches
            return self._sync_emails_single(messages)

    def _sync_emails_batch(self, messages) -> dict[str, Any]:
        """Sync emails using streaming batch operations for reliability"""
        logger.info(f"Using streaming batch mode for {len(messages)} emails")

        total_processed = 0
        total_duplicates = 0
        total_errors = 0
        chunk_size = 50  # Process in smaller chunks to avoid timeouts

        # Process emails in chunks
        for chunk_start in range(0, len(messages), chunk_size):
            chunk_end = min(chunk_start + chunk_size, len(messages))
            chunk = messages[chunk_start:chunk_end]

            logger.info(f"Processing chunk {chunk_start + 1}-{chunk_end} of {len(messages)}")

            # Fetch details for this chunk
            email_list = []
            failed_fetches = 0

            for i, message in enumerate(chunk):
                detail_result = self.gmail_api.get_message_detail(message["id"])
                if not detail_result["success"]:
                    logger.warning(f"Failed to get detail for message {message['id']}")
                    failed_fetches += 1
                    continue

                email_data = self.gmail_api.parse_message(detail_result["data"])
                email_list.append(email_data)

            # Group emails by thread for processing
            if email_list:
                threads_grouped = self._group_messages_by_thread(email_list)
                logger.info(f"Grouped {len(email_list)} emails into {len(threads_grouped)} threads")
                
                # Process threads and save to both systems
                chunk_result = self._process_thread_batch(threads_grouped, email_list)
                
                total_processed += chunk_result["processed"]
                total_duplicates += chunk_result["duplicates"] 
                total_errors += chunk_result["errors"]

        logger.info(
            f"Streaming sync complete: {total_processed} processed, {total_duplicates} duplicates, {total_errors} errors"
        )

        return {
            "success": True,
            "message": f"Synced {total_processed} new emails",
            "processed": total_processed,
            "duplicates": total_duplicates,
            "errors": total_errors,
        }

    def _sync_emails_single(self, messages) -> dict[str, Any]:
        """Sync emails one at a time for smaller batches.

        Args:
            messages: List of message dictionaries from Gmail API.

        Returns:
            dict: Success status with total processed count.
        """
        synced_count = 0
        logger.info(f"Using single-email mode for {len(messages)} emails")

        for message in messages:
            detail_result = self.gmail_api.get_message_detail(message["id"])
            if not detail_result["success"]:
                logger.warning(f"Failed to get detail for message {message['id']}")
                continue

            email_data = self.gmail_api.parse_message(detail_result["data"])
            save_result = self.storage.save_email(email_data)

            if save_result["success"]:
                synced_count += 1
            else:
                logger.warning(
                    f"Failed to save email {email_data.get('message_id', 'unknown')}: {save_result.get('error', 'Unknown error')}"
                )

        logger.info(f"Email sync completed: {synced_count} emails synced")

        # FAIL HARD if no emails were processed - indicates validation or system failure
        if synced_count == 0:
            error_msg = f"CRITICAL FAILURE: 0 emails synced from {len(messages)} retrieved. Check email validation and storage."
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "retrieved": len(messages),
                "processed": synced_count,
            }

        return {
            "success": True,
            "message": f"Synced {synced_count} emails",
            "processed": synced_count,  # Use 'processed' to match other services
        }

    def get_emails(self, limit: int = 100) -> dict[str, Any]:
        """Get emails from local database.

        Args:
            limit: Maximum number of emails to retrieve.

        Returns:
            dict: Success status with list of email data.
        """
        emails = self.storage.get_emails(limit)
        return {"success": True, "data": emails}

    def sync_incremental(self, max_results: int = 500) -> dict[str, Any]:
        """
        Perform incremental sync using Gmail History API.
        Falls back to full sync if history ID is not available or expired.
        """
        logger.info("Starting incremental sync")

        # Get user profile to get email address
        profile_result = self.gmail_api.get_profile()
        if not profile_result["success"]:
            logger.error(f"Failed to get profile: {profile_result.get('error')}")
            return profile_result

        account_email = profile_result["email"]
        current_history_id = profile_result["history_id"]

        # Get sync state from database
        sync_state = self.storage.get_sync_state(account_email)

        if sync_state and sync_state.get("last_history_id"):
            # Try incremental sync
            logger.info(
                f"Attempting incremental sync from history ID {sync_state['last_history_id']}"
            )

            # Update sync status
            self.storage.update_sync_state(account_email, status="syncing")

            # Get history changes
            history_result = self.gmail_api.get_history(
                sync_state["last_history_id"], max_results=max_results
            )

            if history_result.get("success"):
                # Extract message IDs from history
                message_ids = self.gmail_api.extract_message_ids_from_history(
                    history_result.get("history", [])
                )

                if message_ids:
                    logger.info(f"Found {len(message_ids)} new/modified messages")

                    # Fetch and save new messages
                    result = self._fetch_and_save_messages(message_ids, account_email)

                    # Update sync state with new history ID
                    self.storage.update_sync_state(
                        account_email,
                        history_id=history_result["history_id"],
                        messages_processed=result.get("processed", 0),
                        duplicates_found=result.get("duplicates", 0),
                        status="idle",
                    )

                    return result
                else:
                    logger.info("No new messages since last sync")

                    # Update history ID even if no new messages
                    self.storage.update_sync_state(
                        account_email, history_id=history_result["history_id"], status="idle"
                    )

                    return {
                        "success": True,
                        "message": "No new messages",
                        "processed": 0,
                        "duplicates": 0,
                    }

            elif history_result.get("need_full_sync"):
                logger.warning("History ID expired, falling back to full sync")
                # Fall through to full sync
            else:
                # History API failed for other reasons
                error_msg = f"History API failed: {history_result.get('error')}"
                logger.error(error_msg)
                self.storage.update_sync_state(account_email, status="error", error=error_msg)
                return {"success": False, "error": error_msg}
        else:
            logger.info("No sync state found, performing initial full sync")

        # Perform full sync
        logger.info("Performing full sync")
        self.storage.update_sync_state(account_email, status="syncing")

        # Use existing sync method with batch mode
        sync_result = self.sync_emails(max_results=max_results, batch_mode=True)

        if sync_result["success"]:
            # Update sync state with current history ID
            self.storage.update_sync_state(
                account_email,
                history_id=current_history_id,
                messages_processed=sync_result.get("processed", 0),
                duplicates_found=sync_result.get("duplicates", 0),
                status="idle",
            )
        else:
            self.storage.update_sync_state(
                account_email, status="error", error=sync_result.get("error")
            )

        return sync_result

    def _group_messages_by_thread(self, email_list: list[dict]) -> dict[str, list[dict]]:
        """Group emails by thread ID for thread-based processing.
        
        Args:
            email_list: List of parsed email data
            
        Returns:
            Dict mapping thread_id to list of emails in that thread
        """
        threads = {}
        
        for email in email_list:
            # Try to get thread_id from message data
            thread_id = email.get("thread_id") or email.get("message_id")
            
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(email)
        
        return threads

    def _process_thread_batch(self, threads_grouped: dict[str, list[dict]], email_list: list[dict]) -> dict[str, Any]:
        """Process grouped threads and save to both email storage and analog DB.
        
        Args:
            threads_grouped: Dictionary of thread_id -> emails
            email_list: Original email list for backward compatibility
            
        Returns:
            Dict with processing results
        """
        processed = 0
        duplicates = 0
        errors = 0
        
        # First, maintain backward compatibility with existing email storage
        save_result = self.storage.save_emails_batch(email_list, batch_size=len(email_list))
        
        if save_result["success"]:
            processed += save_result["inserted"]
            duplicates += save_result["ignored"]
            errors += save_result["validation_errors"]
            
            logger.info(
                f"Email storage: {save_result['inserted']} new, "
                f"{save_result['ignored']} duplicates, "
                f"{save_result['validation_errors']} errors"
            )
            
            # Process and store summaries for new emails
            if save_result["inserted"] > 0:
                self._process_email_summaries(email_list)
        else:
            logger.error(f"Email storage failed: {save_result.get('error')}")
            errors += len(email_list)
        
        # Process threads using EmailThreadProcessor if available
        if self.thread_processor and threads_grouped:
            try:
                logger.info(f"Processing {len(threads_grouped)} threads with EmailThreadProcessor")
                thread_processed = 0
                
                for thread_id, thread_emails in threads_grouped.items():
                    if len(thread_emails) > 1:  # Only process actual threads (multiple emails)
                        try:
                            # Sort emails chronologically for thread processing
                            sorted_emails = sorted(thread_emails, key=lambda x: x.get("datetime_utc", ""))
                            
                            # Create thread data compatible with EmailThreadProcessor
                            thread_data = {
                                "id": thread_id,
                                "messages": []
                            }
                            
                            for email in sorted_emails:
                                message_data = {
                                    "id": email.get("message_id"),
                                    "payload": {
                                        "headers": [
                                            {"name": "Subject", "value": email.get("subject", "")},
                                            {"name": "From", "value": email.get("sender", "")},
                                            {"name": "To", "value": email.get("recipient_to", "")},
                                            {"name": "Date", "value": email.get("datetime_utc", "")}
                                        ]
                                    },
                                    "internalDate": email.get("datetime_utc", ""),
                                    "body": {"data": email.get("content", "")}
                                }
                                thread_data["messages"].append(message_data)
                            
                            # Process thread and save to analog DB
                            result = self.thread_processor.process_thread(
                                thread_id=thread_id,
                                include_metadata=True,
                                save_to_db=True
                            )
                            
                            if result.get("success"):
                                thread_processed += 1
                                logger.debug(f"Thread {thread_id} processed successfully")
                                
                                # Track thread processing in database
                                self.db.add_thread_tracking(thread_id, len(thread_emails), "processed")
                            
                        except Exception as e:
                            logger.warning(f"Failed to process thread {thread_id}: {e}")
                            continue
                
                logger.info(f"EmailThreadProcessor completed: {thread_processed} threads processed")
                
            except Exception as e:
                logger.error(f"EmailThreadProcessor failed: {e}")
        
        return {
            "processed": processed,
            "duplicates": duplicates,
            "errors": errors
        }

    def _fetch_and_save_messages(
        self, message_ids: list[str], account_email: str
    ) -> dict[str, Any]:
        """
        Fetch full message details and save them using batch operations.

        Args:
            message_ids: List of message IDs to fetch
            account_email: Email account being synced

        Returns:
            Dict with sync results
        """
        email_list = []
        attachments_by_message = {}
        failed_fetches = 0

        for i, message_id in enumerate(message_ids):
            # Fetch message details
            detail_result = self.gmail_api.get_message_detail(message_id)
            if not detail_result["success"]:
                logger.warning(f"Failed to get detail for message {message_id}")
                failed_fetches += 1
                continue

            # Parse email data
            email_data = self.gmail_api.parse_message(detail_result["data"])
            email_list.append(email_data)

            # Get attachments
            attachment_result = self.gmail_api.get_attachments(message_id, detail_result["data"])
            if attachment_result["success"] and attachment_result["attachments"]:
                attachments_by_message[message_id] = attachment_result["attachments"]

            # Log progress
            if (i + 1) % 50 == 0:
                logger.info(f"Fetched {i + 1}/{len(message_ids)} message details")

        logger.info(f"Fetched {len(email_list)} emails, {failed_fetches} failures")

        # Process emails using new thread-based logic (maintains backward compatibility)
        if email_list:
            # Group emails by thread for consistent processing
            threads_grouped = self._group_messages_by_thread(email_list)
            
            # Use the same thread processing logic as batch mode
            result = self._process_thread_batch(threads_grouped, email_list)
            
            # Save attachments with pipeline support
            for message_id, attachments in attachments_by_message.items():
                # Save attachment metadata to database
                self.storage.save_attachments(message_id, attachments)

                # Add attachment info to pipeline for tracking
                for attachment in attachments:
                    if attachment.get("filename"):
                        # Create a placeholder file in raw for tracking
                        placeholder_path = (
                            f"data/raw/email_attachment_{message_id}_{attachment['filename']}.meta"
                        )
                        try:
                            os.makedirs("data/raw", exist_ok=True)
                            with open(placeholder_path, "w") as f:
                                import json

                                json.dump(
                                    {
                                        "message_id": message_id,
                                        "filename": attachment["filename"],
                                        "mime_type": attachment.get("mime_type", ""),
                                        "size_bytes": attachment.get("size_bytes", 0),
                                        "attachment_id": attachment.get("attachment_id", ""),
                                        "source": "gmail",
                                    },
                                    f,
                                    indent=2,
                                )
                            # Move to processed since it's just metadata
                            self.pipeline.move_to_staged(os.path.basename(placeholder_path))
                            self.pipeline.move_to_processed(
                                os.path.basename(placeholder_path),
                                {"type": "email_attachment_metadata"},
                            )
                        except Exception as e:
                            logger.warning(f"Could not track attachment in pipeline: {e}")
            
            save_result = {"success": True, "inserted": result["processed"], "ignored": result["duplicates"]}

            if save_result["success"]:
                logger.info(
                    f"Saved {save_result['inserted']} new emails, "
                    f"{save_result['ignored']} duplicates"
                )

                return {
                    "success": True,
                    "message": f"Synced {save_result['inserted']} new emails",
                    "processed": save_result["inserted"],
                    "duplicates": save_result["ignored"],
                    "errors": save_result.get("validation_errors", 0),
                }
            else:
                return {
                    "success": False,
                    "error": save_result.get("error", "Failed to save emails"),
                }
        else:
            return {
                "success": True,
                "message": "No emails to save",
                "processed": 0,
                "duplicates": 0,
            }

    def _process_email_summaries(self, email_list: list[dict]) -> None:
        """Process and store summaries for a list of emails."""
        try:
            for email_data in email_list:
                # Skip if no content
                if not email_data.get("content"):
                    continue

                # First, add email to content table to get content_id
                content_id = self.db.add_content(
                    content_type="email",
                    title=email_data.get("subject", "No Subject"),
                    content=email_data.get("content", ""),
                    metadata={
                        "message_id": email_data.get("message_id"),
                        "sender": email_data.get("sender"),
                        "recipient": email_data.get("recipient_to"),
                        "datetime_utc": email_data.get("datetime_utc"),
                    },
                )

                # Generate summary
                email_content = email_data.get("content", "")

                if email_content and len(email_content) > 50:  # Only summarize meaningful content
                    summary = self.summarizer.extract_summary(
                        email_content,
                        max_sentences=3,  # Emails typically need fewer sentences
                        max_keywords=10,
                        summary_type="combined",
                    )

                    # Store summary in database
                    if summary and (summary.get("summary_text") or summary.get("tf_idf_keywords")):
                        summary_id = self.db.add_document_summary(
                            document_id=content_id,
                            summary_type="combined",
                            summary_text=summary.get("summary_text"),
                            tf_idf_keywords=summary.get("tf_idf_keywords"),
                            textrank_sentences=summary.get("textrank_sentences"),
                        )

                        if summary_id:
                            logger.debug(
                                f"Generated summary for email: {email_data.get('subject', 'No Subject')[:50]}"
                            )

                            # Export email to markdown (don't fail sync if this fails)
                            try:
                                subject = email_data.get("subject", "No Subject")
                                export_result = self.exporter.save_to_export(
                                    content_id, subject[:50]  # Limit subject length for filename
                                )
                                if export_result["success"]:
                                    logger.debug(f"Exported email to {export_result['filename']}")
                                else:
                                    logger.warning(
                                        f"Export failed for email {subject[:30]}: {export_result.get('error')}"
                                    )
                            except Exception as export_e:
                                logger.warning(
                                    f"Could not export email {email_data.get('subject', 'Unknown')[:30]}: {export_e}"
                                )

        except Exception as e:
            # Don't fail email sync if summarization fails
            logger.warning(f"Could not generate email summaries: {e}")


def main() -> None:
    service = GmailService()
    result = service.sync_emails()  # Uses config by default
    print(result)


if __name__ == "__main__":
    main()
