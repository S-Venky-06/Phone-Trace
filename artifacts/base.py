"""
PhoneTrace -- Base Parser
==========================

Abstract base class for all artifact parsers.

Provides:
    - Structured logging per parser
    - Safe SQLite and JSON file access
    - Timestamp conversion helpers (epoch ms, Chrome 1601, ISO 8601)
    - Error tracking (skipped record counting)

Every concrete parser inherits from BaseParser and implements ``parse()``.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List


# Chrome/WebKit epoch: 1601-01-01 00:00:00 UTC
_CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


class BaseParser(ABC):
    """Abstract base for all forensic artifact parsers.

    Subclasses must implement :meth:`parse` which reads the evidence
    file and returns a list of typed dataclass records.

    Args:
        evidence_dir: Path to the evidence output directory.
    """

    def __init__(self, evidence_dir: str | Path) -> None:
        self._evidence_dir = Path(evidence_dir)
        self._logger = logging.getLogger(
            f"artifacts.{self.__class__.__name__}"
        )
        self._skipped: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @abstractmethod
    def parse(self) -> List[Any]:
        """Parse the evidence file and return a list of typed records.

        Returns:
            A list of dataclass instances (e.g. CallRecord, SMSRecord).

        Raises:
            FileNotFoundError: If the evidence file does not exist.
        """
        ...  # pragma: no cover

    @property
    def skipped_count(self) -> int:
        """Number of records skipped due to parse errors."""
        return self._skipped

    # ------------------------------------------------------------------
    # SQLite helpers
    # ------------------------------------------------------------------

    def _open_sqlite(self, db_name: str) -> sqlite3.Connection:
        """Open a SQLite database from the evidence directory.

        Args:
            db_name: Filename of the database (e.g. ``calllog.db``).

        Returns:
            An open ``sqlite3.Connection``.

        Raises:
            FileNotFoundError: If the database file does not exist.
            sqlite3.DatabaseError: If the file is not a valid database.
        """
        db_path = self._evidence_dir / db_name
        if not db_path.is_file():
            raise FileNotFoundError(
                f"Evidence file not found: {db_path}"
            )
        self._logger.info("Loading %s ...", db_name)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _query_all(
        self,
        db_name: str,
        table: str,
        order_by: str | None = None,
    ) -> List[sqlite3.Row]:
        """Execute ``SELECT * FROM <table>`` and return all rows.

        Args:
            db_name: SQLite database filename.
            table: Table name to query.
            order_by: Optional column name for ORDER BY clause.

        Returns:
            List of sqlite3.Row objects.
        """
        conn = self._open_sqlite(db_name)
        try:
            sql = f"SELECT * FROM {table}"  # noqa: S608
            if order_by:
                sql += f" ORDER BY {order_by}"
            cursor = conn.execute(sql)
            return cursor.fetchall()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # JSON helpers
    # ------------------------------------------------------------------

    def _load_json(self, json_name: str) -> Any:
        """Load and parse a JSON file from the evidence directory.

        Args:
            json_name: Filename of the JSON file.

        Returns:
            Parsed JSON data (typically a list of dicts).

        Raises:
            FileNotFoundError: If the JSON file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
        """
        json_path = self._evidence_dir / json_name
        if not json_path.is_file():
            raise FileNotFoundError(
                f"Evidence file not found: {json_path}"
            )
        self._logger.info("Loading %s ...", json_name)
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # Timestamp conversions
    # ------------------------------------------------------------------

    @staticmethod
    def _epoch_ms_to_datetime(ms: int) -> datetime:
        """Convert Unix epoch milliseconds to a timezone-aware datetime.

        Args:
            ms: Milliseconds since 1970-01-01 00:00:00 UTC.

        Returns:
            Timezone-aware datetime in UTC.
        """
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)

    @staticmethod
    def _chrome_ts_to_datetime(chrome_us: int) -> datetime:
        """Convert a Chrome/WebKit timestamp to a timezone-aware datetime.

        Chrome stores timestamps as microseconds since 1601-01-01 UTC.

        Args:
            chrome_us: Microseconds since 1601-01-01 00:00:00 UTC.

        Returns:
            Timezone-aware datetime in UTC.
        """
        return _CHROME_EPOCH + timedelta(microseconds=chrome_us)

    @staticmethod
    def _iso_to_datetime(iso_str: str) -> datetime:
        """Parse an ISO 8601 timestamp string into a timezone-aware datetime.

        Handles both offset-aware (``+05:30``) and offset-naive strings.
        Naive strings are assumed to be UTC.

        Args:
            iso_str: ISO 8601 formatted string.

        Returns:
            Timezone-aware datetime.
        """
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def _skip_record(self, record_id: Any, reason: str) -> None:
        """Log a warning and increment the skip counter.

        Called when a single record cannot be parsed but the parser
        should continue processing remaining records.

        Args:
            record_id: Identifier of the problematic record.
            reason: Human-readable reason for skipping.
        """
        self._skipped += 1
        self._logger.warning(
            "Skipped record %s: %s", record_id, reason
        )
