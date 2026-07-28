"""
PhoneTrace -- Evidence Validation Module
==========================================

Validates the integrity of parsed forensic evidence.

Checks performed:
    1. All required evidence files exist.
    2. SQLite databases open and contain expected tables/columns.
    3. JSON files parse without errors.
    4. Timestamps are valid datetimes within the expected range.
    5. Record counts are reasonable.
    6. Chrome timestamps use the correct 1601-01-01 epoch.

Produces a structured :class:`ValidationReport`.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("artifacts.validation")


# ---------------------------------------------------------------------------
# Validation Report
# ---------------------------------------------------------------------------

@dataclass
class ValidationCheck:
    """Result of a single validation check.

    Attributes:
        name: Short description of the check.
        passed: Whether the check passed.
        detail: Additional detail (especially on failure).
    """
    name: str
    passed: bool
    detail: str = ""


@dataclass
class ValidationReport:
    """Aggregated results from all validation checks.

    Attributes:
        checks: List of individual check results.
        is_valid: True if every check passed.
    """
    checks: List[ValidationCheck] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if all checks passed."""
        return all(c.passed for c in self.checks)

    @property
    def passed_count(self) -> int:
        """Number of checks that passed."""
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        """Number of checks that failed."""
        return sum(1 for c in self.checks if not c.passed)

    def add(self, name: str, passed: bool, detail: str = "") -> None:
        """Add a check result."""
        self.checks.append(ValidationCheck(name, passed, detail))
        status = "PASS" if passed else "FAIL"
        msg = f"  [{status}] {name}"
        if detail and not passed:
            msg += f" -- {detail}"
        logger.info(msg) if passed else logger.warning(msg)

    def print_report(self) -> None:
        """Print a formatted validation report to stdout."""
        print()
        print("=" * 60)
        print("  PhoneTrace -- Evidence Validation Report")
        print("=" * 60)
        print()
        for check in self.checks:
            status = "[PASS]" if check.passed else "[FAIL]"
            line = f"  {status} {check.name}"
            if check.detail and not check.passed:
                line += f" -- {check.detail}"
            print(line)
        print()
        print(f"  Results: {self.passed_count} passed, "
              f"{self.failed_count} failed")
        if self.is_valid:
            print("  Validation PASSED.")
        else:
            print("  Validation FAILED.")
        print()
        print("=" * 60)


# ---------------------------------------------------------------------------
# Expected schemas
# ---------------------------------------------------------------------------

_EXPECTED_SCHEMAS = {
    "calllog.db": {
        "table": "calls",
        "columns": {"_id", "number", "date", "duration", "type", "name"},
    },
    "mmssms.db": {
        "table": "sms",
        "columns": {"_id", "address", "date", "body", "type"},
    },
    "chrome_history.db": {
        "table": "urls",
        "columns": {"_id", "url", "title", "visit_count", "last_visit_time"},
    },
    "app_usage.db": {
        "table": "app_usage",
        "columns": {"_id", "package_name", "event_type", "timestamp"},
    },
}

_REQUIRED_JSON = ["gps_log.json", "file_metadata.json"]

_ALL_REQUIRED_FILES = list(_EXPECTED_SCHEMAS.keys()) + _REQUIRED_JSON

