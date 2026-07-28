# PhoneTrace -- Timeline Architecture

## Overview

The timeline engine reconstructs a unified forensic timeline from parsed Android artifacts. It sits between the parser framework (Phase 2) and all downstream consumers (GUI, anomaly detection, AI narrative, reporting).

```
Evidence Files
      |
      v
 ParserManager (Phase 2)
      |  provides typed records
      v
 EventFactory
      |  converts records -> ForensicEvent
      v
 TimelineBuilder
      |  sorts, validates, groups
      v
 EvidenceCorrelator
      |  links related events
      v
 Unified Timeline (list[ForensicEvent])
      |
      +-- TimelineFilter / Search
      +-- TimelineStatistics
      +-- TimelineExporter (JSON/CSV)
      +-- Future: GUI, AI, Reports
```

---

## Key Classes

### ForensicEvent

The core data object. Every artifact becomes a `ForensicEvent`:

```python
ForensicEvent(
    timestamp=datetime,       # When it happened
    artifact_type="call",     # "call", "sms", "gps", "browser", "app_usage", "file"
    title="Outgoing Call",    # Short human-readable title
    description="...",        # Detailed description
    source="calllog.db",      # Origin evidence file
    location=EventLocation,   # Optional GPS coordinates
    related=[...],            # Correlated events
    raw_record=CallRecord,    # Original Phase 2 dataclass
    metadata={...},           # Type-specific key-value pairs
)
```

### EventFactory

Registry-based converter. To add a new artifact type:

```python
from timeline import EventFactory, ForensicEvent

def convert_whatsapp(record, idx):
    return ForensicEvent(
        timestamp=record.timestamp,
        artifact_type="whatsapp",
        title="WhatsApp Message",
        description=record.text[:80],
        source="wa.db",
        raw_record=record,
    )

factory = EventFactory()
factory.register(WhatsAppMessage, convert_whatsapp)
```

No existing code needs to change.

### TimelineBuilder

Orchestrates the full pipeline:

```python
from artifacts import ParserManager
from timeline import TimelineBuilder

pm = ParserManager()
pm.load_all()

builder = TimelineBuilder(pm)
events = builder.build()      # list[ForensicEvent], sorted
sessions = builder.sessions   # list[InvestigationSession]
```

### EvidenceCorrelator

7 built-in correlation rules with configurable thresholds:

| Rule | What it detects |
|------|----------------|
| Communication Cluster | Multiple calls/SMS to same contact within N min |
| Movement Cluster | Significant GPS displacement |
| Browser + GPS | Maps URL opened near GPS movement |
| File + GPS | Photo taken near GPS ping |
| SMS + Browser | SMS received, browser opened shortly after |
| Call + Movement | Call followed by GPS travel |
| App + Movement | Navigation app opened before movement |

```python
from timeline import EvidenceCorrelator, CorrelationConfig

config = CorrelationConfig(
    time_window_minutes=20,
    gps_movement_threshold_km=1.0,
)

correlator = EvidenceCorrelator(config)
groups = correlator.correlate(events)
```

### TimelineFilter

Composable filter methods:

```python
from timeline import TimelineFilter

# Chain filters
calls = TimelineFilter.by_artifact(events, "call")
outgoing = TimelineFilter.by_keyword(calls, "Outgoing")
june_10 = TimelineFilter.by_date(outgoing, start, end)

# Unified search
results = TimelineFilter.search(events, "Priya")
```

---

## How Future Modules Should Consume the Timeline

### Rule 1: Never access evidence files directly

```python
# WRONG
import sqlite3
conn = sqlite3.connect("evidence_output/calllog.db")

# CORRECT
from artifacts import ParserManager
from timeline import TimelineBuilder
pm = ParserManager()
pm.load_all()
builder = TimelineBuilder(pm)
events = builder.build()
```

### Rule 2: Use ForensicEvent, not raw records

```python
# Access data through the event
for event in events:
    print(event.timestamp, event.title, event.description)

    # Need type-specific data? Use metadata
    if event.artifact_type == "call":
        duration = event.metadata["duration_seconds"]

    # Need the original record? Use raw_record
    if event.artifact_type == "gps":
        gps: GPSRecord = event.raw_record
```

### Rule 3: Use filters instead of manual loops

```python
from timeline import TimelineFilter

# Find events near a location
nearby = TimelineFilter.by_location(events, 12.93, 77.62, radius_km=0.5)

# Search across all text fields
matches = TimelineFilter.search(events, "whatsapp")
```

### Rule 4: Adding new artifact types

1. Create a new parser in `artifacts/` that returns typed dataclasses
2. Register a converter in `EventFactory`
3. The timeline, filters, search, export, and statistics all work automatically

No changes needed to existing timeline code.
