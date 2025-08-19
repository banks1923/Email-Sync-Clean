#!/usr/bin/env python3
"""
Simple Timeline MCP Server - DEPRECATED

⚠️ DEPRECATION NOTICE ⚠️
This server is deprecated and will be removed in a future version.
Please use the unified Legal Intelligence MCP Server instead:
- File: legal_intelligence_mcp.py
- Tool: legal_timeline_events (provides enhanced timeline generation)

Provides timeline tools for chronological event tracking
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# MCP imports
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Import services
try:
    from shared.simple_db import SimpleDB
    from utilities.timeline.main import TimelineService

    SERVICES_AVAILABLE = True
except ImportError as e:
    print(f"Services not available: {e}")
    SERVICES_AVAILABLE = False


def build_timeline(start_date: str = None, end_date: str = None, case_filter: str = None) -> str:
    """Create chronological event timeline"""
    deprecation_warning = """
⚠️ DEPRECATION WARNING ⚠️
This tool is deprecated. Please use the unified Legal Intelligence MCP Server:
- Tool: legal_timeline_events (provides enhanced timeline generation with Legal BERT analysis)

"""

    if not SERVICES_AVAILABLE:
        return deprecation_warning + "Timeline services not available"

    try:
        TimelineService()
        db = SimpleDB()

        # Build query for timeline events
        query = """
            SELECT * FROM timeline_events
            WHERE 1=1
        """
        params = []

        if start_date:
            query += " AND event_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND event_date <= ?"
            params.append(end_date)

        if case_filter:
            query += " AND (title LIKE ? OR description LIKE ?)"
            params.append(f"%{case_filter}%")
            params.append(f"%{case_filter}%")

        query += " ORDER BY event_date DESC LIMIT 50"

        events = db.fetch(query, tuple(params))

        if not events:
            # Try to sync from emails/content
            # NOTE: Deprecated functionality - utilities.timeline no longer available
            # Use legal_intelligence_mcp.py instead
            print("Timeline sync unavailable in deprecated server")
            events = db.fetch(query, tuple(params))

        if not events:
            return "No timeline events found. Try syncing emails first."

        # Format timeline
        output = deprecation_warning + "📅 Timeline View:\n"
        if case_filter:
            output += f"Case: {case_filter}\n"
        if start_date or end_date:
            output += f"Period: {start_date or 'beginning'} to {end_date or 'now'}\n"
        output += "\n"

        # Group events by date
        events_by_date = {}
        for event in events:
            event_date = event.get("event_date", "")[:10]  # Just date part
            if event_date not in events_by_date:
                events_by_date[event_date] = []
            events_by_date[event_date].append(event)

        for date in sorted(events_by_date.keys(), reverse=True):
            output += f"\n📌 {date}\n"
            for event in events_by_date[date]:
                event_type = event.get("event_type", "unknown")
                title = event.get("title", "Untitled")
                importance = event.get("importance_score", 0)

                # Icon based on type
                icon = "📧" if event_type == "email" else "📄" if event_type == "document" else "📝"

                output += f"  {icon} {title}"
                if importance > 5:
                    output += " ⭐"
                output += "\n"

                if event.get("description"):
                    output += f"     {event['description'][:100]}\n"

        return output

    except Exception as e:
        return f"Error building timeline: {str(e)}"


def get_timeline_gaps(case_number: str = None, days_threshold: int = 30) -> str:
    """Identify missing time periods in timeline"""
    if not SERVICES_AVAILABLE:
        return "Timeline services not available"

    try:
        db = SimpleDB()

        # Get timeline events
        query = "SELECT * FROM timeline_events"
        params = []

        if case_number:
            query += " WHERE title LIKE ? OR description LIKE ?"
            params.append(f"%{case_number}%")
            params.append(f"%{case_number}%")

        query += " ORDER BY event_date ASC"
        events = db.fetch(query, tuple(params))

        if len(events) < 2:
            return "Not enough events to analyze gaps"

        # Find gaps
        gaps = []
        for i in range(len(events) - 1):
            current_date = datetime.fromisoformat(events[i]["event_date"][:10])
            next_date = datetime.fromisoformat(events[i + 1]["event_date"][:10])

            gap_days = (next_date - current_date).days

            if gap_days > days_threshold:
                gaps.append(
                    {
                        "start": events[i]["event_date"][:10],
                        "end": events[i + 1]["event_date"][:10],
                        "days": gap_days,
                        "before_event": events[i]["title"],
                        "after_event": events[i + 1]["title"],
                    }
                )

        # Format output
        output = "🔍 Timeline Gap Analysis:\n"
        if case_number:
            output += f"Case: {case_number}\n"
        output += f"Gap threshold: {days_threshold} days\n\n"

        if gaps:
            output += f"⚠️ Found {len(gaps)} significant gaps:\n\n"
            for gap in gaps:
                output += f"📅 Gap of {gap['days']} days\n"
                output += f"   From: {gap['start']} ({gap['before_event'][:50]})\n"
                output += f"   To:   {gap['end']} ({gap['after_event'][:50]})\n\n"

            # Suggest searches for gap periods
            output += "💡 Suggested searches for gap periods:\n"
            for gap in gaps[:3]:  # Top 3 gaps
                mid_date = datetime.fromisoformat(gap["start"]) + timedelta(days=gap["days"] // 2)
                output += f"  • Search around {mid_date.date()}\n"
        else:
            output += f"✅ No gaps longer than {days_threshold} days found\n"

        # Summary stats
        if events:
            first_date = events[0]["event_date"][:10]
            last_date = events[-1]["event_date"][:10]
            total_days = (
                datetime.fromisoformat(last_date) - datetime.fromisoformat(first_date)
            ).days

            output += "\n📊 Timeline Statistics:\n"
            output += f"  • Total events: {len(events)}\n"
            output += f"  • Date range: {first_date} to {last_date}\n"
            output += f"  • Total days: {total_days}\n"
            output += f"  • Avg events/day: {len(events)/max(total_days, 1):.2f}\n"

        return output

    except Exception as e:
        return f"Error analyzing timeline gaps: {str(e)}"


def add_timeline_event(
    title: str,
    description: str,
    event_date: str = None,
    event_type: str = "note",
    importance: int = 3,
) -> str:
    """Add manual event to timeline"""
    if not SERVICES_AVAILABLE:
        return "Timeline services not available"

    try:
        db = SimpleDB()

        # Generate event ID and set date
        event_id = str(uuid.uuid4())
        if not event_date:
            event_date = datetime.now().isoformat()

        # Validate date format
        try:
            datetime.fromisoformat(event_date.replace("Z", "+00:00"))
        except Exception:
            return "Invalid date format. Use ISO format (YYYY-MM-DD or full datetime)"

        # Insert event
        db.execute(
            """
            INSERT INTO timeline_events
            (event_id, event_type, title, description, event_date, importance_score, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, event_type, title, description, event_date, importance, "manual"),
        )

        # Format output
        output = "✅ Timeline Event Added:\n\n"
        output += f"📌 Title: {title}\n"
        output += f"📝 Description: {description}\n"
        output += f"📅 Date: {event_date[:10]}\n"
        output += f"🏷️ Type: {event_type}\n"
        output += f"⭐ Importance: {importance}/10\n"
        output += f"🔑 Event ID: {event_id[:8]}...\n"

        return output

    except Exception as e:
        return f"Error adding timeline event: {str(e)}"


