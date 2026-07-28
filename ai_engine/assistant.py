"""
PhoneTrace -- AI Assistant Orchestrator
==========================================

Central orchestration layer that connects the AI providers,
context builder, and report generator.

The GUI and backend interact exclusively through this class.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Type

from ai_engine.context_builder import ContextBuilder
from ai_engine.models import InvestigationContext, QueryType
from ai_engine.providers.base import AIProvider
from ai_engine.providers.gemini_provider import GeminiProvider
from ai_engine.providers.ollama_provider import OllamaProvider
from ai_engine.providers.openai_provider import OpenAIProvider
from ai_engine.providers.rule_based import RuleBasedProvider
from ai_engine.report_models import AIQuery, AIResponse, InvestigationReport

logger = logging.getLogger("ai_engine.AIAssistant")


# Provider registry: name -> class
_PROVIDER_REGISTRY: Dict[str, Type[AIProvider]] = {
    "rule_based": RuleBasedProvider,
    "gemini": GeminiProvider,
    "openai": OpenAIProvider,
    "ollama": OllamaProvider,
}


class AIAssistant:
    """Main AI investigation assistant.

    Orchestrates context building, provider selection, and
    report generation.

    Args:
        events: Timeline events from the backend.
        sessions: Investigation sessions.
        correlations: Correlation groups.
        statistics: Statistics report.
        token_budget: Max token budget for context building.

    Usage::

        assistant = AIAssistant(
            events=backend.events,
            sessions=backend.sessions,
            correlations=backend.correlations,
            statistics=backend.statistics,
        )
        response = assistant.ask("Where was the suspect at 22:00?")
    """

    def __init__(
        self,
        events: list | None = None,
        sessions: list | None = None,
        correlations: list | None = None,
        statistics: object | None = None,
        token_budget: int = 8000,
    ) -> None:
        self._events = events or []
        self._sessions = sessions or []
        self._correlations = correlations or []
        self._statistics = statistics
        self._context_builder = ContextBuilder(token_budget)
        self._provider: AIProvider = RuleBasedProvider()
        self._context: Optional[InvestigationContext] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Provider management
    # ------------------------------------------------------------------

    def set_provider(
        self,
        provider_name: str,
        api_key: str = "",
        **kwargs,
    ) -> None:
        """Switch the active AI provider.

        Args:
            provider_name: Key from the provider registry
                (``"rule_based"``, ``"gemini"``, ``"openai"``, ``"ollama"``).
            api_key: API key (for providers that require one).
            **kwargs: Extra arguments passed to the provider constructor
                (e.g. ``model_name``, ``base_url``).
        """
        with self._lock:
            cls = _PROVIDER_REGISTRY.get(provider_name)
            if cls is None:
                raise ValueError(
                    f"Unknown provider: {provider_name}. "
                    f"Available: {list(_PROVIDER_REGISTRY.keys())}"
                )

            import inspect
            sig = inspect.signature(cls.__init__)
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

            if cls.requires_api_key:
                self._provider = cls(api_key=api_key, **filtered_kwargs)
            elif provider_name == "ollama":
                self._provider = cls(**filtered_kwargs)
            else:
                self._provider = cls()

            # Invalidate cached context
            self._context = None
            logger.info("AI provider set to: %s", self._provider.name)

    @property
    def current_provider_name(self) -> str:
        """Name of the currently active provider."""
        return self._provider.name

    @property
    def current_provider(self) -> AIProvider:
        """The currently active provider instance."""
        return self._provider

    def is_provider_available(self) -> bool:
        """Check if the current provider is ready."""
        return self._provider.is_available()

    @staticmethod
    def list_providers() -> List[str]:
        """List all registered provider keys."""
        return list(_PROVIDER_REGISTRY.keys())

    @staticmethod
    def provider_display_names() -> Dict[str, str]:
        """Map provider keys to human-readable names."""
        return {
            key: cls.name
            for key, cls in _PROVIDER_REGISTRY.items()
        }

    # ------------------------------------------------------------------
    # Data management
    # ------------------------------------------------------------------

    def set_data(
        self,
        events: list,
        sessions: list,
        correlations: list,
        statistics: object | None = None,
    ) -> None:
        """Update the underlying forensic data.

        Call this after evidence is reloaded.
        """
        with self._lock:
            self._events = events
            self._sessions = sessions
            self._correlations = correlations
            self._statistics = statistics
            self._context = None  # Invalidate cache
            logger.info("AI data updated: %d events", len(events))

    def _get_context(
        self,
        query: Optional[AIQuery] = None,
    ) -> InvestigationContext:
        """Get or build the investigation context."""
        if query is not None:
            # Build query-specific context (not cached)
            return self._context_builder.build_query_context(
                self._events, self._sessions,
                self._correlations, self._statistics,
                query=query,
            )

        # Use cached full context
        if self._context is None:
            self._context = self._context_builder.build_full_context(
                self._events, self._sessions,
                self._correlations, self._statistics,
            )
        return self._context

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def ask(self, question: str) -> AIResponse:
        """Ask a free-form question about the investigation.

        Args:
            question: Natural language question.

        Returns:
            AIResponse with the answer.
        """
        with self._lock:
            if not self._events:
                return AIResponse(
                    answer="No evidence loaded. Please load evidence first.",
                    confidence=0.0,
                    provider_name=self._provider.name,
                    error="No data",
                )

            query = AIQuery(text=question, query_type=QueryType.GENERAL)
            ctx = self._get_context(query)

            try:
                return self._provider.analyze(ctx, query)
            except Exception as exc:
                logger.error("AI query failed: %s", exc)
                return AIResponse(
                    answer="",
                    provider_name=self._provider.name,
                    error=str(exc),
                )

    def check_alibi(self) -> AIResponse:
        """Verify the suspect's alibi using case configuration.

        Returns:
            AIResponse with the alibi verdict.
        """
        with self._lock:
            if not self._events:
                return AIResponse(
                    answer="No evidence loaded.",
                    confidence=0.0,
                    provider_name=self._provider.name,
                    error="No data",
                )

            query = AIQuery(text="alibi check", query_type=QueryType.ALIBI_CHECK)
            ctx = self._get_context(query)

            try:
                return self._provider.check_alibi(
                    ctx, ctx.alibi_location, ctx.alibi_coords,
                )
            except Exception as exc:
                logger.error("Alibi check failed: %s", exc)
                return AIResponse(
                    answer="",
                    provider_name=self._provider.name,
                    error=str(exc),
                )

    def detect_anomalies(self) -> AIResponse:
        """Detect behavioural anomalies in the forensic data.

        Returns:
            AIResponse listing detected anomalies.
        """
        with self._lock:
            if not self._events:
                return AIResponse(
                    answer="No evidence loaded.",
                    confidence=0.0,
                    provider_name=self._provider.name,
                    error="No data",
                )

            query = AIQuery(text="anomaly detection", query_type=QueryType.ANOMALY)
            ctx = self._get_context(query)

            try:
                return self._provider.detect_anomalies(ctx)
            except Exception as exc:
                logger.error("Anomaly detection failed: %s", exc)
                return AIResponse(
                    answer="",
                    provider_name=self._provider.name,
                    error=str(exc),
                )

    def generate_narrative(self) -> str:
        """Generate a chronological investigation narrative.

        Returns:
            Multi-paragraph narrative string.
        """
        with self._lock:
            if not self._events:
                return "No evidence loaded. Please load evidence first."

            ctx = self._get_context()

            try:
                return self._provider.generate_narrative(ctx)
            except Exception as exc:
                logger.error("Narrative generation failed: %s", exc)
                return f"Error generating narrative: {exc}"

    def generate_report(self) -> InvestigationReport:
        """Generate a full investigation report.

        Returns:
            InvestigationReport with all sections.
        """
        from ai_engine.report_generator import ReportGenerator

        with self._lock:
            if not self._events:
                return InvestigationReport(
                    provider_name=self._provider.name,
                )

            ctx = self._get_context()
            generator = ReportGenerator(self._provider)
            return generator.generate(ctx)
