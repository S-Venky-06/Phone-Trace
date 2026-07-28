"""
PhoneTrace -- Phase 5 AI Assistant Test Suite
================================================

Tests for the AI engine, context builder, providers, and report generator.
Run with:
    python -m unittest test_phase5 -v
"""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from ai_engine import (
    AIAssistant,
    ContextBuilder,
    RuleBasedProvider,
    InvestigationContext,
    AIQuery,
    AIResponse,
    ReportGenerator,
    InvestigationReport,
)
from ai_engine.models import QueryType, SectionType
from ai_engine.providers.gemini_provider import GeminiProvider
from ai_engine.providers.openai_provider import OpenAIProvider
from ai_engine.providers.ollama_provider import OllamaProvider
from timeline import ForensicEvent, EventLocation, StatisticsReport
from case_config import IST, INCIDENT_START, INCIDENT_END


class TestContextBuilder(unittest.TestCase):
    """Verify ContextBuilder builds correct InvestigationContext payloads."""

    def setUp(self):
        self.builder = ContextBuilder(token_budget=1000)

        # Create basic test events
        self.events = [
            # Event inside incident window
            ForensicEvent(
                timestamp=INCIDENT_START + timedelta(minutes=10),
                artifact_type="gps",
                title="GPS Ping",
                description="Located at incident scene",
                source="gps.db",
                location=EventLocation(12.8458, 77.6692, label="Electronic City"),
                metadata={"latitude": "12.8458", "longitude": "77.6692"},
            ),
            # Call event inside incident window
            ForensicEvent(
                timestamp=INCIDENT_START + timedelta(minutes=15),
                artifact_type="call",
                title="Incoming Call",
                description="Call from unknown contact",
                source="calllog.db",
                metadata={
                    "number": "+919000000001",
                    "call_type": "incoming",
                    "duration_seconds": 60,
                },
            ),
            # Event outside incident window
            ForensicEvent(
                timestamp=INCIDENT_START - timedelta(days=2),
                artifact_type="browser",
                title="Browser Visit",
                description="Visited google.com",
                source="chrome_history",
                metadata={"url": "https://www.google.com"},
            ),
        ]
        self.events.sort(key=lambda e: e.timestamp)

        self.sessions = []
        self.correlations = []
        self.stats = StatisticsReport(
            total_events=len(self.events),
            counts_by_type={"gps": 1, "call": 1, "browser": 1},
            unknown_contacts=1,
            communication_frequency={"+919000000001": 1},
            busiest_hour=INCIDENT_START.hour,
            busiest_hour_count=2,
            busiest_day=INCIDENT_START.date(),
            busiest_day_count=2,
            session_count=1,
            correlation_count=0,
            time_range=(self.events[0].timestamp, self.events[-1].timestamp),
            incident_events=2,
        )

    def test_full_context_generation(self):
        ctx = self.builder.build_full_context(
            self.events, self.sessions, self.correlations, self.stats
        )
        self.assertIsNotNone(ctx)
        self.assertEqual(ctx.suspect_name, "Arjun Mehta")
        self.assertEqual(ctx.device_info, "Samsung Galaxy S23")
        self.assertEqual(len(ctx.incident_events), 2)
        self.assertEqual(ctx.artifact_counts["gps"], 1)
        self.assertEqual(ctx.statistics.total_events, 3)
        self.assertEqual(ctx.communication.unknown_contact_count, 1)

    def test_incident_context_generation(self):
        ctx = self.builder.build_incident_context(
            self.events, self.sessions, self.correlations, self.stats
        )
        self.assertEqual(len(ctx.all_events_summary), 0)
        self.assertEqual(len(ctx.incident_events), 2)

    def test_token_budget_sampling(self):
        # Set a tiny budget to force sampling/truncation
        small_builder = ContextBuilder(token_budget=100)
        ctx = small_builder.build_full_context(
            self.events, self.sessions, self.correlations, self.stats
        )
        # Verify the context generated is still valid
        self.assertIsNotNone(ctx)
        prompt_text = ctx.to_prompt_text()
        self.assertIn("INVESTIGATION CONTEXT", prompt_text)


