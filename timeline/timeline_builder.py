"""
PhoneTrace -- Timeline Builder
================================

Constructs the unified forensic timeline from parsed artifacts.

Responsibilities:
    - Collect all records from ParserManager
    - Convert each record into a ForensicEvent via EventFactory
    - Sort events chronologically
    - Filter out events with invalid timestamps
    - Group events into InvestigationSessions
    - Provide structured logging and a summary

Usage::

    from artifacts import ParserManager
    from timeline import TimelineBuilder

    pm = ParserManager()
    pm.load_all()

    builder = TimelineBuilder(pm)
    builder.build()

    events = builder.events          # sorted list[ForensicEvent]
    sessions = builder.sessions      # list[InvestigationSession]
    builder.summary()                # print statistics
"""

from __future__ import annotations

import io
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from artifacts.parser_manager import ParserManager
from timeline.event_factory import EventFactory
from timeline.models import (
    CorrelationConfig,
    ForensicEvent,
    InvestigationSession,
)

# Ensure UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

logger = logging.getLogger("timeline.TimelineBuilder")


class TimelineBuilder:
    """Builds the complete forensic timeline from parsed evidence.

    Args:
        parser_manager: A loaded :class:`ParserManager` instance.
        factory: Optional custom :class:`EventFactory`. If None,
            a default factory with all built-in converters is used.
        config: Optional :class:`CorrelationConfig` for session
            grouping thresholds.
    """

    def __init__(
        self,
        parser_manager: ParserManager,
        factory: Optional[EventFactory] = None,
        config: Optional[CorrelationConfig] = None,
    ) -> None:
        self._pm = parser_manager
        self._factory = factory or EventFactory()
        self._config = config or CorrelationConfig()

        self._events: List[ForensicEvent] = []
        self._sessions: List[InvestigationSession] = []
        self._built: bool = False

        # Conversion stats
        self._counts: dict = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self) -> List[ForensicEvent]:
        """Build the complete timeline.

        Converts all parsed records, sorts chronologically, and
        groups events into investigation sessions.

        Returns:
            Sorted list of ForensicEvent objects.
        """
        logger.info("Loading parsed artifacts...")

        # Log source counts
        sources = {
            "Calls": self._pm.calls,
            "SMS": self._pm.sms,
            "Browser": self._pm.browser,
            "GPS": self._pm.gps,
            "App Usage": self._pm.app_usage,
            "Files": self._pm.files,
        }
        for name, records in sources.items():
            logger.info("  %s: %d", name, len(records))

        # Convert all records
        logger.info("Creating ForensicEvents...")
        all_events: List[ForensicEvent] = []

        for name, records in sources.items():
            converted = self._factory.convert_all(records)
            self._counts[name] = len(converted)
            all_events.extend(converted)

        # Filter out events with invalid timestamps
        valid_events = self._filter_valid(all_events)
        if len(valid_events) < len(all_events):
            dropped = len(all_events) - len(valid_events)
            logger.warning("Dropped %d events with invalid timestamps.", dropped)

        # Sort chronologically
        valid_events.sort(key=lambda e: e.timestamp)

        self._events = valid_events
        logger.info("Total Timeline Events: %d", len(self._events))

        # Group into sessions
        self._sessions = self._build_sessions(self._events)
        logger.info(
            "Grouped into %d Investigation Sessions.", len(self._sessions)
        )

        self._built = True
        logger.info("Timeline construction complete.")
        return self._events

    @property
    def events(self) -> List[ForensicEvent]:
        """The built timeline events (sorted oldest to newest)."""
        if not self._built:
            raise RuntimeError("Call build() before accessing events.")
        return self._events

    @property
    def sessions(self) -> List[InvestigationSession]:
        """Investigation sessions derived from the timeline."""
        if not self._built:
            raise RuntimeError("Call build() before accessing sessions.")
        return self._sessions

    def summary(self) -> None:
        """Print a concise summary of the built timeline."""
        if not self._built:
            print("  TimelineBuilder: Not built yet. Call build() first.")
            return

        print()
        print("=" * 60)
        print("  PhoneTrace -- Timeline Summary")
        print("=" * 60)
        print()
        print("  Events by artifact type:")
        for name, count in self._counts.items():
            print(f"    {name:.<25} {count:>6}")
        print(f"    {'':->30}")
        print(f"    {'Total':.<25} {len(self._events):>6}")
        print()
        if self._events:
            print(f"  Time range: {self._events[0].timestamp.isoformat()}")
            print(f"           to {self._events[-1].timestamp.isoformat()}")
        print(f"  Investigation Sessions: {len(self._sessions)}")
        print()
        print("=" * 60)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _filter_valid(events: List[ForensicEvent]) -> List[ForensicEvent]:
        """Remove events with missing or obviously wrong timestamps.

        Args:
            events: Unfiltered event list.

        Returns:
            List of events with valid timestamps.
        """
        valid: List[ForensicEvent] = []
        min_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
        max_date = datetime(2100, 1, 1, tzinfo=timezone.utc)

        for event in events:
            if event.timestamp is None:
                continue
            # Ensure timezone-aware
            ts = event.timestamp
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if min_date <= ts <= max_date:
                valid.append(event)

        return valid

    def _build_sessions(
        self,
        events: List[ForensicEvent],
    ) -> List[InvestigationSession]:
        """Group events into investigation sessions.

        Events separated by more than ``session_gap_minutes`` start
        a new session.

        Args:
            events: Chronologically sorted events.

        Returns:
            List of InvestigationSession objects.
        """
        if not events:
            return []

        gap = timedelta(minutes=self._config.session_gap_minutes)
        sessions: List[InvestigationSession] = []

        current_events: List[ForensicEvent] = [events[0]]

        for event in events[1:]:
            if (event.timestamp - current_events[-1].timestamp) > gap:
                # Close current session
                sessions.append(InvestigationSession(
                    session_id=len(sessions) + 1,
                    start_time=current_events[0].timestamp,
                    end_time=current_events[-1].timestamp,
                    events=current_events,
                ))
                current_events = [event]
            else:
                current_events.append(event)

        # Close final session
        if current_events:
            sessions.append(InvestigationSession(
                session_id=len(sessions) + 1,
                start_time=current_events[0].timestamp,
                end_time=current_events[-1].timestamp,
                events=current_events,
            ))

        return sessions
