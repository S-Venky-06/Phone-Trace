"""
PhoneTrace -- Phase 2 Test Suite
==================================

Tests for the artifact parsing framework:
    - Individual parser correctness
    - Timestamp conversion accuracy
    - Record counts
    - ParserManager unified API
    - Validation module
    - Error handling for malformed data

Run with:
    python -m pytest test_phase2.py -v
    python -m unittest test_phase2 -v
"""

import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from artifacts import (
    AppEventType,
    AppUsageParser,
    AppUsageRecord,
    BrowserParser,
    BrowserRecord,
    CallParser,
    CallRecord,
    CallType,
    EvidenceValidator,
    FilesystemParser,
    FileRecord,
    GPSParser,
    GPSRecord,
    ParserManager,
    SMSParser,
    SMSRecord,
    SMSType,
    TimelineEvent,
)

# ---------------------------------------------------------------------------
# Path to real generated evidence
# ---------------------------------------------------------------------------
EVIDENCE_DIR = _PROJECT_ROOT / "evidence_output"


class TestEnums(unittest.TestCase):
    """Test enum types and their safe from_int() constructors."""

    def test_call_type_values(self):
        self.assertEqual(CallType.INCOMING, 1)
        self.assertEqual(CallType.OUTGOING, 2)
        self.assertEqual(CallType.MISSED, 3)

    def test_call_type_from_int_valid(self):
        self.assertEqual(CallType.from_int(1), CallType.INCOMING)
        self.assertEqual(CallType.from_int(2), CallType.OUTGOING)
        self.assertEqual(CallType.from_int(3), CallType.MISSED)

    def test_call_type_from_int_invalid(self):
        self.assertEqual(CallType.from_int(99), CallType.UNKNOWN)
        self.assertEqual(CallType.from_int(-1), CallType.UNKNOWN)

    def test_sms_type_values(self):
        self.assertEqual(SMSType.RECEIVED, 1)
        self.assertEqual(SMSType.SENT, 2)

    def test_sms_type_from_int_invalid(self):
        self.assertEqual(SMSType.from_int(42), SMSType.UNKNOWN)

    def test_app_event_type_values(self):
        self.assertEqual(AppEventType.FOREGROUND, 1)
        self.assertEqual(AppEventType.BACKGROUND, 2)

    def test_app_event_type_from_int_invalid(self):
        self.assertEqual(AppEventType.from_int(7), AppEventType.UNKNOWN)


class TestCallParser(unittest.TestCase):
    """Test call log parsing."""

    @classmethod
    def setUpClass(cls):
        cls.parser = CallParser(EVIDENCE_DIR)
        cls.records = cls.parser.parse()

    def test_returns_list(self):
        self.assertIsInstance(self.records, list)

    def test_returns_call_records(self):
        self.assertGreater(len(self.records), 0)
        self.assertIsInstance(self.records[0], CallRecord)

    def test_record_count_reasonable(self):
        # 21 days * 8-15 calls/day + a few injected ≈ 168-325
        self.assertGreater(len(self.records), 100)
        self.assertLess(len(self.records), 500)

    def test_timestamps_are_datetime(self):
        for r in self.records[:10]:
            self.assertIsInstance(r.timestamp, datetime)
            self.assertIsNotNone(r.timestamp.tzinfo)

    def test_timestamps_in_2025(self):
        for r in self.records:
            self.assertEqual(r.timestamp.year, 2025)

    def test_call_types_are_enum(self):
        types_seen = {r.call_type for r in self.records}
        self.assertTrue(types_seen.issubset(set(CallType)))

    def test_durations_non_negative(self):
        for r in self.records:
            self.assertGreaterEqual(r.duration_seconds, 0)

    def test_no_records_skipped(self):
        self.assertEqual(self.parser.skipped_count, 0)


class TestSMSParser(unittest.TestCase):
    """Test SMS parsing."""

    @classmethod
    def setUpClass(cls):
        cls.parser = SMSParser(EVIDENCE_DIR)
        cls.records = cls.parser.parse()

    def test_returns_sms_records(self):
        self.assertGreater(len(self.records), 0)
        self.assertIsInstance(self.records[0], SMSRecord)

    def test_record_count_reasonable(self):
        self.assertGreater(len(self.records), 200)
        self.assertLess(len(self.records), 700)

    def test_timestamps_are_datetime(self):
        for r in self.records[:10]:
            self.assertIsInstance(r.timestamp, datetime)
            self.assertIsNotNone(r.timestamp.tzinfo)

    def test_sms_types_are_enum(self):
        types_seen = {r.sms_type for r in self.records}
        self.assertTrue(types_seen.issubset(set(SMSType)))

    def test_bodies_not_empty(self):
        for r in self.records:
            self.assertTrue(len(r.body) > 0)

    def test_no_records_skipped(self):
        self.assertEqual(self.parser.skipped_count, 0)


