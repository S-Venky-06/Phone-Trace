"""
PhoneTrace -- Case Management Page
=====================================

Create, open, close, delete, and search forensic cases.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from gui.services.case_manager import CaseManager
from gui.theme import TEXT_DIM, BORDER, BG_CARD, TEXT, SELECTION, BG_SECONDARY, BG_ELEVATED, BG_PRIMARY


class _NewCaseDialog(QDialog):
    """Modal dialog for creating a new case."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Case")
        self.setMinimumWidth(400)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
            }}
            QLabel {{
                color: {TEXT};
                font-weight: 500;
            }}
        """)

        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Arjun Mehta Investigation")
        layout.addRow("Case Name:", self.name_edit)

        self.inv_edit = QLineEdit()
        self.inv_edit.setPlaceholderText("e.g. Inspector Sharma")
        layout.addRow("Investigator:", self.inv_edit)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Brief description")
        layout.addRow("Description:", self.desc_edit)

        self.evidence_edit = QLineEdit()
        self.evidence_edit.setPlaceholderText("Leave blank for default")
        layout.addRow("Evidence Dir:", self.evidence_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        # Style dialog buttons
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addRow(buttons)


class CasesPage(QWidget):
    """Case management page with CRUD operations."""

    def __init__(self, case_manager: CaseManager, parent=None):
        super().__init__(parent)
        self._cm = case_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        header = QLabel("Case Management")
        header.setObjectName("heading")
        layout.addWidget(header)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search cases...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._refresh_table)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 8px 12px;
            }}
        """)
        toolbar.addWidget(self._search, 1)

        btn_new = QPushButton("+ New Case")
        btn_new.setObjectName("primaryBtn")
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_new.clicked.connect(self._on_new)
        toolbar.addWidget(btn_new)

        btn_close = QPushButton("Close Case")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self._on_close)
        toolbar.addWidget(btn_close)

        btn_delete = QPushButton("Delete")
        btn_delete.setObjectName("dangerBtn")
        btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_delete.clicked.connect(self._on_delete)
        toolbar.addWidget(btn_delete)

        layout.addLayout(toolbar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Case ID", "Name", "Investigator", "Created", "Status"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._table.verticalHeader().setDefaultSectionSize(36)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {BG_SECONDARY};
                alternate-background-color: {BG_PRIMARY};
                gridline-color: transparent;
                border: 1px solid {BORDER};
                border-radius: 10px;
                selection-background-color: {SELECTION};
                selection-color: {TEXT};
                padding: 2px;
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

        self._refresh_table()

    def _refresh_table(self) -> None:
        query = self._search.text().strip()
        cases = self._cm.search(query) if query else self._cm.cases
        self._table.setRowCount(len(cases))
        for row, case in enumerate(cases):
            self._table.setItem(row, 0, QTableWidgetItem(case.case_id))
            self._table.setItem(row, 1, QTableWidgetItem(case.name))
            self._table.setItem(row, 2, QTableWidgetItem(case.investigator))
            self._table.setItem(row, 3, QTableWidgetItem(case.created))
            self._table.setItem(row, 4, QTableWidgetItem(case.status))

    def _selected_id(self):
        row = self._table.currentRow()
        if row < 0:
            return None
        return self._table.item(row, 0).text()

    def _on_new(self) -> None:
        dlg = _NewCaseDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name = dlg.name_edit.text().strip() or "Untitled Case"
            inv = dlg.inv_edit.text().strip() or "Unknown"
            desc = dlg.desc_edit.text().strip()
            edir = dlg.evidence_edit.text().strip()
            self._cm.create_case(name, inv, edir, desc)
            self._refresh_table()

    def _on_close(self) -> None:
        cid = self._selected_id()
        if cid:
            self._cm.close_case(cid)
            self._refresh_table()

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
