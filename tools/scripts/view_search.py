#!/usr/bin/env python3
"""
Simple search result viewer with better formatting
Usage: python view_search.py "search term"
"""

import sys
from search_intelligence.basic_search import search as perform_search
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import textwrap

def view_search(query, limit=10):
    console = Console()
    
    # Perform search
    results = perform_search(query, limit=limit)
    
    if not results:
        console.print("[yellow]No results found[/yellow]")
        return
    
    console.print(f"\n[bold cyan]Search Results for: '{query}'[/bold cyan]\n")
    
    # Create a table for results
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Type", width=10)
    table.add_column("Title", width=50)
    table.add_column("Date", width=20)
    
    for i, result in enumerate(results, 1):
        source_type = result.get('source_type', 'unknown')
        title = textwrap.shorten(result.get('title', 'Untitled'), width=50)
        date = result.get('created_at', '')[:10] if result.get('created_at') else ''
        
        table.add_row(
            str(i),
            source_type,
            title,
            date
        )
    
    console.print(table)
    
    # Ask user which result to view in detail
    console.print("\n[bold]Enter number to view full content (or 'q' to quit):[/bold] ", end="")
    
    while True:
        choice = input().strip()
        if choice.lower() == 'q':
            break
            
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                result = results[idx]
                
                # Display full content
                console.print("\n" + "="*80)
                console.print(Panel(result.get('title', 'Untitled'), style="bold cyan"))
                
                # Clean up the content for display
                content = result.get('body', '')
                # Remove HTML tags if present
                import re
                content = re.sub('<[^<]+?>', '', content)
                # Wrap text for readability
                wrapped = textwrap.fill(content[:2000], width=80)
                
                console.print(wrapped)
                
                if len(content) > 2000:
                    console.print(f"\n[dim]... (showing first 2000 characters of {len(content)} total)[/dim]")
                
                console.print("\n[bold]Enter number for another result (or 'q' to quit):[/bold] ", end="")
            else:
                console.print("[red]Invalid number. Try again:[/red] ", end="")
        except ValueError:
            console.print("[red]Please enter a number or 'q':[/red] ", end="")

if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else input("Search query: ")
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    view_search(query, limit)