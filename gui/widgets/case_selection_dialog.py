"""
PhoneTrace -- Case Selection Dialog
=====================================

Standalone dialog presented at application launch or when switching cases.
Enables opening, creating, searching, and deleting forensic cases.
"""

from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from gui.pages.cases import _NewCaseDialog
from gui.services.case_manager import CaseInfo, CaseManager
from gui.theme import (
    ACCENT, BG_CARD, BG_ELEVATED, BG_PRIMARY, BG_SECONDARY, BORDER,
    SELECTION, TEXT, TEXT_DIM,
)


class CaseSelectionDialog(QDialog):
    """Standalone window for selecting or creating a forensic case."""

    def __init__(self, case_manager: CaseManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._cm = case_manager
        self._selected_case: Optional[CaseInfo] = None

        self.setWindowTitle("PhoneTrace — Select Investigation Case")
        self.resize(720, 500)
        self.setMinimumSize(600, 400)

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_PRIMARY};
            }}
            QLabel {{
                color: {TEXT};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Header Banner
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)

        title = QLabel("PhoneTrace")
        title.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {ACCENT}; letter-spacing: -0.5px;")
        header_layout.addWidget(title)

        subtitle = QLabel("Select an existing case or create a new case to launch the workstation.")
        subtitle.setStyleSheet(f"font-size: 13px; color: {TEXT_DIM}; font-weight: 400;")
        header_layout.addWidget(subtitle)

        layout.addLayout(header_layout)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search cases by name or investigator...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._refresh_table)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 9px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {ACCENT};
            }}
        """)
        toolbar.addWidget(self._search, 1)

        btn_open = QPushButton("📂 Open Case")
        btn_open.setObjectName("primaryBtn")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setMinimumHeight(38)
        btn_open.clicked.connect(self._on_open)
        toolbar.addWidget(btn_open)

        btn_new = QPushButton("+ New Case")
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.setMinimumHeight(38)
        btn_new.clicked.connect(self._on_new)
        toolbar.addWidget(btn_new)

        btn_delete = QPushButton("Delete")
        btn_delete.setObjectName("dangerBtn")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.setMinimumHeight(38)
        btn_delete.clicked.connect(self._on_delete)
        toolbar.addWidget(btn_delete)

        layout.addLayout(toolbar)

        # Table View
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Case ID", "Case Name", "Investigator", "Created", "Status"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.verticalHeader().setDefaultSectionSize(38)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._on_open)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_SECONDARY};
                alternate-background-color: {BG_PRIMARY};
                gridline-color: transparent;
                border: 1px solid {BORDER};
                border-radius: 10px;
                selection-background-color: {SELECTION};
                selection-color: {TEXT};
                padding: 4px;
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px 12px;
                border: none;
            }}
            QTableWidget::item:hover {{
                background-color: {BG_ELEVATED};
            }}
        """)
        layout.addWidget(self._table)

        # Footer Status & Exit
        footer = QHBoxLayout()
        self._count_label = QLabel("0 cases")
        self._count_label.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500;")
        footer.addWidget(self._count_label)
        footer.addStretch()

        btn_exit = QPushButton("Cancel / Exit")
        btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_exit.setFixedHeight(34)
        btn_exit.clicked.connect(self.reject)
        footer.addWidget(btn_exit)

        layout.addLayout(footer)

        self._refresh_table()

    @property
    def selected_case(self) -> Optional[CaseInfo]:
        """Returns the CaseInfo selected by the user."""
        return self._selected_case

    def _refresh_table(self) -> None:
        query = self._search.text().strip()
        cases = self._cm.search(query) if query else self._cm.cases
        self._table.setRowCount(len(cases))
        self._count_label.setText(f"{len(cases)} case(s) found")

        for row, case in enumerate(cases):
            self._table.setItem(row, 0, QTableWidgetItem(case.case_id))
            self._table.setItem(row, 1, QTableWidgetItem(case.name))
            self._table.setItem(row, 2, QTableWidgetItem(case.investigator))
            self._table.setItem(row, 3, QTableWidgetItem(case.created))
            self._table.setItem(row, 4, QTableWidgetItem(case.status))

        # Auto select first row if available
        if cases and self._table.currentRow() < 0:
            self._table.selectRow(0)

    def _selected_id(self) -> Optional[str]:
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.text() if item else None

    def _on_open(self) -> None:
        cid = self._selected_id()
        if not cid:
            QMessageBox.information(
                self, "Select Case", "Please select a case from the list first."
            )
            return
        case = self._cm.open_case(cid)
        if case:
            self._selected_case = case
            self.accept()

    def _on_new(self) -> None:
        dlg = _NewCaseDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.name_edit.text().strip() or "Untitled Case"
            inv = dlg.inv_edit.text().strip() or "Unknown"
            desc = dlg.desc_edit.text().strip()
            edir = dlg.evidence_edit.text().strip()
            case = self._cm.create_case(name, inv, edir, desc)
            self._selected_case = case
            self.accept()

    def _on_delete(self) -> None:
        cid = self._selected_id()
        if not cid:
            return
        reply = QMessageBox.question(
            self, "Delete Case",
            f"Delete case {cid}? This cannot be undone.",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._cm.delete_case(cid)
            self._refresh_table()
