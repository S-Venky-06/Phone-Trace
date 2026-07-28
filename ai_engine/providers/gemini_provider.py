"""
PhoneTrace -- Google Gemini AI Provider
=========================================

Uses the ``google-generativeai`` SDK to send forensic context
to a Gemini model for analysis.

Requires: ``pip install google-generativeai``
"""

from __future__ import annotations

import logging
from typing import Optional

from ai_engine.models import InvestigationContext
from ai_engine.providers.base import AIProvider
from ai_engine.report_models import AIQuery, AIResponse

logger = logging.getLogger("ai_engine.GeminiProvider")

_SYSTEM_PROMPT = """You are a senior digital forensic investigator analysing evidence from an Android smartphone.
You must answer questions based ONLY on the structured investigation context provided.
Be precise, cite timestamps and locations, and clearly state your confidence level.
When checking alibis, compare GPS evidence against the claimed location.
When detecting anomalies, look for unusual patterns in timing, contacts, movement, and app usage.
Format your responses clearly with bullet points and headings where appropriate."""


class GeminiProvider(AIProvider):
    """Google Gemini LLM provider.

    Args:
        api_key: Google AI API key.
        model_name: Gemini model to use (default: ``gemini-2.0-flash``).
    """

    name = "Gemini"
    requires_api_key = True

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "gemini-2.0-flash",
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._client = None

    def _get_client(self):
        """Lazily initialise the Gemini client."""
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._client = genai.GenerativeModel(
                    self._model_name,
                    system_instruction=_SYSTEM_PROMPT,
                )
            except ImportError:
                logger.error(
                    "google-generativeai not installed. "
                    "Run: pip install google-generativeai"
                )
                raise
            except Exception as exc:
                logger.error("Failed to initialise Gemini: %s", exc)
                raise
        return self._client

    def _call(self, prompt: str) -> str:
        """Send a prompt to Gemini and return the text response."""
        client = self._get_client()
        try:
            response = client.generate_content(prompt)
            return response.text
        except Exception as exc:
            logger.error("Gemini API error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # AIProvider interface
    # ------------------------------------------------------------------

    def analyze(
        self,
        context: InvestigationContext,
        query: AIQuery,
    ) -> AIResponse:
        prompt = (
            f"{context.to_prompt_text()}\n\n"
            f"QUESTION: {query.text}\n\n"
            f"Provide a detailed forensic analysis."
        )
        try:
            answer = self._call(prompt)
            return AIResponse(
                answer=answer,
                confidence=0.8,
                provider_name=self.name,
            )
        except Exception as exc:
            return AIResponse(
                answer="",
                provider_name=self.name,
                error=f"Gemini error: {exc}",
            )

    def generate_narrative(
        self,
        context: InvestigationContext,
    ) -> str:
        prompt = (
            f"{context.to_prompt_text()}\n\n"
            f"Generate a detailed chronological investigation narrative. "
            f"Include an alibi assessment, anomaly analysis, and "
            f"forensic conclusions."
        )
        try:
            return self._call(prompt)
        except Exception as exc:
            return f"Error generating narrative: {exc}"

    def check_alibi(
        self,
        context: InvestigationContext,
        claimed_location: str,
        claimed_coords: tuple[float, float],
    ) -> AIResponse:
        prompt = (
            f"{context.to_prompt_text()}\n\n"
            f"ALIBI VERIFICATION REQUEST:\n"
            f"The suspect claims to have been at {claimed_location} "
            f"(coordinates: {claimed_coords[0]:.4f}, {claimed_coords[1]:.4f}) "
            f"during the incident window.\n\n"
            f"Analyse the GPS evidence and determine if the alibi is "
            f"CONSISTENT, CONTRADICTED, or if there is INSUFFICIENT DATA. "
            f"Cite specific GPS readings and timestamps."
        )
        try:
            answer = self._call(prompt)
            return AIResponse(
                answer=answer,
                confidence=0.8,
                provider_name=self.name,
            )
        except Exception as exc:
            return AIResponse(
                answer="",
                provider_name=self.name,
                error=f"Gemini error: {exc}",
            )

    def detect_anomalies(
        self,
        context: InvestigationContext,
    ) -> AIResponse:
        prompt = (
            f"{context.to_prompt_text()}\n\n"
            f"ANOMALY DETECTION REQUEST:\n"
            f"Analyse the forensic data for behavioural anomalies. "
            f"Look for:\n"
            f"- Unusual timing patterns\n"
            f"- Unknown or suspicious contacts\n"
            f"- GPS location jumps or impossible travel\n"
            f"- Communication pattern breaks\n"
            f"- Suspicious app usage (VPN, cleaning apps)\n"
            f"- Activity spikes during the incident window\n\n"
            f"List each anomaly with supporting evidence."
        )
        try:
            answer = self._call(prompt)
            return AIResponse(
                answer=answer,
                confidence=0.8,
                provider_name=self.name,
            )
        except Exception as exc:
            return AIResponse(
                answer="",
                provider_name=self.name,
                error=f"Gemini error: {exc}",
            )

    def is_available(self) -> bool:
        if not self._api_key:
            return False
        try:
            import google.generativeai  # noqa: F401
            return True
        except ImportError:
            return False
