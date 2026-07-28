"""
PhoneTrace -- Anomaly Detection Models
=========================================

Data structures for representing forensic anomalies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from timeline.models import ForensicEvent


class AnomalySeverity(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class AnomalyCategory(Enum):
    ALIBI_CONTRADICTION = "Alibi Contradiction"
    UNUSUAL_COMMUNICATION = "Unusual Communication"
    BURNER_PHONE = "Burner Phone Contact"
    MISSING_EVIDENCE = "Missing Evidence Log"
    TIMEZONE_DISCREPANCY = "Timezone Discrepancy"
    DUPLICATE_CONTACT = "Duplicate Contact"


@dataclass
class Anomaly:
    """Represents a detected forensic anomaly."""

    anomaly_id: str
    title: str
    description: str
    severity: AnomalySeverity
    category: AnomalyCategory
    timestamp: Optional[datetime] = None
    linked_events: List[ForensicEvent] = field(default_factory=list)
    confidence: float = 0.95
