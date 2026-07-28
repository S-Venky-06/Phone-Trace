"""
PhoneTrace -- Artifacts Package
================================

Reusable Android forensic artifact parsing framework.

Quick start::

    from artifacts import ParserManager

    manager = ParserManager("evidence_output")
    manager.load_all()

    calls   = manager.calls        # list[CallRecord]
    sms     = manager.sms          # list[SMSRecord]
    browser = manager.browser      # list[BrowserRecord]
    gps     = manager.gps          # list[GPSRecord]
    apps    = manager.app_usage    # list[AppUsageRecord]
    files   = manager.files        # list[FileRecord]

    events  = manager.get_all_records()  # list[TimelineEvent]
"""

# Models (dataclasses and enums)
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
    TimelineEvent,
)

# Parsers
from artifacts.base import BaseParser
from artifacts.calls import CallParser
from artifacts.sms import SMSParser
from artifacts.browser import BrowserParser
from artifacts.gps import GPSParser
from artifacts.app_usage import AppUsageParser
from artifacts.filesystem import FilesystemParser

# Manager
from artifacts.parser_manager import ParserManager

# Validation
from artifacts.validation import EvidenceValidator, ValidationReport

__all__ = [
    # Enums
    "CallType",
    "SMSType",
    "AppEventType",
    # Models
    "CallRecord",
    "SMSRecord",
    "BrowserRecord",
    "GPSRecord",
    "AppUsageRecord",
    "FileRecord",
    "TimelineEvent",
    # Parsers
    "BaseParser",
    "CallParser",
    "SMSParser",
    "BrowserParser",
    "GPSParser",
    "AppUsageParser",
    "FilesystemParser",
    # Manager
    "ParserManager",
    # Validation
    "EvidenceValidator",
    "ValidationReport",
]
