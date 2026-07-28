"""
PhoneTrace -- Call Log Parser
===============================

Parses ``calllog.db`` and returns a list of :class:`CallRecord` objects.

Database schema (Phase 1)::

    calls (_id, number, date, duration, type, name)

- ``date`` is Unix epoch milliseconds.
- ``type`` maps to :class:`CallType` (1=incoming, 2=outgoing, 3=missed).
"""

from __future__ import annotations

from typing import List

from artifacts.base import BaseParser
from artifacts.models import CallRecord, CallType

DB_NAME = "calllog.db"
TABLE = "calls"


class CallParser(BaseParser):
    """Parser for Android call log artifacts."""

    def parse(self) -> List[CallRecord]:
        """Parse calllog.db and return typed CallRecord objects.

        Returns:
            Sorted list of CallRecord (by timestamp ascending).

        Raises:
            FileNotFoundError: If calllog.db is missing.
        """
        rows = self._query_all(DB_NAME, TABLE, order_by="date")
        records: List[CallRecord] = []

        for row in rows:
            try:
                record = CallRecord(
                    id=row["_id"],
                    number=row["number"],
                    timestamp=self._epoch_ms_to_datetime(row["date"]),
                    duration_seconds=row["duration"],
                    call_type=CallType.from_int(row["type"]),
                    contact_name=row["name"],
                )
                records.append(record)
            except Exception as exc:
                self._skip_record(row["_id"], str(exc))

        self._logger.info("Parsed %d calls.", len(records))
        return records
