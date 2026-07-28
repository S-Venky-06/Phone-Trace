"""
PhoneTrace -- Statistics Dashboard Page
=========================================

Displays detailed investigative metrics using customized stat cards
and top contact progress bars.
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QGridLayout, QLabel, QScrollArea, QVBoxLayout, QWidget, QFrame,
    QProgressBar, QHBoxLayout,
)

from gui.theme import (
    ACCENT, BG_CARD, BORDER, TEXT, TEXT_DIM, SUCCESS, WARNING, DANGER,
    ARTIFACT_COLORS, AI_ACCENT,
)
from gui.widgets.stat_card import StatCard


class StatisticsPage(QWidget):
    """Statistics dashboard with metric cards and top contacts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target_values = {}
        self._current_values = {}
        self._timer = QTimer()
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._animate_counters)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(28, 24, 28, 24)
        self._layout.setSpacing(20)

        header = QLabel("Investigation Statistics")
        header.setObjectName("heading")
        self._layout.addWidget(header)

        # Cards grid
        grid = QGridLayout()
        grid.setSpacing(14)

        self._c_events = StatCard("⏱", "Total Events", "0", accent_color=ACCENT)
        self._c_calls = StatCard("📞", "Calls", "0", accent_color=ARTIFACT_COLORS["call"])
        self._c_sms = StatCard("💬", "SMS", "0", accent_color=ARTIFACT_COLORS["sms"])
        self._c_gps = StatCard("📍", "GPS Pings", "0", accent_color=ARTIFACT_COLORS["gps"])
        self._c_browser = StatCard("🌐", "Browser", "0", accent_color=ARTIFACT_COLORS["browser"])
        self._c_files = StatCard("📄", "Files", "0", accent_color=ARTIFACT_COLORS["file"])
        self._c_sessions = StatCard("⊟", "Sessions", "0", accent_color=ACCENT)
        self._c_corr = StatCard("⚡", "Correlations", "0", accent_color=WARNING)
        self._c_unknown = StatCard("❓", "Unknown Contacts", "0", accent_color=TEXT_DIM)
        self._c_hour = StatCard("🕐", "Busiest Hour", "0", accent_color=AI_ACCENT)
        self._c_day = StatCard("📅", "Busiest Day", "0", accent_color=AI_ACCENT)
        self._c_incident = StatCard("⚠", "Incident Events", "0", accent_color=DANGER)

        self._cards = [
            (self._c_events, "events"),
            (self._c_calls, "calls"),
            (self._c_sms, "sms"),
            (self._c_gps, "gps"),
            (self._c_browser, "browser"),
            (self._c_files, "files"),
            (self._c_sessions, "sessions"),
            (self._c_corr, "correlations"),
            (self._c_unknown, "unknown"),
            (self._c_incident, "incident"),
        ]

        # Order of displaying in grid (3 rows of 4 cards)
        all_cards_to_grid = [
            self._c_events, self._c_calls, self._c_sms, self._c_gps,
            self._c_browser, self._c_files, self._c_sessions, self._c_corr,
            self._c_unknown, self._c_hour, self._c_day, self._c_incident,
        ]
        for i, card in enumerate(all_cards_to_grid):
            grid.addWidget(card, i // 4, i % 4)
        self._layout.addLayout(grid)

        # Top contacts section
        contacts_header = QLabel("Top Contacts (Calls + SMS)")
        contacts_header.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {TEXT}; margin-top: 12px; background: transparent;"
        )
        self._layout.addWidget(contacts_header)

        self._contacts_frame = QFrame()
        self._contacts_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        self._contacts_layout = QVBoxLayout(self._contacts_frame)
        self._contacts_layout.setSpacing(8)
        self._layout.addWidget(self._contacts_frame)

        self._layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def update_from_backend(self, backend) -> None:
        """Refresh from backend statistics and trigger animations."""
        if not backend or not backend.is_loaded:
            return

        s = backend.statistics
        if not s:
            return

        ct = s.counts_by_type

        # Parse target values for numerical count animation
        self._target_values = {
            "events": s.total_events,
            "calls": ct.get('call', 0),
            "sms": ct.get('sms', 0),
            "gps": ct.get('gps', 0),
            "browser": ct.get('browser', 0),
            "files": ct.get('file', 0),
            "sessions": s.session_count,
            "correlations": s.correlation_count,
            "unknown": s.unknown_contacts,
            "incident": s.incident_events,
        }

        # Initialize current animation state
        for key in self._target_values:
            self._current_values[key] = 0

        self._timer.start()

        # Update non-animating cards directly
        self._c_hour.set_value(f"{s.busiest_hour:02d}:00")
        self._c_hour.set_subtitle(f"{s.busiest_hour_count} events total")

        if s.busiest_day:
            self._c_day.set_value(s.busiest_day.strftime("%b %d, %Y"))
        else:
            self._c_day.set_value("---")

        # Top contacts progress bars
        self._clear_contacts()
        top10 = list(s.communication_frequency.items())[:10]
        max_count = top10[0][1] if top10 else 1

        for number, count in top10:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(12)

            lbl = QLabel(f"{number}")
            lbl.setStyleSheet(
                f"font-size: 13px; font-family: 'Segoe UI', sans-serif; "
                f"color: {TEXT}; background: transparent; font-weight: 500;"
            )
            lbl.setFixedWidth(140)
            row_layout.addWidget(lbl)

            bar = QProgressBar()
            bar.setStyleSheet(f"""
                QProgressBar {{
                    background-color: {BORDER};
                    border: none;
                    border-radius: 4px;
                    text-align: right;
                    color: {TEXT};
                    padding-right: 8px;
                    font-size: 11px;
                    font-weight: 600;
                    min-height: 18px;
                    max-height: 18px;
                }}
                QProgressBar::chunk {{
                    background-color: {ACCENT};
                    border-radius: 4px;
                }}
            """)
            bar.setMaximum(max_count)
            bar.setValue(count)
            bar.setFormat(f"{count} interactions")
            row_layout.addWidget(bar)

            row_widget = QWidget()
            row_widget.setLayout(row_layout)
            row_widget.setStyleSheet("background: transparent;")
            self._contacts_layout.addWidget(row_widget)

    def _animate_counters(self) -> None:
        finished = True
        for key, target in self._target_values.items():
            current = self._current_values[key]
            if current < target:
                diff = target - current
                # Increments dynamically based on remaining difference
                step = max(1, diff // 5)
                self._current_values[key] += step
                finished = False
            else:
                self._current_values[key] = target

        # Apply animated values to cards
        for card, key in self._cards:
            card.set_value(f"{self._current_values[key]:,}")

        if finished:
            self._timer.stop()

    def _clear_contacts(self) -> None:
        while self._contacts_layout.count():
            item = self._contacts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
