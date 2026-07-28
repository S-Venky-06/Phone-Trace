"""
PhoneTrace — Call Log Generator
=================================

Generates a realistic Android call log database (calllog.db).

Table: calls
Columns: _id, number, date (epoch ms), duration (seconds), type, name

Call types follow Android convention:
    1 = Incoming
    2 = Outgoing
    3 = Missed

Anomalies injected:
    - Suspicious calls to/from the burner number during the incident window
    - One missing call entry (referenced by SMS but absent from call log)
    - Duplicate contact name spelling ("Vikram Singh" / "Vikrm Singh")
"""

import logging
import random
import sqlite3
from datetime import timedelta
from typing import Dict, List, Tuple

import case_config as cfg
from evidence_generator.utils import (
    datetime_to_epoch_ms,
    get_day_start,
    get_output_dir,
    random_datetime_in_range,
)

logger = logging.getLogger("evidence_generator.calls")

# ---------------------------------------------------------------------------
# Call type constants (Android convention)
# ---------------------------------------------------------------------------
CALL_INCOMING = 1
CALL_OUTGOING = 2
CALL_MISSED = 3

# The missing call — this entry will be SKIPPED from the call log DB
# but referenced by an SMS message, creating a forensic gap.
MISSING_CALL_TIME = cfg.INCIDENT_START + timedelta(minutes=15)
MISSING_CALL_NUMBER = cfg.SUSPICIOUS_CONTACT["number"]


def _create_database(db_path: str) -> None:
    """Create the calllog.db SQLite database with the correct schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            _id     INTEGER PRIMARY KEY AUTOINCREMENT,
            number  TEXT    NOT NULL,
            date    INTEGER NOT NULL,
            duration INTEGER NOT NULL,
            type    INTEGER NOT NULL,
            name    TEXT
        )
    """)
    conn.commit()
    conn.close()


def _generate_normal_day_calls(day_offset: int) -> List[Tuple]:
    """Generate a normal day's worth of call records.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        List of tuples (number, date_ms, duration, call_type, name).
    """
    day_start = get_day_start(day_offset)
    num_calls = random.randint(*cfg.CALLS_PER_DAY)
    records = []

    # Weight contacts: wife and best friend are more frequent
    weights = [3.0, 2.5, 1.5, 1.5, 1.0, 1.0, 0.8, 0.7]

    for _ in range(num_calls):
        contact = random.choices(cfg.RECURRING_CONTACTS, weights=weights, k=1)[0]
        call_time = random_datetime_in_range(
            day_start, cfg.WAKING_HOUR_START, cfg.WAKING_HOUR_END
        )
        call_type = random.choices(
            [CALL_INCOMING, CALL_OUTGOING, CALL_MISSED],
            weights=[0.40, 0.45, 0.15],
            k=1,
        )[0]

        if call_type == CALL_MISSED:
            duration = 0
        else:
            duration = random.randint(15, 600)  # 15 seconds to 10 minutes

        name = contact["name"]

        # Anomaly: randomly use the duplicate spelling for Vikram Singh
        # (~30% of the time on some days to make it look like a real typo)
        if (
            name == cfg.DUPLICATE_CONTACT_ORIGINAL
            and day_offset >= 10
            and random.random() < 0.30
        ):
            name = cfg.DUPLICATE_CONTACT_VARIANT

        records.append((
            contact["number"],
            datetime_to_epoch_ms(call_time),
            duration,
            call_type,
            name,
        ))

    return records


def _generate_incident_day_calls(day_offset: int) -> Tuple[List[Tuple], bool]:
    """Generate calls for the incident day, including suspicious activity.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        Tuple of (records_list, missing_call_injected).
        The missing call is intentionally omitted from the returned records.
    """
    # Start with normal daytime calls
    records = _generate_normal_day_calls(day_offset)

    missing_call_injected = False

    # --- Suspicious call #1: incoming from burner at 21:45 (before incident) ---
    pre_incident = cfg.INCIDENT_START - timedelta(minutes=15)
    records.append((
        cfg.SUSPICIOUS_CONTACT["number"],
        datetime_to_epoch_ms(pre_incident),
        45,  # 45-second call
        CALL_INCOMING,
        cfg.SUSPICIOUS_CONTACT["name"],  # None — unknown caller
    ))

    # --- Missing call: should be at INCIDENT_START + 15 min ---
    # We deliberately do NOT add this record.
    # The SMS generator will reference it, creating a forensic gap.
    missing_call_injected = True
    logger.info(
        "Missing call injected — skipped entry at %s from %s",
        MISSING_CALL_TIME.isoformat(),
        MISSING_CALL_NUMBER,
    )

    # --- Suspicious call #2: outgoing to burner at 23:10 (during incident) ---
    during_incident = cfg.INCIDENT_START + timedelta(minutes=70)
    records.append((
        cfg.SUSPICIOUS_CONTACT["number"],
        datetime_to_epoch_ms(during_incident),
        120,  # 2-minute call
        CALL_OUTGOING,
        cfg.SUSPICIOUS_CONTACT["name"],
    ))

    # --- Suspicious call #3: incoming from burner at 23:25 (near end) ---
    near_end = cfg.INCIDENT_END - timedelta(minutes=5)
    records.append((
        cfg.SUSPICIOUS_CONTACT["number"],
        datetime_to_epoch_ms(near_end),
        30,
        CALL_INCOMING,
        cfg.SUSPICIOUS_CONTACT["name"],
    ))

    return records, missing_call_injected


def generate_call_log() -> Dict:
    """Generate the complete call log database.

    Creates calllog.db in the evidence output directory containing
    realistic call records for the entire baseline period, with
    anomalies injected on the incident day.

    Returns:
        Dict with generation statistics:
            - total_records: int
            - file: str (output path)
            - missing_call_injected: bool
            - suspicious_calls: int
    """
    output_dir = get_output_dir()
    db_path = str(output_dir / "calllog.db")

    _create_database(db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    all_records = []
    missing_call_injected = False
    suspicious_call_count = 0

    for day in range(cfg.BASELINE_DAYS):
        if day == cfg.INCIDENT_DAY:
            day_records, missing = _generate_incident_day_calls(day)
            missing_call_injected = missing
            # Count suspicious calls (to/from burner number)
            suspicious_call_count = sum(
                1 for r in day_records
                if r[0] == cfg.SUSPICIOUS_CONTACT["number"]
            )
        else:
            day_records = _generate_normal_day_calls(day)
        all_records.extend(day_records)

    # Sort by timestamp for realism
    all_records.sort(key=lambda r: r[1])

    cursor.executemany(
        "INSERT INTO calls (number, date, duration, type, name) VALUES (?, ?, ?, ?, ?)",
        all_records,
    )
    conn.commit()
    conn.close()

    logger.info("Generated %d call records → %s", len(all_records), db_path)

    return {
        "total_records": len(all_records),
        "file": db_path,
        "missing_call_injected": missing_call_injected,
        "suspicious_calls": suspicious_call_count,
    }
