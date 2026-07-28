#!/usr/bin/env python3
"""
PhoneTrace — Evidence Validation Script
=========================================

Automatically verifies that all generated evidence meets acceptance criteria:

    1. All 6 required files exist
    2. SQLite database schemas are correct
    3. JSON files are valid
    4. Timestamp ranges span the expected baseline period
    5. Record counts are within expected ranges
    6. Chrome timestamps use the correct 1601-01-01 epoch
    7. Injected anomalies are detectable:
       - GPS contradicts alibi (phone at Electronic City during incident)
       - Missing call gap exists
       - Suspicious SMS references the missing call
       - Duplicate contact spelling present
       - Timezone inconsistency in browser history

Usage:
    python validate_evidence.py
"""

import io
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, encoding="utf-8", errors="replace"
    )
    sys.stderr = io.TextIOWrapper(
        sys.stderr.buffer, encoding="utf-8", errors="replace"
    )

# Ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import case_config as cfg

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OUTPUT_DIR = _PROJECT_ROOT / cfg.OUTPUT_DIR

REQUIRED_FILES = [
    "calllog.db",
    "mmssms.db",
    "chrome_history.db",
    "app_usage.db",
    "gps_log.json",
    "file_metadata.json",
]

# Expected record count ranges (total across 21 days)
EXPECTED_COUNTS = {
    "calls": (cfg.CALLS_PER_DAY[0] * cfg.BASELINE_DAYS,
              cfg.CALLS_PER_DAY[1] * cfg.BASELINE_DAYS + 10),  # +10 for injected
    "sms": (cfg.SMS_PER_DAY[0] * cfg.BASELINE_DAYS,
            cfg.SMS_PER_DAY[1] * cfg.BASELINE_DAYS + 15),
    "browser": (cfg.BROWSER_VISITS_PER_DAY[0] * cfg.BASELINE_DAYS,
                cfg.BROWSER_VISITS_PER_DAY[1] * cfg.BASELINE_DAYS + 10),
    "app_usage": (cfg.APP_SESSIONS_PER_DAY[0] * cfg.BASELINE_DAYS * 2,
                  cfg.APP_SESSIONS_PER_DAY[1] * cfg.BASELINE_DAYS * 2 + 10),
}

# Chrome epoch reference: minimum valid Chrome timestamp (year 2025)
# Microseconds from 1601-01-01 to 2025-01-01 ≈ 13,380,508,800,000,000
_CHROME_MIN_TIMESTAMP = 13_380_000_000_000_000

# Haversine distance threshold for GPS alibi check (km)
_GPS_DISTANCE_THRESHOLD_KM = 5.0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_passed = 0
_failed = 0
_warnings = 0


def _check(name: str, condition: bool, detail: str = "") -> bool:
    """Record a pass/fail check result.

    Args:
        name: Short description of the check.
        condition: True if check passed.
        detail: Additional detail on failure.

    Returns:
        The condition value.
    """
    global _passed, _failed
    if condition:
        _passed += 1
        print(f"  [PASS] {name}")
    else:
        _failed += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f" -- {detail}"
        print(msg)
    return condition


def _warn(name: str, detail: str = "") -> None:
    """Record a warning (non-fatal)."""
    global _warnings
    _warnings += 1
    msg = f"  [WARN] {name}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two GPS points in kilometres."""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

def validate_files_exist() -> bool:
    """Check that all 6 required evidence files exist."""
    print("\n── File Existence ──")
    all_ok = True
    for fname in REQUIRED_FILES:
        path = OUTPUT_DIR / fname
        ok = _check(f"{fname} exists", path.is_file(),
                     f"Expected at {path}")
        all_ok = all_ok and ok
    return all_ok


