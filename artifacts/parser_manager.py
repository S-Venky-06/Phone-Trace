"""
PhoneTrace -- Parser Manager
==============================

Unified API for loading and accessing all parsed forensic artifacts.

Future phases should interact **only** with :class:`ParserManager` --
never with SQLite databases or JSON files directly.

Usage::

    from artifacts import ParserManager

    manager = ParserManager("evidence_output")
    manager.load_all()

    for call in manager.calls:
        print(call.number, call.timestamp)

    # Unified sorted timeline across all evidence types
    for event in manager.get_all_records():
        print(event.timestamp, event.event_type, event.description)
"""

from __future__ import annotations

import io
import logging
import sys
from pathlib import Path
from typing import List, Optional

from artifacts.base import BaseParser
from artifacts.calls import CallParser
from artifacts.sms import SMSParser
from artifacts.browser import BrowserParser
from artifacts.gps import GPSParser
from artifacts.app_usage import AppUsageParser
from artifacts.filesystem import FilesystemParser
from artifacts.models import (
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

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )

logger = logging.getLogger("artifacts.ParserManager")


class ParserManager:
    """Central manager that orchestrates all artifact parsers.

    Attributes:
        calls: Parsed call records (populated after :meth:`load_all`).
        sms: Parsed SMS records.
        browser: Parsed browser history records.
        gps: Parsed GPS pings.
        app_usage: Parsed app usage events.
        files: Parsed file metadata records.

    Args:
        evidence_dir: Path to the evidence output directory.
            Defaults to ``evidence_output`` relative to the project root.
    """

    def __init__(self, evidence_dir: str | Path | None = None) -> None:
        if evidence_dir is None:
            # Default: evidence_output/ relative to project root
            project_root = Path(__file__).resolve().parent.parent
            evidence_dir = project_root / "evidence_output"
        self._evidence_dir = Path(evidence_dir)

        # Parsed data stores (populated by load_all)
        self.calls: List[CallRecord] = []
        self.sms: List[SMSRecord] = []
        self.browser: List[BrowserRecord] = []
        self.gps: List[GPSRecord] = []
        self.app_usage: List[AppUsageRecord] = []
        self.files: List[FileRecord] = []

        # Parser instances (for skip tracking)
        self._parsers: List[BaseParser] = []

        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def load_all(self) -> None:
        """Execute every parser and populate all data stores.

        This is the primary entry point. Call once, then access
        ``manager.calls``, ``manager.sms``, etc.

        Raises:
            FileNotFoundError: If the evidence directory does not exist.
        """
        if not self._evidence_dir.is_dir():
            raise FileNotFoundError(
                f"Evidence directory not found: {self._evidence_dir}"
            )

        logger.info(
            "Loading all evidence from %s ...", self._evidence_dir
        )

        call_parser = CallParser(self._evidence_dir)
        sms_parser = SMSParser(self._evidence_dir)
        browser_parser = BrowserParser(self._evidence_dir)
        gps_parser = GPSParser(self._evidence_dir)
        app_parser = AppUsageParser(self._evidence_dir)
        fs_parser = FilesystemParser(self._evidence_dir)

        self._parsers = [
            call_parser, sms_parser, browser_parser,
            gps_parser, app_parser, fs_parser,
        ]

        self.calls = call_parser.parse()
        self.sms = sms_parser.parse()
        self.browser = browser_parser.parse()
        self.gps = gps_parser.parse()
        self.app_usage = app_parser.parse()
        self.files = fs_parser.parse()

        self._loaded = True
        logger.info("All evidence loaded successfully.")

    def get_all_records(self) -> List[TimelineEvent]:
        """Return a unified, timestamp-sorted list of all parsed records.

        Wraps every parsed record into a :class:`TimelineEvent` and sorts
        them chronologically. This gives downstream phases a single
        timeline to work with.

        Returns:
            Sorted list of TimelineEvent across all evidence types.
        """
        if not self._loaded:
            raise RuntimeError(
                "Call load_all() before get_all_records()."
            )

        events: List[TimelineEvent] = []

        for r in self.calls:
            direction = r.call_type.name.lower()
            name = r.contact_name or r.number
            events.append(TimelineEvent(
                timestamp=r.timestamp,
                event_type="call",
                source="calllog.db",
                description=f"{direction} call {name} ({r.duration_seconds}s)",
                raw_record=r,
            ))

        for r in self.sms:
            direction = "from" if r.sms_type == SMSType.RECEIVED else "to"
            events.append(TimelineEvent(
                timestamp=r.timestamp,
                event_type="sms",
                source="mmssms.db",
                description=f"SMS {direction} {r.address}",
                raw_record=r,
            ))

        for r in self.browser:
            events.append(TimelineEvent(
                timestamp=r.last_visit_time,
                event_type="browser",
                source="chrome_history.db",
                description=f"Visited {r.title}",
                raw_record=r,
            ))

        for r in self.gps:
            events.append(TimelineEvent(
                timestamp=r.timestamp,
                event_type="gps",
                source="gps_log.json",
                description=(
                    f"GPS ({r.latitude:.4f}, {r.longitude:.4f}) "
                    f"acc={r.accuracy}m via {r.provider}"
                ),
                raw_record=r,
            ))

        for r in self.app_usage:
            action = "opened" if r.event_type.value == 1 else "closed"
            events.append(TimelineEvent(
                timestamp=r.timestamp,
                event_type="app_usage",
                source="app_usage.db",
                description=f"{action} {r.package_name}",
                raw_record=r,
            ))

        for r in self.files:
            events.append(TimelineEvent(
                timestamp=r.created,
                event_type="file",
                source="file_metadata.json",
                description=f"File created: {r.filename} ({r.mime_type})",
                raw_record=r,
            ))

        events.sort(key=lambda e: e.timestamp)
        return events

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def total_skipped(self) -> int:
        """Total number of records skipped across all parsers."""
        return sum(p.skipped_count for p in self._parsers)

    def summary(self) -> None:
        """Print a concise summary of parsed evidence to stdout."""
        if not self._loaded:
            print("  ParserManager: No data loaded. Call load_all() first.")
            return

        print()
        print("=" * 60)
        print("  PhoneTrace -- Parser Summary")
        print("=" * 60)
        print()
        print(f"  Evidence directory: {self._evidence_dir}")
        print()
        print(f"    Calls ............. {len(self.calls):>6}")
        print(f"    SMS ............... {len(self.sms):>6}")
        print(f"    Browser visits .... {len(self.browser):>6}")
        print(f"    GPS pings ......... {len(self.gps):>6}")
        print(f"    App usage events .. {len(self.app_usage):>6}")
        print(f"    File metadata ..... {len(self.files):>6}")
        total = (
            len(self.calls) + len(self.sms) + len(self.browser)
            + len(self.gps) + len(self.app_usage) + len(self.files)
        )
        print(f"    {'':->30}")
        print(f"    Total records ..... {total:>6}")
        print()
        if self.total_skipped:
            print(f"    Skipped records ... {self.total_skipped:>6}")
        else:
            print("    Skipped records ...      0")
        print()
        print("=" * 60)