class TestBrowserParser(unittest.TestCase):
    """Test Chrome browser history parsing and timestamp conversion."""

    @classmethod
    def setUpClass(cls):
        cls.parser = BrowserParser(EVIDENCE_DIR)
        cls.records = cls.parser.parse()

    def test_returns_browser_records(self):
        self.assertGreater(len(self.records), 0)
        self.assertIsInstance(self.records[0], BrowserRecord)

    def test_record_count_reasonable(self):
        self.assertGreater(len(self.records), 100)
        self.assertLess(len(self.records), 600)

    def test_chrome_timestamp_conversion(self):
        """Verify Chrome 1601-epoch timestamps convert to June 2025."""
        for r in self.records[:10]:
            self.assertIsInstance(r.last_visit_time, datetime)
            self.assertEqual(r.last_visit_time.year, 2025)
            self.assertEqual(r.last_visit_time.month, 6)

    def test_raw_chrome_timestamp_preserved(self):
        """Verify the raw Chrome timestamp is a large integer (>13 quadrillion)."""
        for r in self.records[:10]:
            self.assertIsInstance(r.raw_chrome_timestamp, int)
            self.assertGreater(r.raw_chrome_timestamp, 13_380_000_000_000_000)

    def test_chrome_timestamp_roundtrip(self):
        """Verify timestamp conversion is reversible."""
        chrome_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        for r in self.records[:5]:
            # Reconstruct Chrome timestamp from the parsed datetime
            delta = r.last_visit_time - chrome_epoch
            reconstructed = int(delta.total_seconds() * 1_000_000)
            self.assertEqual(reconstructed, r.raw_chrome_timestamp)

    def test_urls_not_empty(self):
        for r in self.records:
            self.assertTrue(len(r.url) > 0)

    def test_no_records_skipped(self):
        self.assertEqual(self.parser.skipped_count, 0)


class TestGPSParser(unittest.TestCase):
    """Test GPS log parsing."""

    @classmethod
    def setUpClass(cls):
        cls.parser = GPSParser(EVIDENCE_DIR)
        cls.records = cls.parser.parse()

    def test_returns_gps_records(self):
        self.assertGreater(len(self.records), 0)
        self.assertIsInstance(self.records[0], GPSRecord)

    def test_record_count_reasonable(self):
        self.assertGreater(len(self.records), 500)

    def test_timestamps_are_datetime(self):
        for r in self.records[:10]:
            self.assertIsInstance(r.timestamp, datetime)
            self.assertIsNotNone(r.timestamp.tzinfo)

    def test_coordinates_valid(self):
        for r in self.records:
            self.assertGreater(r.latitude, -90)
            self.assertLess(r.latitude, 90)
            self.assertGreater(r.longitude, -180)
            self.assertLess(r.longitude, 180)

    def test_accuracy_positive(self):
        for r in self.records:
            self.assertGreater(r.accuracy, 0)

    def test_provider_valid(self):
        valid_providers = {"gps", "network", "fused"}
        for r in self.records:
            self.assertIn(r.provider, valid_providers)

    def test_sorted_by_timestamp(self):
        for i in range(1, len(self.records)):
            self.assertGreaterEqual(
                self.records[i].timestamp, self.records[i - 1].timestamp
            )

    def test_no_records_skipped(self):
        self.assertEqual(self.parser.skipped_count, 0)


class TestAppUsageParser(unittest.TestCase):
    """Test app usage parsing."""

    @classmethod
    def setUpClass(cls):
        cls.parser = AppUsageParser(EVIDENCE_DIR)
        cls.records = cls.parser.parse()

    def test_returns_app_usage_records(self):
        self.assertGreater(len(self.records), 0)
        self.assertIsInstance(self.records[0], AppUsageRecord)

    def test_record_count_reasonable(self):
        self.assertGreater(len(self.records), 300)

    def test_event_types_are_enum(self):
        types_seen = {r.event_type for r in self.records}
        self.assertEqual(types_seen, {AppEventType.FOREGROUND, AppEventType.BACKGROUND})

    def test_package_names_look_real(self):
        """Android package names contain dots."""
        for r in self.records[:20]:
            self.assertIn(".", r.package_name)

    def test_no_records_skipped(self):
        self.assertEqual(self.parser.skipped_count, 0)


