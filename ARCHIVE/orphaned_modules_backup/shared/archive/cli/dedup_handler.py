"""
CLI handlers for deduplication commands
"""

import json

from loguru import logger
from rich.console import Console
from rich.progress import track
from rich.table import Table

from shared.simple_db import SimpleDB
from utilities.deduplication import get_duplicate_detector

console = Console()


def find_duplicates_command(
    content_type: str | None = None,
    threshold: float = 0.8,
    show_groups: bool = False,
    output_json: bool = False
):
    """
    Find duplicate and near-duplicate content in the database
    
    Args:
        content_type: Filter by content type (email, pdf, etc.)
        threshold: Similarity threshold (0.0-1.0)
        show_groups: Show detailed duplicate groups
        output_json: Output as JSON
    """
    console.print(f"[bold cyan]🔍 Scanning for duplicates (threshold: {threshold:.0%})[/bold cyan]")
    
    try:
        # Get content from database
        db = SimpleDB()
        
        # Build query
        if content_type:
            console.print(f"Filtering by type: {content_type}")
            results = db.search_content("", content_type=content_type, limit=1000)
        else:
            results = db.search_content("", limit=1000)
            
        if not results:
            console.print("[yellow]No content found to analyze[/yellow]")
            return
            
        console.print(f"Found {len(results)} documents to analyze")
        
        # Initialize detector
        detector = get_duplicate_detector(threshold=threshold)
        
        # Process documents
        documents = []
        for result in track(results, description="Processing documents..."):
            documents.append({
                'id': result.get('content_id', result.get('id')),
                'content': result.get('content', ''),
                'metadata': {
                    'title': result.get('title', ''),
                    'type': result.get('content_type', ''),
                    'date': result.get('created_time', result.get('created_at', ''))
                }
            })
            
        # Find duplicates
        stats = detector.batch_deduplicate(documents)
        
        if output_json:
            # JSON output
            print(json.dumps(stats, indent=2, default=str))
        else:
            # Rich output
            console.print("\n[bold]📊 Duplicate Detection Results[/bold]")
            console.print(f"Total documents: {stats['total']}")
            console.print(f"Unique documents: [green]{stats['unique']}[/green]")
            console.print(f"Exact duplicates: [yellow]{sum(1 for g in stats['groups'] if g['is_exact'])}[/yellow]")
            console.print(f"Near-duplicates: [orange1]{stats['near_duplicates']}[/orange1]")
            
            if stats['groups'] and show_groups:
                console.print("\n[bold]Duplicate Groups:[/bold]")
                
                for i, group in enumerate(stats['groups'], 1):
                    # Get document details
                    leader_doc = next((d for d in documents if d['id'] == group['leader']), {})
                    
                    console.print(f"\n[cyan]Group {i}[/cyan] (Similarity: {group['avg_similarity']:.1%})")
                    console.print(f"  Leader: {leader_doc.get('metadata', {}).get('title', 'Unknown')[:50]}")
                    console.print(f"  Type: {leader_doc.get('metadata', {}).get('type', 'Unknown')}")
                    console.print(f"  Members: {len(group['members'])} documents")
                    
                    if len(group['members']) > 1:
                        console.print("  Duplicates:")
                        for member_id in group['members'][1:4]:  # Show first 3 duplicates
                            member_doc = next((d for d in documents if d['id'] == member_id), {})
                            title = member_doc.get('metadata', {}).get('title', 'Unknown')[:50]
                            console.print(f"    - {title}")
                        if len(group['members']) > 4:
                            console.print(f"    ... and {len(group['members']) - 4} more")
                            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        logger.error(f"Duplicate detection failed: {e}")


def compare_documents_command(
    doc_id1: str,
    doc_id2: str,
    show_diff: bool = False
):
    """
    Compare similarity between two specific documents
    
    Args:
        doc_id1: First document ID
        doc_id2: Second document ID  
        show_diff: Show detailed differences
    """
    console.print(f"[bold cyan]📊 Comparing documents {doc_id1} and {doc_id2}[/bold cyan]\n")
    
    try:
        db = SimpleDB()
        
        # Get documents
        doc1 = db.get_content(doc_id1)
        doc2 = db.get_content(doc_id2)
        
        if not doc1:
            console.print(f"[red]Document {doc_id1} not found[/red]")
            return
        if not doc2:
            console.print(f"[red]Document {doc_id2} not found[/red]")
            return
            
        # Calculate similarity
        detector = get_duplicate_detector()
        similarity = detector.get_similarity(
            doc1.get('content', ''),
            doc2.get('content', '')
        )
        
        # Display results
        table = Table(title="Document Comparison")
        table.add_column("Property", style="cyan")
        table.add_column("Document 1", style="green")
        table.add_column("Document 2", style="blue")
        
        table.add_row("ID", str(doc_id1), str(doc_id2))
        table.add_row("Title", doc1.get('title', 'N/A')[:50], doc2.get('title', 'N/A')[:50])
        table.add_row("Type", doc1.get('content_type', 'N/A'), doc2.get('content_type', 'N/A'))
        table.add_row("Size", f"{len(doc1.get('content', ''))} chars", f"{len(doc2.get('content', ''))} chars")
        
        console.print(table)
        
        # Similarity verdict
        console.print(f"\n[bold]Similarity Score: {similarity:.1%}[/bold]")
        
        if similarity > 0.99:
            console.print("[red]✅ These documents are EXACT duplicates[/red]")
        elif similarity > 0.8:
            console.print("[yellow]⚠️  These documents are NEAR duplicates[/yellow]")
        elif similarity > 0.5:
            console.print("[blue]📝 These documents are SOMEWHAT similar[/blue]")
        else:
            console.print("[green]❌ These documents are DIFFERENT[/green]")
            
        if show_diff and similarity > 0.3:
            console.print("\n[bold]Content Preview:[/bold]")
            console.print("\n[green]Document 1:[/green]")
            console.print(doc1.get('content', '')[:300] + "...")
            console.print("\n[blue]Document 2:[/blue]")
            console.print(doc2.get('content', '')[:300] + "...")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        logger.error(f"Document comparison failed: {e}")


