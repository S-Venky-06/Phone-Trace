"""
PhoneTrace — GPS Log Generator
================================

Generates a realistic GPS location log (gps_log.json).

Each GPS ping contains:
    - timestamp (ISO 8601 with timezone)
    - latitude (decimal degrees)
    - longitude (decimal degrees)
    - accuracy (metres)
    - provider ("gps", "network", or "fused")

Pings are generated every 10–15 minutes during waking hours.

Anomaly injected:
    - During the incident window, GPS places the phone at Location B
      (Electronic City) instead of Location A (Koramangala / home),
      directly contradicting the suspect's alibi.
"""

import json
import logging
import random
from datetime import timedelta
from typing import Dict, List

import case_config as cfg
from evidence_generator.utils import (
    get_day_start,
    get_output_dir,
    jitter_location,
)

logger = logging.getLogger("evidence_generator.gps")

# ---------------------------------------------------------------------------
# GPS providers (weighted by realism)
# ---------------------------------------------------------------------------
_PROVIDERS = ["gps", "network", "fused"]
_PROVIDER_WEIGHTS = [0.45, 0.20, 0.35]

# ---------------------------------------------------------------------------
# Daily movement schedule (hour → location key from REGULAR_LOCATIONS)
# ---------------------------------------------------------------------------
_WEEKDAY_SCHEDULE = [
    (7, 8, "home"),       # Morning routine
    (8, 9, "home"),       # Getting ready / breakfast
    (9, 10, "office"),    # Commute arrival
    (10, 13, "office"),   # Morning work
    (13, 14, "cafe"),     # Lunch break
    (14, 18, "office"),   # Afternoon work
    (18, 19, "gym"),      # Gym session
    (19, 20, "home"),     # Commute home
    (20, 23, "home"),     # Evening at home
]

_WEEKEND_SCHEDULE = [
    (7, 10, "home"),      # Late morning
    (10, 12, "park"),     # Park visit
    (12, 14, "cafe"),     # Brunch / coffee
    (14, 17, "market"),   # Shopping or errands
    (17, 19, "home"),     # Rest
    (19, 21, "cafe"),     # Dinner out
    (21, 23, "home"),     # Evening at home
]


def _get_location_for_time(hour: int, day_offset: int) -> dict:
    """Determine which location the suspect should be at for a given hour.

    Args:
        hour: Hour of the day (0–23).
        day_offset: Day number from BASELINE_START.

    Returns:
        Location dict with 'latitude' and 'longitude' keys.
    """
    # Determine day of week (BASELINE_START is 2025-06-01 = Sunday)
    day_of_week = (cfg.BASELINE_START.weekday() + day_offset) % 7
    is_weekend = day_of_week in (5, 6)  # Saturday=5, Sunday=6

    schedule = _WEEKEND_SCHEDULE if is_weekend else _WEEKDAY_SCHEDULE

    for start_h, end_h, loc_key in schedule:
        if start_h <= hour < end_h:
            return cfg.REGULAR_LOCATIONS[loc_key]

    # Default to home for hours outside the schedule
    return cfg.REGULAR_LOCATIONS["home"]


def _generate_day_pings(day_offset: int) -> List[dict]:
    """Generate GPS pings for one day during waking hours.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        List of GPS ping dicts.
    """
    day_start = get_day_start(day_offset)
    pings = []

    # Start at WAKING_HOUR_START, ping every 10–15 minutes
    current_time = day_start + timedelta(hours=cfg.WAKING_HOUR_START)
    end_time = day_start + timedelta(hours=cfg.WAKING_HOUR_END)

    while current_time < end_time:
        hour = current_time.hour
        location = _get_location_for_time(hour, day_offset)

        # Add GPS noise
        lat, lng = jitter_location(
            location["latitude"],
            location["longitude"],
            radius_m=random.uniform(10, 80),
        )

        # Accuracy varies by provider
        provider = random.choices(_PROVIDERS, weights=_PROVIDER_WEIGHTS, k=1)[0]
        if provider == "gps":
            accuracy = round(random.uniform(3.0, 15.0), 1)
        elif provider == "network":
            accuracy = round(random.uniform(20.0, 100.0), 1)
        else:  # fused
            accuracy = round(random.uniform(5.0, 30.0), 1)

        pings.append({
            "timestamp": current_time.isoformat(),
            "latitude": lat,
            "longitude": lng,
            "accuracy": accuracy,
            "provider": provider,
        })

        # Next ping in 10–15 minutes
        interval = random.randint(*cfg.GPS_INTERVAL_MINUTES)
        current_time += timedelta(minutes=interval)

    return pings