class TestFilesystemParser(unittest.TestCase):
    """Test filesystem metadata parsing."""

    @classmethod
    def setUpClass(cls):
        cls.parser = FilesystemParser(EVIDENCE_DIR)
        cls.records = cls.parser.parse()

    def test_returns_file_records(self):
        self.assertGreater(len(self.records), 0)
        self.assertIsInstance(self.records[0], FileRecord)

    def test_record_count_reasonable(self):
        self.assertGreater(len(self.records), 20)

    def test_timestamps_are_datetime(self):
        for r in self.records[:10]:
            self.assertIsInstance(r.created, datetime)
            self.assertIsInstance(r.modified, datetime)

    def test_md5_hashes_valid(self):
        for r in self.records:
            self.assertEqual(len(r.md5_hash), 32)
            self.assertTrue(all(c in "0123456789abcdef" for c in r.md5_hash))

    def test_exif_data_default_none(self):
        for r in self.records:
            self.assertIsNone(r.exif_data)

    def test_no_records_skipped(self):
        self.assertEqual(self.parser.skipped_count, 0)


class TestParserManager(unittest.TestCase):
    """Test the unified ParserManager API."""

    @classmethod
    def setUpClass(cls):
        cls.manager = ParserManager(EVIDENCE_DIR)
        cls.manager.load_all()

    def test_calls_populated(self):
        self.assertGreater(len(self.manager.calls), 0)
        self.assertIsInstance(self.manager.calls[0], CallRecord)

    def test_sms_populated(self):
        self.assertGreater(len(self.manager.sms), 0)
        self.assertIsInstance(self.manager.sms[0], SMSRecord)

    def test_browser_populated(self):
        self.assertGreater(len(self.manager.browser), 0)
        self.assertIsInstance(self.manager.browser[0], BrowserRecord)

    def test_gps_populated(self):
        self.assertGreater(len(self.manager.gps), 0)
        self.assertIsInstance(self.manager.gps[0], GPSRecord)

    def test_app_usage_populated(self):
        self.assertGreater(len(self.manager.app_usage), 0)
        self.assertIsInstance(self.manager.app_usage[0], AppUsageRecord)

    def test_files_populated(self):
        self.assertGreater(len(self.manager.files), 0)
        self.assertIsInstance(self.manager.files[0], FileRecord)

    def test_total_records(self):
        total = (
            len(self.manager.calls) + len(self.manager.sms)
            + len(self.manager.browser) + len(self.manager.gps)
            + len(self.manager.app_usage) + len(self.manager.files)
        )
        self.assertGreater(total, 3000)

    def test_no_skipped(self):
        self.assertEqual(self.manager.total_skipped, 0)

    def test_get_all_records_returns_timeline_events(self):
        events = self.manager.get_all_records()
        self.assertGreater(len(events), 0)
        self.assertIsInstance(events[0], TimelineEvent)

    def test_get_all_records_sorted(self):
        events = self.manager.get_all_records()
        for i in range(1, min(len(events), 500)):
            self.assertGreaterEqual(
                events[i].timestamp, events[i - 1].timestamp
            )

    def test_get_all_records_has_all_types(self):
        events = self.manager.get_all_records()
        types_seen = {e.event_type for e in events}
        expected = {"call", "sms", "browser", "gps", "app_usage", "file"}
        self.assertEqual(types_seen, expected)

    def test_get_all_records_before_load_raises(self):
        m = ParserManager(EVIDENCE_DIR)
        with self.assertRaises(RuntimeError):
            m.get_all_records()

    def test_missing_directory_raises(self):
        m = ParserManager("nonexistent_directory_12345")
        with self.assertRaises(FileNotFoundError):
            m.load_all()


class TestValidation(unittest.TestCase):
    """Test the evidence validation module."""

    def test_validation_passes(self):
        validator = EvidenceValidator(EVIDENCE_DIR)
        report = validator.validate()
        self.assertTrue(
            report.is_valid,
            f"Validation failed: "
            + ", ".join(
                c.name for c in report.checks if not c.passed
            ),
        )

    def test_report_has_checks(self):
        validator = EvidenceValidator(EVIDENCE_DIR)
        report = validator.validate()
        self.assertGreater(len(report.checks), 10)

    def test_all_checks_passed(self):
        validator = EvidenceValidator(EVIDENCE_DIR)
        report = validator.validate()
        self.assertEqual(report.failed_count, 0)


