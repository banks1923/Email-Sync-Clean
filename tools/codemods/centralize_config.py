#!/usr/bin/env python3
"""
Automated transformation to centralize configuration using LibCST.

Replaces hardcoded paths and config instantiation across the codebase.
"""
from pathlib import Path
from typing import List

import libcst as cst


class ConfigCentralizationTransformer(cst.CSTTransformer):
    """Transform hardcoded configs to use centralized settings."""

    def __init__(self):
        self.changes = []

    def leave_SimpleStatementLine(
        self, original_node: cst.SimpleStatementLine, updated_node: cst.SimpleStatementLine
    ) -> cst.SimpleStatementLine:
        """Replace hardcoded string literals with settings references."""

        # Track if we made any changes to this line
        made_changes = False
        new_body = []

        for stmt in updated_node.body:
            if isinstance(stmt, cst.Assign):
                new_stmt = self._transform_assignment(stmt)
                if new_stmt != stmt:
                    made_changes = True
                new_body.append(new_stmt)
            else:
                new_body.append(stmt)

        if made_changes:
            return updated_node.with_changes(body=new_body)

        return updated_node

    def _transform_assignment(self, node: cst.Assign) -> cst.Assign:
        """Transform assignment statements with hardcoded paths."""

        if not isinstance(node.value, cst.SimpleString):
            return node

        # Extract string value (remove quotes)
        string_value = node.value.value.strip("'\"")

        # Map common hardcoded values to settings
        replacements = {
            "emails.db": "settings.database.emails_db_path",
            "shared/content.db": "settings.database.content_db_path",
            "credentials.json": "settings.gmail.credentials_path",
            "token.json": "settings.gmail.token_path",
            "data/raw": "settings.paths.raw_documents",
            "data/processed": "settings.paths.processed_documents",
            "data/export": "settings.paths.export_path",
            "data/quarantine": "settings.paths.quarantine",
            "logs": "settings.paths.logs_path",
            "en_core_web_sm": "settings.entity.spacy_model",
            "nlpaueb/legal-bert-base-uncased": "settings.vector.embedding_model",
            "localhost": "settings.vector.qdrant_host",
            "6333": "settings.vector.qdrant_port",
        }

        for old_val, new_val in replacements.items():
            if old_val in string_value:
                self.changes.append(f"Replaced '{string_value}' with {new_val}")
                # Create new attribute access
                parts = new_val.split(".")
                attr_chain = cst.Name(parts[0])
                for part in parts[1:]:
                    attr_chain = cst.Attribute(value=attr_chain, attr=cst.Name(part))

                return node.with_changes(value=attr_chain)

        return node

    def leave_SimpleString(
        self, original_node: cst.SimpleString, updated_node: cst.SimpleString
    ) -> cst.SimpleString:
        """Replace standalone string literals in function calls."""

        string_value = updated_node.value.strip("'\"")

        # Common database paths in function calls
        if string_value == "emails.db":
            return cst.parse_expression("settings.database.emails_db_path")
        elif string_value == "shared/content.db":
            return cst.parse_expression("settings.database.content_db_path")

        return updated_node


def transform_file(file_path: Path) -> bool:
    """Transform a single Python file."""

    try:
        with open(file_path, encoding="utf-8") as f:
            source_code = f.read()

        # Parse the source code
        tree = cst.parse_module(source_code)

        # Apply transformations
        transformer = ConfigCentralizationTransformer()
        modified_tree = tree.visit(transformer)

        # Only write if changes were made
        if transformer.changes:
            # Add import for settings if not present
            modified_code = modified_tree.code
            if "from config.settings import settings" not in modified_code:
                lines = modified_code.split("\n")
                # Find the right place to insert import (after other imports)
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith("from ") or line.strip().startswith("import "):
                        insert_pos = i + 1

                lines.insert(insert_pos, "from config.settings import settings")
                modified_code = "\n".join(lines)

            # Write back the modified code
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_code)

            print(f"✅ Transformed {file_path}")
            for change in transformer.changes:
                print(f"   - {change}")
            return True

        return False

    except Exception as e:
        print(f"❌ Error transforming {file_path}: {e}")
        return False


def find_python_files(root_dir: Path) -> list[Path]:
    """Find all Python files that might need transformation."""

    exclude_patterns = [
        "__pycache__",
        ".git",
        "venv",
        ".venv",
        "node_modules",
        "zarchive",
        "tests",  # Transform tests separately
        "config/settings.py",  # Don't transform the config itself
    ]

    python_files = []

    for file_path in root_dir.rglob("*.py"):
        # Skip excluded directories
        if any(pattern in str(file_path) for pattern in exclude_patterns):
            continue

        python_files.append(file_path)

    return python_files


def move_files_to_config():
    """Move configuration files to .config directory."""

    moves = [
        ("credentials.json", ".config/credentials.json"),
        ("claude_desktop_config.json", ".config/claude_desktop_config.json"),
        ("opencode.json", ".config/opencode.json"),
        ("CHRO_TIMELINE_REPORT.jsonl", "data/reports/chro_timeline_report.jsonl"),
        ("sync_emails_to_qdrant.py", "utilities/maintenance/sync_emails_to_qdrant.py"),
    ]

    for src, dst in moves:
        src_path = Path(src)
        dst_path = Path(dst)

        if src_path.exists():
            # Create destination directory
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            src_path.rename(dst_path)
            print(f"✅ Moved {src} → {dst}")


def main():
    """Run the configuration centralization transformation."""

    root_dir = Path(".")

    print("🔧 Centralizing Email Sync System Configuration")
    print("=" * 60)

    # Step 1: Move files to better locations
    print("\n📁 Moving files to organized locations...")
    move_files_to_config()

    # Step 2: Find Python files to transform
    print("\n🔍 Finding Python files...")
    python_files = find_python_files(root_dir)
    print(f"Found {len(python_files)} Python files")

    # Step 3: Transform each file
    print("\n🔄 Transforming files...")
    transformed_count = 0

    for file_path in python_files:
        if transform_file(file_path):
            transformed_count += 1

    print("\n✨ Transformation complete!")
    print(f"   - Transformed {transformed_count} files")
    print("   - Centralized config in config/settings.py")

    # Step 4: Update requirements.txt
    print("\n📦 Updating requirements...")
    try:
        with open("requirements.txt") as f:
            reqs = f.read()

        if "pydantic[dotenv]" not in reqs:
            with open("requirements.txt", "a") as f:
                f.write("\npydantic[dotenv]>=1.10.0\n")
            print("✅ Added pydantic[dotenv] to requirements.txt")
    except FileNotFoundError:
        print("❌ requirements.txt not found")

    print("\n🎉 Configuration centralization complete!")
    print("\nNext steps:")
    print("1. Install pydantic: pip install 'pydantic[dotenv]'")
    print("2. Create .env file with your secrets")
    print(
        "3. Test services: python -c 'from config.settings import settings; print(settings.database.emails_db_path)'"
    )


if __name__ == "__main__":
    main()
