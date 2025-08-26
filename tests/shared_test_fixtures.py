"""Shared Test Fixtures for Real Component Testing.

Following PROJECT_PHILOSOPHY.md:
- No mocks for internal components
- Real implementations with in-memory storage
- Simple, direct testing without enterprise patterns
"""

import contextlib
import sqlite3
from typing import Any

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


class TestEmbedder:
    """
    Simple test embedder that returns consistent vectors.
    """

    def embed_text(self, text: str) -> dict[str, Any]:
        """
        Return deterministic 1024D vector based on text.
        """
        # Simple hash-based embedding for consistency
        base_value = sum(ord(c) for c in text) / (len(text) + 1) / 1000.0
        return {
            "success": True,
            "embedding": [base_value + i * 0.0001 for i in range(1024)],
            "provider": "test",
            "dimensions": 1024,
        }

    def get_embeddings(self, texts: list[str], provider: str = "test") -> dict[str, Any]:
        """
        Batch embedding for multiple texts.
        """
        embeddings = []
        for text in texts:
            result = self.embed_text(text)
            if result["success"]:
                embeddings.append(result["embedding"])
            else:
                return {"success": False, "error": "Embedding failed"}

        return {"success": True, "embeddings": embeddings, "provider": provider, "dimensions": 1024}


class TestDatabase:
    """
    In-memory SQLite database for testing.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._setup_schema()

    def _setup_schema(self):
        """
        Create test database schema.
        """
        # Emails table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS emails (
                message_id TEXT PRIMARY KEY,
                subject TEXT,
                sender TEXT,
                recipient_to TEXT,
                datetime_utc TEXT,
                content TEXT,
                vector_processed INTEGER DEFAULT 0
            )
        """
        )

        # Content table (for transcripts, documents)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS content (
                id TEXT PRIMARY KEY,
                content_type TEXT,
                title TEXT,
                content TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Documents table (for PDFs)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_hash TEXT NOT NULL,
                file_name TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(file_hash, chunk_index)
            )
        """
        )

        self.conn.commit()

    def get_all_emails(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """
        Get unprocessed emails.
        """
        cursor = self.conn.execute(
            """
            SELECT message_id, subject, sender, recipient_to, datetime_utc, content
            FROM emails
            WHERE vector_processed = 0
            LIMIT ? OFFSET ?
        """,
            (limit, offset),
        )

        emails = []
        for row in cursor:
            emails.append(
                {
                    "message_id": row["message_id"],
                    "subject": row["subject"],
                    "sender": row["sender"],
                    "recipient": row["recipient_to"],
                    "datetime": row["datetime_utc"],
                    "content": row["content"],
                }
            )

        return {"success": True, "emails": emails}

    def get_email_by_id(self, message_id: str) -> dict[str, Any]:
        """
        Get specific email by ID.
        """
        cursor = self.conn.execute(
            """
            SELECT subject, sender, recipient_to, content, datetime_utc
            FROM emails WHERE message_id = ?
        """,
            (message_id,),
        )

        row = cursor.fetchone()
        if row:
            return {
                "success": True,
                "email": {
                    "subject": row["subject"],
                    "sender": row["sender"],
                    "recipient": row["recipient_to"],
                    "content": row["content"],
                    "timestamp": row["datetime_utc"],
                },
            }
        return {"success": False, "error": "Email not found"}

    def mark_email_processed(self, message_id: str) -> bool:
        """
        Mark email as vector processed.
        """
        self.conn.execute(
            "UPDATE emails SET vector_processed = 1 WHERE message_id = ?", (message_id,)
        )
        self.conn.commit()
        return True

    def add_test_emails(self, emails: list[dict[str, str]]):
        """
        Add test emails to database.
        """
        for email in emails:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO emails
                (message_id, subject, sender, recipient_to, datetime_utc, content, vector_processed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    email["message_id"],
                    email["subject"],
                    email["sender"],
                    email.get("recipient", "test@example.com"),
                    email.get("datetime", "2025-01-01 10:00:00"),
                    email["content"],
                    email.get("vector_processed", 0),
                ),
            )
        self.conn.commit()

    def add_content(
        self, content_type: str, title: str, content: str, metadata: dict = None
    ) -> dict[str, Any]:
        """
        Add content (transcript, document) to database.
        """
        import json
        import uuid

        content_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata or {})

        self.conn.execute(
            """
            INSERT INTO content_unified (source_id, source_type, title, body)
            VALUES (?, ?, ?, ?)
        """,
            (content_id, content_type, title, content),
        )
        self.conn.commit()

        return {"success": True, "content_id": content_id}

    def search_content(
        self, query: str, content_type: str = None, limit: int = 10
    ) -> dict[str, Any]:
        """
        Simple keyword search in content.
        """
        sql = """
            SELECT id, source_type, title, body
            FROM content_unified
            WHERE (title LIKE ? OR body LIKE ?)
        """
        params = [f"%{query}%", f"%{query}%"]

        if content_type:
            sql += " AND source_type = ?"
            params.append(content_type)

        sql += " LIMIT ?"
        params.append(limit)

        cursor = self.conn.execute(sql, params)

        results = []
        for row in cursor:
            results.append(
                {
                    "id": row["content_id"],
                    "content_type": row["content_type"],
                    "title": row["title"],
                    "content": row["content"][:200],  # Preview
                    "metadata": row["metadata"],
                }
            )

        return {"success": True, "results": results}

    def close(self):
        """
        Close database connection.
        """
        if self.conn:
            self.conn.close()


class TestQdrantOperations:
    """
    Test Qdrant operations with in-memory client.
    """

    def __init__(self, collection_name: str = "test_emails"):
        self.client = QdrantClient(":memory:")
        self.collection_name = collection_name
        self._setup_collection()
        self.stored_vectors = {}  # Track for testing

    def _setup_collection(self):
        """
        Create test collection with 1024D vectors.
        """
        try:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
            )
        except Exception:
            # Collection might already exist in some tests
            pass

    def check_vector_exists(self, message_id: str) -> dict[str, Any]:
        """
        Check if vector exists in collection.
        """
        try:
            result = self.client.retrieve(collection_name=self.collection_name, ids=[message_id])
            exists = len(result) > 0
            return {"success": True, "exists": exists}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def store_vector(
        self, message_id: str, vector: list[float], metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Store vector with metadata.
        """
        try:
            point = PointStruct(id=message_id, vector=vector, payload=metadata)

            self.client.upsert(collection_name=self.collection_name, points=[point])

            # Track for testing
            self.stored_vectors[message_id] = {"vector": vector, "metadata": metadata}

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_vectors(self, query_vector: list[float], limit: int = 5) -> dict[str, Any]:
        """
        Search for similar vectors.
        """
        try:
            results = self.client.search(
                collection_name=self.collection_name, query_vector=query_vector, limit=limit
            )

            matches = []
            for result in results:
                matches.append({"id": result.id, "score": result.score, "metadata": result.payload})

            return {"success": True, "matches": matches}
        except Exception as e:
            return {"success": False, "error": str(e), "matches": []}

    def delete_collection(self):
        """
        Delete the collection for cleanup.
        """
        with contextlib.suppress(Exception):
            self.client.delete_collection(self.collection_name)


