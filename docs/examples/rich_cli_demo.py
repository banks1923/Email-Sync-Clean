#!/usr/bin/env python3
"""
Rich CLI Demo - Beautiful terminal output examples
Shows how to enhance the Email Sync CLI with rich formatting
"""

import time

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree

# Initialize console
console = Console()


def demo_search_results():
    """Enhanced search results display"""
    console.print("\n[bold cyan]🔍 Search Results[/bold cyan]")

    table = Table(title="Legal Documents Search", show_header=True, header_style="bold magenta")
    table.add_column("Score", style="cyan", justify="right")
    table.add_column("Type", style="green")
    table.add_column("Title", style="yellow")
    table.add_column("Date", style="blue")

    # Sample results
    results = [
        ("0.95", "📄 PDF", "Motion for Summary Judgment", "2024-03-15"),
        ("0.89", "📧 Email", "Re: Contract Terms Discussion", "2024-03-14"),
        ("0.87", "📄 PDF", "Complaint - Case 24NNCV00555", "2024-03-10"),
        ("0.82", "🎙️ Transcript", "Deposition of John Doe", "2024-03-08"),
        ("0.78", "📧 Email", "Settlement Proposal", "2024-03-05"),
    ]

    for score, doc_type, title, date in results:
        table.add_row(score, doc_type, title, date)

    console.print(table)


def demo_progress_bars():
    """Show progress bars for long operations"""
    console.print("\n[bold green]📥 Syncing Emails[/bold green]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        # Simulate email sync
        task1 = progress.add_task("[cyan]Fetching emails...", total=100)
        task2 = progress.add_task("[green]Processing attachments...", total=50)
        task3 = progress.add_task("[yellow]Generating embeddings...", total=100)

        for _ in range(100):
            time.sleep(0.01)
            progress.update(task1, advance=1)
            if _ < 50:
                progress.update(task2, advance=1)
            progress.update(task3, advance=0.5)

        progress.update(task3, advance=50)  # Complete remaining


def demo_status_panel():
    """Show system status in a beautiful panel"""
    status_text = """
[bold green]✅ System Status[/bold green]

[cyan]Database:[/cyan] Connected (6.88 MB)
[cyan]Vector Store:[/cyan] Qdrant running on port 6333
[cyan]Embeddings:[/cyan] Legal BERT (1024D) on CPU

[bold yellow]📊 Content Statistics[/bold yellow]
• Emails: 523
• PDFs: 45
• Transcripts: 12
• Total: 580 documents

[bold blue]🔍 Search Capabilities[/bold blue]
• Keyword Search: ✅ Available
• Semantic Search: ✅ Available
• Hybrid Search: ✅ Available
    """

    panel = Panel(status_text, title="Email Sync System", border_style="green")
    console.print(panel)


def demo_tree_structure():
    """Show document hierarchy as a tree"""
    console.print("\n[bold magenta]📁 Document Structure[/bold magenta]")

    tree = Tree("📂 Legal Case 24NNCV00555")

    emails = tree.add("📧 Emails (23)")
    emails.add("[dim]2024-03-15: Motion discussion[/dim]")
    emails.add("[dim]2024-03-14: Settlement proposal[/dim]")
    emails.add("[dim]2024-03-12: Discovery request[/dim]")

    pdfs = tree.add("📄 Court Documents (12)")
    pdfs.add("[bold]Complaint.pdf[/bold]")
    pdfs.add("[bold]Motion_Summary_Judgment.pdf[/bold]")
    pdfs.add("[bold]Response_Motion.pdf[/bold]")

    transcripts = tree.add("🎙️ Transcripts (3)")
    transcripts.add("[italic]Deposition_John_Doe.txt[/italic]")
    transcripts.add("[italic]Hearing_03_10_2024.txt[/italic]")

    console.print(tree)


def demo_code_syntax():
    """Show code with syntax highlighting"""
    console.print("\n[bold cyan]📝 Query Example[/bold cyan]")

    code = """
# Search for legal documents
from search import get_search_service

search = get_search_service()
results = search.search(
    query="motion for summary judgment",
    filters={
        "since": "last month",
        "content_types": ["pdf", "email"],
        "tags": ["legal", "urgent"]
    },
    limit=10
)

for result in results:
    print(f"Score: {result['score']:.2f}")
    print(f"Title: {result['title']}")
    """

    syntax = Syntax(code, "python", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Python Code", border_style="blue"))


def demo_error_handling():
    """Show beautiful error messages"""
    console.print("\n[bold red]❌ Error Handling Example[/bold red]")

    error_panel = Panel(
        "[red]Failed to connect to Qdrant[/red]\n\n"
        "[yellow]Suggestion:[/yellow] Start Qdrant with:\n"
        "[cyan]cd /path/to/Email\\ Sync[/cyan]\n"
        "[cyan]QDRANT__STORAGE__PATH=./qdrant_data ~/bin/qdrant &[/cyan]\n\n"
        "[dim]Falling back to keyword search only[/dim]",
        title="⚠️ Vector Store Warning",
        border_style="yellow",
    )
    console.print(error_panel)


def main():
    """Run all demos"""
    console.clear()

    # Header
    console.print(
        Panel.fit(
            "[bold cyan]Rich CLI Enhancement Demo[/bold cyan]\n"
            "[dim]Beautiful terminal output for Email Sync[/dim]",
            border_style="cyan",
        )
    )

    # Run demos
    demo_status_panel()
    demo_search_results()
    demo_tree_structure()
    demo_progress_bars()
    demo_code_syntax()
    demo_error_handling()

    # Footer
    console.print("\n[bold green]✨ Rich is now installed and ready to use![/bold green]")
    console.print("[dim]Add 'from rich import print as rprint' to any script[/dim]")
    console.print("[dim]Or use 'from rich.console import Console' for full features[/dim]")


if __name__ == "__main__":
    main()
