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
        from PyQt6.QtGui import QPixmap
        pm = QPixmap(480, 260)
        pm.fill(Qt.GlobalColor.transparent)
        super().__init__(pm, Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        
        self.setFixedSize(480, 260)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Central layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(36, 32, 36, 32)
        self.layout.setSpacing(10)

        title = QLabel("PhoneTrace")
        title.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {ACCENT}; letter-spacing: -1px; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)

        sub = QLabel("Digital Forensic Investigation Workstation")
        sub.setStyleSheet(f"font-size: 13px; color: {TEXT}; font-weight: 500; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(sub)

        self.layout.addStretch()

        self._status = QLabel("Initializing forensic engine...")
        self._status.setStyleSheet(f"font-size: 11px; color: {TEXT_DIM}; background: transparent;")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self._status)

    def drawContents(self, painter):
        """Draw a custom dark rounded background."""
        from PyQt6.QtGui import QPainter, QPainterPath, QColor
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        painter.fillPath(path, QColor(BG_PRIMARY))
        
        # Draw border
        painter.setPen(QColor(BORDER))
        painter.drawPath(path)
        
    def show_message(self, msg: str):
        """Update the loading status message."""
        self._status.setText(msg)
        import sys
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
