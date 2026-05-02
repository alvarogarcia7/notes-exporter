#!/usr/bin/env python3
"""
Apple Notes metadata parser.
Parses Apple Notes export metadata from iCloud-Notes.json.
Converts date formats and extracts relevant fields.
"""

import re
from datetime import datetime
from typing import Optional, Dict, Any

# Optional fallback parser
try:
    from dateutil import parser as date_parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


# Day and month name mappings for Apple Notes date format
DAY_NAMES = {
    'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3,
    'Friday': 4, 'Saturday': 5, 'Sunday': 6
}

MONTH_NAMES = {
    'January': 1, 'February': 2, 'March': 3, 'April': 4,
    'May': 5, 'June': 6, 'July': 7, 'August': 8,
    'September': 9, 'October': 10, 'November': 11, 'December': 12
}


def parse_apple_notes_date(date_str: str) -> Optional[str]:
    """
    Parse Apple Notes date format to ISO 8601.

    Apple Notes format: "Tuesday, 21 March 2023 at 16:05:27"

    Args:
        date_str: Date string in Apple Notes format

    Returns:
        ISO 8601 date string (YYYY-MM-DD HH:MM:SS) or None if parsing fails

    Examples:
        >>> parse_apple_notes_date("Tuesday, 21 March 2023 at 16:05:27")
        '2023-03-21 16:05:27'
        >>> parse_apple_notes_date("Friday, 1 May 2026 at 18:35:16")
        '2026-05-01 18:35:16'
    """
    if not date_str:
        return None

    try:
        # Pattern: "Day, DD Month YYYY at HH:MM:SS"
        # Example: "Tuesday, 21 March 2023 at 16:05:27"
        pattern = r'([A-Za-z]+),\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\s+at\s+(\d{2}):(\d{2}):(\d{2})'
        match = re.match(pattern, date_str.strip())

        if not match:
            # Try using dateutil parser as fallback if available
            if HAS_DATEUTIL:
                try:
                    dt = date_parser.parse(date_str)
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    return None
            return None

        day_name, day, month_name, year, hour, minute, second = match.groups()

        # Validate month name
        if month_name not in MONTH_NAMES:
            return None

        month = MONTH_NAMES[month_name]
        day = int(day)
        year = int(year)
        hour = int(hour)
        minute = int(minute)
        second = int(second)

        # Create datetime object
        dt = datetime(year, month, day, hour, minute, second)

        # Return ISO format with time
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    except (ValueError, AttributeError, KeyError):
        return None


def extract_note_id_from_coredata(fullNoteId: str) -> Optional[str]:
    """
    Extract the note ID from Apple's CoreData full note ID.

    Format: "x-coredata://UUID/ICNote/pID"
    Example: "x-coredata://DD12312-0000-0000-0000-A301023912313/ICNote/p98"

    Args:
        fullNoteId: Full note ID from Apple Notes export

    Returns:
        Extracted note ID (e.g., "98") or None if parsing fails

    Examples:
        >>> extract_note_id_from_coredata("x-coredata://DD12312-0000-0000-0000-A301023912313/ICNote/p98")
        '98'
    """
    if not fullNoteId:
        return None

    try:
        # Pattern: .../pID where ID is the note identifier
        match = re.search(r'/p(\w+)$', fullNoteId)
        if match:
            return match.group(1)
    except (AttributeError, IndexError):
        pass

    return None


def parse_apple_notes_metadata(metadata_entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse a single Apple Notes metadata entry.

    Converts Apple Notes format to standardized format.

    Args:
        metadata_entry: Dictionary with keys like 'created', 'modified', 'fullNoteId', etc.

    Returns:
        Parsed metadata dictionary with standardized fields

    Example:
        >>> entry = {
        ...     "created": "Tuesday, 21 March 2023 at 16:05:27",
        ...     "modified": "Monday, 27 March 2023 at 14:39:28",
        ...     "fullNoteId": "x-coredata://DD12312-0000-0000-0000-A301023912313/ICNote/p98",
        ...     "filename": "Todo-23-3-98",
        ...     "exportCount": 1
        ... }
        >>> result = parse_apple_notes_metadata(entry)
        >>> result['note_id']
        '98'
        >>> result['created']
        '2023-03-21 16:05:27'
    """
    result = {
        "original": metadata_entry,
        "note_id": None,
        "created": None,
        "modified": None,
        "created_date_only": None,
        "modified_date_only": None,
        "filename": metadata_entry.get("filename"),
        "export_count": metadata_entry.get("exportCount"),
        "first_exported": None,
        "last_exported": None,
    }

    # Parse fullNoteId
    if "fullNoteId" in metadata_entry:
        result["note_id"] = extract_note_id_from_coredata(metadata_entry["fullNoteId"])

    # Parse created date
    if "created" in metadata_entry:
        created_iso = parse_apple_notes_date(metadata_entry["created"])
        if created_iso:
            result["created"] = created_iso
            result["created_date_only"] = created_iso.split()[0]  # YYYY-MM-DD

    # Parse modified date
    if "modified" in metadata_entry:
        modified_iso = parse_apple_notes_date(metadata_entry["modified"])
        if modified_iso:
            result["modified"] = modified_iso
            result["modified_date_only"] = modified_iso.split()[0]  # YYYY-MM-DD

    # Parse first exported
    if "firstExported" in metadata_entry:
        first_exported_iso = parse_apple_notes_date(metadata_entry["firstExported"])
        if first_exported_iso:
            result["first_exported"] = first_exported_iso

    # Parse last exported
    if "lastExported" in metadata_entry:
        last_exported_iso = parse_apple_notes_date(metadata_entry["lastExported"])
        if last_exported_iso:
            result["last_exported"] = last_exported_iso

    return result


def load_apple_notes_metadata(json_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Load and parse all Apple Notes metadata entries.

    Args:
        json_data: The parsed iCloud-Notes.json content

    Returns:
        Dictionary mapping note IDs to parsed metadata

    Example:
        >>> data = {
        ...     "98": {
        ...         "created": "Tuesday, 21 March 2023 at 16:05:27",
        ...         "modified": "Monday, 27 March 2023 at 14:39:28",
        ...         "fullNoteId": "x-coredata://DD12312-0000-0000-0000-A301023912313/ICNote/p98",
        ...         "filename": "Todo-23-3-98"
        ...     }
        ... }
        >>> result = load_apple_notes_metadata(data)
        >>> result["98"]["note_id"]
        '98'
    """
    result = {}

    for entry_id, entry_data in json_data.items():
        if isinstance(entry_data, dict):
            parsed = parse_apple_notes_metadata(entry_data)
            result[entry_id] = parsed

    return result


if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)
