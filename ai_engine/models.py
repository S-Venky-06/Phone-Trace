"""
PhoneTrace -- AI Engine Data Models
=====================================

Dataclasses for the AI investigation layer.

These models carry structured forensic context between the
ContextBuilder, AIProviders, and ReportGenerator.  They never
reference raw SQLite rows or parser objects directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class QueryType(Enum):
    """Type of question posed to an AI provider."""
    GENERAL = "general"
    ALIBI_CHECK = "alibi_check"
    ANOMALY = "anomaly"
    TIMELINE_QUESTION = "timeline_question"
    NARRATIVE = "narrative"


class SectionType(Enum):
    """Category of a report section."""
    CASE_OVERVIEW = "case_overview"
    TIMELINE_SUMMARY = "timeline_summary"
    INCIDENT_ANALYSIS = "incident_analysis"
    ALIBI_VERIFICATION = "alibi_verification"
    COMMUNICATION_ANALYSIS = "communication_analysis"
    MOVEMENT_ANALYSIS = "movement_analysis"
    CORRELATION_FINDINGS = "correlation_findings"
    ANOMALY_REPORT = "anomaly_report"
    AI_NARRATIVE = "ai_narrative"
    CONCLUSIONS = "conclusions"


# ---------------------------------------------------------------------------
# Compact Event Summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EventSummary:
    """Compact representation of a ForensicEvent for AI context.

    Avoids sending the full event object (with related-event
    graphs) to LLM providers.

    Attributes:
        timestamp: ISO-formatted timestamp string.
        artifact_type: Event category.
        title: Short human-readable title.
        description: Detailed description.
        location_label: Optional place name or lat/lon string.
        metadata_excerpt: Selected metadata keys relevant to analysis.
    """
    timestamp: str
    artifact_type: str
    title: str
    description: str
    location_label: str = ""
    metadata_excerpt: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Correlation Summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CorrelationSummary:
    """Distilled representation of a CorrelationGroup.

    Attributes:
        rule_name: Name of the correlation rule.
        anchor_title: Title of the anchor event.
        anchor_time: Anchor event timestamp (ISO string).
        correlated_count: Number of correlated events.
        confidence: Confidence score (0.0-1.0).
    """
    rule_name: str
    anchor_title: str
    anchor_time: str
    correlated_count: int
    confidence: float = 1.0


# ---------------------------------------------------------------------------
# Session Summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Compact metadata for an InvestigationSession.

    Attributes:
        session_id: Sequential identifier.
        start: Session start ISO string.
        end: Session end ISO string.
        event_count: Number of events.
        artifact_types: Set of artifact type strings.
    """
    session_id: int
    start: str
    end: str
    event_count: int
    artifact_types: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Movement Summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class MovementSummary:
    """Significant GPS displacement.

    Attributes:
        from_label: Starting location description.
        to_label: Ending location description.
        from_coords: (lat, lon) tuple.
        to_coords: (lat, lon) tuple.
        timestamp: ISO string of the movement time.
        distance_km: Displacement in kilometres.
    """
    from_label: str
    to_label: str
    from_coords: Tuple[float, float]
    to_coords: Tuple[float, float]
    timestamp: str
    distance_km: float


# ---------------------------------------------------------------------------
# Communication Pattern
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CommunicationPattern:
    """Aggregated communication statistics.

    Attributes:
        top_contacts: List of (name_or_number, count) tuples.
        unknown_contact_count: Count of calls/SMS with unknown contacts.
        total_calls: Total call events.
        total_sms: Total SMS events.
        incident_contacts: Contacts active during the incident window.
    """
    top_contacts: Tuple[Tuple[str, int], ...] = ()
    unknown_contact_count: int = 0
    total_calls: int = 0
    total_sms: int = 0
    incident_contacts: Tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Statistics Summary
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class StatsSummary:
    """Key statistical metrics from the timeline.

    Attributes:
        total_events: Total number of events.
        busiest_hour: Hour of day with most events.
        busiest_hour_count: Event count in the busiest hour.
        busiest_day: Date string of busiest day.
        busiest_day_count: Event count on the busiest day.
        session_count: Number of investigation sessions.
        correlation_count: Number of correlation groups.
        incident_event_count: Events during the incident window.
    """
    total_events: int = 0
    busiest_hour: int = 0
    busiest_hour_count: int = 0
    busiest_day: str = ""
    busiest_day_count: int = 0
    session_count: int = 0
    correlation_count: int = 0
    incident_event_count: int = 0


