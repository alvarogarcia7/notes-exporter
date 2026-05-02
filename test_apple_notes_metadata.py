#!/usr/bin/env python3
"""
Tests for Apple Notes metadata parser.
"""

import pytest
from apple_notes_metadata_parser import (
    parse_apple_notes_date,
    extract_note_id_from_coredata,
    parse_apple_notes_metadata,
    load_apple_notes_metadata,
)


class TestParseAppleNotesDate:
    """Tests for parse_apple_notes_date function."""

    def test_standard_format(self):
        """Test standard Apple Notes date format."""
        result = parse_apple_notes_date("Tuesday, 21 March 2023 at 16:05:27")
        assert result == "2023-03-21 16:05:27"

    def test_various_days(self):
        """Test different day names."""
        test_cases = [
            ("Monday, 1 January 2023 at 10:00:00", "2023-01-01 10:00:00"),
            ("Wednesday, 15 June 2023 at 14:30:45", "2023-06-15 14:30:45"),
            ("Friday, 1 May 2026 at 18:35:16", "2026-05-01 18:35:16"),
            ("Sunday, 31 December 2023 at 23:59:59", "2023-12-31 23:59:59"),
        ]
        for input_str, expected in test_cases:
            assert parse_apple_notes_date(input_str) == expected

    def test_various_months(self):
        """Test all month names."""
        months = [
            ("January", "01"), ("February", "02"), ("March", "03"),
            ("April", "04"), ("May", "05"), ("June", "06"),
            ("July", "07"), ("August", "08"), ("September", "09"),
            ("October", "10"), ("November", "11"), ("December", "12"),
        ]
        for month_name, month_num in months:
            date_str = f"Monday, 15 {month_name} 2023 at 12:00:00"
            result = parse_apple_notes_date(date_str)
            assert f"2023-{month_num}-15" in result

    def test_single_digit_day(self):
        """Test single digit days."""
        result = parse_apple_notes_date("Monday, 1 March 2023 at 10:00:00")
        assert result == "2023-03-01 10:00:00"

    def test_leap_year(self):
        """Test leap year date."""
        result = parse_apple_notes_date("Monday, 29 February 2024 at 12:00:00")
        assert result == "2024-02-29 12:00:00"

    def test_different_times(self):
        """Test various time values."""
        test_cases = [
            ("Monday, 1 March 2023 at 00:00:00", "2023-03-01 00:00:00"),
            ("Monday, 1 March 2023 at 12:30:45", "2023-03-01 12:30:45"),
            ("Monday, 1 March 2023 at 23:59:59", "2023-03-01 23:59:59"),
        ]
        for input_str, expected in test_cases:
            assert parse_apple_notes_date(input_str) == expected

    def test_invalid_formats(self):
        """Test rejection of invalid formats."""
        invalid_inputs = [
            "21 March 2023",  # Missing day name
            "Tuesday 21 March 2023 at 16:05:27",  # Missing comma
            "Tuesday, March 21 2023 at 16:05:27",  # Wrong day/month order
            "2023-03-21 16:05:27",  # ISO format (not Apple format)
            "March 21, 2023",  # US format
            None,  # None input
            "",  # Empty string
        ]
        for invalid in invalid_inputs:
            assert parse_apple_notes_date(invalid) is None

    def test_invalid_dates(self):
        """Test rejection of invalid calendar dates."""
        invalid_dates = [
            "Monday, 32 March 2023 at 10:00:00",  # Day 32
            "Monday, 31 February 2023 at 10:00:00",  # Feb 31
            "Monday, 0 March 2023 at 10:00:00",  # Day 0
            "Monday, 15 Month 2023 at 10:00:00",  # Invalid month
        ]
        for invalid in invalid_dates:
            assert parse_apple_notes_date(invalid) is None


class TestExtractNoteIdFromCoredata:
    """Tests for extract_note_id_from_coredata function."""

    def test_standard_format(self):
        """Test standard CoreData ID extraction."""
        fullNoteId = "x-coredata://DD12312-0000-0000-0000-A301023912313/ICNote/p98"
        assert extract_note_id_from_coredata(fullNoteId) == "98"

    def test_various_note_ids(self):
        """Test extraction of various note IDs."""
        test_cases = [
            ("x-coredata://UUID/ICNote/p1", "1"),
            ("x-coredata://UUID/ICNote/p100", "100"),
            ("x-coredata://UUID/ICNote/p12345", "12345"),
            ("x-coredata://UUID/ICNote/pABC123", "ABC123"),
        ]
        for fullNoteId, expected_id in test_cases:
            assert extract_note_id_from_coredata(fullNoteId) == expected_id

    def test_invalid_formats(self):
        """Test rejection of invalid formats."""
        invalid_inputs = [
            "not-a-coredata-id",
            "x-coredata://UUID/ICNote/",  # Missing ID
            "x-coredata://UUID/ICNote",  # Missing /p prefix
            None,
            "",
        ]
        for invalid in invalid_inputs:
            assert extract_note_id_from_coredata(invalid) is None