def export_timeline(start_date: str = None, end_date: str = None, format: str = "json") -> str:
    """Export timeline as JSON or Markdown"""
    if not SERVICES_AVAILABLE:
        return "Timeline services not available"

    try:
        db = SimpleDB()

        # Build query
        query = "SELECT * FROM timeline_events WHERE 1=1"
        params = []

        if start_date:
            query += " AND event_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND event_date <= ?"
            params.append(end_date)

        query += " ORDER BY event_date DESC"
        events = db.fetch(query, tuple(params))

        if not events:
            return "No events to export"

        if format.lower() == "json":
            # JSON export
            export_data = {
                "export_date": datetime.now().isoformat(),
                "event_count": len(events),
                "date_range": {
                    "start": start_date or events[-1]["event_date"][:10],
                    "end": end_date or events[0]["event_date"][:10],
                },
                "events": events,
            }

            output = "📤 Timeline Export (JSON):\n\n"
            output += "```json\n"
            output += json.dumps(export_data, indent=2, default=str)[:5000]
            if len(json.dumps(export_data)) > 5000:
                output += "\n... (truncated)"
            output += "\n```\n"

        else:  # Markdown format
            output = "# Timeline Export\n\n"
            output += f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
            output += f"**Total Events:** {len(events)}\n\n"

            # Group by date
            events_by_date = {}
            for event in events:
                event_date = event.get("event_date", "")[:10]
                if event_date not in events_by_date:
                    events_by_date[event_date] = []
                events_by_date[event_date].append(event)

            for date in sorted(events_by_date.keys(), reverse=True):
                output += f"\n## {date}\n\n"
                for event in events_by_date[date]:
                    output += f"### {event['title']}\n"
                    output += f"- **Type:** {event['event_type']}\n"
                    output += f"- **Time:** {event['event_date'][11:19]}\n"
                    if event.get("description"):
                        output += f"- **Description:** {event['description']}\n"
                    if event.get("importance_score", 0) > 5:
                        output += f"- **Importance:** ⭐ {event['importance_score']}/10\n"
                    output += "\n"

        return output

    except Exception as e:
        return f"Error exporting timeline: {str(e)}"


