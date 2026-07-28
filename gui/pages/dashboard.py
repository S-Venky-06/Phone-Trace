"""
PhoneTrace -- Dashboard Page
===============================

Professional investigation dashboard with metric cards,
case info banner, and styled recent activity feed.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget,
)

from gui.theme import (
    ACCENT, ARTIFACT_COLORS, BG_CARD, BG_ELEVATED, BG_SECONDARY,
    BORDER, DANGER, SUCCESS, TEXT, TEXT_DIM, WARNING,
)
from gui.widgets.stat_card import StatCard


class DashboardPage(QWidget):
    """Main dashboard with metric cards and recent activity list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(28, 24, 28, 24)
        self._layout.setSpacing(20)

        # Header
        header = QLabel("Investigation Dashboard")
        header.setObjectName("heading")
        self._layout.addWidget(header)

        sub = QLabel("Overview of the current forensic investigation")
        sub.setObjectName("subheading")
        self._layout.addWidget(sub)

        # Case Info Banner (initially hidden)
        self._case_banner = QFrame()
        self._case_banner.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 14px 18px;
            }}
        """)
        self._case_banner.setVisible(False)
        banner_layout = QHBoxLayout(self._case_banner)
        banner_layout.setContentsMargins(0, 0, 0, 0)
        self._case_info = QLabel("")
        self._case_info.setStyleSheet(
            f"color: {TEXT}; font-size: 13px; background: transparent;"
        )
        banner_layout.addWidget(self._case_info)
        self._layout.addWidget(self._case_banner)

        # Stat cards grid
        self._cards_grid = QGridLayout()
        self._cards_grid.setSpacing(14)
        self._layout.addLayout(self._cards_grid)

        self._card_events = StatCard(
            "⏱", "Timeline Events", "---",
            accent_color=ACCENT,
        )
        self._card_calls = StatCard(
            "📞", "Calls", "---",
            accent_color=ARTIFACT_COLORS["call"],
        )
        self._card_sms = StatCard(
            "💬", "SMS Messages", "---",
            accent_color=ARTIFACT_COLORS["sms"],
        )
        self._card_gps = StatCard(
            "📍", "GPS Pings", "---",
            accent_color=ARTIFACT_COLORS["gps"],
        )
        self._card_browser = StatCard(
            "🌐", "Browser Visits", "---",
            accent_color=ARTIFACT_COLORS["browser"],
        )
        self._card_files = StatCard(
            "📄", "Files", "---",
            accent_color=ARTIFACT_COLORS["file"],
        )
        self._card_sessions = StatCard(
            "⊟", "Sessions", "---",
            accent_color=ACCENT,
        )
        self._card_corr = StatCard(
            "⚡", "Correlations", "---",
            accent_color=WARNING,
        )

        cards = [
            self._card_events, self._card_calls, self._card_sms,
            self._card_gps, self._card_browser, self._card_files,
            self._card_sessions, self._card_corr,
        ]
        for i, card in enumerate(cards):
            self._cards_grid.addWidget(card, i // 4, i % 4)

        # Recent Activity header
        act_header = QHBoxLayout()
        activity_label = QLabel("Recent Activity")
        activity_label.setStyleSheet(
            f"font-size: 15px; font-weight: 600; color: {TEXT}; "
            f"margin-top: 4px; background: transparent;"
        )
        act_header.addWidget(activity_label)
        act_header.addStretch()
        self._layout.addLayout(act_header)

        # Activity feed
        self._activity_frame = QFrame()
        self._activity_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
            }}
        """)
        self._activity_layout = QVBoxLayout(self._activity_frame)
        self._activity_layout.setContentsMargins(0, 0, 0, 0)
        self._activity_layout.setSpacing(0)

        self._empty_activity = QLabel(
            "  📂  Load evidence to see recent activity."
        )
        self._empty_activity.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 13px; padding: 24px; "
            f"background: transparent;"
        )
        self._empty_activity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._activity_layout.addWidget(self._empty_activity)
        self._layout.addWidget(self._activity_frame)

        self._layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def set_case_info(self, case) -> None:
        """Update and display active case details in the banner."""
        if not case:
            self._case_banner.setVisible(False)
            return

        self._case_info.setText(
            f"<b>Active Case:</b> {case.name} ({case.case_id}) &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Investigator:</b> {case.investigator} &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"<b>Status:</b> <span style='color: {SUCCESS};'>{case.status}</span>"
        )
        self._case_banner.setVisible(True)

    def update_from_backend(self, backend) -> None:
        """Refresh all cards and recent activity from the backend."""
        if not backend or not backend.is_loaded:
            return

        stats = backend.statistics
        if stats:
            self._card_events.set_value(f"{stats.total_events:,}")
            ct = stats.counts_by_type
            self._card_calls.set_value(f"{ct.get('call', 0):,}")
            self._card_sms.set_value(f"{ct.get('sms', 0):,}")
            self._card_gps.set_value(f"{ct.get('gps', 0):,}")
            self._card_browser.set_value(f"{ct.get('browser', 0):,}")
            self._card_files.set_value(f"{ct.get('file', 0):,}")
            self._card_sessions.set_value(f"{stats.session_count:,}")
            self._card_corr.set_value(f"{stats.correlation_count:,}")

        # Recent activity (last 15 events)
        self._clear_activity()

        for idx, event in enumerate(backend.events[-15:]):
            ts = event.timestamp.strftime("%Y-%m-%d  %H:%M")
            color = ARTIFACT_COLORS.get(event.artifact_type, "#64748B")

            # Alternating row background
            bg = BG_CARD if idx % 2 == 0 else BG_SECONDARY

            # Build styled row
            row = QLabel(
                f"<span style='color: {TEXT_DIM}; font-size: 12px;'>{ts}</span>"
                f"&nbsp;&nbsp;"
                f"<span style='background-color: {color}25; color: {color}; "
                f"font-weight: 600; font-size: 11px; padding: 2px 6px; "
                f"border-radius: 3px;'>"
                f" {event.artifact_type.upper()} </span>"
                f"&nbsp;&nbsp;"
                f"<span style='color: {TEXT}; font-weight: 500;'>"
                f"{event.title}</span>"
            )
            row.setStyleSheet(
                f"padding: 10px 16px; background-color: {bg}; "
                f"border-bottom: 1px solid {BORDER};"
            )
            self._activity_layout.addWidget(row)

    def _clear_activity(self) -> None:
        while self._activity_layout.count():
            item = self._activity_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
