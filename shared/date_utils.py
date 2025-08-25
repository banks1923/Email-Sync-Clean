"""Date parsing utilities for flexible search filters.

Handles relative dates like 'last week', 'this month', and absolute
dates.
"""

import re
from datetime import datetime, timedelta


def parse_relative_date(date_str: str) -> datetime | None:
    """
    Parse relative dates like 'last week', 'this month', '3 days ago'.
    """
    if not date_str:
        return None

    date_str = date_str.lower().strip()
    now = datetime.now()

    # Today/yesterday/tomorrow
    if date_str == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str == "yesterday":
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str == "tomorrow":
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # This week/month/year
    elif date_str == "this week":
        days_since_monday = now.weekday()
        return (now - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif date_str == "this month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif date_str == "this year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # Last week/month/year
    elif date_str == "last week":
        days_since_monday = now.weekday()
        last_monday = now - timedelta(days=days_since_monday + 7)
        return last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    elif date_str == "last month":
        if now.month == 1:
            return now.replace(
                year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0
            )
        else:
            return now.replace(
                month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
    elif date_str == "last year":
        return now.replace(
            year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )

    # X days/weeks/months/years ago
    pattern = r"(\d+)\s+(day|week|month|year)s?\s+ago"
    match = re.match(pattern, date_str)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)

        if unit == "day":
            return (now - timedelta(days=amount)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif unit == "week":
            return (now - timedelta(weeks=amount)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        # Month/year approximations
        elif unit == "month":
            return (now - timedelta(days=amount * 30)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif unit == "year":
            return (now - timedelta(days=amount * 365)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

    return None


def parse_date_filter(date_input: str) -> datetime | None:
    """Parse various date formats for filtering.

    Args:
        date_input: Date string in various formats

    Returns:
        datetime object or None if parsing fails
    """
    if not date_input:
        return None

    # Try relative date first
    relative_date = parse_relative_date(date_input)
    if relative_date:
        return relative_date

    # Try absolute date formats
    date_formats = [
        "%Y-%m-%d",  # 2024-01-15
        "%Y/%m/%d",  # 2024/01/15
        "%m/%d/%Y",  # 01/15/2024
        "%m-%d-%Y",  # 01-15-2024
        "%d/%m/%Y",  # 15/01/2024 (European)
        "%Y-%m-%d %H:%M:%S",  # 2024-01-15 10:30:00
        "%Y-%m-%d %H:%M",  # 2024-01-15 10:30
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(date_input.strip(), fmt)
        except ValueError:
            continue

    return None


def get_date_range(
    since: str = None, until: str = None
) -> tuple[datetime | None, datetime | None]:
    """Get date range for filtering.

    Args:
        since: Start date string
        until: End date string

    Returns:
        Tuple of (start_date, end_date)
    """
    start_date = parse_date_filter(since) if since else None
    end_date = parse_date_filter(until) if until else None

    # If end_date is specified without time, set it to end of day
    if end_date and end_date.time() == end_date.min.time():
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    return start_date, end_date


def parse_date_from_filename(filename: str) -> datetime | None:
    """Extract date from filename using common patterns.

    Args:
        filename: Name of file to parse

    Returns:
        datetime object if date found, None otherwise
    """
    if not filename:
        return None
    
    # Common filename date patterns
    patterns = [
        r"(\d{4})-(\d{2})-(\d{2})",  # YYYY-MM-DD
        r"(\d{4})_(\d{2})_(\d{2})",  # YYYY_MM_DD
        r"(\d{4})(\d{2})(\d{2})",    # YYYYMMDD
        r"(\d{2})-(\d{2})-(\d{4})",  # MM-DD-YYYY
        r"(\d{2})_(\d{2})_(\d{4})",  # MM_DD_YYYY
        r"(\d{2})/(\d{2})/(\d{4})",  # MM/DD/YYYY
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            try:
                groups = match.groups()
                if len(groups) == 3:
                    # Determine if it's YYYY-MM-DD or MM-DD-YYYY format
                    if len(groups[0]) == 4:  # YYYY-MM-DD format
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    else:  # MM-DD-YYYY format
                        month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                    
                    # Validate date components
                    if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100:
                        return datetime(year, month, day)
            except (ValueError, TypeError):
                continue
    
    return None
