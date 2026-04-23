"""Date parsing utilities for social listening service.

Standardizes all date formats to YYYY-MM-DD strings.
"""
from datetime import datetime, timedelta
import re


def parse_to_yyyy_mm_dd(date_value) -> str:
    """
    Convert various date formats to YYYY-MM-DD string.

    Handles:
    - ISO datetime strings ("2025-01-31T14:30:00Z")
    - YYYY-MM-DD strings (passthrough)
    - Unix timestamps (1706745600)
    - German relative dates ("vor 2 Tagen")
    - German date format ("01.01.2024")
    - None/empty (returns today's date)

    Args:
        date_value: Date in various formats (str, int, float, or None)

    Returns:
        Date string in YYYY-MM-DD format
    """
    if not date_value:
        return datetime.now().strftime('%Y-%m-%d')

    # Already YYYY-MM-DD
    if isinstance(date_value, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', date_value):
        return date_value

    # Unix timestamp (int, float, or numeric string)
    if isinstance(date_value, (int, float)) or (isinstance(date_value, str) and date_value.isdigit()):
        ts = int(date_value)
        return datetime.fromtimestamp(ts).strftime('%Y-%m-%d')

    # String-based formats
    if isinstance(date_value, str):
        # German relative: "vor 2 Tagen", "vor 1 Tag", "vor 3 Wochen"
        match = re.search(r'vor (\d+) (Tag(?:en)?|Stunde(?:n)?|Minute(?:n)?|Woche(?:n)?|Monat(?:en)?)', date_value, re.IGNORECASE)
        if match:
            num = int(match.group(1))
            unit = match.group(2).lower()
            if 'tag' in unit:
                return (datetime.now() - timedelta(days=num)).strftime('%Y-%m-%d')
            elif 'woche' in unit:
                return (datetime.now() - timedelta(weeks=num)).strftime('%Y-%m-%d')
            elif 'monat' in unit:
                return (datetime.now() - timedelta(days=num * 30)).strftime('%Y-%m-%d')
            else:  # hours/minutes = today
                return datetime.now().strftime('%Y-%m-%d')

        # German date: "01.01.2024" or "1.1.2024"
        match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', date_value)
        if match:
            day = match.group(1).zfill(2)
            month = match.group(2).zfill(2)
            year = match.group(3)
            return f"{year}-{month}-{day}"

        # ISO datetime formats
        iso_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S%z',
        ]
        for fmt in iso_formats:
            try:
                # Handle timezone-aware formats
                parsed = datetime.strptime(date_value[:26].rstrip('Z'), fmt.rstrip('Z'))
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue

    # Fallback: return today's date
    return datetime.now().strftime('%Y-%m-%d')


def get_weekly_date_range() -> tuple[str, str]:
    """Get date range for the past 7 days (for weekly cron jobs).

    Returns:
        Tuple of (date_from, date_to) in YYYY-MM-DD format.
        date_from is 7 days ago, date_to is today.
    """
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    return (week_ago.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d'))


def is_date_in_range(
    date_str: str,
    date_from: str = None,
    date_to: str = None
) -> bool:
    """Check if a date string falls within the given range.

    Args:
        date_str: Date to check in YYYY-MM-DD format
        date_from: Start of range (inclusive), None means no lower bound
        date_to: End of range (inclusive), None means no upper bound

    Returns:
        True if date is within range, False otherwise
    """
    if not date_str:
        return True  # No date = can't filter, include by default

    # Normalize the date to YYYY-MM-DD if needed
    normalized = parse_to_yyyy_mm_dd(date_str)

    if date_from and normalized < date_from:
        return False
    if date_to and normalized > date_to:
        return False
    return True
