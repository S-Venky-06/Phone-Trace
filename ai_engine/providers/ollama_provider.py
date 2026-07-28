"""
PhoneTrace -- Ollama Local LLM Provider
==========================================

Connects to a locally running Ollama instance via its HTTP API.
No API key required — just a running Ollama server.

Default endpoint: ``http://localhost:11434``
"""

from __future__ import annotations

import json
import logging
from typing import Optional
from urllib import request, error

from ai_engine.models import InvestigationContext
from ai_engine.providers.base import AIProvider
from ai_engine.report_models import AIQuery, AIResponse

logger = logging.getLogger("ai_engine.OllamaProvider")

_SYSTEM_PROMPT = """You are a senior digital forensic investigator analysing evidence from an Android smartphone.
You must answer questions based ONLY on the structured investigation context provided.
Be precise, cite timestamps and locations, and clearly state your confidence level.
When checking alibis, compare GPS evidence against the claimed location.
When detecting anomalies, look for unusual patterns in timing, contacts, movement, and app usage.
Format your responses clearly with bullet points and headings where appropriate."""


class OllamaProvider(AIProvider):
    """Ollama local LLM provider.

    Communicates with Ollama via its REST API using only stdlib
    ``urllib`` — no extra dependencies needed.

    Args:
        base_url: Ollama server URL.
        model_name: Model to use (default: ``llama3.1``).
    """

    name = "Ollama"
    requires_api_key = False

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3.1",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name

    def _call(self, prompt: str) -> str:
        """Send a prompt to Ollama and return the text response."""
        url = f"{self._base_url}/api/generate"
        payload = {
            "model": self._model_name,
            "prompt": prompt,
            "system": _SYSTEM_PROMPT,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")

        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("response", "")
        except error.URLError as exc:
            logger.error("Ollama connection error: %s", exc)
            raise
        except Exception as exc:
            logger.error("Ollama error: %s", exc)
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
                confidence=0.75,
                provider_name=self.name,
            )
        except Exception as exc:
            return AIResponse(
                answer="",
                provider_name=self.name,
                error=f"Ollama error: {exc}",
            )

    def generate_narrative(
        self,
        context: InvestigationContext,
    ) -> str:
        prompt = (
            f"{context.to_prompt_text()}\n\n"
            f"Generate a detailed chronological investigation narrative."
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
            f"ALIBI VERIFICATION: The suspect claims to have been at "
            f"{claimed_location} ({claimed_coords[0]:.4f}, "
            f"{claimed_coords[1]:.4f}) during the incident window.\n\n"
            f"Determine: CONSISTENT, CONTRADICTED, or INSUFFICIENT DATA."
        )
        try:
            answer = self._call(prompt)
            return AIResponse(
                answer=answer,
                confidence=0.75,
                provider_name=self.name,
            )
        except Exception as exc:
            return AIResponse(
                answer="",
                provider_name=self.name,
                error=f"Ollama error: {exc}",
            )

    def detect_anomalies(
        self,
        context: InvestigationContext,
    ) -> AIResponse:
        prompt = (
            f"{context.to_prompt_text()}\n\n"
            f"ANOMALY DETECTION: Analyse for behavioural anomalies."
        )
        try:
            answer = self._call(prompt)
            return AIResponse(
                answer=answer,
                confidence=0.75,
                provider_name=self.name,
            )
        except Exception as exc:
            return AIResponse(
                answer="",
                provider_name=self.name,
                error=f"Ollama error: {exc}",
            )

    def is_available(self) -> bool:
        """Check if Ollama is running by pinging the API."""
        try:
            url = f"{self._base_url}/api/tags"
            req = request.Request(url, method="GET")
            with request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
