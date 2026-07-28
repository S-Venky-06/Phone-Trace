"""
PhoneTrace — SMS Generator
============================

Generates a realistic Android SMS database (mmssms.db).

Table: sms
Columns: _id, address, date (epoch ms), body, type

SMS types follow Android convention:
    1 = Received (inbox)
    2 = Sent

Anomalies injected:
    - Suspicious coded/cryptic SMS messages near the incident window
    - SMS referencing a call that is MISSING from the call log
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

logger = logging.getLogger("evidence_generator.sms")

# ---------------------------------------------------------------------------
# SMS type constants
# ---------------------------------------------------------------------------
SMS_RECEIVED = 1
SMS_SENT = 2

# ---------------------------------------------------------------------------
# Realistic message templates by category
# ---------------------------------------------------------------------------
_CASUAL_MESSAGES = [
    "Hey, what's up?",
    "Are you free this evening?",
    "Let's catch up this weekend",
    "Did you see the match last night?",
    "Running a bit late, be there in 15",
    "Can you pick up some milk on the way?",
    "Happy birthday! 🎂",
    "Thanks for dinner last night",
    "Sure, sounds good to me",
    "I'll call you in 10 minutes",
    "Just reached office",
    "On my way home now",
    "Good morning!",
    "Good night, talk tomorrow",
    "LOL that's hilarious",
    "Can you send me that photo?",
    "Meeting got pushed to 3 PM",
    "Traffic is terrible today",
    "What do you want for dinner?",
    "I'll be home by 7",
    "Don't forget to pay the electricity bill",
    "Mom called, she wants us to visit this Sunday",
    "Got the groceries, anything else?",
    "The plumber is coming at 4",
    "Can you book a cab for me?",
    "Just finished at the gym",
    "Weather is so nice today",
    "Did you submit the report?",
    "Team lunch at 1 PM, you coming?",
    "Please check your email, sent you the document",
]

_WORK_MESSAGES = [
    "Can you review the PR before EOD?",
    "Client call rescheduled to Thursday",
    "The deployment went through, all green",
    "Need your inputs on the Q3 budget",
    "Standup in 5 minutes",
    "Working from home today",
    "Will be OOO tomorrow",
    "Can we sync on the roadmap?",
    "Great presentation today!",
    "Sent you the updated slides",
]

_FAMILY_MESSAGES = [
    "Take care of yourself, eat on time",
    "How was your day?",
    "Amma is asking about you",
    "What time are you coming for dinner?",
    "I made your favourite dal today",
    "Don't forget to take your medicines",
    "When is your next holiday?",
    "We should plan a trip soon",
]

# Suspicious / coded messages (for incident window)
_SUSPICIOUS_MESSAGES_RECEIVED = [
    "Package is ready. Come to the usual spot.",
    "ETA?",
    "Don't use this number again after tonight",
    "Bring the thing we discussed. No delays.",
    "All clear on my end",
]

_SUSPICIOUS_MESSAGES_SENT = [
    "On my way. 30 min.",
    "Understood. Will be there.",
    "Done. Leaving now.",
    "Delete this thread",
]

# Message referencing the missing call
_MISSING_CALL_REFERENCE_MSG = (
    "Tried calling you at 10:15 but you didn't pick up. "
    "Are you still coming?"
)


def _pick_message_body(contact: dict) -> str:
    """Select a contextually appropriate message body for a contact.

    Args:
        contact: Contact dict with 'relationship' key.

    Returns:
        A realistic SMS message string.
    """
    rel = contact.get("relationship", "")
    if rel in ("Wife", "Sister"):
        pool = _CASUAL_MESSAGES + _FAMILY_MESSAGES
    elif rel in ("Colleague", "Manager"):
        pool = _CASUAL_MESSAGES + _WORK_MESSAGES
    else:
        pool = _CASUAL_MESSAGES
    return random.choice(pool)


def _generate_normal_day_sms(day_offset: int) -> List[Tuple]:
    """Generate a normal day's worth of SMS records.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        List of tuples (address, date_ms, body, sms_type).
    """
    day_start = get_day_start(day_offset)
    num_sms = random.randint(*cfg.SMS_PER_DAY)
    records = []

    # Weighted contact selection — wife texts most
    weights = [4.0, 2.0, 1.5, 2.0, 1.0, 1.0, 0.8, 1.2]

    for _ in range(num_sms):
        contact = random.choices(cfg.RECURRING_CONTACTS, weights=weights, k=1)[0]
        sms_time = random_datetime_in_range(
            day_start, cfg.WAKING_HOUR_START, cfg.WAKING_HOUR_END
        )
        sms_type = random.choices(
            [SMS_RECEIVED, SMS_SENT],
            weights=[0.55, 0.45],
            k=1,
        )[0]
        body = _pick_message_body(contact)

        records.append((
            contact["number"],
            datetime_to_epoch_ms(sms_time),
            body,
            sms_type,
        ))

    return records


def _generate_incident_day_sms(day_offset: int) -> List[Tuple]:
    """Generate SMS for the incident day, including suspicious messages.

    Args:
        day_offset: Day number (0-indexed) from BASELINE_START.

    Returns:
        List of tuples (address, date_ms, body, sms_type).
    """
    # Start with normal daytime SMS
    records = _generate_normal_day_sms(day_offset)
    burner = cfg.SUSPICIOUS_CONTACT["number"]

    # --- Pre-incident suspicious SMS (received) ---
    pre_1 = cfg.INCIDENT_START - timedelta(minutes=45)
    records.append((
        burner,
        datetime_to_epoch_ms(pre_1),
        _SUSPICIOUS_MESSAGES_RECEIVED[0],  # "Package is ready..."
        SMS_RECEIVED,
    ))

    pre_2 = cfg.INCIDENT_START - timedelta(minutes=30)
    records.append((
        burner,
        datetime_to_epoch_ms(pre_2),
        _SUSPICIOUS_MESSAGES_SENT[0],  # "On my way. 30 min."
        SMS_SENT,
    ))

    # --- SMS referencing the MISSING call ---
    # This call (22:15) does NOT exist in the call log
    ref_time = cfg.INCIDENT_START + timedelta(minutes=20)
    records.append((
        burner,
        datetime_to_epoch_ms(ref_time),
        _MISSING_CALL_REFERENCE_MSG,
        SMS_RECEIVED,
    ))

    # --- During incident: more coded messages ---
    during_1 = cfg.INCIDENT_START + timedelta(minutes=50)
    records.append((
        burner,
        datetime_to_epoch_ms(during_1),
        _SUSPICIOUS_MESSAGES_RECEIVED[1],  # "ETA?"
        SMS_RECEIVED,
    ))

    during_2 = cfg.INCIDENT_START + timedelta(minutes=55)
    records.append((
        burner,
        datetime_to_epoch_ms(during_2),
        _SUSPICIOUS_MESSAGES_SENT[1],  # "Understood..."
        SMS_SENT,
    ))

    # --- Post-incident cleanup messages ---
    post_1 = cfg.INCIDENT_END + timedelta(minutes=5)
    records.append((
        burner,
        datetime_to_epoch_ms(post_1),
        _SUSPICIOUS_MESSAGES_SENT[2],  # "Done. Leaving now."
        SMS_SENT,
    ))

    post_2 = cfg.INCIDENT_END + timedelta(minutes=10)
    records.append((
        burner,
        datetime_to_epoch_ms(post_2),
        _SUSPICIOUS_MESSAGES_RECEIVED[2],  # "Don't use this number..."
        SMS_RECEIVED,
    ))

    post_3 = cfg.INCIDENT_END + timedelta(minutes=12)
    records.append((
        burner,
        datetime_to_epoch_ms(post_3),
        _SUSPICIOUS_MESSAGES_SENT[3],  # "Delete this thread"
        SMS_SENT,
    ))

    logger.info(
        "Injected %d suspicious SMS on incident day (day %d)",
        8,
        day_offset,
    )

    return records


def generate_sms_log() -> Dict:
    """Generate the complete SMS database.

    Creates mmssms.db in the evidence output directory containing
    realistic SMS records for the entire baseline period, with
    suspicious messages injected on the incident day.

    Returns:
        Dict with generation statistics:
            - total_records: int
            - file: str (output path)
            - suspicious_sms: int
    """
    output_dir = get_output_dir()
    db_path = str(output_dir / "mmssms.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sms (
            _id     INTEGER PRIMARY KEY AUTOINCREMENT,
            address TEXT    NOT NULL,
            date    INTEGER NOT NULL,
            body    TEXT    NOT NULL,
            type    INTEGER NOT NULL
        )
    """)

    all_records = []
    suspicious_count = 0

    for day in range(cfg.BASELINE_DAYS):
        if day == cfg.INCIDENT_DAY:
            day_records = _generate_incident_day_sms(day)
            suspicious_count = sum(
                1 for r in day_records
                if r[0] == cfg.SUSPICIOUS_CONTACT["number"]
            )
        else:
            day_records = _generate_normal_day_sms(day)
        all_records.extend(day_records)

    # Sort by timestamp
    all_records.sort(key=lambda r: r[1])

    cursor.executemany(
        "INSERT INTO sms (address, date, body, type) VALUES (?, ?, ?, ?)",
        all_records,
    )
    conn.commit()
    conn.close()

    logger.info("Generated %d SMS records → %s", len(all_records), db_path)

    return {
        "total_records": len(all_records),
        "file": db_path,
        "suspicious_sms": suspicious_count,
    }
