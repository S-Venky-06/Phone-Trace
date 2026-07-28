"""
PhoneTrace -- Splash Screen Widget
======================================

Branded splash screen displayed during application startup.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QFrame, QLabel, QProgressBar, QVBoxLayout, QWidget, QSplashScreen

from gui.theme import ACCENT, BG_CARD, BG_PRIMARY, BORDER, TEXT, TEXT_DIM


class PhoneTraceSplashScreen(QSplashScreen):
    """Branded splash screen for application initialization."""

    def __init__(self) -> None:
        frame = QFrame()
        frame.setFixedSize(480, 260)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_PRIMARY};
                border: 1px solid {BORDER};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(10)

        title = QLabel("PhoneTrace")
        title.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {ACCENT}; letter-spacing: -1px; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Digital Forensic Investigation Workstation")
        sub.setStyleSheet(f"font-size: 13px; color: {TEXT}; font-weight: 500; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        layout.addStretch()

        self._status = QLabel("Initializing forensic engine...")
        self._status.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        pixmap = frame.grab()
        super().__init__(pixmap, Qt.WindowType.WindowStaysOnTopHint)
