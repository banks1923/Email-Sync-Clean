#!/usr/bin/env python3
"""
Test configuration transformation on a single file.
"""

from pathlib import Path

import libcst as cst


def test_single_file(file_path: str):
    """
    Test transformation on a single file.
    """
    
    path = Path(file_path)
    print(f"🧪 Testing transformation on {path}")
    
    # Read original
    with open(path) as f:
        original_content = f.read()
    
    print("📄 Original content preview:")
    print("=" * 50)
    print(original_content[:300] + "..." if len(original_content) > 300 else original_content)
    print("=" * 50)
    
    try:
        # Parse
        cst.parse_module(original_content)
        print("✅ File parsed successfully")
        
        # Simple string replacement approach (safer than AST transformation)
        replacements = {
            '"emails.db"': 'settings.database.emails_db_path',
            "'emails.db'": 'settings.database.emails_db_path',
            '"shared/content.db"': 'settings.database.content_db_path',
            "'shared/content.db'": 'settings.database.content_db_path',
            '"credentials.json"': 'settings.gmail.credentials_path',
            "'credentials.json'": 'settings.gmail.credentials_path',
        }
        
        modified_content = original_content
        changes_made = []
        
        for old_str, new_str in replacements.items():
            if old_str in modified_content:
                modified_content = modified_content.replace(old_str, new_str)
                changes_made.append(f"Replaced {old_str} -> {new_str}")
        
        if changes_made:
            # Add import at top if needed
            if "from config.settings import settings" not in modified_content:
                lines = modified_content.split('\n')
                # Find where to insert import - after docstring and before other imports
                insert_pos = 0
                in_docstring = False
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith('"""'):
                        in_docstring = True
                    elif stripped.endswith('"""') and in_docstring:
                        insert_pos = i + 2  # After docstring + blank line
                        break
                    elif not in_docstring and (stripped.startswith('import ') or stripped.startswith('from ')):
                        insert_pos = i
                        break
                
                lines.insert(insert_pos, "from config.settings import settings")
                modified_content = '\n'.join(lines)
                changes_made.append("Added config.settings import")
            
            print("🔧 Changes made:")
            for change in changes_made:
                print(f"   - {change}")
            
            print("\n📝 Modified content preview:")
            print("=" * 50)
            print(modified_content[:500] + "..." if len(modified_content) > 500 else modified_content)
            print("=" * 50)
            
            # Write to test file
            test_file = path.with_suffix('.py.transformed')
            with open(test_file, 'w') as f:
                f.write(modified_content)
            
            print(f"✅ Test transformation saved to {test_file}")
            
            # Test if transformed file imports correctly
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("test_config", test_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                print("✅ Transformed file imports successfully")
            except Exception as e:
                print(f"❌ Import test failed: {e}")
                
        else:
            print("ℹ️ No changes needed for this file")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_single_file("gmail/config.py")