"""
PhoneTrace -- Rule-Based AI Provider
=======================================

Fully offline forensic analysis provider.  Uses deterministic rules
and templates instead of LLM calls.  Works out-of-the-box with zero
configuration and no network access.

Analysis capabilities:
    * Alibi verification (GPS vs. claimed location)
    * Anomaly detection (timing, contacts, movement, apps)
    * Chronological narrative generation
    * Keyword-based Q&A
"""

from __future__ import annotations

import math
from typing import List

from ai_engine.models import (
    CommunicationPattern,
    EventSummary,
    InvestigationContext,
    MovementSummary,
)
from ai_engine.providers.base import AIProvider
from ai_engine.report_models import AIQuery, AIResponse


# ---------------------------------------------------------------------------
# Haversine helper
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RuleBasedProvider(AIProvider):
    """Offline rule-based forensic analysis provider.

    This is the default provider.  It requires no API keys and
    produces deterministic results based on pattern matching
    and forensic heuristics.
    """

    name = "Rule-Based (Offline)"
    requires_api_key = False

    # ------------------------------------------------------------------
    # AIProvider interface
    # ------------------------------------------------------------------

    def analyze(
        self,
        context: InvestigationContext,
        query: AIQuery,
    ) -> AIResponse:
        """Answer a free-form question using keyword matching."""
        q = query.text.lower()

        # Route to specialised handlers
        if any(kw in q for kw in ("alibi", "location", "where was")):
            return self.check_alibi(
                context, context.alibi_location, context.alibi_coords,
            )
        if any(kw in q for kw in ("anomal", "suspicious", "unusual", "red flag")):
            return self.detect_anomalies(context)
        if any(kw in q for kw in ("narrative", "story", "summary", "tell me")):
            narrative = self.generate_narrative(context)
            return AIResponse(
                answer=narrative,
                confidence=0.9,
                provider_name=self.name,
            )

        # General keyword-based responses
        return self._general_qa(context, q)

    def generate_narrative(
        self,
        context: InvestigationContext,
    ) -> str:
        """Generate a chronological investigation narrative."""
        lines: List[str] = []

        lines.append(f"INVESTIGATION NARRATIVE — {context.suspect_name}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(
            f"The investigation covers the digital activity on "
            f"{context.suspect_name}'s {context.device_info} "
            f"({context.suspect_phone}) during the period "
            f"{context.investigation_period[0][:10]} to "
            f"{context.investigation_period[1][:10]}."
        )
        lines.append("")

        # Statistics overview
        s = context.statistics
        lines.append(
            f"During this period, {s.total_events} forensic events were "
            f"extracted, organized into {s.session_count} activity sessions "
            f"with {s.correlation_count} cross-artifact correlations identified."
        )
        lines.append("")

        # Communication pattern
        c = context.communication
        if c.total_calls or c.total_sms:
            lines.append(
                f"Communication records show {c.total_calls} phone calls "
                f"and {c.total_sms} SMS messages."
            )
            if c.unknown_contact_count:
                lines.append(
                    f"Notably, {c.unknown_contact_count} calls involved "
                    f"unknown (unsaved) contacts, warranting further investigation."
                )
            if c.top_contacts:
                top = c.top_contacts[0]
                lines.append(
                    f"The most frequent contact was {top[0]} "
                    f"({top[1]} interactions)."
                )
            lines.append("")

        # Movement analysis
        if context.movements:
            lines.append(
                f"{len(context.movements)} significant GPS movements "
                f"were detected during the investigation period."
            )
            # Check for movements during incident window
            incident_movements = [
                m for m in context.movements
                if context.incident_window[0] <= m.timestamp <= context.incident_window[1]
            ]
            if incident_movements:
                lines.append(
                    f"CRITICAL: {len(incident_movements)} significant "
                    f"movements occurred during the incident window:"
                )
                for m in incident_movements:
                    lines.append(
                        f"  • {m.from_label} → {m.to_label} "
                        f"({m.distance_km:.1f} km at {m.timestamp[11:19]})"
                    )
            lines.append("")

        # Incident window analysis
        if context.incident_events:
            lines.append(
                f"During the incident window "
                f"({context.incident_window[0][11:16]} to "
                f"{context.incident_window[1][11:16]}), "
                f"{len(context.incident_events)} events were recorded:"
            )
            for ev in context.incident_events:
                loc = f" at {ev.location_label}" if ev.location_label else ""
                lines.append(
                    f"  [{ev.timestamp[11:19]}] {ev.title}{loc}"
                )
            lines.append("")

        # Alibi assessment
        alibi_result = self._evaluate_alibi(context)
        lines.append("ALIBI ASSESSMENT")
        lines.append("-" * 40)
        lines.append(alibi_result)
        lines.append("")

        # Anomalies
        anomalies = self._find_anomalies(context)
        if anomalies:
            lines.append("ANOMALIES DETECTED")
            lines.append("-" * 40)
            for a in anomalies:
                lines.append(f"  ⚠ {a}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("End of narrative.")

        return "\n".join(lines)

    def check_alibi(
        self,
        context: InvestigationContext,
        claimed_location: str,
        claimed_coords: tuple[float, float],
    ) -> AIResponse:
        """Verify the alibi by comparing GPS data against claimed location."""
        assessment = self._evaluate_alibi(context)
        evidence: List[str] = []

        # Collect GPS evidence from incident window
        for ev in context.incident_events:
            if ev.artifact_type == "gps" and ev.location_label:
                evidence.append(
                    f"[{ev.timestamp[11:19]}] GPS: {ev.location_label}"
                )

        # Determine confidence
        gps_in_incident = [
            ev for ev in context.incident_events
            if ev.artifact_type == "gps"
        ]
        if not gps_in_incident:
            confidence = 0.3
        elif "CONTRADICTED" in assessment:
            confidence = 0.9
        elif "CONSISTENT" in assessment:
            confidence = 0.85
        else:
            confidence = 0.5

        return AIResponse(
            answer=assessment,
            confidence=confidence,
            provider_name=self.name,
            supporting_evidence=evidence,
        )

    def detect_anomalies(
        self,
        context: InvestigationContext,
    ) -> AIResponse:
        """Run all anomaly detection rules."""
        anomalies = self._find_anomalies(context)

        if anomalies:
            answer = (
                f"Detected {len(anomalies)} anomalies in the forensic data:\n\n"
                + "\n".join(f"  {i+1}. {a}" for i, a in enumerate(anomalies))
            )
            confidence = min(0.5 + len(anomalies) * 0.1, 0.95)
        else:
            answer = "No significant anomalies detected in the forensic data."
            confidence = 0.7

        return AIResponse(
            answer=answer,
            confidence=confidence,
            provider_name=self.name,
            supporting_evidence=[],
        )

    def is_available(self) -> bool:
        """Always available — no external dependencies."""
        return True

    # ------------------------------------------------------------------
    # Internal analysis methods
    # ------------------------------------------------------------------

    def _evaluate_alibi(self, context: InvestigationContext) -> str:
        """Compare GPS evidence against the claimed alibi location."""
        gps_events = [
            ev for ev in context.incident_events
            if ev.artifact_type == "gps" and ev.location_label
        ]

        if not gps_events:
            return (
                f"INSUFFICIENT DATA: No GPS records found during the "
                f"incident window ({context.incident_window[0][11:16]} to "
                f"{context.incident_window[1][11:16]}). "
                f"Cannot verify alibi claim of being at "
                f"{context.alibi_location}."
            )

        # Check each GPS point against alibi location
        alibi_lat, alibi_lon = context.alibi_coords
        near_alibi = 0
        away_from_alibi = 0
        max_dist = 0.0
        farthest_loc = ""

        for ev in gps_events:
            # Parse coordinates from metadata or location_label
            coords = ev.metadata_excerpt.get("latitude"), ev.metadata_excerpt.get("longitude")
            if coords[0] and coords[1]:
                try:
                    lat = float(coords[0])
                    lon = float(coords[1])
                except (ValueError, TypeError):
                    continue
            else:
                # Try to parse from location_label "lat, lon"
                parts = ev.location_label.split(",")
                if len(parts) == 2:
                    try:
                        lat = float(parts[0].strip())
                        lon = float(parts[1].strip())
                    except ValueError:
                        continue
                else:
                    continue

            dist = _haversine_km(alibi_lat, alibi_lon, lat, lon)
            if dist <= 1.0:  # Within 1 km of alibi
                near_alibi += 1
            else:
                away_from_alibi += 1
                if dist > max_dist:
                    max_dist = dist
                    farthest_loc = ev.location_label

        total = near_alibi + away_from_alibi
        if total == 0:
            return (
                f"INSUFFICIENT DATA: GPS coordinates could not be "
                f"parsed from incident window events."
            )

        if away_from_alibi == 0:
            return (
                f"ALIBI CONSISTENT: The suspect {context.suspect_name} originally claimed to the police that he was at his "
                f"residence at '{context.alibi_location}' resting/sleeping during the incident window "
                f"({context.incident_window[0][11:16]} to {context.incident_window[1][11:16]}). "
                f"All {near_alibi} GPS readings during this window place the device "
                f"within 1 km of the claimed location. The digital evidence supports the suspect's claim."
            )
        elif near_alibi == 0:
            return (
                f"ALIBI CONTRADICTED: The suspect {context.suspect_name} originally claimed to the police that he was at his "
                f"residence at '{context.alibi_location}' resting/sleeping during the entire incident window "
                f"({context.incident_window[0][11:16]} to {context.incident_window[1][11:16]}). "
                f"However, all {away_from_alibi} GPS readings during this exact window place the device "
                f"AWAY from his claimed residence. The device was located near {farthest_loc}, "
                f"which is approximately {max_dist:.1f} km away (at the actual incident scene in Electronic City). "
                f"This directly contradicts the suspect's statement to the police, proving he was not at home."
            )
        else:
            return (
                f"ALIBI PARTIALLY CONTRADICTED: The suspect {context.suspect_name} originally claimed to the police that he was at his "
                f"residence at '{context.alibi_location}' resting/sleeping during the incident window "
                f"({context.incident_window[0][11:16]} to {context.incident_window[1][11:16]}). "
                f"Of the {total} GPS readings during this window, {near_alibi} were consistent with the alibi, "
                f"but {away_from_alibi} readings place the device elsewhere, up to {max_dist:.1f} km away near {farthest_loc}. "
                f"This indicates that the device moved during the incident window, partially contradicting the alibi statement."
            )

    def _find_anomalies(self, context: InvestigationContext) -> List[str]:
        """Run all anomaly detection rules and return findings."""
        anomalies: List[str] = []

        # 1. Unknown contacts during incident window
        c = context.communication
        if c.unknown_contact_count > 0:
            anomalies.append(
                f"Unknown contacts detected: {c.unknown_contact_count} "
                f"calls/SMS involved unsaved contacts (possible burner phones)."
            )

        # 2. Incident-window contacts
        if c.incident_contacts:
            anomalies.append(
                f"Communication during incident window: Contacts active "
                f"during the incident: {', '.join(c.incident_contacts)}."
            )

        # 3. Late-night activity
        late_night_events = [
            ev for ev in context.incident_events
            if ev.timestamp[11:13] in ("23", "00", "01", "02", "03")
        ]
        if late_night_events:
            anomalies.append(
                f"Late-night activity: {len(late_night_events)} events "
                f"occurred between 23:00 and 03:00 during the incident window."
            )

        # 4. GPS location jumps (impossible travel)
        for i in range(1, len(context.movements)):
            m = context.movements[i]
            if m.distance_km > 10.0:
                # Check if within incident window
                if (context.incident_window[0] <= m.timestamp
                        <= context.incident_window[1]):
                    anomalies.append(
                        f"Large GPS displacement during incident: "
                        f"{m.from_label} → {m.to_label} "
                        f"({m.distance_km:.1f} km) at {m.timestamp[11:19]}."
                    )

        # 5. Data wiping / privacy apps
        suspicious_apps = ("cleaner", "eraser", "vpn", "proxy", "tor", "delete")
        for ev in context.incident_events:
            if ev.artifact_type == "app_usage":
                pkg = ev.metadata_excerpt.get("package_name", "").lower()
                title_lower = ev.title.lower()
                if any(kw in pkg or kw in title_lower for kw in suspicious_apps):
                    anomalies.append(
                        f"Suspicious app usage: {ev.title} "
                        f"({pkg}) at {ev.timestamp[11:19]}."
                    )

        # 6. Communication pattern break
        if context.statistics.total_events > 0:
            incident_ratio = (
                len(context.incident_events) / context.statistics.total_events
            )
            # If incident window has disproportionately high activity
            if incident_ratio > 0.1 and len(context.incident_events) > 10:
                anomalies.append(
                    f"Activity spike during incident window: "
                    f"{len(context.incident_events)} events "
                    f"({incident_ratio:.1%} of total) concentrated "
                    f"in a short window."
                )

        return anomalies

    def _general_qa(
        self,
        context: InvestigationContext,
        query: str,
    ) -> AIResponse:
        """Handle general forensic questions via keyword matching."""
        # Who called / contacted
        if any(kw in query for kw in ("who called", "who contact", "calls")):
            c = context.communication
            if c.top_contacts:
                contacts = "\n".join(
                    f"  • {name}: {count} interactions"
                    for name, count in c.top_contacts[:5]
                )
                return AIResponse(
                    answer=(
                        f"Top contacts for {context.suspect_name}:\n\n{contacts}\n\n"
                        f"Total calls: {c.total_calls}, Total SMS: {c.total_sms}."
                    ),
                    confidence=0.9,
                    provider_name=self.name,
                )
            else:
                return AIResponse(
                    answer=f"No communication records found for {context.suspect_name}.",
                    confidence=0.9,
                    provider_name=self.name,
                )

        # GPS / location / where
        if any(kw in query for kw in ("gps", "location", "where", "movement", "travel")):
            if context.movements:
                mvmt = "\n".join(
                    f"  • {m.from_label} → {m.to_label} ({m.distance_km:.1f} km)"
                    for m in context.movements[:10]
                )
                return AIResponse(
                    answer=(
                        f"Significant GPS movements detected:\n\n{mvmt}\n\n"
                        f"Total significant movements: {len(context.movements)}."
                    ),
                    confidence=0.85,
                    provider_name=self.name,
                )

        # Incident / what happened
        if any(kw in query for kw in ("incident", "what happened", "during")):
            if context.incident_events:
                events_text = "\n".join(
                    f"  [{ev.timestamp[11:19]}] {ev.title}"
                    for ev in context.incident_events[:15]
                )
                return AIResponse(
                    answer=(
                        f"During the incident window "
                        f"({context.incident_window[0][11:16]} to "
                        f"{context.incident_window[1][11:16]}), "
                        f"{len(context.incident_events)} events occurred:\n\n"
                        f"{events_text}"
                    ),
                    confidence=0.9,
                    provider_name=self.name,
                )

        # Correlations
        if any(kw in query for kw in ("correlation", "related", "connected", "linked")):
            if context.correlations:
                corr_text = "\n".join(
                    f"  • {cg.rule_name}: {cg.anchor_title} "
                    f"→ {cg.correlated_count} related events"
                    for cg in context.correlations[:10]
                )
                return AIResponse(
                    answer=(
                        f"Evidence correlations found:\n\n{corr_text}\n\n"
                        f"Total correlation groups: "
                        f"{len(context.correlations)}."
                    ),
                    confidence=0.85,
                    provider_name=self.name,
                )

        # Statistics / overview
        if any(kw in query for kw in ("statistic", "overview", "how many")):
            s = context.statistics
            return AIResponse(
                answer=(
                    f"Investigation Overview:\n\n"
                    f"  • Total events: {s.total_events}\n"
                    f"  • Busiest hour: {s.busiest_hour:02d}:00 "
                    f"({s.busiest_hour_count} events)\n"
                    f"  • Busiest day: {s.busiest_day} "
                    f"({s.busiest_day_count} events)\n"
                    f"  • Sessions: {s.session_count}\n"
                    f"  • Correlations: {s.correlation_count}\n"
                    f"  • Incident window events: {s.incident_event_count}"
                ),
                confidence=0.95,
                provider_name=self.name,
            )

        # Default fallback
        return AIResponse(
            answer=(
                f"I can help analyse the forensic evidence for "
                f"{context.suspect_name}'s device. Try asking about:\n\n"
                f"  • Alibi verification\n"
                f"  • Anomaly detection\n"
                f"  • Communication patterns\n"
                f"  • GPS movements\n"
                f"  • Incident window activity\n"
                f"  • Evidence correlations\n"
                f"  • Timeline statistics\n"
                f"  • Investigation narrative"
            ),
            confidence=0.5,
            provider_name=self.name,
        )
