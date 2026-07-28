"""
PhoneTrace -- Backend Service Facade
=======================================

Single facade that wraps all existing backend modules so the GUI
never imports parsers, timeline builders, or exporters directly.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from artifacts import ParserManager
from timeline import (
    CorrelationConfig,
    CorrelationGroup,
    EvidenceCorrelator,
    ForensicEvent,
    InvestigationSession,
    StatisticsReport,
    TimelineBuilder,
    TimelineExporter,
    TimelineFilter,
    TimelineStatistics,
)

logger = logging.getLogger("gui.backend")


class BackendService:
    """Facade providing all backend functionality to the GUI.

    Usage::

        svc = BackendService("evidence_output")
        svc.load()

        events = svc.events
        stats  = svc.statistics
        groups = svc.correlations
    """

    def __init__(
        self,
        evidence_dir: str | Path | None = None,
        config: Optional[CorrelationConfig] = None,
    ) -> None:
        self._evidence_dir = evidence_dir
        self._config = config or CorrelationConfig()

        # Cached results
        self._pm: Optional[ParserManager] = None
        self._builder: Optional[TimelineBuilder] = None
        self._events: List[ForensicEvent] = []
        self._sessions: List[InvestigationSession] = []
        self._correlations: List[CorrelationGroup] = []
        self._statistics: Optional[StatisticsReport] = None
        self._ai_assistant = None
        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, evidence_dir: str | Path | None = None) -> None:
        """Parse evidence, build timeline, correlate, and compute stats."""
        if evidence_dir is not None:
            self._evidence_dir = evidence_dir
        logger.info("Backend: loading evidence...")

        self._pm = ParserManager(self._evidence_dir)
        self._pm.load_all()

        logger.info("Backend: building timeline...")
        self._builder = TimelineBuilder(self._pm, config=self._config)
        self._events = self._builder.build()
        self._sessions = self._builder.sessions

        logger.info("Backend: correlating evidence...")
        correlator = EvidenceCorrelator(self._config)
        self._correlations = correlator.correlate(self._events)

        logger.info("Backend: computing statistics...")
        self._statistics = TimelineStatistics.generate(
            self._events, self._sessions, self._correlations,
        )

        self._loaded = True
        logger.info("Backend: ready (%d events).", len(self._events))

        if self._ai_assistant is not None:
            self._ai_assistant.set_data(
                self._events, self._sessions, self._correlations, self._statistics
            )

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def ai_assistant(self):
        """Lazily initialize the AIAssistant orchestrator."""
        if self._ai_assistant is None:
            from ai_engine import AIAssistant
            self._ai_assistant = AIAssistant(
                events=self._events,
                sessions=self._sessions,
                correlations=self._correlations,
                statistics=self._statistics,
            )
        return self._ai_assistant

    def set_ai_provider(self, name: str, api_key: str = "", **kwargs) -> None:
        """Configure the AI assistant provider."""
        self.ai_assistant.set_provider(name, api_key, **kwargs)

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    @property
    def events(self) -> List[ForensicEvent]:
        return self._events

    @property
    def sessions(self) -> List[InvestigationSession]:
        return self._sessions

    @property
    def correlations(self) -> List[CorrelationGroup]:
        return self._correlations

    @property
    def statistics(self) -> Optional[StatisticsReport]:
        return self._statistics

    @property
    def parser(self) -> Optional[ParserManager]:
        return self._pm

    # ------------------------------------------------------------------
    # Filtering / Search
    # ------------------------------------------------------------------

    def filter_by_artifact(self, artifact_type: str) -> List[ForensicEvent]:
        return TimelineFilter.by_artifact(self._events, artifact_type)

    def filter_by_keyword(self, keyword: str) -> List[ForensicEvent]:
        return TimelineFilter.by_keyword(self._events, keyword)

    def search(self, query: str) -> List[ForensicEvent]:
        return TimelineFilter.search(self._events, query)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_json(self, output_path: str | Path) -> Path:
        return TimelineExporter.to_json(self._events, output_path)

    def export_csv(self, output_path: str | Path) -> Path:
        return TimelineExporter.to_csv(self._events, output_path)
