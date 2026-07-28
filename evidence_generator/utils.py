"""
PhoneTrace — Shared Utility Functions
======================================

Helper functions used across all evidence generator modules.
Handles timestamp conversions, location jitter, logging setup, etc.
"""

import logging
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

import case_config as cfg


# ---------------------------------------------------------------------------
# Chrome Timestamp Epoch
# ---------------------------------------------------------------------------
# Chrome/WebKit uses microseconds since 1601-01-01 00:00:00 UTC.
_CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)


def datetime_to_epoch_ms(dt: datetime) -> int:
    """Convert a timezone-aware datetime to Unix epoch milliseconds.

    This is the timestamp format used by Android call log and SMS databases.

    Args:
        dt: A timezone-aware datetime object.

    Returns:
        Integer milliseconds since 1970-01-01 00:00:00 UTC.
    """
    return int(dt.timestamp() * 1000)


def datetime_to_chrome_timestamp(dt: datetime) -> int:
    """Convert a timezone-aware datetime to Chrome/WebKit timestamp format.

    Chrome stores timestamps as microseconds since 1601-01-01 00:00:00 UTC.

    Args:
        dt: A timezone-aware datetime object.

    Returns:
        Integer microseconds since 1601-01-01 00:00:00 UTC.
    """
    delta = dt.astimezone(timezone.utc) - _CHROME_EPOCH
    return int(delta.total_seconds() * 1_000_000)


def random_datetime_in_range(
    day_start: datetime,
    hour_start: int,
    hour_end: int,
) -> datetime:
    """Generate a random datetime within a specific hour range on a given day.

    Args:
        day_start: A datetime representing midnight (00:00) of the target day.
        hour_start: Earliest hour (inclusive), e.g. 7 for 07:00.
        hour_end: Latest hour (exclusive), e.g. 23 for up to 22:59.

    Returns:
        A timezone-aware datetime within the specified range.
    """
    offset_seconds = random.randint(hour_start * 3600, hour_end * 3600 - 1)
    return day_start + timedelta(seconds=offset_seconds)


def jitter_location(
    lat: float,
    lng: float,
    radius_m: float = 50.0,
) -> Tuple[float, float]:
    """Add realistic GPS noise to a coordinate pair.

    Simulates the natural inaccuracy of GPS hardware by displacing the
    point randomly within a circle of the given radius.

    Args:
        lat: Base latitude in decimal degrees.
        lng: Base longitude in decimal degrees.
        radius_m: Maximum displacement in metres (default 50 m).

    Returns:
        Tuple of (latitude, longitude) with jitter applied.
    """
    # 1 degree of latitude  ≈ 111,320 m
    # 1 degree of longitude ≈ 111,320 m × cos(lat)
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, radius_m)
    delta_lat = (distance * math.cos(angle)) / 111320.0
    delta_lng = (distance * math.sin(angle)) / (
        111320.0 * math.cos(math.radians(lat))
    )
    return round(lat + delta_lat, 6), round(lng + delta_lng, 6)


def get_output_dir() -> Path:
    """Return the evidence output directory path, creating it if needed.

    The path is relative to the project root and defined in case_config.

    Returns:
        A Path object pointing to the output directory.
    """
    # Resolve relative to project root (parent of evidence_generator/)
    project_root = Path(__file__).resolve().parent.parent
    output_path = project_root / cfg.OUTPUT_DIR
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure and return the package-level logger.

    Args:
        level: Logging level (default INFO).

    Returns:
        Configured Logger instance for the evidence_generator package.
    """
    logger = logging.getLogger("evidence_generator")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def get_day_start(day_offset: int) -> datetime:
    """Return midnight (00:00:00) IST for a given day offset from baseline.

    Args:
        day_offset: Number of days after BASELINE_START.

    Returns:
        Timezone-aware datetime at midnight IST on the requested day.
    """
    return cfg.BASELINE_START + timedelta(days=day_offset)


def pick_weighted_contact(
    contacts: list,
    weights: list = None,
) -> dict:
    """Select a contact using optional frequency weights.

    Args:
        contacts: List of contact dicts from case_config.
        weights: Optional list of numeric weights (same length as contacts).

    Returns:
        A single contact dict.
    """
    if weights:
        return random.choices(contacts, weights=weights, k=1)[0]
    return random.choice(contacts)