class TestRuleBasedProvider(unittest.TestCase):
    """Verify alibi checks, anomaly checks, and narrative generation offline."""

    def setUp(self):
        self.provider = RuleBasedProvider()
        self.builder = ContextBuilder()

    def test_alibi_contradicted(self):
        # Event placing device at Electronic City (away from Koramangala home alibi)
        events = [
            ForensicEvent(
                timestamp=INCIDENT_START + timedelta(minutes=10),
                artifact_type="gps",
                title="GPS Ping",
                description="Near Electronic City",
                source="gps.db",
                location=EventLocation(12.8458, 77.6692, label="Electronic City"),
                metadata={"latitude": 12.8458, "longitude": 77.6692},
            )
        ]
        ctx = self.builder.build_full_context(events, [], [], StatisticsReport())
        response = self.provider.check_alibi(ctx, ctx.alibi_location, ctx.alibi_coords)
        self.assertFalse(response.is_error)
        self.assertIn("ALIBI CONTRADICTED", response.answer)
        self.assertEqual(response.provider_name, self.provider.name)

    def test_alibi_consistent(self):
        # Event placing device at Koramangala (within 1km of Home alibi)
        events = [
            ForensicEvent(
                timestamp=INCIDENT_START + timedelta(minutes=10),
                artifact_type="gps",
                title="GPS Ping",
                description="Home",
                source="gps.db",
                location=EventLocation(12.9352, 77.6245, label="Home — Koramangala"),
                metadata={"latitude": 12.9352, "longitude": 77.6245},
            )
        ]
        ctx = self.builder.build_full_context(events, [], [], StatisticsReport())
        response = self.provider.check_alibi(ctx, ctx.alibi_location, ctx.alibi_coords)
        self.assertIn("ALIBI CONSISTENT", response.answer)

    def test_alibi_insufficient_data(self):
        # No GPS events in incident window
        events = [
            ForensicEvent(
                timestamp=INCIDENT_START + timedelta(minutes=10),
                artifact_type="call",
                title="Call",
                description="Call without GPS",
                source="calls.db",
                metadata={},
            )
        ]
        ctx = self.builder.build_full_context(events, [], [], StatisticsReport())
        response = self.provider.check_alibi(ctx, ctx.alibi_location, ctx.alibi_coords)
        self.assertIn("INSUFFICIENT DATA", response.answer)

    def test_anomaly_detection_burner_contacts(self):
        # Stats indicating unknown contacts
        stats = StatisticsReport(unknown_contacts=2)
        ctx = self.builder.build_full_context([], [], [], stats)
        response = self.provider.detect_anomalies(ctx)
        self.assertIn("Unknown contacts detected", response.answer)

    def test_anomaly_detection_suspicious_apps(self):
        # App usage event for cleaner app inside incident window
        events = [
            ForensicEvent(
                timestamp=INCIDENT_START + timedelta(minutes=5),
                artifact_type="app_usage",
                title="Secure Cleaner",
                description="App opened",
                source="app_usage.db",
                metadata={"package_name": "com.piriform.ccleaner"},
            )
        ]
        ctx = self.builder.build_full_context(events, [], [], StatisticsReport())
        response = self.provider.detect_anomalies(ctx)
        self.assertIn("Suspicious app usage", response.answer)

    def test_narrative_generation(self):
        ctx = self.builder.build_full_context([], [], [], StatisticsReport())
        narrative = self.provider.generate_narrative(ctx)
        self.assertIsNotNone(narrative)
        self.assertIn("INVESTIGATION NARRATIVE", narrative)
        self.assertIn("Arjun Mehta", narrative)

    def test_general_qa(self):
        stats = StatisticsReport(
            communication_frequency={"+919876501001": 5}
        )
        ctx = self.builder.build_full_context([], [], [], stats)
        
        # Test who called query routing
        r_who = self.provider.analyze(ctx, AIQuery("Who called Arjun?"))
        self.assertIn("Top contacts", r_who.answer)

        # Test statistics query routing
        r_stats = self.provider.analyze(ctx, AIQuery("how many events?"))
        self.assertIn("Total events", r_stats.answer)