def validate_calllog() -> bool:
    """Validate calllog.db schema, record counts, and anomalies."""
    print("\n── Call Log (calllog.db) ──")
    db_path = OUTPUT_DIR / "calllog.db"
    if not db_path.is_file():
        return _check("calllog.db accessible", False)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Schema check
    cursor.execute("PRAGMA table_info(calls)")
    columns = {row[1] for row in cursor.fetchall()}
    expected_cols = {"_id", "number", "date", "duration", "type", "name"}
    _check("Schema: calls table has correct columns",
           expected_cols.issubset(columns),
           f"Found: {columns}")

    # Record count
    cursor.execute("SELECT COUNT(*) FROM calls")
    count = cursor.fetchone()[0]
    lo, hi = EXPECTED_COUNTS["calls"]
    _check(f"Record count in range [{lo}, {hi}]",
           lo <= count <= hi,
           f"Got {count}")

    # Timestamp range — should span ~21 days
    cursor.execute("SELECT MIN(date), MAX(date) FROM calls")
    min_ts, max_ts = cursor.fetchone()
    if min_ts and max_ts:
        min_dt = datetime.fromtimestamp(min_ts / 1000, tz=timezone.utc)
        max_dt = datetime.fromtimestamp(max_ts / 1000, tz=timezone.utc)
        span_days = (max_dt - min_dt).days
        _check("Timestamp span ≈ 21 days",
               18 <= span_days <= 25,
               f"Span = {span_days} days ({min_dt.date()} to {max_dt.date()})")

    # Suspicious calls from burner number
    cursor.execute("SELECT COUNT(*) FROM calls WHERE number = ?",
                   (cfg.SUSPICIOUS_CONTACT["number"],))
    sus_count = cursor.fetchone()[0]
    _check("Suspicious calls to burner number exist",
           sus_count >= 2,
           f"Found {sus_count}")

    # Missing call gap: check that there's no call at the expected missing time
    missing_ts = int(cfg.INCIDENT_START.timestamp() * 1000) + 15 * 60 * 1000
    # Search for calls within ±2 minutes of the missing call time
    window = 2 * 60 * 1000  # 2 minutes in ms
    cursor.execute(
        "SELECT COUNT(*) FROM calls WHERE number = ? AND date BETWEEN ? AND ?",
        (cfg.SUSPICIOUS_CONTACT["number"], missing_ts - window, missing_ts + window)
    )
    gap_count = cursor.fetchone()[0]
    _check("Missing call gap exists (no call at 22:15 from burner)",
           gap_count == 0,
           f"Found {gap_count} calls in the gap window")

    # Duplicate contact spelling
    cursor.execute("SELECT DISTINCT name FROM calls WHERE number = ?",
                   (cfg.DUPLICATE_CONTACT_NUMBER,))
    names = {row[0] for row in cursor.fetchall()}
    _check("Duplicate contact spelling present",
           len(names) >= 2,
           f"Found names: {names}")

    conn.close()
    return True


def validate_sms() -> bool:
    """Validate mmssms.db schema, counts, and suspicious messages."""
    print("\n── SMS (mmssms.db) ──")
    db_path = OUTPUT_DIR / "mmssms.db"
    if not db_path.is_file():
        return _check("mmssms.db accessible", False)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Schema check
    cursor.execute("PRAGMA table_info(sms)")
    columns = {row[1] for row in cursor.fetchall()}
    expected_cols = {"_id", "address", "date", "body", "type"}
    _check("Schema: sms table has correct columns",
           expected_cols.issubset(columns),
           f"Found: {columns}")

    # Record count
    cursor.execute("SELECT COUNT(*) FROM sms")
    count = cursor.fetchone()[0]
    lo, hi = EXPECTED_COUNTS["sms"]
    _check(f"Record count in range [{lo}, {hi}]",
           lo <= count <= hi,
           f"Got {count}")

    # Suspicious SMS from burner
    cursor.execute("SELECT COUNT(*) FROM sms WHERE address = ?",
                   (cfg.SUSPICIOUS_CONTACT["number"],))
    sus_count = cursor.fetchone()[0]
    _check("Suspicious SMS from burner exist",
           sus_count >= 3,
           f"Found {sus_count}")

    # SMS referencing the missing call
    cursor.execute(
        "SELECT COUNT(*) FROM sms WHERE body LIKE '%calling you%' AND address = ?",
        (cfg.SUSPICIOUS_CONTACT["number"],)
    )
    ref_count = cursor.fetchone()[0]
    _check("SMS referencing missing call exists",
           ref_count >= 1,
           f"Found {ref_count}")

    conn.close()
    return True


