#!/usr/bin/env python3
"""
Simple Docs MCP Server - DEPRECATED

This server is deprecated and will be removed in a future version.
Documentation features are now integrated into the main email-sync server.
- Migration: Run scripts/migrate_mcp_servers.py

Following Email Sync philosophy: Simple > Complex, Working > Perfect
"""

import asyncio
from pathlib import Path

# MCP imports
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool


def find_docs() -> dict[str, list[str]]:
    """Find all documentation files - simple and direct"""
    project_root = Path(__file__).parent.parent
    docs = {
        "CLAUDE.md": [],
        "README.md": [],
        "CHANGELOG.md": [],
        "changelog.md": [],
    }

    for doc_type in docs.keys():
        for file_path in project_root.rglob(doc_type):
            # Skip hidden and archive dirs
            if any(part.startswith(".") or part == "archive" for part in file_path.parts):
                continue
            docs[doc_type].append(str(file_path.relative_to(project_root)))

    return docs


def show_docs(doc_type: str = None, service: str = None, summary: bool = False) -> str:
    """Show documentation - simple function, no classes"""
    docs = find_docs()

    if summary:
        result = "📋 Documentation Summary\n" + "=" * 30 + "\n"
        total = 0
        for dtype, files in docs.items():
            count = len(files)
            total += count
            if count > 0:
                result += f"{dtype:12} {count:2d} files\n"
        result += f"{'Total:':12} {total:2d} files\n"
        return result

    if service:
        # Show docs for specific service
        result = f"📁 {service}/ Documentation:\n"
        found = False
        for dtype, files in docs.items():
            service_files = [f for f in files if f.startswith(f"{service}/")]
            for file_path in service_files:
                found = True
                result += f"\n📄 {file_path}\n" + "-" * len(file_path) + "\n"
                try:
                    full_path = Path(__file__).parent.parent / file_path
                    content = full_path.read_text()[:5000]  # Limit content
                    result += content + ("\n...(truncated)" if len(content) == 5000 else "") + "\n"
                except Exception as e:
                    result += f"Error reading: {e}\n"

        if not found:
            result += f"No documentation found for service: {service}"
        return result

    if doc_type and doc_type != "all":
        # Show specific type
        doc_key = f"{doc_type.upper()}.md"
        files = docs.get(doc_key, [])
        if doc_type.lower() == "changelog":
            files.extend(docs.get("changelog.md", []))

        if not files:
            return f"No {doc_type} files found"

        result = f"📋 All {doc_type.upper()} Files:\n\n"
        for i, file_path in enumerate(files):
            if i > 0:
                result += "\n" + "=" * 50 + "\n\n"
            result += f"📄 {file_path}\n" + "-" * len(file_path) + "\n"
            try:
                full_path = Path(__file__).parent.parent / file_path
                content = full_path.read_text()[:3000]
                result += content + ("\n...(truncated)" if len(content) == 3000 else "") + "\n"
            except Exception as e:
                result += f"Error reading: {e}\n"
        return result

    # Default: show overview
    result = "📚 Email Sync Documentation\n" + "=" * 40 + "\n\n"

    # Main docs
    result += "🏠 Project Documentation:\n"
    for dtype, files in docs.items():
        main_files = [f for f in files if "/" not in f]
        for f in main_files:
            result += f"  • {f}\n"

    # Service docs
    result += "\n🔧 Service Documentation:\n"
    services = set()
    for dtype, files in docs.items():
        for f in files:
            if "/" in f and not f.startswith("tests/"):
                services.add(f.split("/")[0])

    for service in sorted(services):
        result += f"  📁 {service}/\n"
        service_docs = []
        for dtype, files in docs.items():
            service_files = [f.split("/")[-1] for f in files if f.startswith(f"{service}/")]
            service_docs.extend(service_files)
        for doc in sorted(set(service_docs)):
            result += f"    • {doc}\n"

    return result


class DocsServer:
    """Simple docs MCP server - no fancy patterns"""

    def __init__(self):
        self.server = Server("docs-server")
        self.setup_tools()

    def setup_tools(self):
        """Register the docs tool"""

        @self.server.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="docs",
                    description="Show project documentation (CLAUDE.md, README.md, etc.)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["claude", "readme", "changelog", "all"],
                                "description": "Type of docs to show",
                            },
                            "service": {
                                "type": "string",
                                "description": "Show docs for specific service (entity, pdf, gmail, etc.)",
                            },
                            "summary": {
                                "type": "boolean",
                                "description": "Show summary with file counts",
                            },
                        },
                    },
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            if name == "docs":
                try:
                    result = show_docs(
                        doc_type=arguments.get("type"),
                        service=arguments.get("service"),
                        summary=arguments.get("summary", False),
                    )
                    return [TextContent(type="text", text=result)]
                except Exception as e:
                    return [TextContent(type="text", text=f"Error: {str(e)}")]
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the simple docs server"""
    server = DocsServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="docs",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(NotificationOptions(), {}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
