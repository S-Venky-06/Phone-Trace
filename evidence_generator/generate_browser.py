"""
PhoneTrace — Browser History Generator
========================================

Generates a realistic Chrome browser history database (chrome_history.db).

Table: urls
Columns: _id, url, title, visit_count, last_visit_time

Timestamps use the Chrome/WebKit format:
    Microseconds since 1601-01-01 00:00:00 UTC

Anomaly injected:
    - One entry with a timezone inconsistency: timestamp encoded as if
      the browser was in UTC rather than IST, creating a ~5.5 hour offset.
"""

import logging
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

import case_config as cfg
from evidence_generator.utils import (
    datetime_to_chrome_timestamp,
    get_day_start,
    get_output_dir,
    random_datetime_in_range,
)

logger = logging.getLogger("evidence_generator.browser")

# ---------------------------------------------------------------------------
# Realistic browsing patterns — URLs and titles
# ---------------------------------------------------------------------------
_BROWSING_PATTERNS = [
    # News
    ("https://www.ndtv.com/india-news", "Latest News, India News - NDTV"),
    ("https://timesofindia.indiatimes.com/", "Times of India - Breaking News"),
    ("https://www.thehindu.com/news/national/", "National News - The Hindu"),
    ("https://indianexpress.com/", "The Indian Express - Latest News"),
    ("https://www.bbc.com/news", "BBC News - Home"),
    # Social media
    ("https://www.instagram.com/", "Instagram"),
    ("https://twitter.com/home", "Home / X"),
    ("https://www.facebook.com/", "Facebook"),
    ("https://www.linkedin.com/feed/", "LinkedIn Feed"),
    ("https://www.reddit.com/r/india/", "r/india - Reddit"),
    # YouTube
    ("https://www.youtube.com/", "YouTube"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "Rick Astley - Never Gonna Give You Up"),
    ("https://www.youtube.com/results?search_query=python+tutorial", "python tutorial - YouTube"),
    ("https://www.youtube.com/watch?v=rfscVS0vtbw", "Python Tutorial for Beginners - YouTube"),
    # Shopping
    ("https://www.amazon.in/", "Amazon.in - Online Shopping"),
    ("https://www.flipkart.com/", "Flipkart - Online Shopping"),
    ("https://www.swiggy.com/", "Swiggy - Order Food Online"),
    ("https://www.zomato.com/bangalore", "Zomato - Bangalore Restaurants"),
    # Tech / Work
    ("https://stackoverflow.com/questions", "Stack Overflow - Questions"),
    ("https://github.com/", "GitHub"),
    ("https://mail.google.com/mail/", "Gmail"),
    ("https://docs.google.com/document/", "Google Docs"),
    ("https://calendar.google.com/", "Google Calendar"),
    ("https://meet.google.com/", "Google Meet"),
    # Banking / Utility
    ("https://netbanking.hdfcbank.com/", "HDFC Net Banking"),
    ("https://www.irctc.co.in/", "IRCTC - Indian Railways"),
    # Weather / Maps
    ("https://www.google.com/maps/@12.9352,77.6245,15z", "Google Maps - Koramangala"),
    ("https://weather.com/en-IN/weather/today/l/12.97,77.59", "Weather - Bangalore"),
    # Entertainment
    ("https://www.hotstar.com/", "Disney+ Hotstar"),
    ("https://www.primevideo.com/", "Amazon Prime Video"),
    ("https://www.cricbuzz.com/", "Cricbuzz - Live Cricket Scores"),
    # Suspicious (will be used on incident day)
    ("https://www.google.com/maps/@12.8458,77.6692,15z", "Google Maps - Electronic City"),
]

# Suspicious browsing on incident day
_SUSPICIOUS_URLS = [
    ("https://www.google.com/search?q=how+to+delete+call+history+android", "how to delete call history android - Google Search"),
    ("https://www.google.com/maps/dir/Koramangala/Electronic+City", "Koramangala to Electronic City - Google Maps"),
    ("https://www.google.com/search?q=best+burner+phone+apps", "best burner phone apps - Google Search"),
]


