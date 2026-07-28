# PhoneTrace

**AI-Assisted Android Digital Forensic Investigation Workstation**

PhoneTrace reconstructs a smartphone timeline and verifies whether a suspect's claimed alibi matches the evidence extracted from an Android device.

---

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| **Phase 1** | Synthetic evidence generator | ✅ Complete |
| **Phase 2** | Evidence parsing framework | ✅ Complete |
| **Phase 3** | Timeline reconstruction & correlation | ✅ Complete |
| **Phase 4** | Digital Forensics Investigation Dashboard (PyQt6) | ✅ Complete |
| **Phase 5** | AI Investigation Assistant & Reports | ✅ Complete |
| **Phase 6** | Forensic Workstation UI Redesign, GPS Mapping & Anomaly Engine | ✅ Complete |

---

## Quick Start (Phase 1)

### Requirements

- Python 3.12+
- No external packages required (stdlib only)

### Generate Evidence

```bash
python evidence_generator/main_generate.py
```

This creates `evidence_output/` containing:

| File | Format | Description |
|------|--------|-------------|
| `calllog.db` | SQLite | Android call log (table: `calls`) |
| `mmssms.db` | SQLite | SMS messages (table: `sms`) |
| `chrome_history.db` | SQLite | Chrome browser history (table: `urls`) |
| `gps_log.json` | JSON | GPS location pings (every 10–15 min) |
| `app_usage.db` | SQLite | App foreground/background events (table: `app_usage`) |
| `file_metadata.json` | JSON | File system metadata (photos, downloads, etc.) |

### Validate Evidence

```bash
python validate_evidence.py
```

Checks file existence, schemas, timestamp formats, record counts, and anomaly detectability.

---

## Quick Start (Phase 2 — Parsing)

```python
from artifacts import ParserManager

manager = ParserManager()
manager.load_all()

calls   = manager.calls        # list[CallRecord]
sms     = manager.sms          # list[SMSRecord]
browser = manager.browser      # list[BrowserRecord]
gps     = manager.gps          # list[GPSRecord]
apps    = manager.app_usage    # list[AppUsageRecord]
files   = manager.files        # list[FileRecord]
```

Run tests: `python -m unittest test_phase2 -v`

---

## Quick Start (Phase 3 — Timeline)

```python
from artifacts import ParserManager
from timeline import TimelineBuilder, EvidenceCorrelator, TimelineStatistics

pm = ParserManager()
pm.load_all()

# Build timeline
builder = TimelineBuilder(pm)
events = builder.build()
sessions = builder.sessions

# Correlate evidence
correlator = EvidenceCorrelator()
groups = correlator.correlate(events)

# Generate statistics
report = TimelineStatistics.generate(events, sessions, groups)
TimelineStatistics.print_report(report)
```

Features: event factory, 7 correlation rules, investigation sessions, filters, search, statistics, JSON/CSV export.

Run tests: `python -m unittest test_phase3 -v`

See `timeline_architecture.md` for full developer documentation.

---

## Quick Start (Phase 4 — GUI Desktop Application)

Run the desktop interface:
```bash
python -m gui.app
```

Features:
- **Dashboard**: Modern cyber-dark cockpit showing key forensic metrics and recent activity feeds.
- **Cases**: Case management system.
- **Timeline**: Interactive search, keyword filtering, and metadata detail viewing.
- **Correlations**: Side-by-side view of anchored events and their cross-artifact correlates.
- **Graph View**: Redesigned 6-swimlane timeline representation detailing chronological evidence lines.
- **Statistics**: Visual progress-bar based contact frequencies and event analytics.

Run GUI tests:
```bash
python -m unittest test_phase4 -v
```

---

## Quick Start (Phase 5 — AI Investigation Assistant)

Configure and query the AI layer:

```python
from ai_engine import AIAssistant

# Initialize the assistant with timeline data
assistant = AIAssistant(
    events=backend.events,
    sessions=backend.sessions,
    correlations=backend.correlations,
    statistics=backend.statistics,
)

# Use the offline rule-based provider for verification
response = assistant.check_alibi()
print("Alibi Assessment:", response.answer)

# Detect behavioral anomalies
anomalies = assistant.detect_anomalies()
print("Anomalies:", anomalies.answer)

# Generate a full HTML investigation report
report = assistant.generate_report()
html_content = report.to_html()
```