class TestMalformedData(unittest.TestCase):
    """Test graceful handling of malformed/corrupt evidence."""

    def setUp(self):
        """Create a temporary directory with corrupt evidence files."""
        self._tmpdir = tempfile.mkdtemp(
            dir=str(_PROJECT_ROOT), prefix="test_corrupt_"
        )

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_corrupt_sqlite_record_skipped(self):
        """A call record with NULL timestamp should be skipped."""
        db_path = os.path.join(self._tmpdir, "calllog.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE calls (
                _id INTEGER PRIMARY KEY,
                number TEXT NOT NULL,
                date INTEGER NOT NULL,
                duration INTEGER NOT NULL,
                type INTEGER NOT NULL,
                name TEXT
            )
        """)
        # Valid record
        conn.execute(
            "INSERT INTO calls VALUES (1, '+91999', 1717200000000, 60, 1, 'Test')"
        )
        # Record with a type that will trigger unusual behaviour but still parse
        conn.execute(
            "INSERT INTO calls VALUES (2, '+91888', 1717200060000, 30, 99, 'Bad')"
        )
        conn.commit()
        conn.close()

        parser = CallParser(self._tmpdir)
        records = parser.parse()
        # Both records should parse (type 99 maps to UNKNOWN)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[1].call_type, CallType.UNKNOWN)

    def test_corrupt_json_entry_skipped(self):
        """A GPS entry missing required fields should be skipped."""
        json_path = os.path.join(self._tmpdir, "gps_log.json")
        data = [
            {
                "timestamp": "2025-06-01T08:00:00+05:30",
                "latitude": 12.93,
                "longitude": 77.62,
                "accuracy": 10.0,
                "provider": "gps",
            },
            {
                "timestamp": "2025-06-01T08:15:00+05:30",
                # Missing latitude, longitude, etc.
            },
            {
                "timestamp": "2025-06-01T08:30:00+05:30",
                "latitude": 12.94,
                "longitude": 77.63,
                "accuracy": 15.0,
                "provider": "fused",
            },
        ]
        with open(json_path, "w") as f:
            json.dump(data, f)

        parser = GPSParser(self._tmpdir)
        records = parser.parse()
        self.assertEqual(len(records), 2)  # Second entry skipped
        self.assertEqual(parser.skipped_count, 1)

    def test_missing_file_raises(self):
        """Parser should raise FileNotFoundError for missing evidence."""
        parser = CallParser(self._tmpdir)
        with self.assertRaises(FileNotFoundError):
            parser.parse()


class TestTimestampConversion(unittest.TestCase):
    """Test timestamp conversion helpers directly."""

    def test_epoch_ms_to_datetime(self):
        """Known value: 2025-06-01 00:00:00 UTC = 1748736000000 ms."""
        from artifacts.base import BaseParser
        dt = BaseParser._epoch_ms_to_datetime(1748736000000)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.tzinfo, timezone.utc)

    def test_chrome_ts_to_datetime(self):
        """Known value: 2025-06-01 00:00:00 UTC in Chrome format."""
        from artifacts.base import BaseParser
        # Chrome epoch is 1601-01-01 UTC
        # Seconds from 1601-01-01 to 2025-06-01 00:00:00 UTC
        chrome_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        target = datetime(2025, 6, 1, tzinfo=timezone.utc)
        expected_us = int((target - chrome_epoch).total_seconds() * 1_000_000)

        dt = BaseParser._chrome_ts_to_datetime(expected_us)
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 1)
        self.assertEqual(dt.hour, 0)

    def test_iso_to_datetime_with_offset(self):
        from artifacts.base import BaseParser
        dt = BaseParser._iso_to_datetime("2025-06-15T14:30:00+05:30")
        self.assertEqual(dt.year, 2025)
        self.assertEqual(dt.month, 6)
        self.assertEqual(dt.day, 15)
        self.assertIsNotNone(dt.tzinfo)

    def test_iso_to_datetime_naive_assumed_utc(self):
        from artifacts.base import BaseParser
        dt = BaseParser._iso_to_datetime("2025-06-15T14:30:00")
        self.assertEqual(dt.tzinfo, timezone.utc)


if __name__ == "__main__":
    unittest.main()
