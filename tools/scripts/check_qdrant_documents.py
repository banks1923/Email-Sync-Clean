#!/usr/bin/env python3
"""
Check if documents are actually in Qdrant
"""

import random
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utilities.vector_store import get_vector_store


def check_qdrant_documents():
    """Check what's actually in Qdrant"""

    print("Checking Qdrant for document vectors...")
    print("-" * 60)

    try:
        qdrant = get_vector_store()

        # Get collection info
        vector_count = qdrant.count()
        print(f"✅ Collection has {vector_count} total vectors")

        # Do a sample search to see what metadata fields exist
        print("\n📊 Sampling vectors to check metadata...")

        # Create a random query vector
        random_vector = [random.random() for _ in range(1024)]

        results = qdrant.search(random_vector, limit=10)

        email_count = 0
        doc_count = 0

        for match in results:
            metadata = match.get("payload", {})

            # Check if it's a document or email
            if "chunk_id" in metadata or metadata.get("source") == "document":
                doc_count += 1
                if doc_count == 1:  # Print first document
                    print("\n📄 Sample document vector:")
                    print(f"  Metadata keys: {list(metadata.keys())}")
                    print(f"  Source: {metadata.get('source', 'NOT SET')}")
                    print(f"  File: {metadata.get('file_name', 'Unknown')}")
                    print(f"  Chunk ID: {metadata.get('chunk_id', 'None')}")
            elif "message_id" in metadata:
                email_count += 1
                if email_count == 1:  # Print first email
                    print("\n✉️  Sample email vector:")
                    print(f"  Metadata keys: {list(metadata.keys())}")
                    print(f"  Message ID: {metadata.get('message_id')}")
                    print(f"  Subject: {metadata.get('subject', 'No subject')}")

        print("\n📈 Summary:")
        print(f"  Documents found: {doc_count}")
        print(f"  Emails found: {email_count}")

    except Exception as e:
        print(f"❌ Error connecting to Qdrant: {e}")
        print("Make sure Qdrant is running: docker run -p 6333:6333 qdrant/qdrant")


if __name__ == "__main__":
    check_qdrant_documents()
