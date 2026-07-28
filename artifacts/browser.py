"""
PhoneTrace -- Browser History Parser
======================================

Parses ``chrome_history.db`` and returns a list of :class:`BrowserRecord`.

Database schema (Phase 1)::

    urls (_id, url, title, visit_count, last_visit_time)

- ``last_visit_time`` uses the Chrome/WebKit timestamp format:
  microseconds since **1601-01-01 00:00:00 UTC**.
- The raw Chrome timestamp is preserved alongside the converted datetime
  for forensic cross-reference.
"""

from __future__ import annotations

from typing import List

from artifacts.base import BaseParser
from artifacts.models import BrowserRecord

DB_NAME = "chrome_history.db"
TABLE = "urls"


class BrowserParser(BaseParser):
    """Parser for Chrome browser history artifacts."""

    def parse(self) -> List[BrowserRecord]:
        """Parse chrome_history.db and return typed BrowserRecord objects.

        Correctly converts Chrome timestamps (microseconds since
        1601-01-01 UTC) into Python datetime objects.

        Returns:
            Sorted list of BrowserRecord (by last_visit_time ascending).

        Raises:
            FileNotFoundError: If chrome_history.db is missing.
        """
        rows = self._query_all(DB_NAME, TABLE, order_by="last_visit_time")
        records: List[BrowserRecord] = []

        for row in rows:
            try:
                raw_ts = row["last_visit_time"]
                record = BrowserRecord(
                    id=row["_id"],
                    url=row["url"],
                    title=row["title"],
                    visit_count=row["visit_count"],
                    last_visit_time=self._chrome_ts_to_datetime(raw_ts),
                    raw_chrome_timestamp=raw_ts,
                )
                records.append(record)
            except Exception as exc:
                self._skip_record(row["_id"], str(exc))

        self._logger.info("Parsed %d browser visits.", len(records))
        return records
