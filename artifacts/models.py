"""
PhoneTrace -- Data Models
==========================

Strongly-typed dataclasses and enums for all parsed forensic artifacts.

Every parser in the framework returns instances of these models.
Future phases should consume these objects -- never raw database rows
or JSON dicts.

Enums
-----
    CallType        Incoming / Outgoing / Missed
    SMSType         Received / Sent
    AppEventType    Foreground / Background

Dataclasses
-----------
    CallRecord      Parsed call log entry
    SMSRecord       Parsed SMS entry
    BrowserRecord   Parsed Chrome history entry
    GPSRecord       Parsed GPS ping
    AppUsageRecord  Parsed app usage event
    FileRecord      Parsed file-system metadata entry
    TimelineEvent   Unified timeline entry (wraps any record)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CallType(IntEnum):
    """Android call log type codes."""
    INCOMING = 1
    OUTGOING = 2
    MISSED = 3
    UNKNOWN = 0

    @classmethod
    def from_int(cls, value: int) -> "CallType":
        """Safely convert an integer to a CallType, defaulting to UNKNOWN."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


class SMSType(IntEnum):
    """Android SMS type codes."""
    RECEIVED = 1
    SENT = 2
    UNKNOWN = 0

    @classmethod
    def from_int(cls, value: int) -> "SMSType":
        """Safely convert an integer to an SMSType, defaulting to UNKNOWN."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


class AppEventType(IntEnum):
    """Android UsageEvents type codes."""
    FOREGROUND = 1  # ACTIVITY_RESUMED
    BACKGROUND = 2  # ACTIVITY_PAUSED
    UNKNOWN = 0

    @classmethod
    def from_int(cls, value: int) -> "AppEventType":
        """Safely convert an integer to an AppEventType, defaulting to UNKNOWN."""
        try:
            return cls(value)
        except ValueError:
            return cls.UNKNOWN


# ---------------------------------------------------------------------------
# Record Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class CallRecord:
    """A single parsed call log entry.

    Attributes:
        id: Row ID from the database.
        number: Phone number (E.164 format or local).
        timestamp: When the call occurred (timezone-aware).
        duration_seconds: Call duration in seconds (0 for missed calls).
        call_type: Incoming, outgoing, or missed.
        contact_name: Saved contact name, or None if unknown.
    """
    id: int
    number: str
    timestamp: datetime
    duration_seconds: int
    call_type: CallType
    contact_name: Optional[str] = None


@dataclass(frozen=True, slots=True)
class SMSRecord:
    """A single parsed SMS entry.

    Attributes:
        id: Row ID from the database.
        address: Phone number of the other party.
        timestamp: When the message was sent/received (timezone-aware).
        body: Message content.
        sms_type: Received or sent.
    """
    id: int
    address: str
    timestamp: datetime
    body: str
    sms_type: SMSType


@dataclass(frozen=True, slots=True)
class BrowserRecord:
    """A single parsed Chrome browser history entry.

    Attributes:
        id: Row ID from the database.
        url: Full URL visited.
        title: Page title.
        visit_count: Number of visits to this URL.
        last_visit_time: When last visited (timezone-aware datetime).
        raw_chrome_timestamp: Original Chrome timestamp (microseconds
            since 1601-01-01 UTC) preserved for forensic analysis.
    """
    id: int
    url: str
    title: str
    visit_count: int
    last_visit_time: datetime
    raw_chrome_timestamp: int


@dataclass(frozen=True, slots=True)
class GPSRecord:
    """A single parsed GPS location ping.

    Attributes:
        id: Sequence index (GPS logs have no database ID).
        timestamp: When the ping was recorded (timezone-aware).
        latitude: Decimal degrees.
        longitude: Decimal degrees.
        accuracy: Accuracy in metres.
        provider: Location provider (gps, network, fused).
    """
    id: int
    timestamp: datetime
    latitude: float
    longitude: float
    accuracy: float
    provider: str


@dataclass(frozen=True, slots=True)
class AppUsageRecord:
    """A single parsed app usage event.

    Attributes:
        id: Row ID from the database.
        package_name: Android package name (e.g. com.whatsapp).
        event_type: Foreground or background transition.
        timestamp: When the event occurred (timezone-aware).
    """
    id: int
    package_name: str
    event_type: AppEventType
    timestamp: datetime


@dataclass(frozen=True, slots=True)
class FileRecord:
    """A single parsed file-system metadata entry.

    Designed for future EXIF extension -- the ``exif_data`` field can
    hold extracted EXIF metadata once that capability is added.

    Attributes:
        id: Sequence index.
        filename: Base filename.
        path: Full Android filesystem path.
        size_bytes: File size in bytes.
        created: File creation time (timezone-aware).
        modified: File modification time (timezone-aware).
        mime_type: MIME type string.
        md5_hash: MD5 hash of the file contents.
        exif_data: Optional dict for future EXIF extraction.
    """
    id: int
    filename: str
    path: str
    size_bytes: int
    created: datetime
    modified: datetime
    mime_type: str
    md5_hash: str
    exif_data: Optional[dict] = field(default=None)


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """A unified timeline entry that wraps any parsed record.

    Used by ParserManager.get_all_records() to provide a single
    sorted list across all evidence types.

    Attributes:
        timestamp: Event time (timezone-aware).
        event_type: Human-readable type (e.g. "call", "sms", "gps").
        source: Source file name (e.g. "calllog.db").
        description: Short human-readable summary.
        raw_record: The original typed dataclass record.
    """
    timestamp: datetime
    event_type: str
    source: str
    description: str
    raw_record: Any
