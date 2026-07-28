"""
PhoneTrace — File Metadata Generator
=======================================

Generates realistic Android file system metadata (file_metadata.json).

Produces metadata entries for:
    - Photos (DCIM/Camera)
    - Screenshots
    - Downloads (PDFs, APKs, documents)
    - Media files (music, videos)

Each entry contains:
    - filename
    - path (Android-style absolute path)
    - size_bytes
    - created (ISO 8601)
    - modified (ISO 8601)
    - mime_type
    - md5_hash (simulated)
"""

import hashlib
import json
import logging
import random
from datetime import timedelta
from typing import Dict, List

import case_config as cfg
from evidence_generator.utils import (
    get_day_start,
    get_output_dir,
    random_datetime_in_range,
)

logger = logging.getLogger("evidence_generator.file_metadata")

# ---------------------------------------------------------------------------
# File templates by category
# ---------------------------------------------------------------------------
_PHOTO_TEMPLATES = [
    {"prefix": "IMG_", "ext": ".jpg", "mime": "image/jpeg",
     "size_range": (1_500_000, 8_000_000), "path": "/sdcard/DCIM/Camera/"},
    {"prefix": "IMG_", "ext": ".heic", "mime": "image/heif",
     "size_range": (1_000_000, 5_000_000), "path": "/sdcard/DCIM/Camera/"},
]

_SCREENSHOT_TEMPLATE = {
    "prefix": "Screenshot_", "ext": ".png", "mime": "image/png",
    "size_range": (200_000, 2_000_000), "path": "/sdcard/Pictures/Screenshots/",
}

_DOWNLOAD_TEMPLATES = [
    {"name": "invoice_june_2025.pdf", "mime": "application/pdf",
     "size_range": (50_000, 500_000), "path": "/sdcard/Download/"},
    {"name": "salary_slip_may.pdf", "mime": "application/pdf",
     "size_range": (80_000, 300_000), "path": "/sdcard/Download/"},
    {"name": "meeting_notes.pdf", "mime": "application/pdf",
     "size_range": (30_000, 200_000), "path": "/sdcard/Download/"},
    {"name": "project_roadmap_q3.pdf", "mime": "application/pdf",
     "size_range": (100_000, 800_000), "path": "/sdcard/Download/"},
    {"name": "ticket_blr_del_june.pdf", "mime": "application/pdf",
     "size_range": (60_000, 250_000), "path": "/sdcard/Download/"},
    {"name": "apartment_agreement.pdf", "mime": "application/pdf",
     "size_range": (200_000, 1_500_000), "path": "/sdcard/Download/"},
    {"name": "restaurant_menu.pdf", "mime": "application/pdf",
     "size_range": (500_000, 3_000_000), "path": "/sdcard/Download/"},
    {"name": "budget_tracker.xlsx", "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
     "size_range": (20_000, 150_000), "path": "/sdcard/Download/"},
]

_MEDIA_TEMPLATES = [
    {"name": "voice_note_001.m4a", "mime": "audio/mp4",
     "size_range": (50_000, 500_000), "path": "/sdcard/WhatsApp/Media/WhatsApp Audio/"},
    {"name": "voice_note_002.m4a", "mime": "audio/mp4",
     "size_range": (30_000, 300_000), "path": "/sdcard/WhatsApp/Media/WhatsApp Audio/"},
    {"name": "VID_trip_highlights.mp4", "mime": "video/mp4",
     "size_range": (10_000_000, 80_000_000), "path": "/sdcard/DCIM/Camera/"},
    {"name": "podcast_episode_42.mp3", "mime": "audio/mpeg",
     "size_range": (5_000_000, 50_000_000), "path": "/sdcard/Download/"},
    {"name": "spotify_offline_cache.ogg", "mime": "audio/ogg",
     "size_range": (3_000_000, 10_000_000), "path": "/sdcard/Android/data/com.spotify.music/files/"},
    {"name": "whatsapp_video_note.mp4", "mime": "video/mp4",
     "size_range": (1_000_000, 15_000_000), "path": "/sdcard/WhatsApp/Media/WhatsApp Video/"},
]


def _generate_md5(seed_string: str) -> str:
    """Generate a deterministic MD5 hash from a seed string.

    Args:
        seed_string: Input to hash (typically filename + timestamp).

    Returns:
        32-character hex MD5 digest.
    """
    return hashlib.md5(seed_string.encode("utf-8")).hexdigest()


