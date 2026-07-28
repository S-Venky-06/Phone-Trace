"""
PhoneTrace -- SMS Parser
=========================

Parses ``mmssms.db`` and returns a list of :class:`SMSRecord` objects.

Database schema (Phase 1)::

    sms (_id, address, date, body, type)

- ``date`` is Unix epoch milliseconds.
- ``type`` maps to :class:`SMSType` (1=received, 2=sent).
"""

from __future__ import annotations

from typing import List

from artifacts.base import BaseParser
from artifacts.models import SMSRecord, SMSType

DB_NAME = "mmssms.db"
TABLE = "sms"


class SMSParser(BaseParser):
    """Parser for Android SMS artifacts."""

    def parse(self) -> List[SMSRecord]:
        """Parse mmssms.db and return typed SMSRecord objects.

        Returns:
            Sorted list of SMSRecord (by timestamp ascending).

        Raises:
            FileNotFoundError: If mmssms.db is missing.
        """
        rows = self._query_all(DB_NAME, TABLE, order_by="date")
        records: List[SMSRecord] = []

        for row in rows:
            try:
                record = SMSRecord(
                    id=row["_id"],
                    address=row["address"],
                    timestamp=self._epoch_ms_to_datetime(row["date"]),
                    body=row["body"],
                    sms_type=SMSType.from_int(row["type"]),
                )
                records.append(record)
            except Exception as exc:
                self._skip_record(row["_id"], str(exc))

        self._logger.info("Parsed %d SMS messages.", len(records))
        return records
