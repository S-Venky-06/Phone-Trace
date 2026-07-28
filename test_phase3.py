"""
PhoneTrace -- Phase 3 Test Suite
==================================

Tests for the timeline reconstruction and evidence correlation engine:
    - EventFactory converter registry
    - TimelineBuilder sorting and session grouping
    - EvidenceCorrelator rule detection
    - TimelineFilter and search
    - TimelineStatistics
    - TimelineExporter (JSON and CSV)
    - Error resilience

Run with:
    python -m unittest test_phase3 -v
"""

import csv
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from artifacts import ParserManager
from artifacts.models import (
    AppEventType,
    AppUsageRecord,
    BrowserRecord,
    CallRecord,
    CallType,
    FileRecord,
    GPSRecord,
    SMSRecord,
    SMSType,
)
from timeline import (
    CorrelationConfig,
    EvidenceCorrelator,
    EventFactory,
    EventLocation,
    ForensicEvent,
    InvestigationSession,
    StatisticsReport,
    TimelineBuilder,
    TimelineExporter,
    TimelineFilter,
    TimelineStatistics,
)

# ---------------------------------------------------------------------------
# Load real evidence once for integration tests
# ---------------------------------------------------------------------------
EVIDENCE_DIR = _PROJECT_ROOT / "evidence_output"

_pm = ParserManager(EVIDENCE_DIR)
_pm.load_all()

_builder = TimelineBuilder(_pm)
_events = _builder.build()
_sessions = _builder.sessions

_correlator = EvidenceCorrelator()
_groups = _correlator.correlate(_events)


# ===================================================================
# EventFactory Tests
# ===================================================================

class TestEventFactory(unittest.TestCase):
    """Test the registry-based event factory."""

    def setUp(self):
        self.factory = EventFactory()

    def test_default_types_registered(self):
        names = self.factory.supported_types
        expected = {
            "CallRecord", "SMSRecord", "BrowserRecord",
            "GPSRecord", "AppUsageRecord", "FileRecord",
        }
        self.assertEqual(set(names), expected)

    def test_convert_call(self):
        record = CallRecord(
            id=1, number="+91999",
            timestamp=datetime(2025, 6, 10, 14, 0, tzinfo=timezone.utc),
            duration_seconds=60, call_type=CallType.OUTGOING,
            contact_name="Alice",
        )
        event = self.factory.convert(record)
        self.assertIsInstance(event, ForensicEvent)
        self.assertEqual(event.artifact_type, "call")
        self.assertEqual(event.title, "Outgoing Call")
        self.assertIn("Alice", event.description)
        self.assertEqual(event.metadata["duration_seconds"], 60)

    def test_convert_sms(self):
        record = SMSRecord(
            id=1, address="+91888",
            timestamp=datetime(2025, 6, 10, 14, 5, tzinfo=timezone.utc),
            body="Hello world", sms_type=SMSType.RECEIVED,
        )
        event = self.factory.convert(record)
        self.assertIsInstance(event, ForensicEvent)
        self.assertEqual(event.artifact_type, "sms")
        self.assertEqual(event.title, "SMS Received")
        self.assertEqual(event.metadata["body"], "Hello world")

    def test_convert_browser(self):
        record = BrowserRecord(
            id=1, url="https://example.com", title="Example",
            visit_count=3,
            last_visit_time=datetime(2025, 6, 10, 15, 0, tzinfo=timezone.utc),
            raw_chrome_timestamp=13400000000000000,
        )
        event = self.factory.convert(record)
        self.assertIsInstance(event, ForensicEvent)
        self.assertEqual(event.artifact_type, "browser")
        self.assertEqual(event.metadata["url"], "https://example.com")

    def test_convert_gps_has_location(self):
        record = GPSRecord(
            id=1,
            timestamp=datetime(2025, 6, 10, 12, 0, tzinfo=timezone.utc),
            latitude=12.93, longitude=77.62,
            accuracy=15.0, provider="gps",
        )
        event = self.factory.convert(record)
        self.assertIsNotNone(event.location)
        self.assertAlmostEqual(event.location.latitude, 12.93)

    def test_convert_app_usage(self):
        record = AppUsageRecord(
            id=1, package_name="com.whatsapp",
            event_type=AppEventType.FOREGROUND,
            timestamp=datetime(2025, 6, 10, 10, 0, tzinfo=timezone.utc),
        )
        event = self.factory.convert(record)
        self.assertEqual(event.artifact_type, "app_usage")
        self.assertEqual(event.title, "App Opened")

    def test_convert_file(self):
        record = FileRecord(
            id=1, filename="photo.jpg", path="/sdcard/DCIM/photo.jpg",
            size_bytes=5000000,
            created=datetime(2025, 6, 10, 16, 0, tzinfo=timezone.utc),
            modified=datetime(2025, 6, 10, 16, 0, tzinfo=timezone.utc),
            mime_type="image/jpeg", md5_hash="a" * 32,
        )
        event = self.factory.convert(record)
        self.assertEqual(event.artifact_type, "file")
        self.assertEqual(event.metadata["filename"], "photo.jpg")

    def test_convert_all(self):
        records = _pm.calls[:5]
        events = self.factory.convert_all(records)
        self.assertEqual(len(events), 5)
        self.assertTrue(all(isinstance(e, ForensicEvent) for e in events))

    def test_custom_registration(self):
        class FakeRecord:
            pass

        def fake_converter(record, idx):
            return ForensicEvent(
                timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
                artifact_type="fake", title="Fake",
                description="test", source="test.db",
            )

        self.factory.register(FakeRecord, fake_converter)
        self.assertIn("FakeRecord", self.factory.supported_types)
        event = self.factory.convert(FakeRecord())
        self.assertEqual(event.artifact_type, "fake")

    def test_unknown_type_returns_none(self):
        result = self.factory.convert("not a record")
        self.assertIsNone(result)


