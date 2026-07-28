"""
PhoneTrace — App Usage Generator
==================================

Generates a realistic Android app usage database (app_usage.db).

Table: app_usage
Columns: _id, package_name, event_type, timestamp (epoch ms)

Event types follow Android UsageEvents convention:
    1 = ACTIVITY_RESUMED  (move to foreground)
    2 = ACTIVITY_PAUSED   (move to background)

Each "session" consists of a foreground event followed by a background
event after a realistic duration.
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

logger = logging.getLogger("evidence_generator.app_usage")

# ---------------------------------------------------------------------------
# Event type constants (Android UsageEvents)
# ---------------------------------------------------------------------------
EVENT_FOREGROUND = 1  # ACTIVITY_RESUMED
EVENT_BACKGROUND = 2  # ACTIVITY_PAUSED

# ---------------------------------------------------------------------------
# Real Android package names with typical session durations (seconds)
# ---------------------------------------------------------------------------
_APP_PROFILES = [
    # (package_name, min_duration_s, max_duration_s, weight)
    ("com.whatsapp", 30, 600, 4.0),
    ("com.instagram.android", 60, 900, 3.0),
    ("com.google.android.youtube", 120, 1800, 2.5),
    ("com.twitter.android", 30, 600, 1.5),
    ("com.facebook.katana", 60, 900, 1.5),
    ("com.google.android.gm", 15, 300, 2.0),
    ("com.google.android.apps.maps", 30, 300, 1.5),
    ("com.android.chrome", 30, 600, 2.5),
    ("com.google.android.calendar", 10, 120, 1.0),
    ("com.spotify.music", 300, 3600, 1.5),
    ("com.phonepe.app", 15, 120, 1.0),
    ("com.google.android.apps.docs", 60, 600, 0.8),
    ("com.swiggy.android", 30, 300, 1.0),
    ("in.amazon.mShop.android.shopping", 60, 600, 1.0),
    ("com.linkedin.android", 30, 300, 0.8),
    ("com.reddit.frontpage", 60, 900, 0.8),
    ("com.google.android.dialer", 5, 60, 1.5),
    ("com.android.settings", 10, 120, 0.5),
    ("com.google.android.apps.photos", 15, 300, 1.0),
    ("com.samsung.android.messaging", 10, 120, 1.0),
    ("com.cricbuzz.android", 60, 900, 0.7),
    ("com.hotstar.android", 300, 3600, 0.8),
]


def _generate_day_sessions(day_offset: int) -> List[Tuple]:
    """Generate app usage sessions for a single day.

    Each session produces two records: a foreground event and a
    background event (session end).

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        List of tuples (package_name, event_type, timestamp_ms).
    """
    day_start = get_day_start(day_offset)
    num_sessions = random.randint(*cfg.APP_SESSIONS_PER_DAY)
    records = []

    packages = [p[0] for p in _APP_PROFILES]
    weights = [p[3] for p in _APP_PROFILES]
    durations = {p[0]: (p[1], p[2]) for p in _APP_PROFILES}

    for _ in range(num_sessions):
        pkg = random.choices(packages, weights=weights, k=1)[0]
        start_time = random_datetime_in_range(
            day_start, cfg.WAKING_HOUR_START, cfg.WAKING_HOUR_END
        )

        min_dur, max_dur = durations[pkg]
        duration = random.randint(min_dur, max_dur)
        end_time = start_time + timedelta(seconds=duration)

        # Foreground event
        records.append((
            pkg,
            EVENT_FOREGROUND,
            datetime_to_epoch_ms(start_time),
        ))
        # Background event
        records.append((
            pkg,
            EVENT_BACKGROUND,
            datetime_to_epoch_ms(end_time),
        ))

    return records


def generate_app_usage() -> Dict:
    """Generate the complete app usage database.

    Creates app_usage.db in the evidence output directory containing
    foreground/background events for realistic app sessions across the
    entire baseline period.

    Returns:
        Dict with generation statistics:
            - total_records: int
            - total_sessions: int
            - file: str (output path)
    """
    output_dir = get_output_dir()
    db_path = str(output_dir / "app_usage.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_usage (
            _id          INTEGER PRIMARY KEY AUTOINCREMENT,
            package_name TEXT    NOT NULL,
            event_type   INTEGER NOT NULL,
            timestamp    INTEGER NOT NULL
        )
    """)

    all_records = []

    for day in range(cfg.BASELINE_DAYS):
        day_records = _generate_day_sessions(day)
        all_records.extend(day_records)

    # Sort by timestamp
    all_records.sort(key=lambda r: r[2])

    cursor.executemany(
        "INSERT INTO app_usage (package_name, event_type, timestamp) "
        "VALUES (?, ?, ?)",
        all_records,
    )
    conn.commit()
    conn.close()

    total_sessions = len(all_records) // 2
    logger.info(
        "Generated %d app usage records (%d sessions) → %s",
        len(all_records),
        total_sessions,
        db_path,
    )

    return {
        "total_records": len(all_records),
        "total_sessions": total_sessions,
        "file": db_path,
    }
