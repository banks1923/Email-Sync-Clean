#!/usr/bin/env python3
"""
Rich Viewer - Pretty display of search results with optional interactivity.

Usage:
  python tools/scripts/vsearch view "query" [--limit 10] [--interactive]

If the 'rich' library is unavailable, falls back to plain text output.
"""

import argparse
from typing import Dict, List
from lib.exceptions import (
    ValidationError,
    VectorStoreError,
    EnrichmentError,
    SearchError,
)


def _plain_render(results: List[Dict], query: str) -> None:
    print(f"\nSearch Results for: '{query}'\n" + ("-" * 60))
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        source_type = r.get("source_type", "unknown")
        created = (r.get("created_at") or "")[:10]
        print(f"{i:>3}. [{source_type}] {title} {created}")


def _rich_render(results: List[Dict], query: str, interactive: bool) -> int:
    try:
        import re
        import textwrap

        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
    except ImportError:
        _plain_render(results, query)
        return 0

    console = Console()
    console.print(f"\n[bold cyan]Search Results for: '{query}'[/bold cyan]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", width=10)
    table.add_column("Title", width=60)
    table.add_column("Date", width=12)

    for i, r in enumerate(results, 1):
        source_type = r.get("source_type", "unknown")
        title = r.get("title", "Untitled")
        if len(title) > 60:
            title = title[:57] + "..."
        date = (r.get("created_at") or "")[:10]
        table.add_row(str(i), source_type, title, date)

    console.print(table)

    if not interactive:
        return 0

    console.print("\n[bold]Enter number to view full content (or 'q' to quit):[/bold] ", end="")
    while True:
        choice = input().strip()
        if choice.lower() == "q":
            return 0
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                r = results[idx]
                content = r.get("content") or r.get("body") or ""
                # Remove HTML tags if present
                content = re.sub("<[^<]+?>", "", content)
                wrapped = textwrap.fill(content[:4000], width=90)
                console.print("\n" + "=" * 80)
                console.print(Panel(r.get("title", "Untitled"), style="bold cyan"))
                console.print(wrapped)
                if len(content) > 4000:
                    console.print("\n[dim]... (truncated)[/dim]")
                console.print("\n[bold]Enter another number (or 'q' to quit):[/bold] ", end="")
            else:
                console.print("[red]Invalid number. Try again:[/red] ", end="")
        except ValueError:
            console.print("[red]Please enter a number or 'q':[/red] ", end="")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Pretty view of search results")
    parser.add_argument("query", help="Search query text")
    parser.add_argument("--limit", type=int, default=10, help="Max results to display")
    parser.add_argument("--interactive", action="store_true", help="Enable interactive detail view")
    args = parser.parse_args(argv)

    try:
        from lib.search import search as perform_search
    except ImportError as e:
        print(f"Search library unavailable: {e}")
        return 2

    try:
        results = perform_search(args.query, limit=args.limit) or []
        if not results:
            print("No results found")
            return 1
    except ValidationError as e:
        print(f"Invalid query: {e}")
        return 2
    except VectorStoreError as e:
        print(f"Vector store error: {e}")
        return 2
    except EnrichmentError as e:
        print(f"Enrichment error: {e}")
        return 2
    except SearchError as e:
        print(f"Search failed: {e}")
        return 2

    return _rich_render(results, args.query, args.interactive)


if __name__ == "__main__":
    raise SystemExit(main())
