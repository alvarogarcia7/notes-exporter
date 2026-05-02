#!/usr/bin/env python3
"""
Date extraction utility for notes.
Extracts dates from note titles (dd/mm format) or uses creation date.
"""

import re
from datetime import datetime
from typing import Optional, Tuple


def extract_date_from_title(title: str) -> Optional[Tuple[int, int]]:
    """
    Extract date in dd/mm format from note title.

    Args:
        title: Note title string

    Returns:
        Tuple of (day, month) if found, None otherwise

    Examples:
        >>> extract_date_from_title("Meeting 15/05")
        (15, 5)
        >>> extract_date_from_title("15/05 Team Sync")
        (15, 5)
        >>> extract_date_from_title("No date here")
        None
    """
    if not title:
        return None

    # Look for dd/mm pattern (with optional leading zeros)
    # Matches: 15/05, 5/5, 01/01, etc.
    match = re.search(r'\b(\d{1,2})/(\d{1,2})\b', title)

    if not match:
        return None

    try:
        day = int(match.group(1))
        month = int(match.group(2))

        # Validate day and month ranges
        if 1 <= day <= 31 and 1 <= month <= 12:
            # Additional validation: check if date is valid for the month
            if month in [4, 6, 9, 11] and day > 30:
                # April, June, September, November have 30 days
                return None
            if month == 2 and day > 29:
                # February has at most 29 days (leap year)
                return None
            return (day, month)
    except (ValueError, IndexError):
        pass

    return None


def get_note_date(note_data: dict, title: Optional[str] = None) -> Optional[str]:
    """
    Get the date for a note, with title override.

    Priority:
    1. Date extracted from title (dd/mm format)
    2. Creation date from note_data (created/createdTime/timestamp fields)
    3. Modification date from note_data (modified/updatedTime/updated fields)
    4. None if no date found

    Args:
        note_data: Note dictionary (from JSON)
        title: Optional title string (uses note_data['title'] if not provided)

    Returns:
        ISO format date string (YYYY-MM-DD) or None

    Examples:
        >>> note = {"created": "2026-05-02T10:30:00Z", "title": "Meeting 15/05"}
        >>> get_note_date(note)
        '2026-05-15'

        >>> note = {"created": "2026-05-02T10:30:00Z"}
        >>> get_note_date(note)
        '2026-05-02'
    """
    if title is None:
        title = note_data.get('title', '')

    current_year = datetime.now().year

    # Try to extract date from title
    title_date = extract_date_from_title(title)
    if title_date:
        day, month = title_date
        # Use current year by default
        date_str = f"{current_year}-{month:02d}-{day:02d}"
        try:
            return date_str
        except ValueError:
            # Invalid date combination (e.g., 31/02)
            pass

    # Try common date field names in order of preference
    date_fields = [
        'created',
        'createdTime',
        'timestamp',
        'modified',
        'updatedTime',
        'updated',
        'date',
    ]

    for field in date_fields:
        if field in note_data:
            date_value = note_data[field]
            if not date_value:
                continue

            try:
                # Try ISO format first
                if isinstance(date_value, str):
                    # Handle various ISO formats
                    if 'T' in date_value:
                        # ISO 8601 with time
                        dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                    else:
                        # Just date
                        dt = datetime.fromisoformat(date_value)
                    return dt.strftime('%Y-%m-%d')
                elif isinstance(date_value, (int, float)):
                    # Unix timestamp
                    dt = datetime.fromtimestamp(date_value)
                    return dt.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                continue

    return None


def format_message_with_date(message: dict, note_data: dict) -> dict:
    """
    Add date field to message dictionary.

    Args:
        message: Message dictionary with 'id', 'note', etc.
        note_data: Note data dictionary

    Returns:
        Updated message with 'date' field added
    """
    title = note_data.get('title') or message.get('filename', '').replace('.json', '')
    date = get_note_date(note_data, title)

    message['date'] = date

    return message


if __name__ == "__main__":
    # Simple test
    import doctest
    doctest.testmod(verbose=True)
