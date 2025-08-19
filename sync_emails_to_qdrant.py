#!/usr/bin/env python3
"""
Sync emails from Gmail and process them into Qdrant vector store.
"""

from loguru import logger
from gmail.main import GmailService
from utilities.vector_store import get_vector_store
from utilities.embeddings import get_embedding_service
from shared.simple_db import SimpleDB

def main():
    logger.info("Starting email sync to Qdrant process")
    
    # Initialize services
    gmail_service = GmailService(db_path='data/emails.db')
    SimpleDB()
    vector_store = get_vector_store()
    embedding_service = get_embedding_service()
    
    # Step 1: Sync emails from Gmail (smaller batch for testing)
    logger.info("Syncing emails from Gmail...")
    sync_result = gmail_service.sync_emails(max_results=50, batch_mode=False)
    
    if not sync_result["success"]:
        logger.error(f"Failed to sync emails: {sync_result.get('error')}")
        return
    
    logger.info(f"Synced {sync_result.get('processed', 0)} emails from Gmail")
    
    # Step 2: Get emails from database
    emails = gmail_service.get_emails(limit=100)
    
    if emails["success"] and emails["data"]:
        logger.info(f"Found {len(emails['data'])} emails in database")
        
        # Step 3: Process emails into Qdrant
        processed = 0
        for email in emails["data"]:
            try:
                # Create text for embedding
                text = f"Subject: {email.get('subject', '')}\n"
                text += f"From: {email.get('sender', '')}\n"
                text += f"Content: {email.get('content', '')[:1000]}"  # Limit content length
                
                # Generate embedding
                embedding = embedding_service.get_embedding(text)
                
                # Store in Qdrant
                vector_store.upsert(
                    vector=embedding,
                    payload={
                        "type": "email",
                        "subject": email.get('subject', ''),
                        "sender": email.get('sender', ''),
                        "date": email.get('datetime_utc', ''),
                        "message_id": email.get('message_id'),
                        "content": text[:500]  # Store snippet for display
                    },
                    id=email.get('message_id')
                )
                
                processed += 1
                logger.debug(f"Processed email: {email.get('subject', 'No subject')[:50]}")
                    
            except Exception as e:
                logger.error(f"Error processing email {email.get('message_id')}: {e}")
                continue
        
        logger.info(f"Successfully processed {processed} emails into Qdrant")
        
        # Step 4: Verify by searching
        test_query = "legal"
        logger.info(f"Testing search with query: '{test_query}'")
        
        # Generate query embedding
        query_embedding = embedding_service.get_embedding(test_query)
        
        search_results = vector_store.search(
            vector=query_embedding,
            limit=5
        )
        
        if search_results:
            logger.info(f"Search returned {len(search_results)} results")
            for i, result in enumerate(search_results[:3], 1):
                logger.info(f"  {i}. Score: {result['score']:.3f}, Subject: {result['payload'].get('subject', 'N/A')[:50]}")
        else:
            logger.warning("No search results found")
    else:
        logger.warning("No emails found in database to process")
    
    logger.info("Email sync to Qdrant process complete")

if __name__ == "__main__":
    main()