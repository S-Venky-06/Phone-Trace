"""
PhoneTrace -- Timeline Statistics
===================================

Generates investigative metrics from the forensic timeline.

Provides counts, frequencies, busiest periods, and communication
patterns that power the investigation dashboard.
"""

from __future__ import annotations

import io
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple

from timeline.models import (
    CorrelationGroup,
    ForensicEvent,
    InvestigationSession,
)

# Ensure UTF-8 on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )


@dataclass
class StatisticsReport:
    """Aggregated metrics from the forensic timeline.

    Attributes:
        total_events: Total number of timeline events.
        counts_by_type: Event count per artifact type.
        unknown_contacts: Count of calls/SMS with unknown contacts.
        communication_frequency: (contact -> count) for calls + SMS.
        busiest_hour: Hour of day (0-23) with most events.
        busiest_day: Date with most events.
        session_count: Number of investigation sessions.
        correlation_count: Number of detected correlation groups.
        time_range: (earliest, latest) event timestamps.
        incident_events: Events during the incident window (if detected).
    """
    total_events: int = 0
    counts_by_type: Dict[str, int] = field(default_factory=dict)
    unknown_contacts: int = 0
    communication_frequency: Dict[str, int] = field(default_factory=dict)
    busiest_hour: int = 0
    busiest_hour_count: int = 0
    busiest_day: Optional[date] = None
    busiest_day_count: int = 0
    session_count: int = 0
    correlation_count: int = 0
    time_range: Optional[Tuple[datetime, datetime]] = None
    incident_events: int = 0


class TimelineStatistics:
    """Generates investigative metrics from the forensic timeline.

    Usage::

        stats = TimelineStatistics()
        report = stats.generate(
            events=builder.events,
            sessions=builder.sessions,
            correlations=correlation_groups,
        )
        stats.print_report(report)
    """

    @staticmethod
    def generate(
        events: List[ForensicEvent],
        sessions: Optional[List[InvestigationSession]] = None,
        correlations: Optional[List[CorrelationGroup]] = None,
        incident_start: Optional[datetime] = None,
        incident_end: Optional[datetime] = None,
    ) -> StatisticsReport:
        """Generate a statistics report from the timeline.

        Args:
            events: The full sorted timeline.
            sessions: Investigation sessions (from TimelineBuilder).
            correlations: Correlation groups (from EvidenceCorrelator).
            incident_start: Optional start of the incident window.
            incident_end: Optional end of the incident window.

        Returns:
            A populated StatisticsReport.
        """
        report = StatisticsReport()

        if not events:
            return report

        report.total_events = len(events)

        # -- Counts by type --
        type_counter: Counter = Counter()
        for e in events:
            type_counter[e.artifact_type] += 1
        report.counts_by_type = dict(type_counter.most_common())

        # -- Time range --
        report.time_range = (events[0].timestamp, events[-1].timestamp)

        # -- Unknown contacts (calls without a saved contact name) --
        unknown = 0
        for e in events:
            if e.artifact_type == "call":
                contact = e.metadata.get("contact_name")
                if contact is None or contact == "None" or contact == "":
                    unknown += 1
        report.unknown_contacts = unknown

        # -- Communication frequency --
        comm_counter: Counter = Counter()
        for e in events:
            if e.artifact_type in ("call", "sms"):
                number = (
                    e.metadata.get("number")
                    or e.metadata.get("address")
                    or "unknown"
                )
                comm_counter[number] += 1
        report.communication_frequency = dict(
            comm_counter.most_common()
        )

        # -- Busiest hour --
        hour_counter: Counter = Counter()
        for e in events:
            hour_counter[e.timestamp.hour] += 1
        if hour_counter:
            busiest_h, busiest_h_count = hour_counter.most_common(1)[0]
            report.busiest_hour = busiest_h
            report.busiest_hour_count = busiest_h_count

        # -- Busiest day --
        day_counter: Counter = Counter()
        for e in events:
            day_counter[e.timestamp.date()] += 1
        if day_counter:
            busiest_d, busiest_d_count = day_counter.most_common(1)[0]
            report.busiest_day = busiest_d
            report.busiest_day_count = busiest_d_count

        # -- Sessions and correlations --
        report.session_count = len(sessions) if sessions else 0
        report.correlation_count = len(correlations) if correlations else 0

        # -- Incident window events --
        if incident_start and incident_end:
            report.incident_events = sum(
                1 for e in events
                if incident_start <= e.timestamp <= incident_end
            )

        return report

    @staticmethod
    def print_report(report: StatisticsReport) -> None:
        """Print a formatted statistics report to stdout.

        Args:
            report: The StatisticsReport to display.
        """
        print()
        print("=" * 60)
        print("  PhoneTrace -- Timeline Statistics")
        print("=" * 60)
        print()

        print(f"  Total Events: {report.total_events}")
        print()

        print("  Events by artifact type:")
        for atype, count in report.counts_by_type.items():
            print(f"    {atype:.<25} {count:>6}")
        print()

        if report.time_range:
            start, end = report.time_range
            print(f"  Time Range: {start.isoformat()}")
            print(f"           to {end.isoformat()}")
            print()

        print(f"  Unknown Contacts: {report.unknown_contacts}")
        print()

        print(f"  Busiest Hour: {report.busiest_hour:02d}:00"
              f" ({report.busiest_hour_count} events)")
        if report.busiest_day:
            print(f"  Busiest Day:  {report.busiest_day.isoformat()}"
                  f" ({report.busiest_day_count} events)")
        print()

        print("  Top 5 contacts (calls + SMS):")
        top5 = list(report.communication_frequency.items())[:5]
        for number, count in top5:
            print(f"    {number:.<30} {count:>4}")
        print()

        print(f"  Investigation Sessions: {report.session_count}")
        print(f"  Correlation Groups: {report.correlation_count}")

        if report.incident_events:
            print(f"  Incident Window Events: {report.incident_events}")
        print()
        print("=" * 60)