# ===================================================================
# TimelineBuilder Tests
# ===================================================================

class TestTimelineBuilder(unittest.TestCase):
    """Test the timeline builder."""

    def test_events_populated(self):
        self.assertGreater(len(_events), 3000)

    def test_events_are_forensic_events(self):
        self.assertTrue(all(isinstance(e, ForensicEvent) for e in _events))

    def test_events_sorted_chronologically(self):
        for i in range(1, min(len(_events), 500)):
            self.assertGreaterEqual(
                _events[i].timestamp, _events[i - 1].timestamp
            )

    def test_all_artifact_types_present(self):
        types = {e.artifact_type for e in _events}
        expected = {"call", "sms", "browser", "gps", "app_usage", "file"}
        self.assertEqual(types, expected)

    def test_sessions_created(self):
        self.assertGreater(len(_sessions), 0)

    def test_sessions_are_investigation_sessions(self):
        self.assertTrue(
            all(isinstance(s, InvestigationSession) for s in _sessions)
        )

    def test_sessions_have_events(self):
        for session in _sessions:
            self.assertGreater(session.event_count, 0)

    def test_sessions_cover_all_events(self):
        total = sum(s.event_count for s in _sessions)
        self.assertEqual(total, len(_events))

    def test_session_ids_sequential(self):
        ids = [s.session_id for s in _sessions]
        self.assertEqual(ids, list(range(1, len(_sessions) + 1)))

    def test_session_properties(self):
        s = _sessions[0]
        self.assertGreaterEqual(s.duration_seconds, 0)
        self.assertIsInstance(s.artifact_types, set)

    def test_build_required_before_access(self):
        fresh = TimelineBuilder(_pm)
        with self.assertRaises(RuntimeError):
            _ = fresh.events


# ===================================================================
# EvidenceCorrelator Tests
# ===================================================================

class TestEvidenceCorrelator(unittest.TestCase):
    """Test the evidence correlation engine."""

    def test_groups_detected(self):
        self.assertGreater(len(_groups), 0)

    def test_groups_have_rule_names(self):
        for g in _groups:
            self.assertTrue(len(g.rule_name) > 0)

    def test_groups_have_anchor(self):
        for g in _groups:
            self.assertIsInstance(g.anchor_event, ForensicEvent)

    def test_communication_clusters_found(self):
        comm_groups = [g for g in _groups if g.rule_name == "communication_cluster"]
        self.assertGreater(len(comm_groups), 0)

    def test_related_events_populated(self):
        """At least some events should have related events."""
        events_with_related = [e for e in _events if e.related]
        self.assertGreater(len(events_with_related), 0)

    def test_default_rules_registered(self):
        c = EvidenceCorrelator()
        self.assertEqual(len(c.rule_names), 7)

    def test_custom_rule_registration(self):
        c = EvidenceCorrelator()

        def dummy_rule(events, config):
            return []

        c.add_rule("Dummy Rule", dummy_rule)
        self.assertEqual(len(c.rule_names), 8)
        self.assertIn("Dummy Rule", c.rule_names)