def deduplicate_database_command(
    threshold: float = 0.95,
    dry_run: bool = True,
    content_type: str | None = None
):
    """
    Remove duplicate content from database
    
    Args:
        threshold: Similarity threshold for removal
        dry_run: Preview only, don't delete
        content_type: Filter by content type
    """
    mode = "DRY RUN" if dry_run else "LIVE"
    console.print(f"[bold red]🗑️  Database Deduplication ({mode})[/bold red]")
    console.print(f"Threshold: {threshold:.0%}")
    
    if not dry_run:
        confirm = console.input("[red]This will DELETE data. Continue? (yes/no): [/red]")
        if confirm.lower() != 'yes':
            console.print("[yellow]Cancelled[/yellow]")
            return
            
    try:
        db = SimpleDB()
        
        # Get content
        if content_type:
            results = db.search_content("", content_type=content_type, limit=5000)
        else:
            results = db.search_content("", limit=5000)
            
        console.print(f"Analyzing {len(results)} documents...")
        
        # Find duplicates
        detector = get_duplicate_detector(threshold=threshold)
        documents = [
            {
                'id': r.get('content_id', r.get('id')),
                'content': r.get('content', ''),
                'metadata': {
                    'title': r.get('title', ''),
                    'type': r.get('content_type', ''),
                    'created_at': r.get('created_time', r.get('created_at', ''))
                }
            }
            for r in results
        ]
        
        stats = detector.batch_deduplicate(documents)
        
        # Identify items to delete (keep oldest in each group)
        to_delete = []
        for group in stats['groups']:
            if group['avg_similarity'] >= threshold:
                # Sort by creation date, keep oldest
                members_with_dates = []
                for member_id in group['members']:
                    doc = next((d for d in documents if d['id'] == member_id), None)
                    if doc:
                        members_with_dates.append((
                            member_id,
                            doc['metadata'].get('created_at', '9999')
                        ))
                        
                members_with_dates.sort(key=lambda x: x[1])
                
                # Mark all but the first for deletion
                for member_id, _ in members_with_dates[1:]:
                    to_delete.append(member_id)
                    
        console.print(f"\n[bold]Found {len(to_delete)} duplicates to remove[/bold]")
        
        if to_delete:
            # Show what will be deleted
            table = Table(title="Documents to Delete")
            table.add_column("ID", style="red")
            table.add_column("Title", style="yellow")
            table.add_column("Type", style="cyan")
            
            for doc_id in to_delete[:10]:  # Show first 10
                doc = next((d for d in documents if d['id'] == doc_id), {})
                table.add_row(
                    str(doc_id),
                    doc.get('metadata', {}).get('title', 'Unknown')[:50],
                    doc.get('metadata', {}).get('type', 'Unknown')
                )
                
            console.print(table)
            
            if len(to_delete) > 10:
                console.print(f"... and {len(to_delete) - 10} more")
                
            if not dry_run:
                console.print("\n[yellow]Deleting duplicates...[/yellow]")
                
                deleted = 0
                for doc_id in track(to_delete, description="Deleting..."):
                    try:
                        # Delete from content table
                        db.db.execute_query(
                            "DELETE FROM content WHERE content_id = ?",
                            (doc_id,)
                        )
                        deleted += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {doc_id}: {e}")
                        
                console.print(f"[green]✅ Deleted {deleted} duplicates[/green]")
            else:
                console.print("\n[cyan]ℹ️  Run without --dry-run to actually delete[/cyan]")
        else:
            console.print("[green]✅ No duplicates found[/green]")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        logger.error(f"Deduplication failed: {e}")


def build_duplicate_index_command():
    """Build duplicate detection index for all content"""
    console.print("[bold cyan]🔨 Building duplicate detection index[/bold cyan]")
    
    try:
        db = SimpleDB()
        detector = get_duplicate_detector()
        
        # Get all content
        results = db.search_content("", limit=10000)
        console.print(f"Indexing {len(results)} documents...")
        
        # Add to index
        for result in track(results, description="Building index..."):
            detector.add_document(
                str(result.get('content_id', result.get('id'))),
                result.get('content', ''),
                {
                    'title': result.get('title', ''),
                    'type': result.get('content_type', ''),
                    'created_at': result.get('created_time', result.get('created_at', ''))
                }
            )
            
        console.print("[green]✅ Index built successfully[/green]")
        
        # Show statistics
        groups = detector.find_all_duplicates()
        console.print(f"\nFound {len(groups)} duplicate groups")
        
        if groups:
            total_duplicates = sum(len(g) - 1 for g in groups.values())
            console.print(f"Total duplicate documents: {total_duplicates}")
            
    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        logger.error(f"Index building failed: {e}")