# Chrome timestamp minimum for year 2025
_CHROME_MIN_2025 = 13_380_000_000_000_000


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class EvidenceValidator:
    """Validates evidence files for structural integrity.

    Args:
        evidence_dir: Path to the evidence output directory.
    """

    def __init__(self, evidence_dir: str | Path) -> None:
        self._evidence_dir = Path(evidence_dir)

    def validate(self) -> ValidationReport:
        """Run all validation checks and return a report.

        Returns:
            A :class:`ValidationReport` with all check results.
        """
        report = ValidationReport()

        self._check_files_exist(report)
        self._check_sqlite_schemas(report)
        self._check_json_valid(report)
        self._check_chrome_timestamps(report)
        self._check_record_counts(report)
        self._check_timestamp_ranges(report)

        return report

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_files_exist(self, report: ValidationReport) -> None:
        """Verify all required evidence files exist."""
        for fname in _ALL_REQUIRED_FILES:
            path = self._evidence_dir / fname
            report.add(
                f"{fname} exists",
                path.is_file(),
                f"Not found: {path}",
            )

    def _check_sqlite_schemas(self, report: ValidationReport) -> None:
        """Verify SQLite databases have correct tables and columns."""
        for db_name, spec in _EXPECTED_SCHEMAS.items():
            db_path = self._evidence_dir / db_name
            if not db_path.is_file():
                continue

            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.execute(
                    f"PRAGMA table_info({spec['table']})"
                )
                columns = {row[1] for row in cursor.fetchall()}
                conn.close()

                missing = spec["columns"] - columns
                report.add(
                    f"{db_name}: table '{spec['table']}' schema correct",
                    len(missing) == 0,
                    f"Missing columns: {missing}" if missing else "",
                )
            except sqlite3.DatabaseError as exc:
                report.add(
                    f"{db_name}: database accessible",
                    False,
                    str(exc),
                )

    def _check_json_valid(self, report: ValidationReport) -> None:
        """Verify JSON files parse without errors."""
        for json_name in _REQUIRED_JSON:
            json_path = self._evidence_dir / json_name
            if not json_path.is_file():
                continue

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                report.add(
                    f"{json_name}: valid JSON",
                    isinstance(data, list) and len(data) > 0,
                    f"Expected non-empty list, got {type(data).__name__}",
                )
            except json.JSONDecodeError as exc:
                report.add(f"{json_name}: valid JSON", False, str(exc))

    def _check_chrome_timestamps(self, report: ValidationReport) -> None:
        """Verify Chrome timestamps use the 1601-01-01 epoch."""
        db_path = self._evidence_dir / "chrome_history.db"
        if not db_path.is_file():
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute(
                "SELECT MIN(last_visit_time) FROM urls"
            )
            min_ts = cursor.fetchone()[0]
            conn.close()

            report.add(
                "Chrome timestamps use 1601 epoch",
                min_ts is not None and min_ts > _CHROME_MIN_2025,
                f"Min timestamp = {min_ts}",
            )
        except sqlite3.DatabaseError as exc:
            report.add("Chrome timestamps accessible", False, str(exc))

    def _check_record_counts(self, report: ValidationReport) -> None:
        """Verify record counts are reasonable (> 0)."""
        for db_name, spec in _EXPECTED_SCHEMAS.items():
            db_path = self._evidence_dir / db_name
            if not db_path.is_file():
                continue

            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.execute(
                    f"SELECT COUNT(*) FROM {spec['table']}"
                )
                count = cursor.fetchone()[0]
                conn.close()

                report.add(
                    f"{db_name}: has records",
                    count > 0,
                    f"Count = {count}",
                )
            except sqlite3.DatabaseError:
                pass

        for json_name in _REQUIRED_JSON:
            json_path = self._evidence_dir / json_name
            if not json_path.is_file():
                continue
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                report.add(
                    f"{json_name}: has records",
                    isinstance(data, list) and len(data) > 0,
                    f"Count = {len(data) if isinstance(data, list) else 'N/A'}",
                )
            except (json.JSONDecodeError, Exception):
                pass

    def _check_timestamp_ranges(self, report: ValidationReport) -> None:
        """Verify timestamps fall within an expected date range."""
        # Check call log date range as a representative sample
        db_path = self._evidence_dir / "calllog.db"
        if not db_path.is_file():
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute(
                "SELECT MIN(date), MAX(date) FROM calls"
            )
            min_ts, max_ts = cursor.fetchone()
            conn.close()

            if min_ts and max_ts:
                min_dt = datetime.fromtimestamp(
                    min_ts / 1000, tz=timezone.utc
                )
                max_dt = datetime.fromtimestamp(
                    max_ts / 1000, tz=timezone.utc
                )
                span_days = (max_dt - min_dt).days
                report.add(
                    "Timestamp range spans ~21 days",
                    15 <= span_days <= 30,
                    f"Span = {span_days} days "
                    f"({min_dt.date()} to {max_dt.date()})",
                )
        except (sqlite3.DatabaseError, Exception) as exc:
            report.add("Timestamp range check", False, str(exc))