# ---------------------------------------------------------------------------
# Investigation Context  (the main payload to AI providers)
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class InvestigationContext:
    """Complete structured context for AI analysis.

    This is the single object passed to every AI provider.
    It contains enough information to answer forensic questions
    without the provider needing direct database or parser access.

    Attributes:
        case_summary: Free-text case overview.
        suspect_name: Name of the suspect.
        suspect_phone: Suspect's phone number.
        device_info: Device make/model.
        investigation_period: (start_iso, end_iso) of the evidence window.
        incident_window: (start_iso, end_iso) of the incident.
        alibi_location: Claimed alibi location description.
        alibi_coords: (lat, lon) of the alibi location.
        incident_location: Where evidence places the phone.
        incident_coords: (lat, lon) of the incident location.
        artifact_counts: {artifact_type -> count}.
        statistics: Aggregated stats.
        incident_events: Events during the incident window.
        correlations: Distilled correlation summaries.
        sessions: Session metadata.
        movements: Significant GPS displacements.
        communication: Communication pattern analysis.
        all_events_summary: Summary of ALL events (for large investigations).
    """
    case_summary: str = ""
    suspect_name: str = ""
    suspect_phone: str = ""
    device_info: str = ""
    investigation_period: Tuple[str, str] = ("", "")
    incident_window: Tuple[str, str] = ("", "")
    alibi_location: str = ""
    alibi_coords: Tuple[float, float] = (0.0, 0.0)
    incident_location: str = ""
    incident_coords: Tuple[float, float] = (0.0, 0.0)
    artifact_counts: Dict[str, int] = field(default_factory=dict)
    statistics: StatsSummary = field(default_factory=StatsSummary)
    incident_events: List[EventSummary] = field(default_factory=list)
    correlations: List[CorrelationSummary] = field(default_factory=list)
    sessions: List[SessionSummary] = field(default_factory=list)
    movements: List[MovementSummary] = field(default_factory=list)
    communication: CommunicationPattern = field(
        default_factory=CommunicationPattern,
    )
    all_events_summary: List[EventSummary] = field(default_factory=list)

    def to_prompt_text(self) -> str:
        """Serialize the context into a structured text block for LLM prompts.

        Returns:
            A formatted multi-line string suitable for injection into
            an LLM system or user prompt.
        """
        lines: List[str] = []

        lines.append("=== INVESTIGATION CONTEXT ===")
        lines.append("")
        lines.append(f"Case: {self.case_summary}")
        lines.append(f"Suspect: {self.suspect_name} ({self.suspect_phone})")
        lines.append(f"Device: {self.device_info}")
        lines.append(
            f"Investigation Period: {self.investigation_period[0]} "
            f"to {self.investigation_period[1]}"
        )
        lines.append(
            f"Incident Window: {self.incident_window[0]} "
            f"to {self.incident_window[1]}"
        )
        lines.append(
            f"Alibi Location: {self.alibi_location} "
            f"({self.alibi_coords[0]:.4f}, {self.alibi_coords[1]:.4f})"
        )
        lines.append(
            f"Incident Location: {self.incident_location} "
            f"({self.incident_coords[0]:.4f}, {self.incident_coords[1]:.4f})"
        )
        lines.append("")

        # Artifact counts
        lines.append("--- Artifact Counts ---")
        for atype, count in self.artifact_counts.items():
            lines.append(f"  {atype}: {count}")
        lines.append("")

        # Statistics
        s = self.statistics
        lines.append("--- Key Statistics ---")
        lines.append(f"  Total Events: {s.total_events}")
        lines.append(f"  Busiest Hour: {s.busiest_hour:02d}:00 ({s.busiest_hour_count} events)")
        lines.append(f"  Busiest Day: {s.busiest_day} ({s.busiest_day_count} events)")
        lines.append(f"  Sessions: {s.session_count}")
        lines.append(f"  Correlations: {s.correlation_count}")
        lines.append(f"  Incident Window Events: {s.incident_event_count}")
        lines.append("")

        # Communication
        c = self.communication
        lines.append("--- Communication Pattern ---")
        lines.append(f"  Total Calls: {c.total_calls}")
        lines.append(f"  Total SMS: {c.total_sms}")
        lines.append(f"  Unknown Contacts: {c.unknown_contact_count}")
        if c.top_contacts:
            lines.append("  Top Contacts:")
            for name, count in c.top_contacts[:5]:
                lines.append(f"    {name}: {count} interactions")
        if c.incident_contacts:
            lines.append(f"  Incident Window Contacts: {', '.join(c.incident_contacts)}")
        lines.append("")

        # Movements
        if self.movements:
            lines.append("--- Significant Movements ---")
            for m in self.movements[:20]:
                lines.append(
                    f"  [{m.timestamp}] {m.from_label} -> {m.to_label} "
                    f"({m.distance_km:.1f} km)"
                )
            lines.append("")

        # Incident events
        if self.incident_events:
            lines.append("--- Incident Window Events ---")
            for ev in self.incident_events:
                loc = f" @ {ev.location_label}" if ev.location_label else ""
                lines.append(f"  [{ev.timestamp}] [{ev.artifact_type}] {ev.title}{loc}")
                if ev.description:
                    lines.append(f"    {ev.description}")
            lines.append("")

        # Correlations
        if self.correlations:
            lines.append("--- Correlation Groups ---")
            for cg in self.correlations:
                lines.append(
                    f"  Rule: {cg.rule_name} | Anchor: {cg.anchor_title} "
                    f"@ {cg.anchor_time} | Related: {cg.correlated_count} "
                    f"events | Confidence: {cg.confidence:.0%}"
                )
            lines.append("")

        lines.append("=== END CONTEXT ===")
        return "\n".join(lines)
