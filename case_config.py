"""
PhoneTrace — Shared Case Configuration
========================================

Central configuration for the forensic case scenario.
All generator modules import from this file to ensure consistency.
No forensic parameters should be duplicated elsewhere.
"""

from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Deterministic seed — guarantees reproducible evidence generation
# ---------------------------------------------------------------------------
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------
IST = timezone(timedelta(hours=5, minutes=30))

# ---------------------------------------------------------------------------
# Suspect Identity
# ---------------------------------------------------------------------------
SUSPECT_NAME = "Arjun Mehta"
SUSPECT_PHONE = "+919876543210"
SUSPECT_DEVICE = "Samsung Galaxy S23"
SUSPECT_IMEI = "352916100012345"

# ---------------------------------------------------------------------------
# Baseline Period  (21 days — 3 full weeks)
# ---------------------------------------------------------------------------
BASELINE_START = datetime(2025, 6, 1, 0, 0, 0, tzinfo=IST)
BASELINE_DAYS = 21
BASELINE_END = BASELINE_START + timedelta(days=BASELINE_DAYS)

# ---------------------------------------------------------------------------
# Incident Window
# ---------------------------------------------------------------------------
INCIDENT_DAY = 19  # 0-indexed offset from BASELINE_START → June 20, 2025
INCIDENT_DATE = BASELINE_START + timedelta(days=INCIDENT_DAY)
INCIDENT_START = INCIDENT_DATE.replace(hour=22, minute=0, second=0, microsecond=0)
INCIDENT_END = INCIDENT_DATE.replace(hour=23, minute=30, second=0, microsecond=0)

# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------
# Location A — Claimed alibi (suspect says they were here)
ALIBI_LOCATION = {
    "name": "Home — Koramangala",
    "latitude": 12.9352,
    "longitude": 77.6245,
    "description": "Suspect's residence in Koramangala, Bangalore",
}

# Location B — Where evidence places the phone
INCIDENT_LOCATION = {
    "name": "Electronic City",
    "latitude": 12.8458,
    "longitude": 77.6692,
    "description": "Industrial/tech park area in Electronic City, Bangalore",
}

# Regular locations the suspect visits during normal daily life
REGULAR_LOCATIONS = {
    "home": {
        "name": "Home — Koramangala",
        "latitude": 12.9352,
        "longitude": 77.6245,
    },
    "office": {
        "name": "Office — Indiranagar",
        "latitude": 12.9784,
        "longitude": 77.6408,
    },
    "gym": {
        "name": "Cult Fitness — HSR Layout",
        "latitude": 12.9116,
        "longitude": 77.6389,
    },
    "cafe": {
        "name": "Third Wave Coffee — Koramangala",
        "latitude": 12.9345,
        "longitude": 77.6260,
    },
    "market": {
        "name": "Forum Mall — Koramangala",
        "latitude": 12.9340,
        "longitude": 77.6117,
    },
    "park": {
        "name": "Cubbon Park",
        "latitude": 12.9763,
        "longitude": 77.5929,
    },
}

# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------
# Recurring contacts (regular people the suspect communicates with)
RECURRING_CONTACTS = [
    {"name": "Priya Mehta",   "number": "+919876501001", "relationship": "Wife"},
    {"name": "Vikram Singh",  "number": "+919876501002", "relationship": "Best Friend"},
    {"name": "Rohit Sharma",  "number": "+919876501003", "relationship": "Colleague"},
    {"name": "Anita Desai",   "number": "+919876501004", "relationship": "Sister"},
    {"name": "Karan Patel",   "number": "+919876501005", "relationship": "Colleague"},
    {"name": "Deepa Nair",    "number": "+919876501006", "relationship": "Manager"},
    {"name": "Suresh Kumar",  "number": "+919876501007", "relationship": "Neighbour"},
    {"name": "Meera Joshi",   "number": "+919876501008", "relationship": "College Friend"},
]

# Suspicious unknown contact (burner phone)
SUSPICIOUS_CONTACT = {
    "name": None,  # No saved name — appears as unknown
    "number": "+919000000001",
    "relationship": "Unknown",
}

# Duplicate spelling variant for anomaly injection
# Same person as "Vikram Singh" but with a typo — suggests manual contact editing
DUPLICATE_CONTACT_ORIGINAL = "Vikram Singh"
DUPLICATE_CONTACT_VARIANT = "Vikrm Singh"
DUPLICATE_CONTACT_NUMBER = "+919876501002"

# ---------------------------------------------------------------------------
# Waking Hours (for GPS / app usage generation)
# ---------------------------------------------------------------------------
WAKING_HOUR_START = 7   # 07:00
WAKING_HOUR_END = 23    # 23:00

# ---------------------------------------------------------------------------
# Data Volume Targets (per day)
# ---------------------------------------------------------------------------
CALLS_PER_DAY = (8, 15)
SMS_PER_DAY = (15, 25)
BROWSER_VISITS_PER_DAY = (10, 20)
GPS_INTERVAL_MINUTES = (10, 15)
APP_SESSIONS_PER_DAY = (10, 20)

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
OUTPUT_DIR = "evidence_output"
