"""
PhoneTrace -- App Usage Parser
================================

Parses ``app_usage.db`` and returns a list of :class:`AppUsageRecord`.

Database schema (Phase 1)::

    app_usage (_id, package_name, event_type, timestamp)

- ``timestamp`` is Unix epoch milliseconds.
- ``event_type`` maps to :class:`AppEventType`
  (1=foreground, 2=background).
"""

from __future__ import annotations

from typing import List

from artifacts.base import BaseParser
from artifacts.models import AppEventType, AppUsageRecord

DB_NAME = "app_usage.db"
TABLE = "app_usage"


class AppUsageParser(BaseParser):
    """Parser for Android app usage artifacts."""

    def parse(self) -> List[AppUsageRecord]:
        """Parse app_usage.db and return typed AppUsageRecord objects.

        Returns:
            Sorted list of AppUsageRecord (by timestamp ascending).

        Raises:
            FileNotFoundError: If app_usage.db is missing.
        """
        rows = self._query_all(DB_NAME, TABLE, order_by="timestamp")
        records: List[AppUsageRecord] = []

        for row in rows:
            try:
                record = AppUsageRecord(
                    id=row["_id"],
                    package_name=row["package_name"],
                    event_type=AppEventType.from_int(row["event_type"]),
                    timestamp=self._epoch_ms_to_datetime(row["timestamp"]),
                )
                records.append(record)
            except Exception as exc:
                self._skip_record(row["_id"], str(exc))

        self._logger.info("Parsed %d app usage events.", len(records))
        return records