def validate_browser() -> bool:
    """Validate chrome_history.db schema and Chrome timestamp encoding."""
    print("\n── Browser History (chrome_history.db) ──")
    db_path = OUTPUT_DIR / "chrome_history.db"
    if not db_path.is_file():
        return _check("chrome_history.db accessible", False)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Schema check
    cursor.execute("PRAGMA table_info(urls)")
    columns = {row[1] for row in cursor.fetchall()}
    expected_cols = {"_id", "url", "title", "visit_count", "last_visit_time"}
    _check("Schema: urls table has correct columns",
           expected_cols.issubset(columns),
           f"Found: {columns}")

    # Record count
    cursor.execute("SELECT COUNT(*) FROM urls")
    count = cursor.fetchone()[0]
    lo, hi = EXPECTED_COUNTS["browser"]
    _check(f"Record count in range [{lo}, {hi}]",
           lo <= count <= hi,
           f"Got {count}")

    # Chrome timestamp format: all values should be > 13_380_000_000_000_000
    cursor.execute("SELECT MIN(last_visit_time), MAX(last_visit_time) FROM urls")
    min_ts, max_ts = cursor.fetchone()
    _check("Chrome timestamps use 1601 epoch (min > 13.38 × 10¹⁵)",
           min_ts is not None and min_ts > _CHROME_MIN_TIMESTAMP,
           f"Min timestamp = {min_ts}")

    # Verify timestamp range maps to 2025 dates
    if min_ts and max_ts:
        # Convert Chrome timestamp back to datetime
        chrome_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        min_dt = chrome_epoch + timedelta(microseconds=min_ts)
        max_dt = chrome_epoch + timedelta(microseconds=max_ts)
        _check("Chrome timestamps map to June 2025",
               min_dt.year == 2025 and min_dt.month == 6,
               f"Range: {min_dt.date()} to {max_dt.date()}")

    # Timezone anomaly: check for an entry with an offset that doesn't match IST
    # The anomaly entry should have a timestamp ~5.5 hours off from expected
    cursor.execute(
        "SELECT last_visit_time FROM urls WHERE url LIKE '%atm%electronic%'"
    )
    row = cursor.fetchone()
    if row:
        anomaly_ts = row[0]
        chrome_epoch = datetime(1601, 1, 1, tzinfo=timezone.utc)
        anomaly_dt = chrome_epoch + timedelta(microseconds=anomaly_ts)
        # The correct IST time would be 22:45 IST on incident day
        # The anomaly is stamped as if that IST time were UTC, so it should
        # appear ~5.5 hours earlier when interpreted correctly
        expected_correct_hour = 22 + 0  # ~22:45 IST → 17:15 UTC
        actual_utc_hour = anomaly_dt.hour
        # If stamped as UTC when it should be IST, the UTC hour would be 22
        # instead of 17
        is_tz_anomaly = abs(actual_utc_hour - 22) <= 1
        _check("Timezone anomaly detected (UTC instead of IST)",
               is_tz_anomaly,
               f"Entry UTC hour = {actual_utc_hour} (expected ~22 if wrong, ~17 if correct)")
    else:
        _check("Timezone anomaly entry exists", False, "ATM search entry not found")

    conn.close()
    return True


def validate_gps() -> bool:
    """Validate gps_log.json structure and GPS alibi contradiction."""
    print("\n── GPS Log (gps_log.json) ──")
    json_path = OUTPUT_DIR / "gps_log.json"
    if not json_path.is_file():
        return _check("gps_log.json accessible", False)

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            pings = json.load(f)
        except json.JSONDecodeError as e:
            return _check("JSON is valid", False, str(e))

    _check("JSON is valid", True)
    _check("GPS log is a list", isinstance(pings, list))

    # Record count: ~60-90 pings/day × 21 days
    count = len(pings)
    _check(f"GPS ping count reasonable (>500)",
           count > 500,
           f"Got {count}")

    # Check required fields
    if pings:
        required_fields = {"timestamp", "latitude", "longitude", "accuracy", "provider"}
        first_ping = pings[0]
        _check("GPS pings have required fields",
               required_fields.issubset(first_ping.keys()),
               f"Found: {set(first_ping.keys())}")

    # GPS alibi contradiction: find pings during incident window near Location B
    incident_start_str = cfg.INCIDENT_START.isoformat()
    incident_end_str = cfg.INCIDENT_END.isoformat()

    pings_at_location_b = []
    for ping in pings:
        ts = ping["timestamp"]
        if incident_start_str <= ts <= incident_end_str:
            dist = _haversine_km(
                ping["latitude"], ping["longitude"],
                cfg.INCIDENT_LOCATION["latitude"],
                cfg.INCIDENT_LOCATION["longitude"],
            )
            if dist < _GPS_DISTANCE_THRESHOLD_KM:
                pings_at_location_b.append(ping)

    _check("GPS contradicts alibi (pings at Location B during incident)",
           len(pings_at_location_b) >= 2,
           f"Found {len(pings_at_location_b)} pings near Electronic City "
           f"during {incident_start_str} to {incident_end_str}")

    # Verify those pings are NOT near the alibi location
    if pings_at_location_b:
        sample = pings_at_location_b[0]
        dist_to_alibi = _haversine_km(
            sample["latitude"], sample["longitude"],
            cfg.ALIBI_LOCATION["latitude"],
            cfg.ALIBI_LOCATION["longitude"],
        )
        _check("GPS pings during incident are far from alibi location",
               dist_to_alibi > _GPS_DISTANCE_THRESHOLD_KM,
               f"Distance to alibi = {dist_to_alibi:.1f} km")

    return True


