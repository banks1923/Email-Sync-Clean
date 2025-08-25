#!/usr/bin/env python3
"""Batch processor for parsing email messages using advanced deduplication.

Processes all email files and populates the new message-level schema.
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from shared.simple_db import SimpleDB
from email_parsing.message_deduplicator import MessageDeduplicator


class EmailBatchProcessor:
    """
    Batch processor for email message extraction and deduplication.
    """
    
    def __init__(self, db: SimpleDB, email_dir: str = None):
        """Initialize the batch processor.

        Args:
            db: SimpleDB instance
            email_dir: Directory containing email files (default: data/Stoneman_dispute/user_data/emails)
        """
        self.db = db
        self.deduplicator = MessageDeduplicator()
        
        # Use default email directory if not specified
        if email_dir is None:
            email_dir = "data/Stoneman_dispute/user_data/emails"
        self.email_dir = Path(email_dir)
        
        # Processing statistics
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_messages': 0,
            'unique_messages': 0,
            'duplicate_messages': 0,
            'total_occurrences': 0,
            'processing_time': 0.0,
            'errors': []
        }
        
        # Resume tracking
        self.processed_files_path = Path('.processed_emails.json')
        self.processed_files = self._load_processed_files()
    
    def _load_processed_files(self) -> set:
        """
        Load list of already processed files for resume capability.
        """
        if self.processed_files_path.exists():
            try:
                with open(self.processed_files_path) as f:
                    return set(json.load(f))
            except Exception as e:
                logger.warning(f"Could not load processed files list: {e}")
        return set()
    
    def _save_processed_file(self, filepath: str):
        """
        Mark a file as processed.
        """
        self.processed_files.add(filepath)
        try:
            with open(self.processed_files_path, 'w') as f:
                json.dump(list(self.processed_files), f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save processed files list: {e}")
    
    def find_email_files(self) -> list[Path]:
        """Find all email files in the configured directory.

        Returns:
            List of Path objects for email files
        """
        email_files = []
        
        # Common email file patterns
        patterns = ['*.eml', '*.msg', '*.txt', 'email_*.txt', '*.email']
        
        if not self.email_dir.exists():
            logger.error(f"Email directory does not exist: {self.email_dir}")
            return email_files
        
        # Find files matching patterns
        for pattern in patterns:
            email_files.extend(self.email_dir.glob(pattern))
        
        # Also check subdirectories
        for pattern in patterns:
            email_files.extend(self.email_dir.rglob(pattern))
        
        # Remove duplicates and sort
        email_files = sorted(set(email_files))
        
        logger.info(f"Found {len(email_files)} email files in {self.email_dir}")
        return email_files
    
    def process_email(self, email_path: Path) -> tuple[int, int]:
        """Process a single email file.

        Args:
            email_path: Path to email file

        Returns:
            Tuple of (unique_messages_count, total_occurrences_count)
        """
        try:
            # Read email content
            with open(email_path, encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Use filename as email_id
            email_id = email_path.stem
            
            # Parse messages using deduplicator
            messages = self.deduplicator.parse_email_thread(content, email_id)
            
            if not messages:
                logger.debug(f"No messages extracted from {email_path.name}")
                return 0, 0
            
            # Deduplicate messages
            unique_messages = self.deduplicator.deduplicate_messages(messages)
            
            # Store in database
            unique_count = 0
            occurrence_count = 0
            
            for msg_hash, msg_data in unique_messages.items():
                # Add to individual_messages table
                is_new = self.db.add_individual_message(
                    message_hash=msg_hash,
                    content=msg_data['content'],
                    subject=msg_data['subject'],
                    sender_email=msg_data['sender'],
                    sender_name=None,  # Could extract from sender field
                    recipients=None,  # Could extract if available
                    date_sent=msg_data['date'],
                    message_id=None,  # Would need email headers
                    parent_message_id=None,
                    thread_id=None,  # Could infer from subject/headers
                    content_type=msg_data['context_type'],
                    first_seen_email_id=email_id
                )
                
                if is_new:
                    unique_count += 1
                    
                    # Also add to content_unified for vector search
                    self.db.add_content(
                        content_type='email_message',
                        title=msg_data['subject'] or f"Message from {msg_data['sender'] or 'Unknown'}",
                        content=msg_data['content'],
                        message_hash=msg_hash  # Pass the hash for TEXT source_id
                    )
                
                # Record all occurrences
                for occurrence in msg_data['occurrences']:
                    self.db.add_message_occurrence(
                        message_hash=msg_hash,
                        email_id=email_id,
                        position_in_email=occurrence['position'],
                        context_type=occurrence['context_type'],
                        quote_depth=occurrence['quote_depth']
                    )
                    occurrence_count += 1
            
            logger.info(f"Processed {email_path.name}: {len(messages)} messages, "
                       f"{unique_count} new unique, {occurrence_count} occurrences")
            
            return unique_count, occurrence_count
            
        except Exception as e:
            logger.error(f"Failed to process {email_path}: {e}")
            self.stats['errors'].append({
                'file': str(email_path),
                'error': str(e)
            })
            raise
    
    def process_all(self, resume: bool = True) -> dict:
        """Process all email files in batch.

        Args:
            resume: If True, skip already processed files

        Returns:
            Processing statistics dictionary
        """
        start_time = time.time()
        
        # Find all email files
        email_files = self.find_email_files()
        self.stats['total_files'] = len(email_files)
        
        if not email_files:
            logger.warning("No email files found to process")
            return self.stats
        
        # Process each file
        for i, email_path in enumerate(email_files, 1):
            # Skip if already processed (resume capability)
            if resume and str(email_path) in self.processed_files:
                logger.debug(f"Skipping already processed: {email_path.name}")
                continue
            
            try:
                logger.info(f"Processing [{i}/{len(email_files)}]: {email_path.name}")
                
                unique_count, occurrence_count = self.process_email(email_path)
                
                # Update statistics
                self.stats['processed_files'] += 1
                self.stats['unique_messages'] += unique_count
                self.stats['total_occurrences'] += occurrence_count
                
                # Mark as processed for resume capability
                self._save_processed_file(str(email_path))
                
                # Progress update every 10 files
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = self.stats['processed_files'] / elapsed
                    logger.info(f"Progress: {i}/{len(email_files)} files, "
                               f"{rate:.1f} files/second")
                
            except Exception as e:
                logger.error(f"Failed to process {email_path.name}: {e}")
                self.stats['failed_files'] += 1
                continue
        
        # Calculate final statistics
        self.stats['processing_time'] = time.time() - start_time
        
        # Get total message count from database
        total_messages = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM individual_messages"
        )
        self.stats['total_messages'] = total_messages['count'] if total_messages else 0
        
        # Calculate deduplication rate
        if self.stats['total_occurrences'] > 0:
            self.stats['deduplication_rate'] = (
                1 - (self.stats['total_messages'] / self.stats['total_occurrences'])
            ) * 100
        
        return self.stats
    
    def print_report(self):
        """
        Print a summary report of processing results.
        """
        print("\n" + "="*60)
        print("EMAIL PARSING BATCH PROCESSING REPORT")
        print("="*60)
        print(f"Total files found:        {self.stats['total_files']}")
        print(f"Successfully processed:   {self.stats['processed_files']}")
        print(f"Failed files:            {self.stats['failed_files']}")
        print("-"*60)
        print(f"Total unique messages:    {self.stats['total_messages']}")
        print(f"Total occurrences:       {self.stats['total_occurrences']}")
        
        if self.stats.get('deduplication_rate'):
            print(f"Deduplication rate:      {self.stats['deduplication_rate']:.1f}%")
        
        print(f"Processing time:         {self.stats['processing_time']:.1f} seconds")
        
        if self.stats['processing_time'] > 0:
            rate = self.stats['processed_files'] / self.stats['processing_time']
            print(f"Processing rate:         {rate:.1f} files/second")
        
        if self.stats['errors']:
            print("\n" + "-"*60)
            print(f"ERRORS ({len(self.stats['errors'])} files):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {Path(error['file']).name}: {error['error']}")
            if len(self.stats['errors']) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more errors")
        
        print("="*60 + "\n")


def main():
    """
    Main entry point for batch processing.
    """
    parser = argparse.ArgumentParser(
        description="Batch process email files for message-level deduplication"
    )
    parser.add_argument(
        '--email-dir',
        help='Directory containing email files',
        default='data/Stoneman_dispute/user_data/emails'
    )
    parser.add_argument(
        '--db-path',
        help='Path to SQLite database',
        default='data/system_data/emails.db'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Process all files, ignore resume state'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset processing state and start fresh'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.add(sys.stderr, level="INFO")
    
    # Reset processing state if requested
    if args.reset:
        processed_file = Path('.processed_emails.json')
        if processed_file.exists():
            processed_file.unlink()
            logger.info("Reset processing state")
    
    # Initialize database connection
    db = SimpleDB(args.db_path)
    
    # Create processor and run
    processor = EmailBatchProcessor(db, args.email_dir)
    
    try:
        logger.info("Starting email batch processing...")
        stats = processor.process_all(resume=not args.no_resume)
        processor.print_report()
        
        # Save final statistics
        stats_file = Path('email_processing_stats.json')
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        logger.info(f"Statistics saved to {stats_file}")
        
    except KeyboardInterrupt:
        logger.warning("Processing interrupted by user")
        processor.print_report()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error during processing: {e}")
        processor.print_report()
        sys.exit(1)


if __name__ == '__main__':
    main()