def _generate_photo_entries(day_offset: int) -> List[dict]:
    """Generate photo metadata entries for a given day.

    Generates 0–4 photos per day, simulating casual phone photography.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        List of file metadata dicts.
    """
    day_start = get_day_start(day_offset)
    num_photos = random.choices([0, 1, 2, 3, 4], weights=[0.2, 0.3, 0.25, 0.15, 0.1], k=1)[0]
    entries = []

    for i in range(num_photos):
        template = random.choice(_PHOTO_TEMPLATES)
        created = random_datetime_in_range(
            day_start, cfg.WAKING_HOUR_START, cfg.WAKING_HOUR_END
        )
        timestamp_str = created.strftime("%Y%m%d_%H%M%S")
        filename = f"{template['prefix']}{timestamp_str}_{i:03d}{template['ext']}"
        full_path = template["path"] + filename
        size = random.randint(*template["size_range"])

        # Modified is usually same as created, sometimes slightly later
        modified = created + timedelta(seconds=random.randint(0, 10))

        entries.append({
            "filename": filename,
            "path": full_path,
            "size_bytes": size,
            "created": created.isoformat(),
            "modified": modified.isoformat(),
            "mime_type": template["mime"],
            "md5_hash": _generate_md5(full_path + timestamp_str),
        })

    return entries


def _generate_screenshot_entries(day_offset: int) -> List[dict]:
    """Generate screenshot metadata entries for a given day.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        List of file metadata dicts.
    """
    day_start = get_day_start(day_offset)
    num_screenshots = random.choices([0, 1, 2], weights=[0.5, 0.35, 0.15], k=1)[0]
    entries = []

    for i in range(num_screenshots):
        t = _SCREENSHOT_TEMPLATE
        created = random_datetime_in_range(
            day_start, cfg.WAKING_HOUR_START, cfg.WAKING_HOUR_END
        )
        timestamp_str = created.strftime("%Y%m%d_%H%M%S")
        filename = f"{t['prefix']}{timestamp_str}{t['ext']}"
        full_path = t["path"] + filename
        size = random.randint(*t["size_range"])

        entries.append({
            "filename": filename,
            "path": full_path,
            "size_bytes": size,
            "created": created.isoformat(),
            "modified": created.isoformat(),
            "mime_type": t["mime"],
            "md5_hash": _generate_md5(full_path + timestamp_str),
        })

    return entries


def _generate_download_entries() -> List[dict]:
    """Generate download file metadata spread across the baseline period.

    Returns:
        List of file metadata dicts for downloads.
    """
    entries = []

    for template in _DOWNLOAD_TEMPLATES:
        day_offset = random.randint(0, cfg.BASELINE_DAYS - 1)
        day_start = get_day_start(day_offset)
        created = random_datetime_in_range(
            day_start, cfg.WAKING_HOUR_START, cfg.WAKING_HOUR_END
        )
        size = random.randint(*template["size_range"])
        full_path = template["path"] + template["name"]

        entries.append({
            "filename": template["name"],
            "path": full_path,
            "size_bytes": size,
            "created": created.isoformat(),
            "modified": created.isoformat(),
            "mime_type": template["mime"],
            "md5_hash": _generate_md5(full_path + created.isoformat()),
        })

    return entries


def _generate_media_entries() -> List[dict]:
    """Generate media file metadata spread across the baseline period.

    Returns:
        List of file metadata dicts for audio/video files.
    """
    entries = []

    for template in _MEDIA_TEMPLATES:
        day_offset = random.randint(0, cfg.BASELINE_DAYS - 1)
        day_start = get_day_start(day_offset)
        created = random_datetime_in_range(
            day_start, cfg.WAKING_HOUR_START, cfg.WAKING_HOUR_END
        )
        size = random.randint(*template["size_range"])
        full_path = template["path"] + template["name"]

        entries.append({
            "filename": template["name"],
            "path": full_path,
            "size_bytes": size,
            "created": created.isoformat(),
            "modified": created.isoformat(),
            "mime_type": template["mime"],
            "md5_hash": _generate_md5(full_path + created.isoformat()),
        })

    return entries


def generate_file_metadata() -> Dict:
    """Generate the complete file metadata JSON.

    Creates file_metadata.json in the evidence output directory with
    realistic Android file system metadata for photos, screenshots,
    downloads, and media files.

    Returns:
        Dict with generation statistics:
            - total_records: int
            - file: str (output path)
            - photos: int
            - screenshots: int
            - downloads: int
            - media: int
    """
    output_dir = get_output_dir()
    json_path = str(output_dir / "file_metadata.json")

    all_entries = []

    # Photos and screenshots — daily generation
    photo_count = 0
    screenshot_count = 0
    for day in range(cfg.BASELINE_DAYS):
        photos = _generate_photo_entries(day)
        screenshots = _generate_screenshot_entries(day)
        photo_count += len(photos)
        screenshot_count += len(screenshots)
        all_entries.extend(photos)
        all_entries.extend(screenshots)

    # Downloads and media — spread across the period
    downloads = _generate_download_entries()
    media = _generate_media_entries()
    all_entries.extend(downloads)
    all_entries.extend(media)

    # Sort by creation time
    all_entries.sort(key=lambda e: e["created"])

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, indent=2, ensure_ascii=False)

    logger.info("Generated %d file metadata entries → %s", len(all_entries), json_path)

    return {
        "total_records": len(all_entries),
        "file": json_path,
        "photos": photo_count,
        "screenshots": screenshot_count,
        "downloads": len(downloads),
        "media": len(media),
    }