def validate_app_usage() -> bool:
    """Validate app_usage.db schema and record counts."""
    print("\n── App Usage (app_usage.db) ──")
    db_path = OUTPUT_DIR / "app_usage.db"
    if not db_path.is_file():
        return _check("app_usage.db accessible", False)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Schema check
    cursor.execute("PRAGMA table_info(app_usage)")
    columns = {row[1] for row in cursor.fetchall()}
    expected_cols = {"_id", "package_name", "event_type", "timestamp"}
    _check("Schema: app_usage table has correct columns",
           expected_cols.issubset(columns),
           f"Found: {columns}")

    # Record count
    cursor.execute("SELECT COUNT(*) FROM app_usage")
    count = cursor.fetchone()[0]
    lo, hi = EXPECTED_COUNTS["app_usage"]
    _check(f"Record count in range [{lo}, {hi}]",
           lo <= count <= hi,
           f"Got {count}")

    # Event types should be 1 (foreground) or 2 (background)
    cursor.execute("SELECT DISTINCT event_type FROM app_usage")
    event_types = {row[0] for row in cursor.fetchall()}
    _check("Event types are 1 (foreground) and 2 (background)",
           event_types == {1, 2},
           f"Found: {event_types}")

    # Check that real Android package names are used
    cursor.execute("SELECT DISTINCT package_name FROM app_usage LIMIT 5")
    packages = [row[0] for row in cursor.fetchall()]
    has_real_packages = any("." in pkg for pkg in packages)
    _check("Uses real Android package names",
           has_real_packages,
           f"Sample: {packages}")

    conn.close()
    return True


def validate_file_metadata() -> bool:
    """Validate file_metadata.json structure."""
    print("\n── File Metadata (file_metadata.json) ──")
    json_path = OUTPUT_DIR / "file_metadata.json"
    if not json_path.is_file():
        return _check("file_metadata.json accessible", False)

    with open(json_path, "r", encoding="utf-8") as f:
        try:
            entries = json.load(f)
        except json.JSONDecodeError as e:
            return _check("JSON is valid", False, str(e))

    _check("JSON is valid", True)
    _check("File metadata is a list", isinstance(entries, list))

    count = len(entries)
    _check("File metadata count > 20", count > 20, f"Got {count}")

    # Check required fields
    if entries:
        required_fields = {"filename", "path", "size_bytes", "created",
                           "modified", "mime_type", "md5_hash"}
        first = entries[0]
        _check("Entries have required fields",
               required_fields.issubset(first.keys()),
               f"Found: {set(first.keys())}")

    # Check for variety of file types
    mime_types = {e.get("mime_type", "") for e in entries}
    has_images = any("image" in m for m in mime_types)
    has_pdf = any("pdf" in m for m in mime_types)
    has_audio = any("audio" in m for m in mime_types)
    _check("Contains photos, PDFs, and media files",
           has_images and has_pdf and has_audio,
           f"MIME types found: {mime_types}")

    # Check MD5 hashes are valid hex strings
    if entries:
        sample_hash = entries[0].get("md5_hash", "")
        _check("MD5 hashes are 32-char hex",
               len(sample_hash) == 32 and all(c in "0123456789abcdef" for c in sample_hash),
               f"Sample: {sample_hash}")

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Run all validation checks and report results.

    Returns:
        0 if all checks passed, 1 if any failed.
    """
    print("=" * 65)
    print("  PhoneTrace -- Evidence Validation")
    print("=" * 65)

    if not OUTPUT_DIR.is_dir():
        print(f"\n  [FAIL] Output directory not found: {OUTPUT_DIR}")
        print("  Run 'python evidence_generator/main_generate.py' first.")
        return 1

    validate_files_exist()
    validate_calllog()
    validate_sms()
    validate_browser()
    validate_gps()
    validate_app_usage()
    validate_file_metadata()

    # Final summary
    print()
    print("=" * 65)
    print(f"  RESULTS: {_passed} passed, {_failed} failed, {_warnings} warnings")
    print("=" * 65)

    if _failed == 0:
        print("\n  ALL CHECKS PASSED -- Evidence is valid and internally consistent.")
        return 0
    else:
        print(f"\n  {_failed} CHECK(S) FAILED -- Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
