"""Database operations for entity service using SimpleDB.

Follows CLAUDE.md principles - simple and direct.
"""

import hashlib
import json

from shared.simple_db import SimpleDB


class EntityDatabase:
    def __init__(self, db_path="data/system_data/emails.db") -> None:
        # Use absolute path to avoid symlink issues in MCP context
        import os
        from config.settings import settings
        
        # Use settings-based path for consistency
        try:
            db_path = os.path.abspath(settings.database.emails_db_path)
        except:
            # Fallback to absolute path resolution
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.getcwd(), db_path)
        
        self.db = SimpleDB(db_path)
        self.db_path = db_path
        self.init_result = self._ensure_entities_table()

    def _ensure_entities_table(self):
        """
        Create entity tables if they don't exist and handle schema migration.
        """
        try:
            # Create entity_content_mapping table (v2 schema)
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS entity_content_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id TEXT NOT NULL,
                    entity_text TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_label TEXT NOT NULL,
                    start_char INTEGER NOT NULL,
                    end_char INTEGER NOT NULL,
                    confidence REAL,
                    normalized_form TEXT,
                    processed_time TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Add new columns if they don't exist (schema migration)
            new_columns = [
                ("entity_id", "TEXT"),
                ("aliases", "TEXT"),
                ("frequency", "INTEGER DEFAULT 1"),
                ("last_seen", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
                ("extractor_type", "TEXT DEFAULT 'spacy'"),
                ("role_type", "TEXT"),
            ]

            # Check which columns already exist
            existing_columns = self.db.fetch("PRAGMA table_info(entity_content_mapping)")
            existing_column_names = {col["name"] for col in existing_columns}

            for column_name, column_def in new_columns:
                if column_name not in existing_column_names:
                    try:
                        self.db.execute(
                            f"ALTER TABLE entity_content_mapping ADD COLUMN {column_name} {column_def}"
                        )
                    except Exception:
                        # Column already exists or other error, skip silently
                        pass

            # Create consolidated entities table for deduplicated entities
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS consolidated_entities (
                    entity_id TEXT PRIMARY KEY,
                    primary_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    aliases TEXT,
                    total_mentions INTEGER DEFAULT 1,
                    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                    confidence_score REAL DEFAULT 0.8,
                    additional_info TEXT
                )
            """
            )

            # Create entity relationships table for knowledge graph
            self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS entity_relationships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_entity_id TEXT NOT NULL,
                    target_entity_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    confidence REAL DEFAULT 0.5,
                    source_message_id TEXT,
                    context_snippet TEXT,
                    extraction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_entity_id) REFERENCES consolidated_entities(entity_id),
                    FOREIGN KEY (target_entity_id) REFERENCES consolidated_entities(entity_id),
                    UNIQUE(source_entity_id, target_entity_id, relationship_type)
                )
            """
            )

            # Create performance indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_entities_content_id ON entity_content_mapping(content_id)",
                "CREATE INDEX IF NOT EXISTS idx_entities_type ON entity_content_mapping(entity_type)",
                "CREATE INDEX IF NOT EXISTS idx_entities_label ON entity_content_mapping(entity_label)",
                "CREATE INDEX IF NOT EXISTS idx_entities_normalized ON entity_content_mapping(normalized_form)",
                "CREATE INDEX IF NOT EXISTS idx_entities_entity_id ON entity_content_mapping(entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_entities_extractor ON entity_content_mapping(extractor_type)",
                "CREATE INDEX IF NOT EXISTS idx_consolidated_type ON consolidated_entities(entity_type)",
                "CREATE INDEX IF NOT EXISTS idx_consolidated_name ON consolidated_entities(primary_name)",
                "CREATE INDEX IF NOT EXISTS idx_relationships_source ON entity_relationships(source_entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_relationships_target ON entity_relationships(target_entity_id)",
                "CREATE INDEX IF NOT EXISTS idx_relationships_type ON entity_relationships(relationship_type)",
            ]

            for index_sql in indexes:
                self.db.execute(index_sql)

        except Exception as e:
            return {"success": False, "error": f"Failed to create entity tables: {str(e)}"}

        return {"success": True}

    def store_entities(self, entities_data):
        """
        Store extracted entities for an email with enhanced fields.
        """
        if not entities_data:
            return {"success": True, "stored": 0}

        stored_count = 0
        try:
            for entity in entities_data:
                # Generate entity_id if not provided
                entity_id = entity.get("entity_id", self._generate_entity_id(entity))

                self.db.execute(
                    """
                    INSERT INTO entity_content_mapping
                    (content_id, entity_text, entity_type, entity_label, start_char, end_char,
                     confidence, normalized_form, entity_id, extractor_type, role_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        entity.get("content_id", entity.get("message_id", "")),  # Support both content_id and message_id
                        entity["text"],
                        entity["type"],
                        entity["label"],
                        entity["start"],
                        entity["end"],
                        entity.get("confidence", 1.0),
                        entity.get("normalized_form", entity["text"].lower()),
                        entity_id,
                        entity.get("extractor_type", "unknown"),
                        entity.get("role_type"),
                    ),
                )
                stored_count += 1

        except Exception as e:
            return {"success": False, "error": f"Failed to store entities: {str(e)}"}

        return {"success": True, "stored": stored_count}

    def _generate_entity_id(self, entity):
        """
        Generate a unique entity ID based on normalized form and type.
        """
        normalized = entity.get("normalized_form", entity["text"].lower())
        entity_type = entity["type"]
        # Create hash of normalized form + type for uniqueness
        hash_input = f"{normalized}|{entity_type}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]

    def get_entities_for_email(self, message_id):
        """
        Get all entities for a specific email (by message_id or content_id).
        """
        try:
            # First try as content_id (v2 schema)
            entities = self.db.fetch(
                "SELECT * FROM entity_content_mapping WHERE content_id = ? ORDER BY start_char",
                (message_id,),
            )
            
            # If no results, try to look up by legacy message_id
            if not entities:
                # Look up message_hash for this message_id
                message_hash = self.db.fetch_one(
                    "SELECT message_hash FROM individual_messages WHERE message_id = ?",
                    (message_id,)
                )
                if message_hash:
                    entities = self.db.fetch(
                        "SELECT * FROM entity_content_mapping WHERE content_id = ? ORDER BY start_char",
                        (message_hash["message_hash"],),
                    )
            return {"success": True, "data": entities}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_entities_by_type(self, entity_type, limit=100):
        """
        Get entities of a specific type.
        """
        try:
            entities = self.db.fetch(
                "SELECT * FROM entity_content_mapping WHERE entity_type = ? LIMIT ?", (entity_type, limit)
            )
            return {"success": True, "data": entities}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def count_entities(self):
        """
        Get total entity count.
        """
        try:
            result = self.db.fetch_one("SELECT COUNT(*) as count FROM entity_content_mapping")
            return result["count"] if result else 0
        except Exception:
            return 0

    def count_entities_by_type(self):
        """
        Get entity counts grouped by type.
        """
        try:
            results = self.db.fetch(
                "SELECT entity_type, COUNT(*) as count FROM entity_content_mapping GROUP BY entity_type"
            )
            return {"success": True, "data": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def store_consolidated_entity(
        self, entity_id, primary_name, entity_type, aliases=None, additional_info=None
    ):
        """
        Store or update a consolidated entity.
        """
        try:
            aliases_json = json.dumps(aliases) if aliases else None
            info_json = json.dumps(additional_info) if additional_info else None

            self.db.execute(
                """
                INSERT OR REPLACE INTO consolidated_entities
                (entity_id, primary_name, entity_type, aliases, additional_info, last_seen)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (entity_id, primary_name, entity_type, aliases_json, info_json),
            )

            return {"success": True, "entity_id": entity_id}

        except Exception as e:
            return {"success": False, "error": f"Failed to store consolidated entity: {str(e)}"}

    def get_consolidated_entity(self, entity_id):
        """
        Get a consolidated entity by ID.
        """
        try:
            entity = self.db.fetch_one(
                "SELECT * FROM consolidated_entities WHERE entity_id = ?", (entity_id,)
            )
            return {"success": True, "data": entity}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_consolidated_entities(self, entity_type=None, name_pattern=None, limit=100):
        """
        Search consolidated entities.
        """
        try:
            conditions = []
            params = []

            if entity_type:
                conditions.append("entity_type = ?")
                params.append(entity_type)

            if name_pattern:
                conditions.append("primary_name LIKE ?")
                params.append(f"%{name_pattern}%")

            where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
            query = f"SELECT * FROM consolidated_entities{where_clause} ORDER BY total_mentions DESC LIMIT ?"
            params.append(limit)

            results = self.db.fetch(query, tuple(params))
            return {"success": True, "data": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def store_entity_relationship(
        self,
        source_entity_id,
        target_entity_id,
        relationship_type,
        confidence=0.5,
        source_message_id=None,
        context_snippet=None,
    ):
        """
        Store an entity relationship.
        """
        try:
            self.db.execute(
                """
                INSERT OR REPLACE INTO entity_relationships
                (source_entity_id, target_entity_id, relationship_type, confidence,
                 source_message_id, context_snippet)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    source_entity_id,
                    target_entity_id,
                    relationship_type,
                    confidence,
                    source_message_id,
                    context_snippet,
                ),
            )

            return {"success": True}

        except Exception as e:
            return {"success": False, "error": f"Failed to store relationship: {str(e)}"}

    def get_entity_relationships(self, entity_id, relationship_type=None):
        """
        Get relationships for an entity.
        """
        try:
            conditions = ["(source_entity_id = ? OR target_entity_id = ?)"]
            params = [entity_id, entity_id]

            if relationship_type:
                conditions.append("relationship_type = ?")
                params.append(relationship_type)

            where_clause = " WHERE " + " AND ".join(conditions)
            query = f"SELECT * FROM entity_relationships{where_clause} ORDER BY confidence DESC"

            results = self.db.fetch(query, tuple(params))
            return {"success": True, "data": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_knowledge_graph(self, entity_ids=None, max_depth=2):
        """
        Get knowledge graph data for visualization.
        """
        try:
            if entity_ids:
                # Get relationships for specific entities
                placeholders = ",".join(["?"] * len(entity_ids))
                query = f"""
                    SELECT DISTINCT r.*,
                           s.primary_name as source_name, s.entity_type as source_type,
                           t.primary_name as target_name, t.entity_type as target_type
                    FROM entity_relationships r
                    JOIN consolidated_entities s ON r.source_entity_id = s.entity_id
                    JOIN consolidated_entities t ON r.target_entity_id = t.entity_id
                    WHERE r.source_entity_id IN ({placeholders})
                       OR r.target_entity_id IN ({placeholders})
                    ORDER BY r.confidence DESC
                """
                params = tuple(entity_ids + entity_ids)
            else:
                # Get all relationships (limited for performance)
                query = """
                    SELECT DISTINCT r.*,
                           s.primary_name as source_name, s.entity_type as source_type,
                           t.primary_name as target_name, t.entity_type as target_type
                    FROM entity_relationships r
                    JOIN consolidated_entities s ON r.source_entity_id = s.entity_id
                    JOIN consolidated_entities t ON r.target_entity_id = t.entity_id
                    WHERE r.confidence > 0.3
                    ORDER BY r.confidence DESC
                    LIMIT 1000
                """
                params = ()

            results = self.db.fetch(query, params)
            return {"success": True, "data": results}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_entity_statistics(self):
        """
        Get comprehensive entity statistics.
        """
        try:
            # Basic counts
            total_raw = self.db.fetch_one("SELECT COUNT(*) as count FROM entity_content_mapping")["count"]
            total_consolidated = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM consolidated_entities"
            )["count"]
            total_relationships = self.db.fetch_one(
                "SELECT COUNT(*) as count FROM entity_relationships"
            )["count"]

            # Entity types breakdown
            types_breakdown = self.db.fetch(
                "SELECT entity_type, COUNT(*) as count FROM consolidated_entities GROUP BY entity_type"
            )
            types_breakdown = [
                {"type": row["entity_type"], "count": row["count"]} for row in types_breakdown
            ]

            # Relationship types breakdown
            relationships_breakdown = self.db.fetch(
                "SELECT relationship_type, COUNT(*) as count FROM entity_relationships GROUP BY relationship_type"
            )
            relationships_breakdown = [
                {"type": row["relationship_type"], "count": row["count"]}
                for row in relationships_breakdown
            ]

            return {
                "success": True,
                "raw_entities": total_raw,
                "consolidated_entities": total_consolidated,
                "relationships": total_relationships,
                "entity_types": types_breakdown,
                "relationship_types": relationships_breakdown,
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to get statistics: {str(e)}"}