# ===================================================================
# TimelineFilter Tests
# ===================================================================

class TestTimelineFilter(unittest.TestCase):
    """Test timeline filters and search."""

    def test_by_artifact(self):
        calls = TimelineFilter.by_artifact(_events, "call")
        self.assertGreater(len(calls), 0)
        self.assertTrue(all(e.artifact_type == "call" for e in calls))

    def test_by_artifact_gps(self):
        gps = TimelineFilter.by_artifact(_events, "gps")
        self.assertGreater(len(gps), 1000)

    def test_by_date(self):
        start = datetime(2025, 6, 10, tzinfo=timezone.utc)
        end = datetime(2025, 6, 11, tzinfo=timezone.utc)
        filtered = TimelineFilter.by_date(_events, start, end)
        self.assertGreater(len(filtered), 0)
        for e in filtered:
            self.assertGreaterEqual(e.timestamp, start)
            self.assertLessEqual(e.timestamp, end)

    def test_by_contact(self):
        # Filter by a known contact number
        filtered = TimelineFilter.by_contact(_events, "+919876501001")
        self.assertGreater(len(filtered), 0)

    def test_by_contact_name(self):
        filtered = TimelineFilter.by_contact(_events, "Priya")
        self.assertGreater(len(filtered), 0)

    def test_by_keyword(self):
        filtered = TimelineFilter.by_keyword(_events, "Outgoing")
        self.assertGreater(len(filtered), 0)

    def test_by_package(self):
        filtered = TimelineFilter.by_package(_events, "whatsapp")
        self.assertGreater(len(filtered), 0)

    def test_by_file_type(self):
        filtered = TimelineFilter.by_file_type(_events, "image/")
        self.assertGreater(len(filtered), 0)

    def test_by_location(self):
        # Search near home coordinates
        filtered = TimelineFilter.by_location(
            _events, 12.9352, 77.6245, radius_km=1.0
        )
        self.assertGreater(len(filtered), 0)

    def test_search_url(self):
        filtered = TimelineFilter.search(_events, "youtube")
        self.assertGreater(len(filtered), 0)

    def test_search_phone_number(self):
        filtered = TimelineFilter.search(_events, "+919876501002")
        self.assertGreater(len(filtered), 0)

    def test_search_no_results(self):
        filtered = TimelineFilter.search(_events, "xyznonexistent12345")
        self.assertEqual(len(filtered), 0)

    def test_filters_composable(self):
        calls = TimelineFilter.by_artifact(_events, "call")
        outgoing = TimelineFilter.by_keyword(calls, "Outgoing")
        self.assertGreater(len(outgoing), 0)
        self.assertLessEqual(len(outgoing), len(calls))


# ===================================================================
# TimelineStatistics Tests
# ===================================================================

class TestTimelineStatistics(unittest.TestCase):
    """Test timeline statistics."""

    @classmethod
    def setUpClass(cls):
        cls.report = TimelineStatistics.generate(
            events=_events,
            sessions=_sessions,
            correlations=_groups,
        )

    def test_total_events(self):
        self.assertEqual(self.report.total_events, len(_events))

    def test_counts_by_type(self):
        self.assertIn("call", self.report.counts_by_type)
        self.assertIn("gps", self.report.counts_by_type)
        self.assertIn("sms", self.report.counts_by_type)

    def test_busiest_hour_valid(self):
        self.assertGreaterEqual(self.report.busiest_hour, 0)
        self.assertLessEqual(self.report.busiest_hour, 23)

    def test_busiest_day_exists(self):
        self.assertIsNotNone(self.report.busiest_day)

    def test_session_count(self):
        self.assertEqual(self.report.session_count, len(_sessions))

    def test_correlation_count(self):
        self.assertEqual(self.report.correlation_count, len(_groups))

    def test_time_range(self):
        self.assertIsNotNone(self.report.time_range)
        start, end = self.report.time_range
        self.assertLess(start, end)

    def test_communication_frequency(self):
        self.assertGreater(len(self.report.communication_frequency), 0)

    def test_unknown_contacts_reasonable(self):
        # Should be a small number (only burner number calls)
        self.assertGreater(self.report.unknown_contacts, 0)
        self.assertLess(self.report.unknown_contacts, 50)

    def test_incident_window(self):
        from case_config import INCIDENT_START, INCIDENT_END
        report = TimelineStatistics.generate(
            _events, _sessions, _groups,
            incident_start=INCIDENT_START,
            incident_end=INCIDENT_END,
        )
        self.assertGreater(report.incident_events, 0)


