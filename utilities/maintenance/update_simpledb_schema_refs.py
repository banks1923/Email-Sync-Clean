#!/usr/bin/env python3
"""
Update SimpleDB to use 'id' instead of 'content_id' after schema migration.
This updates the actual Python code to match the new schema.
"""

import re
from pathlib import Path
from typing import List, Tuple
from loguru import logger


def update_simpledb_references(file_path: Path, dry_run: bool = True) -> List[Tuple[int, str, str]]:
    """Update content_id references to id in SimpleDB."""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    changes = []
    
    # Patterns to replace - carefully crafted to avoid breaking other code
    replacements = [
        # SQL column references (unaliased)
        (r"\bSELECT\s+content_id\b", "SELECT id"),
        (r"\bWHERE\s+content_id\s*=\s*\?", "WHERE id = ?"),
        (r"\bDELETE\s+FROM\s+content\s+WHERE\s+content_id\s*=\s*\?", "DELETE FROM content WHERE id = ?"),
        # Aliased column references: content.content_id or c.content_id
        (r"\bcontent\.content_id\b", "content.id"),
        (r"\b([A-Za-z_][A-Za-z0-9_]*)\.content_id\b", r"\1.id"),
        # INSERT column lists
        (r"INSERT\s+OR\s+IGNORE\s+INTO\s+content\s*\(\s*content_id\s*,", "INSERT OR IGNORE INTO content (id,"),
        (r"INSERT\s+INTO\s+content\s*\(\s*content_id\s*,", "INSERT INTO content (id,"),
        # UPDATE with explicit predicate
        (r"UPDATE\s+content\s+SET\s+(.*?)\s+WHERE\s+content_id\s*=\s*\?", r"UPDATE content SET \1 WHERE id = ?"),
        # Foreign keys in DDL
        (r"REFERENCES\s+content\s*\(\s*content_id\s*\)", "REFERENCES content(id)"),
        # Column name arrays in Python (double-quoted)
        (r'"content_id"\s*,\s*"content_type"', '"id", "content_type"'),
        # Dict key access for results
        (r"existing\['content_id'\]", "existing['id']"),
        (r'existing\["content_id"\]', 'existing["id"]'),
        # Comments / docstrings wording
        (r"Returns content_id\.", "Returns content ID."),
        (r"returning existing content_id:", "returning existing ID:"),
    ]
    multiline_patterns = {
        r"UPDATE\s+content\s+SET\s+(.*?)\s+WHERE\s+id\s*=\s*\?": re.DOTALL
    }
    
    new_content = content
    
    for pattern, replacement in replacements:
        flags = multiline_patterns.get(pattern, 0)
        matches = list(re.finditer(pattern, new_content, flags))
        for match in matches:
            # Calculate line number
            line_num = new_content[:match.start()].count('\n') + 1
            old_text = match.group(0)
            new_text = re.sub(pattern, replacement, old_text)
            
            if old_text != new_text:
                changes.append((line_num, old_text, new_text))
                new_content = new_content[:match.start()] + new_text + new_content[match.end():]
    
    if not dry_run and changes:
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")
        with open(backup_path, 'w') as bf:
            bf.write(content)
        with open(file_path, 'w') as f:
            f.write(new_content)
    
    return changes


def update_table_creation(file_path: Path, dry_run: bool = True) -> bool:
    """Update the CREATE TABLE statement for content table, switching to id PK and adding new columns if missing."""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    in_content_table = False
    table_start = -1
    table_end = -1

    for i, line in enumerate(lines):
        if not in_content_table and 'CREATE TABLE' in line and 'content' in line:
            in_content_table = True
            table_start = i
            continue
        if in_content_table and ');' in line:
            table_end = i
            break

    if table_start >= 0 and table_end >= 0:
        # Normalize PK name
        for i in range(table_start, table_end + 1):
            if 'id TEXT PRIMARY KEY' in lines[i]:
                lines[i] = lines[i].replace('id TEXT PRIMARY KEY', 'id TEXT PRIMARY KEY')
            if 'content_id TEXT NOT NULL' in lines[i]:
                lines[i] = lines[i].replace('content_id TEXT NOT NULL', 'id TEXT NOT NULL')

        block = ''.join(lines[table_start:table_end])
        # Columns we want to ensure exist
        new_columns = [
            "                source_type TEXT,\n",
            "                external_id TEXT,\n",
            "                parent_content_id TEXT,\n",
            "                updated_at TIMESTAMP,\n",
        ]
        for col in new_columns:
            col_name = col.strip().rstrip(',')  # e.g., "source_type TEXT"
            if col_name not in block:
                lines.insert(table_end, col)
                table_end += 1  # maintain correct end index after insertion

        if not dry_run:
            with open(file_path, 'w') as f:
                f.writelines(lines)
        return True

    return False


