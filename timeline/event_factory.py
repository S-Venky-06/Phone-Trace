"""
PhoneTrace -- Event Factory
=============================

Registry-based converter that transforms Phase 2 parsed records into
Phase 3 :class:`ForensicEvent` objects.

The factory uses a registry pattern: each record type has a registered
converter function. To add support for a new artifact type, simply call::

    factory.register(NewRecordType, my_converter_function)

No existing code needs to change.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Type

from artifacts.models import (
    AppEventType,
    AppUsageRecord,
    BrowserRecord,
    CallRecord,
    CallType,
    FileRecord,
    GPSRecord,
    SMSRecord,
    SMSType,
)
from timeline.models import EventLocation, ForensicEvent

logger = logging.getLogger("timeline.EventFactory")

# Type alias for converter functions
ConverterFn = Callable[[Any, int], ForensicEvent]


# ---------------------------------------------------------------------------
# Built-in converters
# ---------------------------------------------------------------------------

def _convert_call(record: CallRecord, idx: int) -> ForensicEvent:
    """Convert a CallRecord into a ForensicEvent."""
    type_label = record.call_type.name.capitalize()
    contact = record.contact_name or record.number
    duration = record.duration_seconds

    if record.call_type == CallType.MISSED:
        title = "Missed Call"
        desc = f"Missed call from {contact}"
    elif record.call_type == CallType.OUTGOING:
        title = "Outgoing Call"
        desc = f"Outgoing call to {contact} ({duration}s)"
    elif record.call_type == CallType.INCOMING:
        title = "Incoming Call"
        desc = f"Incoming call from {contact} ({duration}s)"
    else:
        title = "Call"
        desc = f"Call with {contact} ({duration}s)"

    return ForensicEvent(
        timestamp=record.timestamp,
        artifact_type="call",
        title=title,
        description=desc,
        source="calllog.db",
        raw_record=record,
        metadata={
            "number": record.number,
            "contact_name": record.contact_name,
            "duration_seconds": duration,
            "call_type": type_label.lower(),
        },
    )


def _convert_sms(record: SMSRecord, idx: int) -> ForensicEvent:
    """Convert an SMSRecord into a ForensicEvent."""
    if record.sms_type == SMSType.RECEIVED:
        title = "SMS Received"
        desc = f"SMS from {record.address}: {record.body[:80]}"
    elif record.sms_type == SMSType.SENT:
        title = "SMS Sent"
        desc = f"SMS to {record.address}: {record.body[:80]}"
    else:
        title = "SMS"
        desc = f"SMS with {record.address}: {record.body[:80]}"

    return ForensicEvent(
        timestamp=record.timestamp,
        artifact_type="sms",
        title=title,
        description=desc,
        source="mmssms.db",
        raw_record=record,
        metadata={
            "address": record.address,
            "sms_type": record.sms_type.name.lower(),
            "body": record.body,
        },
    )


def _convert_browser(record: BrowserRecord, idx: int) -> ForensicEvent:
    """Convert a BrowserRecord into a ForensicEvent."""
    title = "Web Visit"
    desc = f"Visited: {record.title} ({record.url[:80]})"

    return ForensicEvent(
        timestamp=record.last_visit_time,
        artifact_type="browser",
        title=title,
        description=desc,
        source="chrome_history.db",
        raw_record=record,
        metadata={
            "url": record.url,
            "page_title": record.title,
            "visit_count": record.visit_count,
            "raw_chrome_timestamp": record.raw_chrome_timestamp,
        },
    )


def _convert_gps(record: GPSRecord, idx: int) -> ForensicEvent:
    """Convert a GPSRecord into a ForensicEvent."""
    title = "GPS Ping"
    desc = (
        f"Location ({record.latitude:.4f}, {record.longitude:.4f}) "
        f"acc={record.accuracy}m via {record.provider}"
    )

    return ForensicEvent(
        timestamp=record.timestamp,
        artifact_type="gps",
        title=title,
        description=desc,
        source="gps_log.json",
        location=EventLocation(
            latitude=record.latitude,
            longitude=record.longitude,
            accuracy=record.accuracy,
        ),
        raw_record=record,
        metadata={
            "provider": record.provider,
            "accuracy": record.accuracy,
        },
    )


def _convert_app_usage(record: AppUsageRecord, idx: int) -> ForensicEvent:
    """Convert an AppUsageRecord into a ForensicEvent."""
    if record.event_type == AppEventType.FOREGROUND:
        title = "App Opened"
        action = "opened"
    elif record.event_type == AppEventType.BACKGROUND:
        title = "App Closed"
        action = "closed"
    else:
        title = "App Event"
        action = "event"

    desc = f"{record.package_name} {action}"

    return ForensicEvent(
        timestamp=record.timestamp,
        artifact_type="app_usage",
        title=title,
        description=desc,
        source="app_usage.db",
        raw_record=record,
        metadata={
            "package_name": record.package_name,
            "event_type": record.event_type.name.lower(),
        },
    )


def _convert_file(record: FileRecord, idx: int) -> ForensicEvent:
    """Convert a FileRecord into a ForensicEvent."""
    title = "File Created"
    desc = f"{record.filename} ({record.mime_type}, {record.size_bytes} bytes)"

    return ForensicEvent(
        timestamp=record.created,
        artifact_type="file",
        title=title,
        description=desc,
        source="file_metadata.json",
        raw_record=record,
        metadata={
            "filename": record.filename,
            "path": record.path,
            "mime_type": record.mime_type,
            "size_bytes": record.size_bytes,
            "md5_hash": record.md5_hash,
        },
    )


# ---------------------------------------------------------------------------
# Event Factory
# ---------------------------------------------------------------------------

class EventFactory:
    """Registry-based converter from parsed records to ForensicEvents.

    Usage::

        factory = EventFactory()
        events = factory.convert_all(parser_manager.calls)

    To add a new artifact type::

        factory.register(MyNewRecord, my_converter_fn)

    Converter function signature::

        def my_converter(record: MyNewRecord, idx: int) -> ForensicEvent:
            ...
    """

    def __init__(self) -> None:
        self._registry: Dict[Type, ConverterFn] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in converters for all Phase 2 record types."""
        self._registry[CallRecord] = _convert_call
        self._registry[SMSRecord] = _convert_sms
        self._registry[BrowserRecord] = _convert_browser
        self._registry[GPSRecord] = _convert_gps
        self._registry[AppUsageRecord] = _convert_app_usage
        self._registry[FileRecord] = _convert_file

    def register(self, record_type: Type, converter: ConverterFn) -> None:
        """Register a converter for a new record type.

        Args:
            record_type: The dataclass type to convert.
            converter: Function that takes ``(record, index)`` and
                returns a :class:`ForensicEvent`.
        """
        self._registry[record_type] = converter
        logger.info("Registered converter for %s", record_type.__name__)

    def convert(self, record: Any, idx: int = 0) -> Optional[ForensicEvent]:
        """Convert a single parsed record into a ForensicEvent.

        Args:
            record: A Phase 2 dataclass record.
            idx: Optional index for ordering.

        Returns:
            A ForensicEvent, or None if conversion fails.
        """
        converter = self._registry.get(type(record))
        if converter is None:
            logger.warning(
                "No converter registered for %s", type(record).__name__
            )
            return None

        try:
            return converter(record, idx)
        except Exception as exc:
            logger.warning(
                "Failed to convert %s #%d: %s",
                type(record).__name__, idx, exc,
            )
            return None

    def convert_all(self, records: List[Any]) -> List[ForensicEvent]:
        """Convert a list of parsed records into ForensicEvents.

        Records that fail conversion are skipped with a warning.

        Args:
            records: List of Phase 2 dataclass records (all same type).

        Returns:
            List of successfully converted ForensicEvents.
        """
        events: List[ForensicEvent] = []
        for idx, record in enumerate(records):
            event = self.convert(record, idx)
            if event is not None:
                events.append(event)
        return events

    @property
    def supported_types(self) -> List[str]:
        """List of registered record type names."""
        return [t.__name__ for t in self._registry]
