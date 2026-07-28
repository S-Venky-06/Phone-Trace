"""
PhoneTrace -- Native Qt Interactive Charts Widget
====================================================

Custom QPainter-drawn chart widgets for investigative statistics.
- ActivityHeatmapWidget: 7x24 grid of event density
- ArtifactPieChartWidget: Donut chart of artifact distribution
- DailyEventBarChartWidget: Bar chart of daily event volumes
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from gui.theme import (
    ACCENT, ARTIFACT_COLORS, BG_CARD, BG_ELEVATED, BG_SECONDARY, BORDER,
    TEXT, TEXT_DIM,
)


class ActivityHeatmapWidget(QFrame):
    """7 days (Mon-Sun) x 24 hours activity density heatmap grid."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        # Grid array [day 0..6][hour 0..23] -> count
        self._grid: List[List[int]] = [[0] * 24 for _ in range(7)]
        self._max_count = 1

    def set_data(self, events: list) -> None:
        """Process ForensicEvent timestamps into day x hour grid."""
        self._grid = [[0] * 24 for _ in range(7)]
        self._max_count = 1

        for ev in events:
            if hasattr(ev, "timestamp") and ev.timestamp:
                day = ev.timestamp.weekday()  # 0 = Monday
                hour = ev.timestamp.hour
                self._grid[day][hour] += 1
                if self._grid[day][hour] > self._max_count:
                    self._max_count = self._grid[day][hour]
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        margin_left = 45
        margin_top = 35
        margin_bottom = 25
        margin_right = 20

        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        if w <= 0 or h <= 0:
            return

        cell_w = w / 24.0
        cell_h = h / 7.0

        # Title
        painter.setPen(QColor(TEXT))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(14, 22, "Activity Density Heatmap (Day × Hour)")

        # Draw Y Labels (Days)
        label_font = QFont("Segoe UI", 8)
        painter.setFont(label_font)
        painter.setPen(QColor(TEXT_DIM))

        for d_idx, day_name in enumerate(days):
            y = margin_top + d_idx * cell_h + cell_h / 2.0 + 4
            painter.drawText(10, int(y), day_name)

        # Draw X Labels (Hours: 0, 4, 8, 12, 16, 20)
        for hr in range(0, 24, 4):
            x = margin_left + hr * cell_w + cell_w / 2.0 - 8
            painter.drawText(int(x), self.height() - 8, f"{hr:02d}:00")

        # Base color accent (0x3B, 0x82, 0xF6 = #3B82F6)
        base_r, base_g, base_b = 59, 130, 246

        # Draw Heatmap Cells
        for d in range(7):
            for h_idx in range(24):
                val = self._grid[d][h_idx]
                x = margin_left + h_idx * cell_w
                y = margin_top + d * cell_h

                rect = QRectF(x + 1, y + 1, cell_w - 2, cell_h - 2)

                if val == 0:
                    fill = QColor(BG_SECONDARY)
                else:
                    alpha = int(40 + 215 * (val / float(self._max_count)))
                    fill = QColor(base_r, base_g, base_b, min(alpha, 255))

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(fill))
                painter.drawRoundedRect(rect, 3, 3)


class ArtifactPieChartWidget(QFrame):
    """Donut chart showing distribution of artifact types."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        self._counts: Dict[str, int] = {}
        self._total = 0

    def set_data(self, counts: Dict[str, int]) -> None:
        self._counts = counts
        self._total = sum(counts.values())
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Title
        painter.setPen(QColor(TEXT))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(14, 22, "Artifact Type Breakdown")

        if self._total == 0:
            return

        # Draw Donut Chart on Left
        chart_size = min(self.width() * 0.45, self.height() - 50)
        cx = 25 + chart_size / 2.0
        cy = 35 + (self.height() - 35) / 2.0
        r_outer = chart_size / 2.0
        r_inner = r_outer * 0.55

        rect_outer = QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2)

        start_angle = 90 * 16
        for atype, count in self._counts.items():
            if count <= 0:
                continue
            span_angle = int(round(-360 * 16 * (count / float(self._total))))
            color_hex = ARTIFACT_COLORS.get(atype, "#64748B")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.drawPie(rect_outer, start_angle, span_angle)

            start_angle += span_angle

        # Inner hole (Donut shape)
        rect_inner = QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2)
        painter.setBrush(QBrush(QColor(BG_CARD)))
        painter.drawEllipse(rect_inner)

        # Total label inside hole
        painter.setPen(QColor(TEXT))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(rect_inner, Qt.AlignmentFlag.AlignCenter, f"{self._total:,}\nTotal")

        # Draw Legend on Right
        legend_x = cx + r_outer + 25
        legend_y = 45
        label_font = QFont("Segoe UI", 9)
        painter.setFont(label_font)

        for atype, count in self._counts.items():
            if count <= 0:
                continue
            pct = (count / float(self._total)) * 100
            color_hex = ARTIFACT_COLORS.get(atype, "#64748B")

            # Color pill
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.drawRoundedRect(QRectF(legend_x, legend_y, 12, 12), 3, 3)

            # Label text
            painter.setPen(QColor(TEXT))
            label_str = f"{atype.upper()}: {count:,} ({pct:.1f}%)"
            painter.drawText(int(legend_x + 20), int(legend_y + 10), label_str)

            legend_y += 22
            if legend_y > self.height() - 20:
                break


class DailyEventBarChartWidget(QFrame):
    """Bar chart displaying daily event counts across the baseline window."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(220)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 12px;
            }}
        """)
        self._daily_counts: List[Tuple[str, int]] = []  # [(date_str, count)]
        self._max_val = 1

    def set_data(self, events: list) -> None:
        """Group events by date and calculate counts."""
        from collections import defaultdict
        counts_by_date = defaultdict(int)

        for ev in events:
            if hasattr(ev, "timestamp") and ev.timestamp:
                d_str = ev.timestamp.strftime("%b %d")
                counts_by_date[d_str] += 1

        self._daily_counts = sorted(counts_by_date.items(), key=lambda x: x[0])
        self._max_val = max([c for _, c in self._daily_counts] or [1])
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Title
        painter.setPen(QColor(TEXT))
        font = QFont("Segoe UI", 10, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(14, 22, "Daily Event Volume Timeline")

        if not self._daily_counts:
            return

        margin_left = 40
        margin_right = 20
        margin_top = 40
        margin_bottom = 30

        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        if w <= 0 or h <= 0:
            return

        n_bars = len(self._daily_counts)
        bar_w = w / float(n_bars)

        # Draw Y-Axis baseline
        painter.setPen(QPen(QColor(BORDER), 1))
        painter.drawLine(margin_left, self.height() - margin_bottom, self.width() - margin_right, self.height() - margin_bottom)

        # Draw Bars
        painter.setFont(QFont("Segoe UI", 8))

        for idx, (date_str, count) in enumerate(self._daily_counts):
            bar_h = (count / float(self._max_val)) * h
            x = margin_left + idx * bar_w + bar_w * 0.15
            bw = bar_w * 0.7
            y = self.height() - margin_bottom - bar_h

            rect = QRectF(x, y, bw, bar_h)

            # Highlight bar if high volume
            color = QColor(ACCENT) if count < self._max_val * 0.8 else QColor("#F59E0B")

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawRoundedRect(rect, 3, 3)

            # Draw X label every 3 bars
            if idx % 3 == 0 or idx == n_bars - 1:
                painter.setPen(QColor(TEXT_DIM))
                painter.drawText(int(x - 5), self.height() - 10, date_str)
