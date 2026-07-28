"""
PhoneTrace -- Timeline Export
===============================

Export the forensic timeline to JSON and CSV formats.

Handles serialization of datetimes, enums, optional locations,
and metadata dictionaries.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from timeline.models import ForensicEvent

logger = logging.getLogger("timeline.TimelineExporter")


class _EventEncoder(json.JSONEncoder):
    """Custom JSON encoder for ForensicEvent objects."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ForensicEvent):
            return self._serialize_event(obj)
        return super().default(obj)

    @staticmethod
    def _serialize_event(event: ForensicEvent) -> Dict[str, Any]:
        """Convert a ForensicEvent to a JSON-serializable dict."""
        result: Dict[str, Any] = {
            "timestamp": event.timestamp.isoformat(),
            "artifact_type": event.artifact_type,
            "title": event.title,
            "description": event.description,
            "source": event.source,
            "metadata": event.metadata,
        }

        if event.location is not None:
            result["location"] = {
                "latitude": event.location.latitude,
                "longitude": event.location.longitude,
                "accuracy": event.location.accuracy,
                "label": event.location.label,
            }
        else:
            result["location"] = None

        # Related events: just store count + types to avoid circular refs
        if event.related:
            result["related_count"] = len(event.related)
            result["related_types"] = list(
                {r.artifact_type for r in event.related}
            )
        else:
            result["related_count"] = 0
            result["related_types"] = []

        return result


class TimelineExporter:
    """Export ForensicEvent lists to JSON and CSV.

    Usage::

        exporter = TimelineExporter()
        exporter.to_json(events, "timeline.json")
        exporter.to_csv(events, "timeline.csv")
    """

    @staticmethod
    def to_json(
        events: List[ForensicEvent],
        output_path: str | Path,
        indent: int = 2,
    ) -> Path:
        """Export timeline events to a JSON file.

        Args:
            events: List of ForensicEvent objects.
            output_path: Destination file path.
            indent: JSON indentation level.

        Returns:
            Path to the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(events, f, cls=_EventEncoder, indent=indent,
                      ensure_ascii=False)

        logger.info(
            "Exported %d events to JSON: %s", len(events), path
        )
        return path

    @staticmethod
    def to_csv(
        events: List[ForensicEvent],
        output_path: str | Path,
    ) -> Path:
        """Export timeline events to a CSV file.

        Columns: timestamp, artifact_type, title, description, source,
        latitude, longitude, accuracy, related_count

        Args:
            events: List of ForensicEvent objects.
            output_path: Destination file path.

        Returns:
            Path to the written file.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "timestamp",
            "artifact_type",
            "title",
            "description",
            "source",
            "latitude",
            "longitude",
            "accuracy",
            "related_count",
        ]

        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for event in events:
                row = {
                    "timestamp": event.timestamp.isoformat(),
                    "artifact_type": event.artifact_type,
                    "title": event.title,
                    "description": event.description,
                    "source": event.source,
                    "latitude": (
                        event.location.latitude
                        if event.location else ""
                    ),
                    "longitude": (
                        event.location.longitude
                        if event.location else ""
                    ),
                    "accuracy": (
                        event.location.accuracy
                        if event.location else ""
                    ),
                    "related_count": len(event.related),
                }
                writer.writerow(row)

        logger.info(
            "Exported %d events to CSV: %s", len(events), path
        )
        return path
