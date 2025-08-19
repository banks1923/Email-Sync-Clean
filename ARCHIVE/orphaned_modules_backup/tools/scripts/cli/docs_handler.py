#!/usr/bin/env python3
"""
Documentation handler for CLI - displays project documentation
Gathers CLAUDE.md, README.md, and CHANGELOG.md files across the project
"""

from pathlib import Path


def find_documentation_files() -> dict[str, list[tuple[str, str]]]:
    """Find all documentation files in the project"""
    project_root = Path(__file__).parent.parent.parent
    doc_files = {
        "CLAUDE.md": [],
        "README.md": [],
        "CHANGELOG.md": [],
        "changelog.md": [],
    }

    # Search for documentation files
    for doc_type in doc_files.keys():
        for file_path in project_root.rglob(doc_type):
            # Skip archived and hidden directories
            if any(part.startswith(".") or part == "archive" for part in file_path.parts):
                continue

            relative_path = file_path.relative_to(project_root)
            doc_files[doc_type].append((str(relative_path), str(file_path)))

    return doc_files


def show_docs_overview():
    """Display overview of all documentation files"""
    doc_files = find_documentation_files()

    print("📚 Email Sync Documentation Overview")
    print("=" * 50)

    # Main project docs first
    print("\n🏠 Project Documentation:")
    for doc_type, files in doc_files.items():
        if not files:
            continue

        main_files = [f for f in files if "/" not in f[0]]
        if main_files:
            for rel_path, _ in main_files:
                print(f"  • {rel_path}")

    # Service-specific docs
    print("\n🔧 Service Documentation:")
    service_docs = {}

    for doc_type, files in doc_files.items():
        for rel_path, full_path in files:
            if "/" in rel_path and not rel_path.startswith("tests/"):
                service = rel_path.split("/")[0]
                if service not in service_docs:
                    service_docs[service] = []
                service_docs[service].append(rel_path)

    for service, docs in sorted(service_docs.items()):
        print(f"  📁 {service}/")
        for doc in docs:
            doc_name = doc.split("/")[-1]
            print(f"    • {doc_name}")

    return True


def show_docs_content(doc_type: str = None, service: str = None):
    """Display content of specific documentation files"""
    doc_files = find_documentation_files()

    if doc_type and doc_type.upper() not in ["CLAUDE", "README", "CHANGELOG"]:
        print(f"❌ Invalid doc type: {doc_type}")
        print("Valid types: claude, readme, changelog")
        return False

    # Determine which files to show
    files_to_show = []

    if service:
        # Show docs for specific service
        for doc_name, file_list in doc_files.items():
            for rel_path, full_path in file_list:
                if rel_path.startswith(f"{service}/"):
                    if not doc_type or doc_name.lower().startswith(doc_type.lower()):
                        files_to_show.append((rel_path, full_path))
    elif doc_type:
        # Show all files of specific type
        doc_key = f"{doc_type.upper()}.md"
        if doc_key in doc_files:
            files_to_show.extend(doc_files[doc_key])

        # Also check lowercase changelog
        if doc_type.lower() == "changelog":
            files_to_show.extend(doc_files.get("changelog.md", []))
    else:
        # Show main project docs only
        for doc_name, file_list in doc_files.items():
            main_files = [f for f in file_list if "/" not in f[0]]
            files_to_show.extend(main_files)

    if not files_to_show:
        print("❌ No documentation found")
        if service:
            print(f"   Service: {service}")
        if doc_type:
            print(f"   Type: {doc_type}")
        return False

    # Display files
    for i, (rel_path, full_path) in enumerate(files_to_show):
        if i > 0:
            print("\n" + "=" * 60 + "\n")

        print(f"📄 {rel_path}")
        print("-" * len(rel_path))

        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    print(content)
                else:
                    print("(empty file)")
        except Exception as e:
            print(f"❌ Error reading file: {e}")

    return True


def show_docs_summary():
    """Show condensed summary of all documentation"""
    doc_files = find_documentation_files()

    print("📋 Documentation Summary")
    print("=" * 30)

    total_files = 0
    for doc_type, files in doc_files.items():
        count = len(files)
        total_files += count
        if count > 0:
            print(f"{doc_type:12} {count:2d} files")

    print(f"{'Total:':12} {total_files:2d} files")

    # Show key project info from main CLAUDE.md
    main_claude = next((f[1] for f in doc_files.get("CLAUDE.md", []) if "/" not in f[0]), None)
    if main_claude:
        try:
            with open(main_claude) as f:
                content = f.read()
                # Extract first few lines for quick overview
                lines = content.split("\n")[:10]
                print(f"\n🏠 Project Overview (from {Path(main_claude).name}):")
                for line in lines:
                    if line.strip() and not line.startswith("#"):
                        print(f"  {line}")
                        break
        except Exception:
            pass

    return True


def list_services_with_docs():
    """List all services that have documentation"""
    doc_files = find_documentation_files()
    services = set()

    for doc_type, files in doc_files.items():
        for rel_path, _ in files:
            if "/" in rel_path and not rel_path.startswith("tests/"):
                service = rel_path.split("/")[0]
                services.add(service)

    print("🔧 Services with Documentation:")
    for service in sorted(services):
        print(f"  • {service}")

    print("\nUse: /docs --service <service_name> to view specific service docs")
    return True
