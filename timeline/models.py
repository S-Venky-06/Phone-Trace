"""
PhoneTrace -- Timeline Data Models
====================================

Enhanced dataclasses for the forensic timeline engine.

These models extend beyond Phase 2's ``TimelineEvent`` to include
location data, related-event links, investigation sessions, and
correlation groups -- all needed for evidence reconstruction.

Phase 2's ``TimelineEvent`` in ``artifacts/models.py`` remains untouched.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class EventLocation:
    """Geographic coordinates associated with a timeline event.

    Attributes:
        latitude: Decimal degrees.
        longitude: Decimal degrees.
        accuracy: Accuracy in metres (if available).
        label: Optional human-readable place name.
    """
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    label: Optional[str] = None


# ---------------------------------------------------------------------------
# Core Timeline Event
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ForensicEvent:
    """A single event on the unified forensic timeline.

    This is the primary data object consumed by all downstream modules
    (GUI, anomaly detection, AI narrative, reporting).

    Attributes:
        timestamp: When the event occurred (timezone-aware).
        artifact_type: Category string (``"call"``, ``"sms"``, ``"gps"``,
            ``"browser"``, ``"app_usage"``, ``"file"``).
        title: Short human-readable title (e.g. ``"Outgoing Call"``).
        description: Detailed description of the event.
        source: Origin evidence file (e.g. ``"calllog.db"``).
        location: Optional geographic coordinates.
        related: Events that are forensically correlated to this one.
        raw_record: The original typed dataclass from Phase 2.
        metadata: Arbitrary key-value pairs for type-specific data
            (e.g. ``{"duration_seconds": 120, "call_type": "outgoing"}``).
    """
    timestamp: datetime
    artifact_type: str
    title: str
    description: str
    source: str
    location: Optional[EventLocation] = None
    related: List["ForensicEvent"] = field(default_factory=list)
    raw_record: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Investigation Session
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class InvestigationSession:
    """A cluster of temporally-close events forming one activity window.

    Sessions are produced by grouping events that fall within a
    configurable time gap (default 15 minutes).

    Attributes:
        session_id: Sequential session identifier.
        start_time: Timestamp of the first event.
        end_time: Timestamp of the last event.
        events: The events belonging to this session.
    """
    session_id: int
    start_time: datetime
    end_time: datetime
    events: List[ForensicEvent] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Total duration of the session in seconds."""
        return (self.end_time - self.start_time).total_seconds()

    @property
    def event_count(self) -> int:
        """Number of events in this session."""
        return len(self.events)

    @property
    def artifact_types(self) -> set:
        """Set of distinct artifact types present in this session."""
        return {e.artifact_type for e in self.events}


# ---------------------------------------------------------------------------
# Correlation Group
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CorrelationGroup:
    """A set of events linked by a correlation rule.

    Attributes:
        rule_name: Name of the correlation rule that produced this group.
        anchor_event: The primary event that triggered the correlation.
        correlated_events: Events that are related to the anchor.
        confidence: Optional confidence score (0.0--1.0).
    """
    rule_name: str
    anchor_event: ForensicEvent
    correlated_events: List[ForensicEvent] = field(default_factory=list)
    confidence: float = 1.0

    @property
    def all_events(self) -> List[ForensicEvent]:
        """All events in the group (anchor + correlated)."""
        return [self.anchor_event] + self.correlated_events


# ---------------------------------------------------------------------------
# Correlation Configuration
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CorrelationConfig:
    """Configurable thresholds for the evidence correlator.

    All time windows are in minutes. Distance thresholds are in the
    units noted below.

    Attributes:
        time_window_minutes: Max gap between events to consider
            them related (default 15).
        gps_movement_threshold_km: Minimum displacement to count
            as significant movement (default 0.5 km).
        location_proximity_m: Max distance for co-location matching
            (default 200 metres).
        session_gap_minutes: Max gap between events within one
            investigation session (default 15).
        communication_cluster_minutes: Window for grouping calls/SMS
            to the same contact (default 10).
    """
    time_window_minutes: float = 15.0
    gps_movement_threshold_km: float = 0.5
    location_proximity_m: float = 200.0
    session_gap_minutes: float = 15.0
    communication_cluster_minutes: float = 10.0
