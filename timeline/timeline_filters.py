"""
PhoneTrace -- Timeline Filters & Search
=========================================

Reusable filter and search operations for the forensic timeline.

All methods accept a list of :class:`ForensicEvent` and return a
filtered subset. They are composable -- chain multiple calls to
narrow results progressively.

The ``TimelineFilter`` class is stateless and can be reused freely.
Future GUI and reporting modules should use these filters rather
than implementing their own filtering logic.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional

from timeline.models import ForensicEvent


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in kilometres."""
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


class TimelineFilter:
    """Stateless filter and search engine for ForensicEvent lists.

    Every method returns a new filtered list without modifying the
    input. Methods are composable::

        filtered = (
            TimelineFilter.by_date(events, start, end)
            |> TimelineFilter.by_artifact(_, "call")
            |> TimelineFilter.by_contact(_, "+919876501001")
        )

    Or equivalently::

        f = TimelineFilter()
        result = f.by_contact(
            f.by_artifact(
                f.by_date(events, start, end),
                "call",
            ),
            "+919876501001",
        )
    """

    @staticmethod
    def by_date(
        events: List[ForensicEvent],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[ForensicEvent]:
        """Filter events within a date/time range.

        Args:
            events: Input event list.
            start: Inclusive start time (or None for no lower bound).
            end: Inclusive end time (or None for no upper bound).

        Returns:
            Events falling within [start, end].
        """
        result = events
        if start is not None:
            result = [e for e in result if e.timestamp >= start]
        if end is not None:
            result = [e for e in result if e.timestamp <= end]
        return result

    @staticmethod
    def by_contact(
        events: List[ForensicEvent],
        name_or_number: str,
    ) -> List[ForensicEvent]:
        """Filter events involving a specific contact.

        Matches against phone numbers, contact names, and SMS addresses
        (case-insensitive partial match).

        Args:
            events: Input event list.
            name_or_number: Contact name or phone number to search for.

        Returns:
            Events involving the specified contact.
        """
        query = name_or_number.lower()
        result: List[ForensicEvent] = []

        for e in events:
            meta = e.metadata
            # Check number, address, contact_name
            number = str(meta.get("number", "")).lower()
            address = str(meta.get("address", "")).lower()
            contact = str(meta.get("contact_name", "") or "").lower()

            if query in number or query in address or query in contact:
                result.append(e)

        return result

    @staticmethod
    def by_location(
        events: List[ForensicEvent],
        latitude: float,
        longitude: float,
        radius_km: float = 1.0,
    ) -> List[ForensicEvent]:
        """Filter events near a geographic point.

        Args:
            events: Input event list.
            latitude: Center latitude.
            longitude: Center longitude.
            radius_km: Search radius in kilometres.

        Returns:
            Events with locations within the radius.
        """
        result: List[ForensicEvent] = []
        for e in events:
            if e.location is not None:
                dist = _haversine_km(
                    latitude, longitude,
                    e.location.latitude, e.location.longitude,
                )
                if dist <= radius_km:
                    result.append(e)
        return result

    @staticmethod
    def by_artifact(
        events: List[ForensicEvent],
        artifact_type: str,
    ) -> List[ForensicEvent]:
        """Filter events by artifact type.

        Args:
            events: Input event list.
            artifact_type: Type string (e.g. ``"call"``, ``"sms"``,
                ``"gps"``, ``"browser"``, ``"app_usage"``, ``"file"``).

        Returns:
            Events of the specified type.
        """
        return [e for e in events if e.artifact_type == artifact_type]

    @staticmethod
    def by_keyword(
        events: List[ForensicEvent],
        keyword: str,
    ) -> List[ForensicEvent]:
        """Filter events whose title or description contains a keyword.

        Case-insensitive.

        Args:
            events: Input event list.
            keyword: Search term.

        Returns:
            Events matching the keyword.
        """
        kw = keyword.lower()
        return [
            e for e in events
            if kw in e.title.lower() or kw in e.description.lower()
        ]

    @staticmethod
    def by_package(
        events: List[ForensicEvent],
        package_name: str,
    ) -> List[ForensicEvent]:
        """Filter app usage events by Android package name.

        Partial match supported (e.g. ``"whatsapp"`` matches
        ``"com.whatsapp"``).

        Args:
            events: Input event list.
            package_name: Full or partial package name.

        Returns:
            Matching app usage events.
        """
        pkg = package_name.lower()
        return [
            e for e in events
            if pkg in str(e.metadata.get("package_name", "")).lower()
        ]

    @staticmethod
    def by_file_type(
        events: List[ForensicEvent],
        mime_prefix: str,
    ) -> List[ForensicEvent]:
        """Filter file events by MIME type prefix.

        Args:
            events: Input event list.
            mime_prefix: MIME prefix (e.g. ``"image/"``, ``"application/pdf"``).

        Returns:
            File events matching the MIME prefix.
        """
        prefix = mime_prefix.lower()
        return [
            e for e in events
            if e.artifact_type == "file"
            and str(e.metadata.get("mime_type", "")).lower().startswith(prefix)
        ]

    @staticmethod
    def search(
        events: List[ForensicEvent],
        query: str,
    ) -> List[ForensicEvent]:
        """Unified search across all text fields of timeline events.

        Searches: title, description, and all string values in metadata
        (contact names, phone numbers, URLs, filenames, message text,
        browser titles, package names).

        Case-insensitive.

        Args:
            events: Input event list.
            query: Search query string.

        Returns:
            Events matching the query in any text field.
        """
        q = query.lower()
        results: List[ForensicEvent] = []

        for e in events:
            # Check title and description
            if q in e.title.lower() or q in e.description.lower():
                results.append(e)
                continue

            # Check all string metadata values
            for value in e.metadata.values():
                if isinstance(value, str) and q in value.lower():
                    results.append(e)
                    break

        return results