# ===================================================================
# TimelineExporter Tests
# ===================================================================

class TestTimelineExporter(unittest.TestCase):
    """Test JSON and CSV export."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(
            dir=str(_PROJECT_ROOT), prefix="test_export_"
        )

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_json_export(self):
        path = TimelineExporter.to_json(
            _events[:50],
            os.path.join(self._tmpdir, "timeline.json"),
        )
        self.assertTrue(path.is_file())

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data), 50)
        self.assertIn("timestamp", data[0])
        self.assertIn("artifact_type", data[0])

    def test_csv_export(self):
        path = TimelineExporter.to_csv(
            _events[:50],
            os.path.join(self._tmpdir, "timeline.csv"),
        )
        self.assertTrue(path.is_file())

        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), 50)
        self.assertIn("timestamp", rows[0])
        self.assertIn("artifact_type", rows[0])

    def test_json_roundtrip_timestamps(self):
        path = TimelineExporter.to_json(
            _events[:5],
            os.path.join(self._tmpdir, "ts_test.json"),
        )
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Timestamps should be ISO 8601 strings
        ts = data[0]["timestamp"]
        dt = datetime.fromisoformat(ts)
        self.assertIsNotNone(dt.tzinfo)

    def test_json_location_present(self):
        gps_events = [e for e in _events if e.artifact_type == "gps"][:5]
        path = TimelineExporter.to_json(
            gps_events,
            os.path.join(self._tmpdir, "gps.json"),
        )
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsNotNone(data[0]["location"])
        self.assertIn("latitude", data[0]["location"])

    def test_csv_gps_columns(self):
        gps_events = [e for e in _events if e.artifact_type == "gps"][:5]
        path = TimelineExporter.to_csv(
            gps_events,
            os.path.join(self._tmpdir, "gps.csv"),
        )
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader)
        self.assertNotEqual(row["latitude"], "")
        self.assertNotEqual(row["longitude"], "")


# ===================================================================
# ForensicEvent Model Tests
# ===================================================================

class TestForensicEventModel(unittest.TestCase):
    """Test ForensicEvent dataclass."""

    def test_location_optional(self):
        event = ForensicEvent(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            artifact_type="call", title="Test",
            description="test", source="test.db",
        )
        self.assertIsNone(event.location)
        self.assertEqual(event.related, [])
        self.assertEqual(event.metadata, {})

    def test_location_attached(self):
        loc = EventLocation(latitude=12.93, longitude=77.62)
        event = ForensicEvent(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            artifact_type="gps", title="GPS",
            description="test", source="gps.json",
            location=loc,
        )
        self.assertIsNotNone(event.location)
        self.assertAlmostEqual(event.location.latitude, 12.93)

    def test_related_mutable(self):
        e1 = ForensicEvent(
            timestamp=datetime(2025, 6, 1, tzinfo=timezone.utc),
            artifact_type="call", title="Call",
            description="test", source="test.db",
        )
        e2 = ForensicEvent(
            timestamp=datetime(2025, 6, 1, 0, 5, tzinfo=timezone.utc),
            artifact_type="sms", title="SMS",
            description="test", source="test.db",
        )
        e1.related.append(e2)
        self.assertEqual(len(e1.related), 1)


# ===================================================================
# InvestigationSession Tests
# ===================================================================

class TestInvestigationSession(unittest.TestCase):
    """Test investigation session model."""

    def test_session_properties(self):
        events = [
            ForensicEvent(
                timestamp=datetime(2025, 6, 1, 10, i, tzinfo=timezone.utc),
                artifact_type="call" if i % 2 == 0 else "sms",
                title="E", description="d", source="s",
            )
            for i in range(5)
        ]
        session = InvestigationSession(
            session_id=1,
            start_time=events[0].timestamp,
            end_time=events[-1].timestamp,
            events=events,
        )
        self.assertEqual(session.event_count, 5)
        self.assertEqual(session.duration_seconds, 240.0)
        self.assertEqual(session.artifact_types, {"call", "sms"})


if __name__ == "__main__":
    unittest.main()
