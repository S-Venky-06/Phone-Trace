"""
PhoneTrace -- AI Provider Base Class
=======================================

Abstract interface that every AI provider must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ai_engine.models import InvestigationContext
from ai_engine.report_models import AIQuery, AIResponse


class AIProvider(ABC):
    """Abstract base class for all AI providers.

    Subclasses must implement every abstract method.
    The ``name`` and ``requires_api_key`` class-level attributes
    identify the provider in the settings UI and orchestration layer.
    """

    name: str = "base"
    requires_api_key: bool = False

    @abstractmethod
    def analyze(
        self,
        context: InvestigationContext,
        query: AIQuery,
    ) -> AIResponse:
        """Answer a free-form forensic question.

        Args:
            context: The investigation context.
            query: The user's question.

        Returns:
            An AIResponse with the answer.
        """

    @abstractmethod
    def generate_narrative(
        self,
        context: InvestigationContext,
    ) -> str:
        """Generate a chronological investigation narrative.

        Args:
            context: The investigation context.

        Returns:
            A multi-paragraph narrative string.
        """

    @abstractmethod
    def check_alibi(
        self,
        context: InvestigationContext,
        claimed_location: str,
        claimed_coords: tuple[float, float],
    ) -> AIResponse:
        """Verify a suspect's alibi against forensic evidence.

        Args:
            context: The investigation context.
            claimed_location: Human-readable alibi location.
            claimed_coords: (lat, lon) of the alibi location.

        Returns:
            An AIResponse with the alibi verdict.
        """

    @abstractmethod
    def detect_anomalies(
        self,
        context: InvestigationContext,
    ) -> AIResponse:
        """Identify behavioural anomalies in the forensic data.

        Args:
            context: The investigation context.

        Returns:
            An AIResponse listing detected anomalies.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is ready to use.

        Returns:
            True if the provider can process queries.
        """