### In-App AI Integration:
1. Navigate to the **AI Assistant** page to ask natural-language questions, check alibis, or run anomaly scans asynchronously.
2. Configure **Gemini**, **OpenAI**, or **Ollama** models directly from the **Settings** panel (requires API Key or local server endpoint).
3. View and export beautifully formatted forensic reports from the **Reports** page.

Run AI tests:
```bash
python -m unittest test_phase5 -v
```

---

## Project Structure

```
Phone-Trace/
├── case_config.py               # Shared case configuration
├── requirements.txt             # Dependencies (stdlib only)
├── validate_evidence.py         # Evidence validation script
├── test_phase2.py               # Phase 2 test suite (70 tests)
├── test_phase3.py               # Phase 3 test suite (60 tests)
├── parser_architecture.md       # Phase 2 developer docs
├── timeline_architecture.md     # Phase 3 developer docs
├── README.md
│
├── evidence_generator/          # Phase 1 — Synthetic evidence
│   ├── __init__.py
│   ├── main_generate.py         # Entry point
│   ├── utils.py                 # Shared helpers
│   ├── generate_calls.py        # Call log generator
│   ├── generate_sms.py          # SMS generator
│   ├── generate_browser.py      # Chrome history generator
│   ├── generate_gps.py          # GPS log generator
│   ├── generate_app_usage.py    # App usage generator
│   └── generate_file_metadata.py # File metadata generator
│
├── artifacts/                   # Phase 2 — Parsing framework
│   ├── __init__.py
│   ├── base.py                  # Abstract base parser
│   ├── models.py                # Data models (7 dataclasses)
│   ├── calls.py                 # Call log parser
│   ├── sms.py                   # SMS parser
│   ├── browser.py               # Chrome history parser
│   ├── gps.py                   # GPS log parser
│   ├── app_usage.py             # App usage parser
│   ├── filesystem.py            # File metadata parser
│   ├── parser_manager.py        # Unified parser API
│   └── validation.py            # Evidence validation
│
├── timeline/                    # Phase 3 — Timeline engine
│   ├── __init__.py
│   ├── models.py                # Timeline data models
│   ├── event_factory.py         # Record -> ForensicEvent converter
│   ├── timeline_builder.py      # Timeline construction + sessions
│   ├── correlator.py            # Evidence correlation (7 rules)
│   ├── timeline_filters.py      # Filters + search
│   ├── statistics.py            # Investigative metrics
│   └── timeline_export.py       # JSON + CSV export
│
├── evidence_output/             # Generated evidence (runtime)
│
├── parsers/                     # Legacy placeholder
├── ai_engine/                   # Phase 5 — AI Investigation Assistant
├── anomaly_detection/           # Anomaly rules placeholder
├── reporting/                   # Reporting package placeholder
├── gui/                         # Phase 4 — Desktop GUI Dashboard (PyQt6)
└── adb_extraction/              # ADB extraction placeholder
```

---

## Forensic Scenario

The generated evidence represents 21 days of activity for suspect **Arjun Mehta**.

- **Claimed alibi**: At home in Koramangala, Bangalore during the incident window (June 20, 2025, 22:00–23:30 IST)
- **Evidence suggests**: Phone was at Electronic City (~15 km away)

### Injected Anomalies

1. **Suspicious calls** — Calls to/from an unknown burner number during the incident
2. **Suspicious SMS** — Coded/cryptic messages near the incident window
3. **Missing call log entry** — A call referenced in SMS is absent from the call log
4. **GPS contradiction** — GPS places phone at Electronic City during alibi period
5. **Duplicate contact spelling** — "Vikram Singh" and "Vikrm Singh" for the same number
6. **Timezone inconsistency** — One Chrome entry stamped in UTC instead of IST

---

## Technical Notes

- **Deterministic**: All generation uses `random.seed(42)` for reproducibility
- **Chrome timestamps**: Microseconds since 1601-01-01 UTC (WebKit/Chrome format)
- **Call/SMS timestamps**: Unix epoch milliseconds (Android format)
- **GPS timestamps**: ISO 8601 with timezone
- **No external dependencies**: Uses only Python standard library

---

## License

This project is for educational and forensic research purposes.