class TimelineServer:
    """Simple timeline MCP server"""

    def __init__(self):
        self.server = Server("timeline-server")
        self.setup_tools()

    def setup_tools(self):
        """Register timeline tools"""

        @self.server.list_tools()
        async def handle_list_tools():
            return [
                Tool(
                    name="build_timeline",
                    description="Create chronological event timeline",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "Start date (YYYY-MM-DD)",
                            },
                            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                            "case_filter": {
                                "type": "string",
                                "description": "Filter by case number",
                            },
                        },
                    },
                ),
                Tool(
                    name="timeline_gaps",
                    description="Identify missing time periods in timeline",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "case_number": {
                                "type": "string",
                                "description": "Case number to analyze",
                            },
                            "days_threshold": {
                                "type": "integer",
                                "description": "Gap threshold in days",
                                "default": 30,
                            },
                        },
                    },
                ),
                Tool(
                    name="add_timeline_event",
                    description="Add manual event to timeline",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Event title"},
                            "description": {"type": "string", "description": "Event description"},
                            "event_date": {
                                "type": "string",
                                "description": "Event date (ISO format)",
                            },
                            "event_type": {
                                "type": "string",
                                "description": "Event type",
                                "enum": ["note", "meeting", "deadline", "filing", "hearing"],
                                "default": "note",
                            },
                            "importance": {
                                "type": "integer",
                                "description": "Importance (1-10)",
                                "default": 3,
                            },
                        },
                        "required": ["title", "description"],
                    },
                ),
                Tool(
                    name="export_timeline",
                    description="Export timeline as JSON or Markdown",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "start_date": {
                                "type": "string",
                                "description": "Start date (YYYY-MM-DD)",
                            },
                            "end_date": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                            "format": {
                                "type": "string",
                                "description": "Export format",
                                "enum": ["json", "markdown"],
                                "default": "json",
                            },
                        },
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            try:
                if name == "build_timeline":
                    result = build_timeline(
                        start_date=arguments.get("start_date"),
                        end_date=arguments.get("end_date"),
                        case_filter=arguments.get("case_filter"),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "timeline_gaps":
                    result = get_timeline_gaps(
                        case_number=arguments.get("case_number"),
                        days_threshold=arguments.get("days_threshold", 30),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "add_timeline_event":
                    result = add_timeline_event(
                        title=arguments["title"],
                        description=arguments["description"],
                        event_date=arguments.get("event_date"),
                        event_type=arguments.get("event_type", "note"),
                        importance=arguments.get("importance", 3),
                    )
                    return [TextContent(type="text", text=result)]

                elif name == "export_timeline":
                    result = export_timeline(
                        start_date=arguments.get("start_date"),
                        end_date=arguments.get("end_date"),
                        format=arguments.get("format", "json"),
                    )
                    return [TextContent(type="text", text=result)]

                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]

            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the timeline server"""
    server = TimelineServer()

    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="timeline",
                server_version="1.0.0",
                capabilities=server.server.get_capabilities(NotificationOptions(), {}),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