def _inject_incident_gps(pings: List[dict], day_offset: int) -> int:
    """Replace GPS pings during the incident window with Location B.

    Modifies the pings list in-place: any ping falling within the
    incident window will have its coordinates changed to Electronic City,
    directly contradicting the suspect's alibi.

    Args:
        pings: List of GPS ping dicts for the incident day.
        day_offset: The incident day offset.

    Returns:
        Number of pings modified (placed at Location B).
    """
    incident_start_iso = cfg.INCIDENT_START.isoformat()
    incident_end_iso = cfg.INCIDENT_END.isoformat()
    modified_count = 0

    # Also inject pings for travel TO Electronic City (starting ~21:30)
    travel_start = cfg.INCIDENT_START - timedelta(minutes=30)
    travel_start_iso = travel_start.isoformat()

    for ping in pings:
        ts = ping["timestamp"]

        if travel_start_iso <= ts <= incident_end_iso:
            # Progressive movement from home to Electronic City
            if ts < incident_start_iso:
                # In transit: interpolate between home and EC
                progress = 0.5 + random.uniform(0, 0.3)
                lat = (
                    cfg.ALIBI_LOCATION["latitude"]
                    + progress * (
                        cfg.INCIDENT_LOCATION["latitude"]
                        - cfg.ALIBI_LOCATION["latitude"]
                    )
                )
                lng = (
                    cfg.ALIBI_LOCATION["longitude"]
                    + progress * (
                        cfg.INCIDENT_LOCATION["longitude"]
                        - cfg.ALIBI_LOCATION["longitude"]
                    )
                )
                lat, lng = jitter_location(lat, lng, radius_m=150)
            else:
                # At Electronic City
                lat, lng = jitter_location(
                    cfg.INCIDENT_LOCATION["latitude"],
                    cfg.INCIDENT_LOCATION["longitude"],
                    radius_m=random.uniform(20, 100),
                )

            ping["latitude"] = lat
            ping["longitude"] = lng
            ping["accuracy"] = round(random.uniform(8.0, 50.0), 1)
            modified_count += 1

    # Ensure we have at least a few pings during the core incident window
    if modified_count < 3:
        for minutes_offset in [0, 20, 45, 70, 85]:
            t = cfg.INCIDENT_START + timedelta(minutes=minutes_offset)
            if t > cfg.INCIDENT_END:
                break
            lat, lng = jitter_location(
                cfg.INCIDENT_LOCATION["latitude"],
                cfg.INCIDENT_LOCATION["longitude"],
                radius_m=random.uniform(20, 80),
            )
            pings.append({
                "timestamp": t.isoformat(),
                "latitude": lat,
                "longitude": lng,
                "accuracy": round(random.uniform(8.0, 40.0), 1),
                "provider": random.choice(["gps", "fused"]),
            })
            modified_count += 1

    logger.info(
        "GPS anomaly: %d pings placed at Electronic City during incident window",
        modified_count,
    )

    return modified_count


def generate_gps_log() -> Dict:
    """Generate the complete GPS location log.

    Creates gps_log.json in the evidence output directory with pings
    every 10–15 minutes during waking hours for the entire baseline
    period. During the incident window, GPS contradicts the alibi.

    Returns:
        Dict with generation statistics:
            - total_records: int
            - file: str (output path)
            - gps_anomaly_pings: int
    """
    output_dir = get_output_dir()
    json_path = str(output_dir / "gps_log.json")

    all_pings = []
    gps_anomaly_count = 0

    for day in range(cfg.BASELINE_DAYS):
        day_pings = _generate_day_pings(day)

        if day == cfg.INCIDENT_DAY:
            gps_anomaly_count = _inject_incident_gps(day_pings, day)

        all_pings.extend(day_pings)

    # Sort by timestamp
    all_pings.sort(key=lambda p: p["timestamp"])

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_pings, f, indent=2, ensure_ascii=False)

    logger.info("Generated %d GPS pings → %s", len(all_pings), json_path)

    return {
        "total_records": len(all_pings),
        "file": json_path,
        "gps_anomaly_pings": gps_anomaly_count,
    }