def add_upsert_method(file_path: Path, dry_run: bool = True) -> bool:
    """Add an upsert_content method to SimpleDB."""
    
    upsert_method = '''
    def upsert_content(
        self,
        source_type: str,
        external_id: str,
        content_type: str,
        title: str,
        content: str,
        metadata: dict = None,
        parent_content_id: str = None
    ) -> str:
        """
        Upsert content using business key (source_type, external_id).

        Args:
            source_type: Type of source (email, pdf, transcript, etc.)
            external_id: External identifier (message_id, file_hash, etc.)
            content_type: Type of content
            title: Content title
            content: Actual content text
            metadata: Optional metadata dict
            parent_content_id: Optional parent content ID for attachments

        Returns:
            Content ID (UUID)
        """
        import uuid
        from uuid import UUID, uuid5
        import json
        import hashlib

        # Deterministic UUID from business key (namespace DNS as stable base)
        UUID_NAMESPACE = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
        content_id = str(uuid5(UUID_NAMESPACE, f"{source_type}:{external_id}"))

        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # Prepare metadata
        if metadata is None:
            metadata = {}
        metadata_json = json.dumps(metadata, ensure_ascii=False)

        # UPSERT operation
        cursor = self.execute("""
            INSERT INTO content (
                id, source_type, external_id, content_type, title, 
                content, metadata, content_hash, char_count, parent_content_id,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(source_type, external_id) DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                metadata = excluded.metadata,
                content_hash = excluded.content_hash,
                char_count = excluded.char_count,
                updated_at = CURRENT_TIMESTAMP
        """, (id, source_type, external_id, content_type, title,
            content, metadata_json, content_hash, len(content), parent_content_id
        ))

        if cursor.rowcount > 0:
            logger.info(f"Content upserted: {source_type}:{external_id} -> {content_id}")

        return content_id
''' 
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if method already exists
    if 'def upsert_content' in content:
        logger.info("upsert_content method already exists")
        return False
    
    # Find a good place to insert (after add_content method)
    insert_pos = content.find('def update_content(')
    if insert_pos == -1:
        insert_pos = content.find('def delete_content(')
    
    if insert_pos > 0:
        # Insert the new method
        new_content = content[:insert_pos] + upsert_method + '\n' + content[insert_pos:]
        
        if not dry_run:
            with open(file_path, 'w') as f:
                f.write(new_content)
        
        return True
    
    return False


def main():
    """Run the code updates."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Update SimpleDB code for new schema")
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be changed without modifying files')
    parser.add_argument('--file', default='shared/simple_db.py',
                       help='Path to simple_db.py file')
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return 1
    
    logger.info(f"Updating SimpleDB references (dry_run={args.dry_run})")
    
    # Update content_id references
    changes = update_simpledb_references(file_path, dry_run=args.dry_run)
    
    if changes:
        logger.info(f"Found {len(changes)} changes to make:")
        for line_num, old, new in changes[:10]:  # Show first 10
            logger.info(f"  Line {line_num}: '{old}' -> '{new}'")
        if len(changes) > 10:
            logger.info(f"  ... and {len(changes) - 10} more changes")
    else:
        
        logger.info("No changes needed for content_id references (file may already use 'id').")
    
    # Update CREATE TABLE statement
    if update_table_creation(file_path, dry_run=args.dry_run):
        logger.info("Updated CREATE TABLE content statement")
    
    # Add upsert method
    if add_upsert_method(file_path, dry_run=args.dry_run):
        logger.info("Added upsert_content method")
    
    if args.dry_run:
        logger.info("DRY RUN complete - no files were modified")
        logger.info("Run without --dry-run to apply changes")
    else:
        logger.info("SimpleDB code updated successfully")
    
    return 0


if __name__ == "__main__":
    exit(main())