def _generate_normal_day_browsing(day_offset: int) -> List[Tuple]:
    """Generate a normal day's browser history entries.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        List of tuples (url, title, visit_count, last_visit_time_chrome).
    """
    day_start = get_day_start(day_offset)
    num_visits = random.randint(*cfg.BROWSER_VISITS_PER_DAY)
    records = []

    # Exclude the last suspicious entry from normal browsing
    normal_urls = _BROWSING_PATTERNS[:-1]

    for _ in range(num_visits):
        url, title = random.choice(normal_urls)
        visit_time = random_datetime_in_range(
            day_start, cfg.WAKING_HOUR_START, cfg.WAKING_HOUR_END
        )
        visit_count = random.randint(1, 5)
        chrome_ts = datetime_to_chrome_timestamp(visit_time)

        records.append((url, title, visit_count, chrome_ts))

    return records


def _generate_incident_day_browsing(day_offset: int) -> Tuple[List[Tuple], bool]:
    """Generate browser history for the incident day with anomalies.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        Tuple of (records_list, timezone_anomaly_injected).
    """
    # Normal daytime browsing
    records = _generate_normal_day_browsing(day_offset)

    # --- Suspicious searches near the incident ---
    for i, (url, title) in enumerate(_SUSPICIOUS_URLS):
        visit_time = cfg.INCIDENT_START - timedelta(minutes=120 - i * 30)
        chrome_ts = datetime_to_chrome_timestamp(visit_time)
        records.append((url, title, 1, chrome_ts))

    # --- Google Maps Electronic City during incident ---
    ec_time = cfg.INCIDENT_START + timedelta(minutes=30)
    ec_url, ec_title = _BROWSING_PATTERNS[-1]  # Electronic City maps
    chrome_ts = datetime_to_chrome_timestamp(ec_time)
    records.append((ec_url, ec_title, 1, chrome_ts))

    # --- Timezone anomaly: one entry stamped in UTC instead of IST ---
    # This creates a ~5.5 hour discrepancy when analyzed
    tz_anomaly_time = cfg.INCIDENT_START + timedelta(minutes=45)
    # Intentionally treat IST time as if it were UTC (wrong conversion)
    naive_time = tz_anomaly_time.replace(tzinfo=None)
    wrong_tz_time = naive_time.replace(tzinfo=timezone.utc)  # Should be IST!
    chrome_ts_wrong = datetime_to_chrome_timestamp(wrong_tz_time)

    records.append((
        "https://www.google.com/search?q=nearby+atm+electronic+city",
        "nearby atm electronic city - Google Search",
        1,
        chrome_ts_wrong,
    ))

    logger.info(
        "Injected timezone anomaly: entry stamped in UTC instead of IST "
        "(~5.5 hour offset)"
    )

    return records, True


def generate_browser_history() -> Dict:
    """Generate the complete Chrome browser history database.

    Creates chrome_history.db in the evidence output directory using
    Chrome's timestamp format (microseconds since 1601-01-01 UTC).

    Returns:
        Dict with generation statistics:
            - total_records: int
            - file: str (output path)
            - timezone_anomaly_injected: bool
            - suspicious_searches: int
    """
    output_dir = get_output_dir()
    db_path = str(output_dir / "chrome_history.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            _id             INTEGER PRIMARY KEY AUTOINCREMENT,
            url             TEXT    NOT NULL,
            title           TEXT    NOT NULL,
            visit_count     INTEGER NOT NULL DEFAULT 1,
            last_visit_time INTEGER NOT NULL
        )
    """)

    all_records = []
    tz_anomaly = False
    suspicious_search_count = 0

    for day in range(cfg.BASELINE_DAYS):
        if day == cfg.INCIDENT_DAY:
            day_records, tz_anomaly = _generate_incident_day_browsing(day)
            suspicious_search_count = len(_SUSPICIOUS_URLS) + 2  # + maps + ATM
        else:
            day_records = _generate_normal_day_browsing(day)
        all_records.extend(day_records)

    # Sort by Chrome timestamp
    all_records.sort(key=lambda r: r[3])

    cursor.executemany(
        "INSERT INTO urls (url, title, visit_count, last_visit_time) "
        "VALUES (?, ?, ?, ?)",
        all_records,
    )
    conn.commit()
    conn.close()

    logger.info("Generated %d browser records → %s", len(all_records), db_path)

    return {
        "total_records": len(all_records),
        "file": db_path,
        "timezone_anomaly_injected": tz_anomaly,
        "suspicious_searches": suspicious_search_count,
    }
