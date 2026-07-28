"""
PhoneTrace -- GPS Log Parser
==============================

Parses ``gps_log.json`` and returns a list of :class:`GPSRecord` objects.

JSON structure (Phase 1)::

    [
      {
        "timestamp": "2025-06-01T07:00:00+05:30",
        "latitude": 12.935327,
        "longitude": 77.6244,
        "accuracy": 19.5,
        "provider": "fused"
      },
      ...
    ]

- ``timestamp`` is an ISO 8601 string with timezone offset.
"""

from __future__ import annotations

from typing import List

from artifacts.base import BaseParser
from artifacts.models import GPSRecord

JSON_NAME = "gps_log.json"


class GPSParser(BaseParser):
    """Parser for GPS location log artifacts."""

    def parse(self) -> List[GPSRecord]:
        """Parse gps_log.json and return typed GPSRecord objects.

        Returns:
            Sorted list of GPSRecord (by timestamp ascending).

        Raises:
            FileNotFoundError: If gps_log.json is missing.
        """
        data = self._load_json(JSON_NAME)
        records: List[GPSRecord] = []

        for idx, entry in enumerate(data):
            try:
                record = GPSRecord(
                    id=idx,
                    timestamp=self._iso_to_datetime(entry["timestamp"]),
                    latitude=float(entry["latitude"]),
                    longitude=float(entry["longitude"]),
                    accuracy=float(entry["accuracy"]),
                    provider=str(entry["provider"]),
                )
                records.append(record)
            except Exception as exc:
                self._skip_record(idx, str(exc))

        # Sort by timestamp (should already be sorted, but enforce)
        records.sort(key=lambda r: r.timestamp)

        self._logger.info("Parsed %d GPS pings.", len(records))
        return records
