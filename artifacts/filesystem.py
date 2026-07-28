"""
PhoneTrace -- Filesystem Metadata Parser
==========================================

Parses ``file_metadata.json`` and returns a list of :class:`FileRecord`.

JSON structure (Phase 1)::

    [
      {
        "filename": "IMG_20250601_143012_000.jpg",
        "path": "/sdcard/DCIM/Camera/IMG_20250601_143012_000.jpg",
        "size_bytes": 3456789,
        "created": "2025-06-01T14:30:12+05:30",
        "modified": "2025-06-01T14:30:22+05:30",
        "mime_type": "image/jpeg",
        "md5_hash": "a1b2c3d4..."
      },
      ...
    ]

Design note:
    The :class:`FileRecord` dataclass includes an ``exif_data`` field
    (defaulting to ``None``) so that a future EXIF extraction module
    can populate it without changing the model or this parser's API.
"""

from __future__ import annotations

from typing import List

from artifacts.base import BaseParser
from artifacts.models import FileRecord

JSON_NAME = "file_metadata.json"


class FilesystemParser(BaseParser):
    """Parser for Android filesystem metadata artifacts."""

    def parse(self) -> List[FileRecord]:
        """Parse file_metadata.json and return typed FileRecord objects.

        Returns:
            Sorted list of FileRecord (by creation time ascending).

        Raises:
            FileNotFoundError: If file_metadata.json is missing.
        """
        data = self._load_json(JSON_NAME)
        records: List[FileRecord] = []

        for idx, entry in enumerate(data):
            try:
                record = FileRecord(
                    id=idx,
                    filename=entry["filename"],
                    path=entry["path"],
                    size_bytes=int(entry["size_bytes"]),
                    created=self._iso_to_datetime(entry["created"]),
                    modified=self._iso_to_datetime(entry["modified"]),
                    mime_type=entry["mime_type"],
                    md5_hash=entry["md5_hash"],
                    exif_data=entry.get("exif_data"),  # Future extension
                )
                records.append(record)
            except Exception as exc:
                self._skip_record(idx, str(exc))

        # Sort by creation time
        records.sort(key=lambda r: r.created)

        self._logger.info("Parsed %d file metadata entries.", len(records))
        return records
