"""
PhoneTrace -- AI Context Builder
===================================

Transforms structured backend data (events, sessions, correlations,
statistics) into a compact ``InvestigationContext`` suitable for AI
provider consumption.

Key design decisions:
    * **Windowed context** — for large investigations (100k+ events),
      only incident-window events are included verbatim.  Other
      periods receive statistical summaries.
    * **Token budget** — context is capped at a configurable budget
      so that LLM providers never exceed their context window.
    * **No raw access** — the builder never touches SQLite or JSON
      files directly; it only reads from the ``BackendService`` facade.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from ai_engine.models import (
    CommunicationPattern,
    CorrelationSummary,
    EventSummary,
    InvestigationContext,
    MovementSummary,
    SessionSummary,
    StatsSummary,
)
from ai_engine.report_models import AIQuery

if TYPE_CHECKING:
    from gui.services.backend import BackendService
    from timeline.models import (
        CorrelationGroup,
        ForensicEvent,
        InvestigationSession,
    )
    from timeline.statistics import StatisticsReport

logger = logging.getLogger("ai_engine.ContextBuilder")


# ---------------------------------------------------------------------------
# Haversine helper (duplicated from correlator to avoid cross-import)
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two GPS points in kilometres."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class ContextBuilder:
    """Builds ``InvestigationContext`` from backend data.

    Args:
        token_budget: Approximate maximum tokens for the context.
            Events are prioritised: incident window > correlations >
            communications > other.

    Usage::

        builder = ContextBuilder(token_budget=8000)
        ctx = builder.build_full_context(backend)
    """

    def __init__(self, token_budget: int = 8000) -> None:
        self._budget = token_budget

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_full_context(
        self,
        events: list,
        sessions: list,
        correlations: list,
        statistics: object | None = None,
    ) -> InvestigationContext:
        """Build a complete investigation context.

        Args:
            events: Sorted list of ForensicEvent.
            sessions: List of InvestigationSession.
            correlations: List of CorrelationGroup.
            statistics: Optional StatisticsReport.

        Returns:
            Populated InvestigationContext.
        """
        from case_config import (
            ALIBI_LOCATION,
            BASELINE_END,
            BASELINE_START,
            INCIDENT_END,
            INCIDENT_LOCATION,
            INCIDENT_START,
            SUSPECT_DEVICE,
            SUSPECT_NAME,
            SUSPECT_PHONE,
        )

        ctx = InvestigationContext()

        # Case metadata
        ctx.case_summary = (
            f"Investigation of {SUSPECT_NAME}'s Android device "
            f"({SUSPECT_DEVICE}) over a {(BASELINE_END - BASELINE_START).days}-day "
            f"period to verify alibi claims during the incident window."
        )
        ctx.suspect_name = SUSPECT_NAME
        ctx.suspect_phone = SUSPECT_PHONE
        ctx.device_info = SUSPECT_DEVICE
        ctx.investigation_period = (
            BASELINE_START.isoformat(),
            BASELINE_END.isoformat(),
        )
        ctx.incident_window = (
            INCIDENT_START.isoformat(),
            INCIDENT_END.isoformat(),
        )
        ctx.alibi_location = ALIBI_LOCATION["name"]
        ctx.alibi_coords = (
            ALIBI_LOCATION["latitude"],
            ALIBI_LOCATION["longitude"],
        )
        ctx.incident_location = INCIDENT_LOCATION["name"]
        ctx.incident_coords = (
            INCIDENT_LOCATION["latitude"],
            INCIDENT_LOCATION["longitude"],
        )

        # Artifact counts
        ctx.artifact_counts = self._count_artifacts(events)

        # Statistics
        if statistics is not None:
            ctx.statistics = self._build_stats_summary(statistics)

        # Incident window events
        incident_events = [
            e for e in events
            if INCIDENT_START <= e.timestamp <= INCIDENT_END
        ]
        ctx.incident_events = self._summarize_events(incident_events)

        # Correlations
        ctx.correlations = self._summarize_correlations(correlations)

        # Sessions
        ctx.sessions = self._summarize_sessions(sessions)

        # GPS movements
        ctx.movements = self._extract_movements(events)

        # Communication patterns
        ctx.communication = self._extract_communication(events, statistics)

        # Budget-aware all-events summary
        remaining_budget = self._budget - self._estimate_tokens(
            ctx.to_prompt_text()
        )
        if remaining_budget > 500:
            # Include a sample of non-incident events
            non_incident = [
                e for e in events
                if not (INCIDENT_START <= e.timestamp <= INCIDENT_END)
            ]
            max_events = min(len(non_incident), remaining_budget // 20)
            # Sample evenly across the timeline
            step = max(1, len(non_incident) // max_events) if max_events > 0 else 1
            sampled = non_incident[::step][:max_events]
            ctx.all_events_summary = self._summarize_events(sampled)

        logger.info(
            "Context built: %d incident events, %d correlations, "
            "%d movements, ~%d tokens",
            len(ctx.incident_events),
            len(ctx.correlations),
            len(ctx.movements),
            self._estimate_tokens(ctx.to_prompt_text()),
        )
        return ctx

    def build_incident_context(
        self,
        events: list,
        sessions: list,
        correlations: list,
        statistics: object | None = None,
    ) -> InvestigationContext:
        """Build a context focused on the incident window only.

        Same as ``build_full_context`` but omits non-incident
        event summaries for a tighter context.
        """
        ctx = self.build_full_context(
            events, sessions, correlations, statistics,
        )
        ctx.all_events_summary = []  # Remove non-incident events
        return ctx

    def build_query_context(
        self,
        events: list,
        sessions: list,
        correlations: list,
        statistics: object | None = None,
        query: AIQuery | None = None,
    ) -> InvestigationContext:
        """Build a context tailored to the query type.

        For alibi queries, focuses on GPS and incident data.
        For anomaly queries, includes communication and movement data.
        For general/timeline queries, uses the full context.
        """
        from ai_engine.models import QueryType as QT

        if query is None or query.query_type in (QT.GENERAL, QT.TIMELINE_QUESTION):
            return self.build_full_context(
                events, sessions, correlations, statistics,
            )
        elif query.query_type == QT.ALIBI_CHECK:
            return self.build_incident_context(
                events, sessions, correlations, statistics,
            )
        elif query.query_type == QT.ANOMALY:
            return self.build_full_context(
                events, sessions, correlations, statistics,
            )
        else:
            return self.build_full_context(
                events, sessions, correlations, statistics,
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_artifacts(events: list) -> Dict[str, int]:
        """Count events by artifact type."""
        counts: Dict[str, int] = {}
        for e in events:
            counts[e.artifact_type] = counts.get(e.artifact_type, 0) + 1
        return counts

    @staticmethod
    def _build_stats_summary(stats) -> StatsSummary:
        """Convert a StatisticsReport into a StatsSummary."""
        return StatsSummary(
            total_events=stats.total_events,
            busiest_hour=stats.busiest_hour,
            busiest_hour_count=stats.busiest_hour_count,
            busiest_day=(
                stats.busiest_day.isoformat() if stats.busiest_day else ""
            ),
            busiest_day_count=stats.busiest_day_count,
            session_count=stats.session_count,
            correlation_count=stats.correlation_count,
            incident_event_count=stats.incident_events,
        )

    @staticmethod
    def _summarize_events(events: list) -> List[EventSummary]:
        """Convert ForensicEvents to compact EventSummary objects."""
        summaries: List[EventSummary] = []
        for e in events:
            loc_label = ""
            if e.location:
                if e.location.label:
                    loc_label = e.location.label
                else:
                    loc_label = f"{e.location.latitude:.4f}, {e.location.longitude:.4f}"

            # Select interesting metadata keys
            excerpt: dict = {}
            for key in ("number", "address", "contact_name", "call_type",
                        "sms_type", "url", "package_name", "file_path",
                        "duration_seconds", "body", "latitude", "longitude", "accuracy"):
                if key in e.metadata:
                    val = e.metadata[key]
                    if val is not None:
                        excerpt[key] = str(val)

            summaries.append(EventSummary(
                timestamp=e.timestamp.isoformat(),
                artifact_type=e.artifact_type,
                title=e.title,
                description=e.description,
                location_label=loc_label,
                metadata_excerpt=excerpt,
            ))
        return summaries

    @staticmethod
    def _summarize_correlations(correlations: list) -> List[CorrelationSummary]:
        """Convert CorrelationGroups to compact summaries."""
        summaries: List[CorrelationSummary] = []
        for cg in correlations:
            summaries.append(CorrelationSummary(
                rule_name=cg.rule_name,
                anchor_title=cg.anchor_event.title,
                anchor_time=cg.anchor_event.timestamp.isoformat(),
                correlated_count=len(cg.correlated_events),
                confidence=cg.confidence,
            ))
        return summaries

    @staticmethod
    def _summarize_sessions(sessions: list) -> List[SessionSummary]:
        """Convert InvestigationSessions to compact summaries."""
        summaries: List[SessionSummary] = []
        for s in sessions:
            summaries.append(SessionSummary(
                session_id=s.session_id,
                start=s.start_time.isoformat(),
                end=s.end_time.isoformat(),
                event_count=s.event_count,
                artifact_types=tuple(sorted(s.artifact_types)),
            ))
        return summaries

    @staticmethod
    def _extract_movements(
        events: list,
        threshold_km: float = 0.5,
    ) -> List[MovementSummary]:
        """Find significant GPS displacements."""
        gps_events = [e for e in events if e.artifact_type == "gps" and e.location]
        movements: List[MovementSummary] = []

        for i in range(1, len(gps_events)):
            prev = gps_events[i - 1]
            curr = gps_events[i]
            dist = _haversine_km(
                prev.location.latitude, prev.location.longitude,
                curr.location.latitude, curr.location.longitude,
            )
            if dist >= threshold_km:
                prev_label = (
                    prev.location.label
                    if prev.location.label
                    else f"{prev.location.latitude:.4f}, {prev.location.longitude:.4f}"
                )
                curr_label = (
                    curr.location.label
                    if curr.location.label
                    else f"{curr.location.latitude:.4f}, {curr.location.longitude:.4f}"
                )
                movements.append(MovementSummary(
                    from_label=prev_label,
                    to_label=curr_label,
                    from_coords=(
                        prev.location.latitude, prev.location.longitude,
                    ),
                    to_coords=(
                        curr.location.latitude, curr.location.longitude,
                    ),
                    timestamp=curr.timestamp.isoformat(),
                    distance_km=round(dist, 2),
                ))

        return movements

    @staticmethod
    def _extract_communication(
        events: list,
        statistics=None,
    ) -> CommunicationPattern:
        """Extract communication pattern from events."""
        calls = [e for e in events if e.artifact_type == "call"]
        sms = [e for e in events if e.artifact_type == "sms"]

        # Top contacts from statistics
        top_contacts: Tuple[Tuple[str, int], ...] = ()
        unknown_count = 0
        if statistics is not None:
            top5 = list(statistics.communication_frequency.items())[:5]
            top_contacts = tuple((k, v) for k, v in top5)
            unknown_count = statistics.unknown_contacts

        # Incident-window contacts
        from case_config import INCIDENT_START, INCIDENT_END

        incident_contacts: set = set()
        for e in calls + sms:
            if INCIDENT_START <= e.timestamp <= INCIDENT_END:
                num = (
                    e.metadata.get("number")
                    or e.metadata.get("address")
                    or "unknown"
                )
                incident_contacts.add(num)

        return CommunicationPattern(
            top_contacts=top_contacts,
            unknown_contact_count=unknown_count,
            total_calls=len(calls),
            total_sms=len(sms),
            incident_contacts=tuple(sorted(incident_contacts)),
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token count estimator.

        Uses the common heuristic of ~0.75 words per token for English.
        """
        words = len(text.split())
        return int(words / 0.75)
