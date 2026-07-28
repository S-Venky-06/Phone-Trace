"""
PhoneTrace -- Bookmark & Tag Manager
========================================

Tracks user-bookmarked events and tags during investigation.
Persists data to ``bookmarks.json`` in the project root.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("gui.bookmarks")

_BOOKMARKS_FILE = "bookmarks.json"


@dataclass
class BookmarkItem:
    """Dataclass for a bookmarked event."""

    event_id: str
    title: str
    artifact_type: str
    timestamp_str: str
    tag: str = "Suspicious"  # Default tags: "Suspicious", "Alibi Contradiction", "Key Evidence", "Verified"
    notes: str = ""


class BookmarkManager:
    """Manages bookmarks and tags for forensic events."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent.parent
        self._root = Path(project_root)
        self._path = self._root / _BOOKMARKS_FILE
        self._bookmarks: Dict[str, BookmarkItem] = {}
        self._load()

    def add_bookmark(
        self,
        event_id: str,
        title: str,
        artifact_type: str,
        timestamp_str: str,
        tag: str = "Suspicious",
        notes: str = "",
    ) -> BookmarkItem:
        item = BookmarkItem(
            event_id=event_id,
            title=title,
            artifact_type=artifact_type,
            timestamp_str=timestamp_str,
            tag=tag,
            notes=notes,
        )
        self._bookmarks[event_id] = item
        self._save()
        logger.info("Bookmarked event: %s (%s)", title, tag)
        return item

    def remove_bookmark(self, event_id: str) -> bool:
        if event_id in self._bookmarks:
            del self._bookmarks[event_id]
            self._save()
            logger.info("Removed bookmark: %s", event_id)
            return True
        return False

    def is_bookmarked(self, event_id: str) -> bool:
        return event_id in self._bookmarks

    def get_bookmark(self, event_id: str) -> Optional[BookmarkItem]:
        return self._bookmarks.get(event_id)

    @property
    def bookmarks(self) -> List[BookmarkItem]:
        return list(self._bookmarks.values())

    def _save(self) -> None:
        try:
            data = [asdict(b) for b in self._bookmarks.values()]
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.error("Failed to save bookmarks: %s", exc)

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._bookmarks = {
                item["event_id"]: BookmarkItem(**item) for item in data
            }
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning("Could not load bookmarks: %s", exc)
