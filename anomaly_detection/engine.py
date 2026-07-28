"""
PhoneTrace -- Anomaly Detection Engine
=========================================

Orchestrates forensic anomaly rules over parsed timeline events.
"""

from __future__ import annotations

import logging
from typing import List

from anomaly_detection.models import Anomaly
from anomaly_detection.rules import (
    detect_alibi_contradiction,
    detect_burner_phone_contact,
    detect_timezone_discrepancy,
)
from timeline.models import ForensicEvent

logger = logging.getLogger("anomaly.engine")


class AnomalyEngine:
    """Evaluates timeline events against forensic anomaly rules."""

    def __init__(self) -> None:
        self._rules = [
            detect_alibi_contradiction,
            detect_burner_phone_contact,
            detect_timezone_discrepancy,
        ]

    def analyze(self, events: List[ForensicEvent]) -> List[Anomaly]:
        """Run all anomaly rules and return detected anomalies."""
        logger.info("AnomalyEngine: analyzing %d events...", len(events))
        detected: List[Anomaly] = []

        for rule_fn in self._rules:
            try:
                results = rule_fn(events)
                detected.extend(results)
            except Exception as exc:
                logger.warning("Anomaly rule '%s' failed: %s", rule_fn.__name__, exc)

        logger.info("AnomalyEngine: detected %d anomalies.", len(detected))
        return detected
