"""
PhoneTrace -- Evidence Correlator
===================================

Rule-based engine that automatically identifies forensic relationships
between timeline events across different artifact types.

Correlation rules:
    1. Communication Cluster  -- calls/SMS to same contact within N min
    2. Movement Cluster       -- significant GPS displacement
    3. Browser + GPS          -- Maps opened near GPS movement
    4. File + GPS             -- photo taken near GPS location
    5. SMS + Browser          -- SMS received then browser opened
    6. Call + Movement        -- call followed by GPS travel
    7. App + Movement         -- nav app opened before GPS movement

Each rule is a standalone method that can be individually enabled or
disabled. All thresholds are driven by :class:`CorrelationConfig`.
"""

from __future__ import annotations

import logging
import math
from datetime import timedelta
from typing import Callable, Dict, List, Optional, Set, Tuple

from timeline.models import (
    CorrelationConfig,
    CorrelationGroup,
    EventLocation,
    ForensicEvent,
)

logger = logging.getLogger("timeline.EvidenceCorrelator")

# Type alias for correlation rule functions
RuleFn = Callable[
    [List[ForensicEvent], CorrelationConfig],
    List[CorrelationGroup],
]


# ---------------------------------------------------------------------------
# Geo-distance helper
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS points in kilometres."""
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


def _within_minutes(
    e1: ForensicEvent, e2: ForensicEvent, minutes: float,
) -> bool:
    """Check if two events are within N minutes of each other."""
    return abs((e1.timestamp - e2.timestamp).total_seconds()) <= minutes * 60


# ---------------------------------------------------------------------------
# Built-in correlation rules
# ---------------------------------------------------------------------------

def _rule_communication_cluster(
    events: List[ForensicEvent],
    config: CorrelationConfig,
) -> List[CorrelationGroup]:
    """Group calls/SMS to the same contact within a short time window.

    A cluster forms when multiple communications (call or SMS) involve
    the same phone number within ``communication_cluster_minutes``.
    """
    groups: List[CorrelationGroup] = []
    comm_events = [e for e in events if e.artifact_type in ("call", "sms")]

    if not comm_events:
        return groups

    # Group by contact number
    by_contact: Dict[str, List[ForensicEvent]] = {}
    for e in comm_events:
        number = e.metadata.get("number") or e.metadata.get("address", "")
        if number:
            by_contact.setdefault(number, []).append(e)

    window = timedelta(minutes=config.communication_cluster_minutes)

    for number, contact_events in by_contact.items():
        contact_events.sort(key=lambda e: e.timestamp)

        # Sliding window to find clusters
        cluster: List[ForensicEvent] = [contact_events[0]]
        for evt in contact_events[1:]:
            if (evt.timestamp - cluster[-1].timestamp) <= window:
                cluster.append(evt)
            else:
                if len(cluster) >= 2:
                    anchor = cluster[0]
                    correlated = cluster[1:]
                    for c in correlated:
                        anchor.related.append(c)
                        c.related.append(anchor)
                    groups.append(CorrelationGroup(
                        rule_name="communication_cluster",
                        anchor_event=anchor,
                        correlated_events=correlated,
                    ))
                cluster = [evt]

        # Close final cluster
        if len(cluster) >= 2:
            anchor = cluster[0]
            correlated = cluster[1:]
            for c in correlated:
                anchor.related.append(c)
                c.related.append(anchor)
            groups.append(CorrelationGroup(
                rule_name="communication_cluster",
                anchor_event=anchor,
                correlated_events=correlated,
            ))

    return groups


def _rule_movement_cluster(
    events: List[ForensicEvent],
    config: CorrelationConfig,
) -> List[CorrelationGroup]:
    """Detect significant GPS displacement sequences.

    Groups consecutive GPS pings where cumulative movement exceeds
    ``gps_movement_threshold_km``.
    """
    groups: List[CorrelationGroup] = []
    gps_events = [e for e in events if e.artifact_type == "gps" and e.location]

    if len(gps_events) < 2:
        return groups

    cluster: List[ForensicEvent] = [gps_events[0]]

    for i in range(1, len(gps_events)):
        prev_loc = gps_events[i - 1].location
        curr_loc = gps_events[i].location
        dist = _haversine_km(
            prev_loc.latitude, prev_loc.longitude,
            curr_loc.latitude, curr_loc.longitude,
        )

        if dist >= config.gps_movement_threshold_km:
            cluster.append(gps_events[i])
        else:
            if len(cluster) >= 2:
                groups.append(CorrelationGroup(
                    rule_name="movement_cluster",
                    anchor_event=cluster[0],
                    correlated_events=cluster[1:],
                ))
                for c in cluster[1:]:
                    cluster[0].related.append(c)
            cluster = [gps_events[i]]

    if len(cluster) >= 2:
        groups.append(CorrelationGroup(
            rule_name="movement_cluster",
            anchor_event=cluster[0],
            correlated_events=cluster[1:],
        ))
        for c in cluster[1:]:
            cluster[0].related.append(c)

    return groups


def _rule_browser_gps(
    events: List[ForensicEvent],
    config: CorrelationConfig,
) -> List[CorrelationGroup]:
    """Correlate Maps/directions URLs with nearby GPS movement.

    Fires when a Google Maps or directions URL is opened within
    ``time_window_minutes`` of a significant GPS movement.
    """
    groups: List[CorrelationGroup] = []
    maps_keywords = ("maps", "directions", "navigate", "route")

    browser_events = [
        e for e in events
        if e.artifact_type == "browser"
        and any(kw in e.metadata.get("url", "").lower() for kw in maps_keywords)
    ]
    gps_events = [e for e in events if e.artifact_type == "gps" and e.location]

    for b_evt in browser_events:
        for g_evt in gps_events:
            if _within_minutes(b_evt, g_evt, config.time_window_minutes):
                b_evt.related.append(g_evt)
                g_evt.related.append(b_evt)
                groups.append(CorrelationGroup(
                    rule_name="browser_gps",
                    anchor_event=b_evt,
                    correlated_events=[g_evt],
                ))
                break  # One GPS match per browser event

    return groups


def _rule_file_gps(
    events: List[ForensicEvent],
    config: CorrelationConfig,
) -> List[CorrelationGroup]:
    """Correlate file creation with nearby GPS pings.

    Fires when a photo/file is created within ``time_window_minutes``
    of a GPS ping, and the GPS ping is within ``location_proximity_m``.
    """
    groups: List[CorrelationGroup] = []
    file_events = [e for e in events if e.artifact_type == "file"]
    gps_events = [e for e in events if e.artifact_type == "gps" and e.location]

    proximity_km = config.location_proximity_m / 1000.0

    for f_evt in file_events:
        for g_evt in gps_events:
            if _within_minutes(f_evt, g_evt, config.time_window_minutes):
                # Found a temporally close GPS ping
                f_evt.related.append(g_evt)
                groups.append(CorrelationGroup(
                    rule_name="file_gps",
                    anchor_event=f_evt,
                    correlated_events=[g_evt],
                ))
                # Attach location to file event if not already set
                if f_evt.location is None:
                    f_evt.location = g_evt.location
                break

    return groups


def _rule_sms_browser(
    events: List[ForensicEvent],
    config: CorrelationConfig,
) -> List[CorrelationGroup]:
    """Correlate SMS receipt with subsequent browser activity.

    Fires when an SMS is received and a browser visit occurs within
    ``time_window_minutes``.
    """
    groups: List[CorrelationGroup] = []
    sms_events = [
        e for e in events
        if e.artifact_type == "sms"
        and e.metadata.get("sms_type") == "received"
    ]
    browser_events = [e for e in events if e.artifact_type == "browser"]

    for s_evt in sms_events:
        for b_evt in browser_events:
            delta = (b_evt.timestamp - s_evt.timestamp).total_seconds()
            if 0 < delta <= config.time_window_minutes * 60:
                s_evt.related.append(b_evt)
                b_evt.related.append(s_evt)
                groups.append(CorrelationGroup(
                    rule_name="sms_browser",
                    anchor_event=s_evt,
                    correlated_events=[b_evt],
                ))
                break

    return groups


def _rule_call_movement(
    events: List[ForensicEvent],
    config: CorrelationConfig,
) -> List[CorrelationGroup]:
    """Correlate calls with subsequent GPS movement.

    Fires when an outgoing call is followed by significant GPS
    displacement within ``time_window_minutes``.
    """
    groups: List[CorrelationGroup] = []
    call_events = [
        e for e in events
        if e.artifact_type == "call"
        and e.metadata.get("call_type") in ("outgoing", "incoming")
    ]
    gps_events = [e for e in events if e.artifact_type == "gps" and e.location]

    if len(gps_events) < 2:
        return groups

    for c_evt in call_events:
        # Find GPS pings shortly after the call
        nearby_gps = [
            g for g in gps_events
            if 0 <= (g.timestamp - c_evt.timestamp).total_seconds()
            <= config.time_window_minutes * 60
        ]
        if len(nearby_gps) >= 2:
            dist = _haversine_km(
                nearby_gps[0].location.latitude,
                nearby_gps[0].location.longitude,
                nearby_gps[-1].location.latitude,
                nearby_gps[-1].location.longitude,
            )
            if dist >= config.gps_movement_threshold_km:
                for g in nearby_gps:
                    c_evt.related.append(g)
                groups.append(CorrelationGroup(
                    rule_name="call_movement",
                    anchor_event=c_evt,
                    correlated_events=nearby_gps,
                ))

    return groups


def _rule_app_movement(
    events: List[ForensicEvent],
    config: CorrelationConfig,
) -> List[CorrelationGroup]:
    """Correlate navigation app usage with GPS movement.

    Fires when a navigation-related app is opened before significant
    GPS displacement.
    """
    groups: List[CorrelationGroup] = []
    nav_packages = (
        "com.google.android.apps.maps",
        "com.waze",
        "com.ubercab",
        "com.olacabs.customer",
    )

    app_events = [
        e for e in events
        if e.artifact_type == "app_usage"
        and e.metadata.get("event_type") == "foreground"
        and e.metadata.get("package_name", "") in nav_packages
    ]
    gps_events = [e for e in events if e.artifact_type == "gps" and e.location]

    if len(gps_events) < 2:
        return groups

    for a_evt in app_events:
        nearby_gps = [
            g for g in gps_events
            if 0 <= (g.timestamp - a_evt.timestamp).total_seconds()
            <= config.time_window_minutes * 60
        ]
        if len(nearby_gps) >= 2:
            dist = _haversine_km(
                nearby_gps[0].location.latitude,
                nearby_gps[0].location.longitude,
                nearby_gps[-1].location.latitude,
                nearby_gps[-1].location.longitude,
            )
            if dist >= config.gps_movement_threshold_km:
                for g in nearby_gps:
                    a_evt.related.append(g)
                groups.append(CorrelationGroup(
                    rule_name="app_movement",
                    anchor_event=a_evt,
                    correlated_events=nearby_gps,
                ))

    return groups


# ---------------------------------------------------------------------------
# Correlator Engine
# ---------------------------------------------------------------------------

class EvidenceCorrelator:
    """Rule-based evidence correlation engine.

    Automatically identifies forensic relationships between events
    from different artifact sources.

    Args:
        config: Correlation thresholds. If None, defaults are used.

    Usage::

        correlator = EvidenceCorrelator()
        groups = correlator.correlate(timeline_events)
    """

    def __init__(self, config: Optional[CorrelationConfig] = None) -> None:
        self._config = config or CorrelationConfig()
        self._rules: List[Tuple[str, RuleFn]] = []
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register all built-in correlation rules."""
        self._rules = [
            ("Communication Cluster", _rule_communication_cluster),
            ("Movement Cluster", _rule_movement_cluster),
            ("Browser + GPS", _rule_browser_gps),
            ("File + GPS", _rule_file_gps),
            ("SMS + Browser", _rule_sms_browser),
            ("Call + Movement", _rule_call_movement),
            ("App + Movement", _rule_app_movement),
        ]

    def add_rule(self, name: str, rule_fn: RuleFn) -> None:
        """Register a custom correlation rule.

        Args:
            name: Human-readable rule name.
            rule_fn: Function ``(events, config) -> list[CorrelationGroup]``.
        """
        self._rules.append((name, rule_fn))
        logger.info("Registered correlation rule: %s", name)

    def correlate(
        self,
        events: List[ForensicEvent],
    ) -> List[CorrelationGroup]:
        """Run all correlation rules against the timeline.

        Each rule may append to ``event.related`` and produce
        :class:`CorrelationGroup` objects.

        Args:
            events: Chronologically sorted ForensicEvents.

        Returns:
            List of all detected CorrelationGroups.
        """
        logger.info("Running correlation with %d rules...", len(self._rules))
        all_groups: List[CorrelationGroup] = []

        for name, rule_fn in self._rules:
            try:
                groups = rule_fn(events, self._config)
                all_groups.extend(groups)
                if groups:
                    logger.info(
                        "  Rule '%s': %d groups detected.", name, len(groups)
                    )
            except Exception as exc:
                logger.warning(
                    "  Rule '%s' failed: %s", name, exc
                )

        logger.info(
            "Correlation complete: %d groups detected.", len(all_groups)
        )
        return all_groups

    @property
    def rule_names(self) -> List[str]:
        """List of registered rule names."""
        return [name for name, _ in self._rules]
