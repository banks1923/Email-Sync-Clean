#!/usr/bin/env python3
"""
CLI Main - Modular CLI entry point with argument parsing
Coordinates all handler modules following clean architecture
"""

import argparse
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import handler modules
from tools.scripts.cli.docs_handler import (
    list_services_with_docs,
    show_docs_content,
    show_docs_overview,
    show_docs_summary,
)
from tools.scripts.cli.info_handler import show_info, show_pdf_stats
from tools.scripts.cli.notes_handler import create_note, show_notes_for_content
from tools.scripts.cli.process_handler import embed_content, process_emails
from tools.scripts.cli.search_handler import search_emails, search_multi_content
from tools.scripts.cli.timeline_handler import show_timeline
from tools.scripts.cli.upload_handler import (
    process_pdf_uploads,
    process_uploads,
    upload_directory,
    upload_pdf,
)


def setup_search_commands(subparsers):
    """Setup search-related commands"""
    search_parser = subparsers.add_parser("search", help="Search emails by similarity")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "-n", "--limit", type=int, default=5, help="Number of results (default: 5)"
    )
    search_parser.add_argument(
        "--mode", 
        choices=["database", "analog", "hybrid"], 
        default="hybrid",
        help="Search mode: database (SQLite), analog (markdown), or hybrid (both)"
    )

    multi_parser = subparsers.add_parser(
        "multi-search", help="Search across PDFs and transcriptions only"
    )
    multi_parser.add_argument("query", help="Search query")
    multi_parser.add_argument(
        "-l", "--limit", type=int, default=5, help="Number of results (default: 5)"
    )


def setup_process_commands(subparsers):
    """Setup processing commands"""
    process_parser = subparsers.add_parser("process", help="Generate embeddings for emails")
    process_parser.add_argument(
        "-n", "--limit", type=int, help="Number of emails to process (default: all unprocessed)"
    )

    embed_parser = subparsers.add_parser(
        "embed", help="Generate embeddings for specific content types"
    )
    embed_parser.add_argument(
        "--content-type",
        choices=["transcript", "transcription", "pdf", "document"],
        default="transcript",
        help="Content type to process (default: transcript)",
    )
    embed_parser.add_argument(
        "-n", "--limit", type=int, help="Number of items to process (default: all unprocessed)"
    )


def setup_upload_commands(subparsers):
    """Setup upload and batch processing commands"""
    upload_parser = subparsers.add_parser("upload", help="Upload PDF file or directory")
    upload_parser.add_argument("path", help="PDF file path or directory path")
    upload_parser.add_argument(
        "-n", "--limit", type=int, help="Max files to process (directory only)"
    )
    upload_parser.add_argument("--source", default="upload", help="Source type (default: upload)")

    subparsers.add_parser("process-uploads", help="Process videos from uploads directory")
    subparsers.add_parser(
        "process-pdf-uploads", help="Process PDFs from uploads directory and move to processed"
    )


def setup_info_commands(subparsers):
    """Setup info and statistics commands"""
    subparsers.add_parser("info", help="Show collection information")
    subparsers.add_parser("pdf-stats", help="Show PDF collection statistics")


def setup_timeline_commands(subparsers):
    """Setup timeline commands"""
    timeline_parser = subparsers.add_parser(
        "timeline", help="View chronological timeline of content"
    )
    timeline_parser.add_argument("--start-date", help="Start date filter (YYYY-MM-DD format)")
    timeline_parser.add_argument("--end-date", help="End date filter (YYYY-MM-DD format)")
    timeline_parser.add_argument(
        "--types",
        nargs="+",
        choices=["email", "document"],
        default=["email", "document"],
        help="Event types to include",
    )
    timeline_parser.add_argument(
        "-n", "--limit", type=int, default=20, help="Number of events to show (default: 20)"
    )


def setup_notes_commands(subparsers):
    """Setup notes commands"""
    note_parser = subparsers.add_parser("note", help="Create a note")
    note_parser.add_argument("title", help="Note title")
    note_parser.add_argument("content", help="Note content")
    note_parser.add_argument("--type", default="general", help="Note type (default: general)")
    note_parser.add_argument("--tags", nargs="*", help="Note tags")
    note_parser.add_argument(
        "--importance",
        type=int,
        choices=[1, 2, 3, 4, 5],
        default=1,
        help="Importance level 1-5 (default: 1)",
    )

    show_notes_parser = subparsers.add_parser("notes", help="Show notes for content")
    show_notes_parser.add_argument("content_type", choices=["email", "document", "transcript"])
    show_notes_parser.add_argument("content_id", help="Content identifier")


def setup_docs_commands(subparsers):
    """Setup documentation commands"""
    docs_parser = subparsers.add_parser("docs", help="Show project documentation")
    docs_parser.add_argument(
        "--type",
        choices=["claude", "readme", "changelog"],
        help="Show specific type of documentation",
    )
    docs_parser.add_argument("--service", help="Show docs for specific service")
    docs_parser.add_argument("--summary", action="store_true", help="Show documentation summary")
    docs_parser.add_argument(
        "--services", action="store_true", help="List services with documentation"
    )


def _handle_docs(args):
    """Handle docs command with various options"""
    if args.services:
        return list_services_with_docs()
    elif args.summary:
        return show_docs_summary()
    elif args.type or args.service:
        return show_docs_content(args.type, args.service)
    else:
        return show_docs_overview()


def _handle_upload(args):
    """Handle upload command with path validation"""
    if os.path.isfile(args.path):
        return upload_pdf(args.path, args.source)
    elif os.path.isdir(args.path):
        return upload_directory(args.path, args.limit)
    else:
        print(f"❌ Path not found: {args.path}")
        return False


def route_command(args):
    """Route parsed arguments to appropriate handler"""
    # Command dispatch table
    command_handlers = {
        "search": lambda: search_emails(args.query, args.limit, mode=getattr(args, 'mode', 'database')),
        "process": lambda: process_emails(args.limit),
        "embed": lambda: embed_content(args.content_type, args.limit),
        "info": show_info,
        "pdf-stats": show_pdf_stats,
        "process-uploads": process_uploads,
        "process-pdf-uploads": process_pdf_uploads,
        "multi-search": lambda: search_multi_content(args.query, args.limit),
        "timeline": lambda: show_timeline(args.start_date, args.end_date, args.types, args.limit),
        "note": lambda: create_note(
            args.title, args.content, args.type, args.tags, args.importance
        ),
        "notes": lambda: show_notes_for_content(args.content_type, args.content_id),
        "upload": lambda: _handle_upload(args),
        "docs": lambda: _handle_docs(args),
    }

    # Dispatch to handler
    handler = command_handlers.get(args.command)
    return handler() if handler else False


def main():
    """Main CLI entry point with modular command routing"""
    parser = argparse.ArgumentParser(description="🤖 AI-Powered Hybrid Email Search CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup all command groups
    setup_search_commands(subparsers)
    setup_process_commands(subparsers)
    setup_upload_commands(subparsers)
    setup_info_commands(subparsers)
    setup_timeline_commands(subparsers)
    setup_notes_commands(subparsers)
    setup_docs_commands(subparsers)

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        # No command given - check if there's a search query as first argument
        if len(sys.argv) > 1:
            # Treat first argument as search query
            query = " ".join(sys.argv[1:])
            return search_emails(query)
        else:
            parser.print_help()
            return False

    # Execute command via appropriate handler
    result = route_command(args)
    if result is False:
        parser.print_help()
    return result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