class TestParseAppleNotesMetadata:
    """Tests for parse_apple_notes_metadata function."""

    def test_complete_metadata_entry(self):
        """Test parsing complete metadata entry."""
        entry = {
            "created": "Tuesday, 21 March 2023 at 16:05:27",
            "exportCount": 1,
            "filename": "Todo-23-3-98",
            "firstExported": "Friday, 1 May 2026 at 18:35:16",
            "fullNoteId": "x-coredata://DD12312-0000-0000-0000-A301023912313/ICNote/p98",
            "lastExported": "Friday, 1 May 2026 at 18:35:16",
            "modified": "Monday, 27 March 2023 at 14:39:28"
        }

        result = parse_apple_notes_metadata(entry)

        assert result["note_id"] == "98"
        assert result["created"] == "2023-03-21 16:05:27"
        assert result["created_date_only"] == "2023-03-21"
        assert result["modified"] == "2023-03-27 14:39:28"
        assert result["modified_date_only"] == "2023-03-27"
        assert result["filename"] == "Todo-23-3-98"
        assert result["export_count"] == 1

    def test_minimal_metadata_entry(self):
        """Test parsing minimal metadata entry."""
        entry = {
            "filename": "MinimalNote"
        }

        result = parse_apple_notes_metadata(entry)

        assert result["filename"] == "MinimalNote"
        assert result["note_id"] is None
        assert result["created"] is None
        assert result["modified"] is None

    def test_empty_metadata_entry(self):
        """Test parsing empty metadata entry."""
        entry = {}
        result = parse_apple_notes_metadata(entry)

        assert result["filename"] is None
        assert result["created"] is None
        assert result["modified"] is None

    def test_metadata_preserves_original(self):
        """Test that original data is preserved."""
        entry = {
            "created": "Tuesday, 21 March 2023 at 16:05:27",
            "custom_field": "custom_value"
        }

        result = parse_apple_notes_metadata(entry)

        assert result["original"] == entry
        assert result["original"]["custom_field"] == "custom_value"


class TestLoadAppleNotesMetadata:
    """Tests for load_apple_notes_metadata function."""

    def test_load_multiple_entries(self):
        """Test loading multiple metadata entries."""
        json_data = {
            "98": {
                "created": "Tuesday, 21 March 2023 at 16:05:27",
                "filename": "Todo-23-3-98",
                "fullNoteId": "x-coredata://UUID1/ICNote/p98"
            },
            "99": {
                "created": "Wednesday, 22 March 2023 at 10:00:00",
                "filename": "Note-23-3-99",
                "fullNoteId": "x-coredata://UUID2/ICNote/p99"
            }
        }

        result = load_apple_notes_metadata(json_data)

        assert len(result) == 2
        assert result["98"]["note_id"] == "98"
        assert result["99"]["note_id"] == "99"
        assert result["98"]["filename"] == "Todo-23-3-98"
        assert result["99"]["filename"] == "Note-23-3-99"

    def test_load_empty_data(self):
        """Test loading empty metadata."""
        json_data = {}
        result = load_apple_notes_metadata(json_data)

        assert result == {}

    def test_load_ignores_non_dict_entries(self):
        """Test that non-dict entries are ignored."""
        json_data = {
            "98": {
                "created": "Tuesday, 21 March 2023 at 16:05:27",
                "filename": "Todo-23-3-98"
            },
            "string_value": "not a dict",
            "99": {
                "filename": "Note-23-3-99"
            }
        }

        result = load_apple_notes_metadata(json_data)

        # Non-dict entry "string_value" should be skipped
        assert len(result) == 2
        assert "98" in result
        assert "99" in result
        assert "string_value" not in result


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_typical_apple_notes_export(self):
        """Test with typical Apple Notes export structure."""
        export_data = {
            "1": {
                "created": "Monday, 15 January 2024 at 09:30:00",
                "modified": "Tuesday, 16 January 2024 at 10:15:30",
                "filename": "Daily-Standup",
                "fullNoteId": "x-coredata://ABC123/ICNote/p1",
                "exportCount": 2,
                "firstExported": "Friday, 1 May 2026 at 18:00:00",
                "lastExported": "Friday, 1 May 2026 at 19:00:00"
            },
            "2": {
                "created": "Wednesday, 17 January 2024 at 14:45:00",
                "modified": "Wednesday, 17 January 2024 at 15:20:00",
                "filename": "Project-Roadmap",
                "fullNoteId": "x-coredata://DEF456/ICNote/p2",
                "exportCount": 1,
                "firstExported": "Friday, 1 May 2026 at 18:30:00",
                "lastExported": "Friday, 1 May 2026 at 18:30:00"
            }
        }

        result = load_apple_notes_metadata(export_data)

        assert len(result) == 2
        assert result["1"]["note_id"] == "1"
        assert result["1"]["created_date_only"] == "2024-01-15"
        assert result["2"]["note_id"] == "2"
        assert result["2"]["modified_date_only"] == "2024-01-17"

    def test_message_format_for_nats(self):
        """Test creating NATS message format."""
        entry = {
            "created": "Tuesday, 21 March 2023 at 16:05:27",
            "modified": "Monday, 27 March 2023 at 14:39:28",
            "filename": "Todo-23-3-98",
            "fullNoteId": "x-coredata://DD12312-0000-0000-0000-A301023912313/ICNote/p98",
            "exportCount": 1
        }

        parsed = parse_apple_notes_metadata(entry)

        # Build NATS message format
        message = {
            "source": "apple-notes-metadata",
            "note_id": parsed["note_id"],
            "created": parsed["created"],
            "created_date": parsed["created_date_only"],
            "modified": parsed["modified"],
            "filename": parsed["filename"]
        }

        assert message["note_id"] == "98"
        assert message["created"] == "2023-03-21 16:05:27"
        assert message["created_date"] == "2023-03-21"
        assert message["modified"] == "2023-03-27 14:39:28"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
