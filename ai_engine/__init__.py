"""
PhoneTrace -- AI Engine Package
=================================

AI-powered forensic investigation layer.

Provides context building, multiple AI providers (rule-based + LLMs),
investigation report generation, and an orchestration assistant.

Quick start::

    from ai_engine import AIAssistant

    assistant = AIAssistant(
        events=backend.events,
        sessions=backend.sessions,
        correlations=backend.correlations,
        statistics=backend.statistics,
    )

    # Check alibi
    response = assistant.check_alibi()
    print(response.answer)

    # Generate report
    report = assistant.generate_report()
    html = report.to_html()
"""

from ai_engine.models import (
    CommunicationPattern,
    CorrelationSummary,
    EventSummary,
    InvestigationContext,
    MovementSummary,
    QueryType,
    SectionType,
    SessionSummary,
    StatsSummary,
)
from ai_engine.report_models import (
    AIQuery,
    AIResponse,
    InvestigationReport,
    ReportSection,
)
from ai_engine.context_builder import ContextBuilder
from ai_engine.assistant import AIAssistant
from ai_engine.report_generator import ReportGenerator
from ai_engine.providers.base import AIProvider
from ai_engine.providers.rule_based import RuleBasedProvider

__all__ = [
    # Models
    "EventSummary",
    "CorrelationSummary",
    "SessionSummary",
    "MovementSummary",
    "CommunicationPattern",
    "StatsSummary",
    "InvestigationContext",
    "QueryType",
    "SectionType",
    "AIQuery",
    "AIResponse",
    "ReportSection",
    "InvestigationReport",
    # Core
    "ContextBuilder",
    "AIAssistant",
    "ReportGenerator",
    "AIProvider",
    "RuleBasedProvider",
]
