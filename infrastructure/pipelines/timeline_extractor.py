"""
Timeline Extraction System

Extracts dates and events from document text to generate chronological timelines.
Follows CLAUDE.md principles: simple, direct implementation under 450 lines.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser
from loguru import logger

# Logger is now imported globally from loguru


class TimelineExtractor:
    """
    Extracts timeline events from document text using regex and dateutil parsing.

    Features:
    - Multiple date format detection
    - Context extraction (±50 chars around dates)
    - Event type classification from context
    - Confidence scoring based on format clarity
    """

    def __init__(self):
        """Initialize timeline extractor with date patterns and event keywords."""
        # Date patterns ordered by specificity (most specific first)
        self.date_patterns = [
            # ISO format: 2024-08-15, 2024/08/15
            r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",
            # US format: 08/15/2024, 8/15/24
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            # Written format: August 15, 2024, Aug 15 2024
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[,]?\s+\d{1,2}[,]?\s+\d{4}\b",
            # Day Month Year: 15 August 2024
            r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\b",
            # Simple formats: 8/15, Aug 15 (current year assumed)
            r"\b\d{1,2}[/-]\d{1,2}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\b",
        ]

        # Compile regex patterns for performance
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.date_patterns
        ]

        # Event type keywords for classification
        self.event_keywords = {
            "filing": ["filed", "filing", "submitted", "lodged", "docketed"],
            "hearing": ["hearing", "trial", "conference", "proceeding", "appearance", "scheduled"],
            "deadline": ["due", "deadline", "expires", "must", "shall", "by"],
            "service": ["served", "service", "notice", "summons", "subpoena"],
            "order": ["ordered", "ruled", "granted", "denied", "judgment", "order"],
            "motion": ["motion", "request", "petition", "application", "quash"],
            "discovery": ["discovery", "deposition", "interrogatories", "production"],
            "settlement": ["settlement", "agreement", "stipulation", "mediation"],
            "appeal": ["appeal", "appellate", "review", "reversal"],
        }

    def extract_dates_from_text(self, text: str, source_doc: str = None) -> list[dict[str, Any]]:
        """
        Extract all dates from text with context and classification.

        Args:
            text: Text content to analyze
            source_doc: Source document identifier

        Returns:
            List of date events with metadata
        """
        events = []

        for pattern_idx, pattern in enumerate(self.compiled_patterns):
            for match in pattern.finditer(text):
                date_str = match.group().strip()
                start_pos = match.start()
                end_pos = match.end()

                # Extract context (±50 characters)
                context_start = max(0, start_pos - 50)
                context_end = min(len(text), end_pos + 50)
                context = text[context_start:context_end].strip()

                # Parse the date
                parsed_date = self._parse_date(date_str)
                if not parsed_date:
                    continue

                # Classify event type and assign confidence
                event_type = self._classify_event_type(context)
                confidence = self._calculate_confidence(date_str, context, pattern_idx)

                event = {
                    "date": parsed_date.isoformat(),
                    "date_text": date_str,
                    "event_type": event_type,
                    "context": context,
                    "confidence": confidence,
                    "source_document": source_doc,
                    "position": start_pos,
                }

                events.append(event)

        # Remove duplicates (same date within 1 character position)
        events = self._deduplicate_events(events)

        # Sort by date
        events.sort(key=lambda x: x["date"])

        logger.info(f"Extracted {len(events)} timeline events from text")
        return events

    def extract_dates_from_file(self, file_path: str) -> list[dict[str, Any]]:
        """
        Extract dates from a markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            List of date events
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # Extract just the content (skip YAML frontmatter if present)
            if content.startswith("---\n"):
                parts = content.split("---\n", 2)
                if len(parts) >= 3:
                    content = parts[2]

            source_doc = Path(file_path).name
            return self.extract_dates_from_text(content, source_doc)

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return []

    def _parse_date(self, date_str: str) -> datetime | None:
        """Parse date string using dateutil with fallbacks."""
        try:
            # Try dateutil parser first
            return date_parser.parse(date_str, fuzzy=True)
        except Exception:
            try:
                # Try common formats manually
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y"]:
                    try:
                        return datetime.strptime(date_str, fmt)
                    except ValueError:
                        continue
            except Exception:
                pass

        logger.debug(f"Could not parse date: {date_str}")
        return None

    def _classify_event_type(self, context: str) -> str:
        """Classify event type based on context keywords."""
        context_lower = context.lower()

        # Count keyword matches for each event type
        type_scores = {}
        for event_type, keywords in self.event_keywords.items():
            score = sum(1 for keyword in keywords if keyword in context_lower)
            if score > 0:
                type_scores[event_type] = score

        if type_scores:
            # Return type with highest score
            return max(type_scores.items(), key=lambda x: x[1])[0]

        return "event"  # Default type

    def _calculate_confidence(self, date_str: str, context: str, pattern_idx: int) -> str:
        """Calculate confidence level based on date format and context clarity."""
        confidence_score = 0

        # Pattern specificity (0-3 points)
        if pattern_idx == 0:  # ISO format
            confidence_score += 3
        elif pattern_idx == 1:  # US format with year
            confidence_score += 2
        elif pattern_idx == 2:  # Written format
            confidence_score += 2
        elif pattern_idx == 3:  # Day Month Year
            confidence_score += 1

        # Date string quality (0-2 points)
        if len(date_str) > 8:  # Full date with year
            confidence_score += 2
        elif len(date_str) > 5:  # Month/day
            confidence_score += 1

        # Context quality (0-2 points)
        context_keywords = ["filed", "served", "hearing", "due", "dated", "on", "by"]
        context_matches = sum(1 for kw in context_keywords if kw in context.lower())
        if context_matches >= 2:
            confidence_score += 2
        elif context_matches >= 1:
            confidence_score += 1

        # Convert to confidence level
        if confidence_score >= 6:
            return "HIGH"
        elif confidence_score >= 3:
            return "MEDIUM"
        else:
            return "LOW"

    def _deduplicate_events(self, events: list[dict]) -> list[dict]:
        """Remove duplicate events (same date within close proximity)."""
        if not events:
            return events

        deduplicated = []
        events.sort(key=lambda x: (x["date"], x["position"]))

        for event in events:
            # Check if this event is too similar to an existing one
            duplicate = False
            for existing in deduplicated:
                # Consider duplicate if same date and close position OR same date text
                same_date = existing["date"] == event["date"]
                close_position = abs(existing["position"] - event["position"]) < 50
                same_text = existing["date_text"] == event["date_text"]

                if same_date and (close_position or same_text):
                    # Keep the one with higher confidence
                    if self._confidence_score(event["confidence"]) > self._confidence_score(
                        existing["confidence"]
                    ):
                        deduplicated.remove(existing)
                        break
                    else:
                        duplicate = True
                        break

            if not duplicate:
                deduplicated.append(event)

        return deduplicated

    def _confidence_score(self, confidence: str) -> int:
        """Convert confidence string to numeric score."""
        return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(confidence, 0)

    def generate_timeline_summary(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Generate summary statistics for timeline events.

        Args:
            events: List of timeline events

        Returns:
            Dictionary with timeline statistics
        """
        if not events:
            return {
                "total_events": 0,
                "date_range": None,
                "event_types": {},
                "confidence_distribution": {},
                "timeline_span_days": 0,
            }

        # Calculate date range
        dates = [datetime.fromisoformat(event["date"]) for event in events]
        start_date = min(dates)
        end_date = max(dates)
        span_days = (end_date - start_date).days

        # Count event types
        event_types = {}
        for event in events:
            event_type = event["event_type"]
            event_types[event_type] = event_types.get(event_type, 0) + 1

        # Count confidence levels
        confidence_dist = {}
        for event in events:
            conf = event["confidence"]
            confidence_dist[conf] = confidence_dist.get(conf, 0) + 1

        return {
            "total_events": len(events),
            "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "event_types": event_types,
            "confidence_distribution": confidence_dist,
            "timeline_span_days": span_days,
            "high_confidence_events": len([e for e in events if e["confidence"] == "HIGH"]),
            "medium_confidence_events": len([e for e in events if e["confidence"] == "MEDIUM"]),
            "low_confidence_events": len([e for e in events if e["confidence"] == "LOW"]),
        }

    def filter_events_by_confidence(
        self, events: list[dict[str, Any]], min_confidence: str = "MEDIUM"
    ) -> list[dict[str, Any]]:
        """
        Filter events by minimum confidence level.

        Args:
            events: List of timeline events
            min_confidence: Minimum confidence level ('LOW', 'MEDIUM', 'HIGH')

        Returns:
            Filtered list of events
        """
        min_score = self._confidence_score(min_confidence)
        return [
            event for event in events if self._confidence_score(event["confidence"]) >= min_score
        ]

    def group_events_by_date(self, events: list[dict[str, Any]]) -> dict[str, list[dict]]:
        """
        Group events by date for timeline display.

        Args:
            events: List of timeline events

        Returns:
            Dictionary with dates as keys and event lists as values
        """
        grouped = {}
        for event in events:
            date_key = event["date"].split("T")[0]  # Get date part only
            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(event)

        # Sort events within each date by confidence and position
        for date_key in grouped:
            grouped[date_key].sort(
                key=lambda x: (self._confidence_score(x["confidence"]), -x["position"]),
                reverse=True,
            )

        return grouped

    def generate_markdown_timeline(
        self, events: list[dict[str, Any]], output_path: str = None, min_confidence: str = "MEDIUM"
    ) -> str:
        """
        Generate markdown timeline from events.

        Args:
            events: List of timeline events
            output_path: Optional file path to save timeline
            min_confidence: Minimum confidence level to include

        Returns:
            Markdown timeline content
        """
        # Filter events by confidence
        filtered_events = self.filter_events_by_confidence(events, min_confidence)

        if not filtered_events:
            return "# Timeline\n\nNo timeline events found with the specified confidence level.\n"

        # Group events by date
        grouped_events = self.group_events_by_date(filtered_events)

        # Generate summary
        summary = self.generate_timeline_summary(filtered_events)

        # Build markdown content
        markdown_lines = [
            "# Document Timeline",
            "",
            "## Summary",
            "",
            f"- **Total Events**: {summary['total_events']}",
            f"- **Date Range**: {summary['date_range']['start']} to {summary['date_range']['end']}",
            f"- **Timeline Span**: {summary['timeline_span_days']} days",
            f"- **High Confidence Events**: {summary['high_confidence_events']}",
            f"- **Medium Confidence Events**: {summary['medium_confidence_events']}",
            f"- **Low Confidence Events**: {summary['low_confidence_events']}",
            "",
            "## Event Types",
            "",
        ]

        # Add event type breakdown
        for event_type, count in sorted(summary["event_types"].items()):
            markdown_lines.append(f"- **{event_type.title()}**: {count} events")

        markdown_lines.extend(
            [
                "",
                "## Timeline Events",
                "",
                "_Events are grouped by date and ordered chronologically._",
                "",
            ]
        )

        # Add events grouped by date
        for date_key in sorted(grouped_events.keys()):
            date_events = grouped_events[date_key]

            # Format date header
            try:
                date_obj = datetime.fromisoformat(date_key)
                formatted_date = date_obj.strftime("%B %d, %Y (%A)")
            except (ValueError, TypeError):
                formatted_date = date_key

            markdown_lines.append(f"### {formatted_date}")
            markdown_lines.append("")

            # Add events for this date
            for event in date_events:
                confidence_badge = self._get_confidence_badge(event["confidence"])
                event_type_badge = f"**{event['event_type'].title()}**"

                # Format the event entry
                event_line = f"- {confidence_badge} {event_type_badge}: {event['date_text']}"

                # Add context if meaningful
                context = event["context"].strip()
                if context and len(context) > len(event["date_text"]) + 20:
                    # Clean up context for display
                    clean_context = self._clean_context_for_display(context, event["date_text"])
                    if clean_context:
                        event_line += f" - _{clean_context}_"

                # Add source document
                if event.get("source_document"):
                    event_line += f" `({event['source_document']})`"

                markdown_lines.append(event_line)

            markdown_lines.append("")

        # Add footer
        markdown_lines.extend(
            [
                "---",
                "",
                f"_Timeline generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
                f"_Minimum confidence level: {min_confidence}_",
                "",
            ]
        )

        markdown_content = "\n".join(markdown_lines)

        # Save to file if path provided
        if output_path:
            try:
                # Ensure directory exists
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                logger.info(f"Timeline saved to {output_path}")
            except Exception as e:
                logger.error(f"Error saving timeline to {output_path}: {e}")

        return markdown_content

    def _get_confidence_badge(self, confidence: str) -> str:
        """Get colored badge for confidence level."""
        badges = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}
        return badges.get(confidence, "⚪")

    def _clean_context_for_display(self, context: str, date_text: str) -> str:
        """Clean context text for display in timeline."""
        # Remove the date text from context to avoid duplication
        clean_context = context.replace(date_text, "").strip()

        # Remove extra whitespace and normalize
        clean_context = " ".join(clean_context.split())

        # Truncate if too long
        if len(clean_context) > 100:
            clean_context = clean_context[:97] + "..."

        # Remove if it's just fragments
        if len(clean_context) < 10:
            return ""

        return clean_context

    def store_events_in_database(
        self, events: list[dict[str, Any]], db_path: str = "emails.db"
    ) -> dict[str, Any]:
        """
        Store extracted timeline events in database using timeline service.

        Args:
            events: List of timeline events to store
            db_path: Path to database file

        Returns:
            Dictionary with storage results
        """
        try:
            from utilities.timeline.database import TimelineDatabase

            timeline_db = TimelineDatabase(db_path)

            stored_count = 0
            errors = []

            for event in events:
                try:
                    # Create timeline event in database
                    result = timeline_db.create_timeline_event(
                        event_type=event["event_type"],
                        title=f"{event['event_type'].title()}: {event['date_text']}",
                        event_date=event["date"],
                        description=event.get("context", ""),
                        metadata={
                            "confidence": event["confidence"],
                            "date_text": event["date_text"],
                            "position": event.get("position", 0),
                            "extraction_source": "timeline_extractor",
                        },
                        source_type="document",
                        importance_score=self._get_importance_score(event),
                    )

                    if result.get("success"):
                        stored_count += 1
                    else:
                        errors.append(
                            f"Event {event['date_text']}: {result.get('error', 'Unknown error')}"
                        )

                except Exception as e:
                    errors.append(f"Event {event['date_text']}: {str(e)}")

            return {
                "success": True,
                "total_events": len(events),
                "stored_count": stored_count,
                "error_count": len(errors),
                "errors": errors,
            }

        except ImportError:
            return {
                "success": False,
                "error": "Timeline service not available - database storage skipped",
            }
        except Exception as e:
            return {"success": False, "error": f"Database storage failed: {str(e)}"}

    def _get_importance_score(self, event: dict[str, Any]) -> int:
        """Calculate importance score for database storage (0-10)."""
        score = 5  # Base score

        # Adjust by confidence
        confidence_scores = {"HIGH": 3, "MEDIUM": 1, "LOW": -1}
        score += confidence_scores.get(event["confidence"], 0)

        # Adjust by event type importance
        important_types = {"filing", "hearing", "order", "deadline"}
        if event["event_type"] in important_types:
            score += 2

        # Ensure score is in valid range
        return max(0, min(10, score))