class TestAIAssistant(unittest.TestCase):
    """Verify AIAssistant orchestrates data and config switching correctly."""

    def test_provider_switching(self):
        assistant = AIAssistant()
        self.assertEqual(assistant.current_provider_name, "Rule-Based (Offline)")
        
        # Switch to Ollama
        assistant.set_provider("ollama", base_url="http://localhost:11434")
        self.assertEqual(assistant.current_provider_name, "Ollama")
        self.assertIsInstance(assistant.current_provider, OllamaProvider)

        # Switch to OpenAI
        assistant.set_provider("openai", api_key="sk-test-key")
        self.assertEqual(assistant.current_provider_name, "OpenAI")
        self.assertIsInstance(assistant.current_provider, OpenAIProvider)

        # Switch back to Rule-Based
        assistant.set_provider("rule_based")
        self.assertEqual(assistant.current_provider_name, "Rule-Based (Offline)")

    def test_empty_state_handling(self):
        assistant = AIAssistant(events=[])
        response = assistant.ask("Who is suspect?")
        self.assertIn("No evidence loaded", response.answer)

        response = assistant.check_alibi()
        self.assertTrue(response.is_error)

        report = assistant.generate_report()
        self.assertEqual(len(report.sections), 0)


class TestReportGenerator(unittest.TestCase):
    """Verify ReportGenerator outputs all expected investigation sections."""

    def setUp(self):
        self.provider = RuleBasedProvider()
        self.builder = ContextBuilder()
        self.generator = ReportGenerator(self.provider)

        events = [
            ForensicEvent(
                timestamp=INCIDENT_START + timedelta(minutes=10),
                artifact_type="gps",
                title="GPS Ping",
                description="Near Electronic City",
                source="gps.db",
                location=EventLocation(12.8458, 77.6692, label="Electronic City"),
                metadata={"latitude": 12.8458, "longitude": 77.6692},
            )
        ]
        self.ctx = self.builder.build_full_context(events, [], [], StatisticsReport())

    def test_report_sections(self):
        report = self.generator.generate(self.ctx)
        self.assertIsInstance(report, InvestigationReport)
        self.assertEqual(report.provider_name, self.provider.name)
        
        # Verify 10 distinct sections are present
        self.assertEqual(len(report.sections), 10)
        
        # Check section types
        expected_types = [
            SectionType.CASE_OVERVIEW,
            SectionType.TIMELINE_SUMMARY,
            SectionType.INCIDENT_ANALYSIS,
            SectionType.ALIBI_VERIFICATION,
            SectionType.COMMUNICATION_ANALYSIS,
            SectionType.MOVEMENT_ANALYSIS,
            SectionType.CORRELATION_FINDINGS,
            SectionType.ANOMALY_REPORT,
            SectionType.AI_NARRATIVE,
            SectionType.CONCLUSIONS,
        ]
        for i, section in enumerate(report.sections):
            self.assertEqual(section.section_type, expected_types[i])
            self.assertIsNotNone(section.title)
            self.assertIsNotNone(section.content)

    def test_html_rendering(self):
        report = self.generator.generate(self.ctx)
        html_out = report.to_html()
        self.assertIn("<!DOCTYPE html>", html_out)
        self.assertIn("PhoneTrace Investigation Report", html_out)
        self.assertIn("Arjun Mehta", html_out)


class TestLLMProviders(unittest.TestCase):
    """Verify LLM provider interfaces and connection availability checks."""

    def test_gemini_provider_is_available(self):
        provider = GeminiProvider(api_key="")
        self.assertFalse(provider.is_available())

        provider = GeminiProvider(api_key="dummy-key")
        try:
            import google.generativeai  # noqa: F401
            with patch("google.generativeai.GenerativeModel"):
                self.assertTrue(provider.is_available())
        except ImportError:
            self.assertFalse(provider.is_available())

    def test_openai_provider_is_available(self):
        provider = OpenAIProvider(api_key="")
        self.assertFalse(provider.is_available())

        provider = OpenAIProvider(api_key="dummy-key")
        try:
            import openai  # noqa: F401
            self.assertTrue(provider.is_available())
        except ImportError:
            self.assertFalse(provider.is_available())

    def test_ollama_provider_is_available(self):
        # Connection check will fail because there is no server running locally on a test environment
        provider = OllamaProvider(base_url="http://localhost:11434")
        self.assertFalse(provider.is_available())

        # Mock urllib request to return 200 OK
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.status = 200
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            self.assertTrue(provider.is_available())


if __name__ == "__main__":
    unittest.main()
