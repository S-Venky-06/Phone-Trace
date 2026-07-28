"""
PhoneTrace -- Search Bar Widget
=================================

Professional pill-shaped search input with icon prefix and clear button.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget

from gui.theme import ACCENT, BG_SECONDARY, BORDER, TEXT, TEXT_DIM


class SearchBar(QWidget):
    """Search input that emits a signal when the user presses Enter or clicks Search."""

    searched = pyqtSignal(str)

    def __init__(self, placeholder: str = "Search timeline...", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._input = QLineEdit()
        self._input.setPlaceholderText(f"🔍  {placeholder}")
        self._input.setClearButtonEnabled(True)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 18px;
                padding: 8px 16px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {ACCENT};
            }}
        """)
        self._input.returnPressed.connect(self._on_search)
        layout.addWidget(self._input, 1)

        btn = QPushButton("Search")
        btn.setObjectName("primaryBtn")
        btn.setFixedWidth(80)
        btn.setFixedHeight(36)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT};
                color: #ffffff;
                border: none;
                border-radius: 18px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #2563EB;
            }}
            QPushButton:pressed {{
                background-color: #1D4ED8;
            }}
        """)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(self._on_search)
        layout.addWidget(btn)

    def _on_search(self) -> None:
        text = self._input.text().strip()
        self.searched.emit(text)

    def clear(self) -> None:
        self._input.clear()

    @property
    def text(self) -> str:
        return self._input.text().strip()
