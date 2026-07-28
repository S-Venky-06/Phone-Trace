"""
PhoneTrace -- Anomaly Detection Rules
========================================

Individual detection rules evaluating forensic timeline events for suspicious behavior,
alibi contradictions, and data discrepancies.
"""

from __future__ import annotations

import logging
from typing import List

from case_config import ALIBI_LOCATION, INCIDENT_LOCATION, INCIDENT_START, INCIDENT_END
from anomaly_detection.models import Anomaly, AnomalyCategory, AnomalySeverity
from timeline.models import ForensicEvent

logger = logging.getLogger("anomaly.rules")


def detect_alibi_contradiction(events: List[ForensicEvent]) -> List[Anomaly]:
    """Detect GPS pings placing the device away from alibi location during incident window."""
    anomalies = []
    incident_gps = [
        e for e in events
        if e.artifact_type == "gps"
        and e.timestamp
        and e.location is not None
        and INCIDENT_START <= e.timestamp <= INCIDENT_END
    ]

    for idx, event in enumerate(incident_gps):
        lat = event.location.latitude
        lon = event.location.longitude
        inc_lat = INCIDENT_LOCATION["latitude"]
        inc_lon = INCIDENT_LOCATION["longitude"]

        # Check proximity to Incident Location (within 0.05 degrees ~5km)
        if abs(lat - inc_lat) < 0.05 and abs(lon - inc_lon) < 0.05:
            anomalies.append(
                Anomaly(
                    anomaly_id=f"ANOM-GPS-{idx+1:03d}",
                    title="GPS Location Contradicts Claimed Alibi",
                    description=(
                        f"Device GPS ping recorded at {event.timestamp.strftime('%H:%M:%S')} IST "
                        f"near {INCIDENT_LOCATION['name']} ({lat:.4f}, {lon:.4f}), contradicting "
                        f"suspect's claimed presence at {ALIBI_LOCATION['name']}."
                    ),
                    severity=AnomalySeverity.CRITICAL,
                    category=AnomalyCategory.ALIBI_CONTRADICTION,
                    timestamp=event.timestamp,
                    linked_events=[event],
                    confidence=0.98,
                )
            )
    return anomalies


def detect_burner_phone_contact(events: List[ForensicEvent]) -> List[Anomaly]:
    """Detect calls or SMS with unknown/unnamed contacts during or near incident window."""
    anomalies = []
    incident_comms = [
        e for e in events
        if e.artifact_type in ("call", "sms")
        and e.timestamp
        and INCIDENT_START <= e.timestamp <= INCIDENT_END
    ]

    for idx, event in enumerate(incident_comms):
        meta = event.metadata or {}
        contact_name = meta.get("contact_name") or meta.get("name")
        number = meta.get("number") or meta.get("address") or ""

        if not contact_name or contact_name == "Unknown":
            anomalies.append(
                Anomaly(
                    anomaly_id=f"ANOM-COMM-{idx+1:03d}",
                    title=f"Incident Window Communication with Unknown Contact ({number})",
                    description=(
                        f"{event.artifact_type.upper()} event with unknown number {number} "
                        f"at {event.timestamp.strftime('%H:%M:%S')} IST during the incident window. "
                        f"Indicates potential burner phone communication."
                    ),
                    severity=AnomalySeverity.HIGH,
                    category=AnomalyCategory.BURNER_PHONE,
                    timestamp=event.timestamp,
                    linked_events=[event],
                    confidence=0.92,
                )
            )
    return anomalies


def detect_timezone_discrepancy(events: List[ForensicEvent]) -> List[Anomaly]:
    """Detect browser or file timestamps recorded in UTC instead of IST timezone."""
    anomalies = []
    browser_events = [e for e in events if e.artifact_type == "browser"]

    for idx, event in enumerate(browser_events):
        meta = event.metadata or {}
        if meta.get("is_utc") or "UTC" in event.description:
            anomalies.append(
                Anomaly(
                    anomaly_id=f"ANOM-TZ-{idx+1:03d}",
                    title="Browser Timestamp Timezone Discrepancy",
                    description=(
                        f"Chrome visit to '{event.title}' recorded with raw UTC timestamp "
                        f"differing from system local timezone offset."
                    ),
                    severity=AnomalySeverity.MEDIUM,
                    category=AnomalyCategory.TIMEZONE_DISCREPANCY,
                    timestamp=event.timestamp,
                    linked_events=[event],
                    confidence=0.88,
                )
            )
    return anomalies
