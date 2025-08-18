#!/usr/bin/env python3
"""
Rich Search Demo - Shows beautiful search results with rich formatting.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from shared.simple_db import SimpleDB

console = Console()


def demo_search():
    """Demo search with rich formatting."""
    # Show search panel
    console.print(
        Panel.fit(
            "[bold cyan]🤖 AI-Powered Search Demo[/bold cyan]\n[yellow]Query: 'rich formatting'[/yellow]",
            border_style="cyan",
        )
    )

    # Get data from database
    db = SimpleDB()
    results = db.search_content("rich formatting", limit=5)

    if results:
        console.print(f"[green]✅ Found {len(results)} matches[/green]\n")

        # Create a beautiful table for results
        table = Table(title="🔍 Search Results")
        table.add_column("Score", justify="right", style="cyan", width=8)
        table.add_column("Type", style="green", width=12)
        table.add_column("Title", style="yellow", width=40)
        table.add_column("Preview", style="white", width=60)

        for i, result in enumerate(results[:5], 1):
            content_type = result.get("content_type", "unknown")
            title = result.get("title", "No title")[:40]
            content = result.get("content", "")[:60] + "..."

            # Content type icons
            type_icons = {"email": "📧", "pdf": "📄", "transcript": "🎙️"}
            icon = type_icons.get(content_type, "📄")

            table.add_row(
                "1.000",  # Keyword search doesn't have scores
                f"{icon} {content_type}",
                title,
                content,
            )

        console.print(table)

        if len(results) > 5:
            console.print(f"\n[dim]... and {len(results) - 5} more results[/dim]")
    else:
        console.print("[red]❌ No results found[/red]")

    # Show a tip panel
    console.print("\n")
    console.print(
        Panel(
            "[yellow]💡 Tip:[/yellow] Use semantic search for better results!\n"
            "[cyan]Run:[/cyan] scripts/vsearch search 'your query'",
            title="Search Tips",
            border_style="yellow",
        )
    )


if __name__ == "__main__":
    demo_search()
