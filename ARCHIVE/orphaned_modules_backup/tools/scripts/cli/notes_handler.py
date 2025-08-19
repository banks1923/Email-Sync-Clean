#!/usr/bin/env python3
"""
Notes Handler - Modular CLI component for notes operations
Handles: note, notes commands
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def create_note(title, content, note_type="general", tags=None, importance=1):
    """Create a new note"""
    print(f"📝 Creating note: {title}")

    try:
        from utilities.notes import NotesService

        notes_service = NotesService()

        result = notes_service.create_note(
            title=title,
            content=content,
            note_type=note_type,
            tags=tags or [],
            importance_level=importance,
        )

        if result["success"]:
            note_id = result["note_id"]
            print("✅ Note created successfully!")
            print(f"   🆔 Note ID: {note_id}")
            print(f"   📝 Type: {note_type}")
            print(f"   🏷️  Tags: {', '.join(tags) if tags else 'None'}")
            print(f"   ⭐ Importance: {importance}/5")
            return True
        else:
            print(f"❌ Note creation failed: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Note creation error: {e}")
        return False


def show_notes_for_content(content_type, content_id):
    """Show notes linked to specific content"""
    print(f"📝 Notes for {content_type}: {content_id}")
    print("=" * 50)

    try:
        from utilities.notes import NotesService

        notes_service = NotesService()

        result = notes_service.get_notes_for_content(content_type, content_id)

        if result["success"]:
            notes = result.get("notes", [])
            if notes:
                print(f"📋 Found {len(notes)} notes:\n")

                for i, note in enumerate(notes, 1):
                    title = note.get("title", "No title")
                    content = note.get("content", "")
                    note_type = note.get("note_type", "general")
                    importance = note.get("importance_level", 1)
                    tags = note.get("tags", [])
                    created = note.get("created_date", "Unknown")

                    print(f"📝 {i}. {title}")
                    print(f"   📅 Created: {created}")
                    print(f"   📂 Type: {note_type}")
                    print(f"   ⭐ Importance: {importance}/5")
                    if tags:
                        print(f"   🏷️  Tags: {', '.join(tags)}")
                    print(f"   📄 Content: {content[:100]}{'...' if len(content) > 100 else ''}")
                    print()
            else:
                print("📋 No notes found for this content")

            return True
        else:
            print(f"❌ Error retrieving notes: {result['error']}")
            return False

    except Exception as e:
        print(f"❌ Notes error: {e}")
        return False
