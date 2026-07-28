"""
PhoneTrace -- Timeline Package
================================

Unified forensic timeline reconstruction and evidence correlation engine.

Quick start::

    from artifacts import ParserManager
    from timeline import TimelineBuilder, EvidenceCorrelator

    pm = ParserManager()
    pm.load_all()

    builder = TimelineBuilder(pm)
    events = builder.build()
    sessions = builder.sessions

    correlator = EvidenceCorrelator()
    groups = correlator.correlate(events)
"""

# Models
from timeline.models import (
    CorrelationConfig,
    CorrelationGroup,
    EventLocation,
    ForensicEvent,
    InvestigationSession,
)

# Core components
from timeline.event_factory import EventFactory
from timeline.timeline_builder import TimelineBuilder
from timeline.correlator import EvidenceCorrelator
from timeline.timeline_filters import TimelineFilter
from timeline.statistics import StatisticsReport, TimelineStatistics
from timeline.timeline_export import TimelineExporter

__all__ = [
    # Models
    "ForensicEvent",
    "EventLocation",
    "InvestigationSession",
    "CorrelationGroup",
    "CorrelationConfig",
    # Core
    "EventFactory",
    "TimelineBuilder",
    "EvidenceCorrelator",
    "TimelineFilter",
    "TimelineStatistics",
    "StatisticsReport",
    "TimelineExporter",
]