class TestGmailService:
    """
    Minimal Gmail service for testing.
    """

    def __init__(self, db: TestDatabase):
        self.db = db

    def sync_emails(self, max_results: int = 50) -> dict[str, Any]:
        """
        Simulate email sync by adding test emails.
        """
        test_emails = [
            {
                "message_id": f"gmail_{i}",
                "subject": f"Test Email {i}",
                "sender": f"sender{i}@test.com",
                "content": f"This is test email content number {i}",
            }
            for i in range(min(max_results, 5))
        ]

        self.db.add_test_emails(test_emails)

        return {"success": True, "synced": len(test_emails), "new_emails": len(test_emails)}


class TestVectorService:
    """
    Minimal vector service for testing.
    """

    def __init__(self, embedder: TestEmbedder, qdrant: TestQdrantOperations, db: TestDatabase):
        self.embedder = embedder
        self.qdrant = qdrant
        self.db = db
        self.validation_result = {"success": True}

    def process_emails(self, limit: int = 100) -> dict[str, Any]:
        """
        Process unprocessed emails.
        """
        result = self.db.get_all_emails(limit=limit)
        if not result["success"]:
            return {"success": False, "error": "Failed to get emails"}

        processed = 0
        failed = 0

        for email in result["emails"]:
            # Check if already processed
            exists_result = self.qdrant.check_vector_exists(email["message_id"])
            if exists_result.get("exists", False):
                continue

            # Generate embedding
            embedding_result = self.embedder.embed_text(email["content"])
            if not embedding_result["success"]:
                failed += 1
                continue

            # Store vector
            store_result = self.qdrant.store_vector(
                email["message_id"],
                embedding_result["embedding"],
                {
                    "subject": email["subject"],
                    "sender": email["sender"],
                    "content": email["content"][:200],
                },
            )

            if store_result["success"]:
                self.db.mark_email_processed(email["message_id"])
                processed += 1
            else:
                failed += 1

        return {
            "success": True,
            "processed": processed,
            "failed": failed,
            "provider": "test",
            "dimensions": 1024,
        }

    def search_similar(self, query: str, limit: int = 5) -> dict[str, Any]:
        """
        Search for similar content.
        """
        # Generate query embedding
        embedding_result = self.embedder.embed_text(query)
        if not embedding_result["success"]:
            return {"success": False, "error": "Failed to embed query"}

        # Search vectors
        search_result = self.qdrant.search_vectors(embedding_result["embedding"], limit)

        if not search_result["success"]:
            return search_result

        # Return results
        return {"success": True, "data": search_result["matches"], "query": query}


# Pytest fixtures for easy use
@pytest.fixture
def test_embedder():
    """
    Provide test embedder.
    """
    return TestEmbedder()


@pytest.fixture
def test_db():
    """
    Provide in-memory test database.
    """
    db = TestDatabase()
    yield db
    db.close()


@pytest.fixture
def test_qdrant():
    """
    Provide in-memory Qdrant client.
    """
    qdrant = TestQdrantOperations()
    yield qdrant
    qdrant.delete_collection()


@pytest.fixture
def test_gmail_service(test_db):
    """
    Provide test Gmail service.
    """
    return TestGmailService(test_db)


@pytest.fixture
def test_vector_service(test_embedder, test_qdrant, test_db):
    """
    Provide test vector service.
    """
    return TestVectorService(test_embedder, test_qdrant, test_db)
