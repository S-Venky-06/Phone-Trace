# PhoneTrace -- GUI Architecture

## Overview

The GUI is a PyQt6 desktop application following MVC architecture.
It consumes the existing backend modules (ParserManager, TimelineBuilder, EvidenceCorrelator, TimelineFilter, TimelineStatistics, TimelineExporter) without duplicating any business logic.

```
┌─────────────────────────────────────────────────────────┐
│                     MainWindow                          │
│ ┌─────────┬────────────────────────┬──────────────────┐ │
│ │ MenuBar │       ToolBar          │                  │ │
│ ├─────────┼────────────────────────┼──────────────────┤ │
│ │         │                        │                  │ │
│ │ Sidebar │   QStackedWidget       │  DetailsPanel    │ │
│ │         │   ┌──────────────────┐ │                  │ │
│ │ ⌂ Dash  │   │  Active Page     │ │  Event Details   │ │
│ │ ☰ Cases │   │  (9 pages)       │ │  Metadata        │ │
│ │ ⏱ Time  │   │                  │ │  Location        │ │
│ │ ⚡ Corr  │   │                  │ │  Related         │ │
│ │ ☃ Evid  │   │                  │ │                  │ │
│ │ ≡ Stats │   │                  │ │                  │ │
│ │ ◈ Graph │   └──────────────────┘ │                  │ │
│ │ ⎘ Rpts  │                        │                  │ │
│ │ ⚙ Sett  │                        │                  │ │
│ ├─────────┴────────────────────────┴──────────────────┤ │
│ │                     StatusBar                       │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Window Hierarchy

```
MainWindow (QMainWindow)
├── MenuBar (File, View, Help)
├── ToolBar (Load, Dashboard, Timeline, Correlations, Graph)
├── Central Widget
│   ├── Sidebar (navigation, page_changed signal)
│   ├── QSplitter
│   │   ├── QStackedWidget (9 pages)
│   │   │   ├── DashboardPage
│   │   │   ├── CasesPage
│   │   │   ├── TimelinePage
│   │   │   ├── CorrelationPage
│   │   │   ├── EvidencePage
│   │   │   ├── StatisticsPage
│   │   │   ├── GraphView
│   │   │   ├── ReportsPage
│   │   │   └── SettingsPage
│   │   └── DetailsPanel
└── StatusBar
```

---

## Navigation Flow

1. User clicks a sidebar button → `Sidebar.page_changed(key)` signal fires
2. `MainWindow._navigate(key)` switches `QStackedWidget` index
3. Pages with data reload on navigation or on initial "Load Evidence"
4. Clicking events in Timeline/Correlation/Evidence/Graph pages emits `event_selected`
5. `DetailsPanel.show_event()` updates the right panel

---

## MVC Responsibilities

| Layer | Class | Role |
|-------|-------|------|
| **Model** | `BackendService` | Wraps all backend modules, caches data |
| **Model** | `CaseManager` | Case CRUD + persistence |
| **Model** | `SettingsManager` | Settings read/write |
| **View** | Pages (`dashboard.py`, etc.) | Display data using Qt widgets |
| **View** | Widgets (`stat_card.py`, etc.) | Reusable UI components |
| **Controller** | `MainWindow` | Wires signals, handles navigation, triggers loads |

---

## Backend Integration Points

### BackendService (gui/services/backend.py)

The single facade wrapping:
- `ParserManager.load_all()` → parse evidence
- `TimelineBuilder.build()` → create timeline + sessions
- `EvidenceCorrelator.correlate()` → detect correlations
- `TimelineStatistics.generate()` → compute metrics
- `TimelineFilter.search()` / `by_artifact()` → filtering
- `TimelineExporter.to_json()` / `to_csv()` → export

GUI pages **never** import `artifacts.*` or `timeline.*` directly. Everything goes through `BackendService`.

### Data Flow

```
Load Evidence button clicked
    → MainWindow._load_evidence()
    → BackendService.load()
        → ParserManager.load_all()
        → TimelineBuilder.build()
        → EvidenceCorrelator.correlate()
        → TimelineStatistics.generate()
    → Refresh all pages
    → Status bar update
```

---

## File Structure

```
gui/
├── __init__.py              # Package exports
├── __main__.py              # python -m gui runner
├── app.py                   # QApplication entry point
├── main_window.py           # MainWindow (controller)
├── theme.py                 # Dark theme QSS
│
├── services/
│   ├── __init__.py
│   ├── backend.py           # BackendService facade
│   ├── case_manager.py      # CaseManager + CaseInfo
│   └── settings_manager.py  # SettingsManager
│
├── widgets/
│   ├── __init__.py
│   ├── sidebar.py           # Navigation sidebar
│   ├── details_panel.py     # Right details panel
│   ├── stat_card.py         # Metric card
│   └── search_bar.py        # Search input
│
└── pages/
    ├── __init__.py
    ├── dashboard.py          # Stat cards + recent activity
    ├── cases.py              # Case CRUD table
    ├── evidence.py           # Tree explorer
    ├── timeline_page.py      # QTableView + filters
    ├── correlation.py        # Correlation groups table
    ├── statistics_page.py    # Stats dashboard
    ├── graph_view.py         # QGraphicsView node graph
    ├── reports.py            # JSON/CSV export
    └── settings.py           # Editable config form
```

---

## How to Add Future Pages

1. Create `gui/pages/new_page.py` with a `QWidget` subclass
2. Add an entry to `NAV_ITEMS` in `gui/widgets/sidebar.py`
3. In `MainWindow._build_central_widget()`, instantiate the page and add to `self._pages`
4. If the page emits `event_selected`, connect it in `MainWindow._connect_signals()`
5. Add a `load_from_backend(backend)` method if the page needs data

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+L | Load Evidence |
| Ctrl+T | Navigate to Timeline |
| Ctrl+E | Navigate to Reports |
| Ctrl+Q | Quit |
| Ctrl+F | Search (when search bar has focus) |
