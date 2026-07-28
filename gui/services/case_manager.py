"""
PhoneTrace -- Case Manager
============================

Lightweight case state management for the GUI.
Tracks case metadata in a local JSON file.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("gui.cases")

_CASES_FILE = "cases.json"


@dataclass
class CaseInfo:
    """Metadata for a single forensic case."""
    case_id: str
    name: str
    investigator: str
    created: str  # ISO timestamp
    evidence_dir: str
    status: str = "Open"
    description: str = ""


class CaseManager:
    """Create / open / close / delete forensic cases.

    Stores case metadata in ``cases.json`` in the project root.
    """

    def __init__(self, project_root: str | Path | None = None) -> None:
        if project_root is None:
            project_root = Path(__file__).resolve().parent.parent.parent
        self._root = Path(project_root)
        self._path = self._root / _CASES_FILE
        self._cases: List[CaseInfo] = []
        self._active: Optional[CaseInfo] = None
        self._load()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_case(
        self,
        name: str,
        investigator: str,
        evidence_dir: str = "",
        description: str = "",
    ) -> CaseInfo:
        """Create a new case and save it."""
        case_id = f"CASE-{len(self._cases) + 1:04d}"
        if not evidence_dir:
            evidence_dir = str(self._root / "evidence_output")

        case = CaseInfo(
            case_id=case_id,
            name=name,
            investigator=investigator,
            created=datetime.now().isoformat(timespec="seconds"),
            evidence_dir=evidence_dir,
            description=description,
        )
        self._cases.append(case)
        self._active = case
        self._save()
        logger.info("Created case: %s (%s)", case.name, case.case_id)
        return case

    def open_case(self, case_id: str) -> Optional[CaseInfo]:
        """Set a case as the active case."""
        for case in self._cases:
            if case.case_id == case_id:
                self._active = case
                case.status = "Open"
                self._save()
                logger.info("Opened case: %s", case.name)
                return case
        return None

    def close_case(self, case_id: str) -> bool:
        """Mark a case as closed."""
        for case in self._cases:
            if case.case_id == case_id:
                case.status = "Closed"
                if self._active and self._active.case_id == case_id:
                    self._active = None
                self._save()
                logger.info("Closed case: %s", case.name)
                return True
        return False

    def delete_case(self, case_id: str) -> bool:
        """Remove a case from the list."""
        for i, case in enumerate(self._cases):
            if case.case_id == case_id:
                removed = self._cases.pop(i)
                if self._active and self._active.case_id == case_id:
                    self._active = None
                self._save()
                logger.info("Deleted case: %s", removed.name)
                return True
        return False

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @property
    def cases(self) -> List[CaseInfo]:
        """All known cases."""
        return list(self._cases)

    @property
    def active_case(self) -> Optional[CaseInfo]:
        """Currently active case, or None."""
        return self._active

    def search(self, query: str) -> List[CaseInfo]:
        """Search cases by name or investigator."""
        q = query.lower()
        return [
            c for c in self._cases
            if q in c.name.lower() or q in c.investigator.lower()
        ]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        try:
            data = {
                "cases": [asdict(c) for c in self._cases],
                "active_id": self._active.case_id if self._active else None,
            }
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.error("Failed to save cases: %s", exc)

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._cases = [CaseInfo(**c) for c in data.get("cases", [])]
            active_id = data.get("active_id")
            if active_id:
                self.open_case(active_id)
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.warning("Could not load cases: %s", exc)
