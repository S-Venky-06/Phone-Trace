"""
PhoneTrace -- Reports Page
=============================

Export timeline to JSON/CSV and generate AI investigation reports.
Enhanced with workstation-style buttons and layout.
"""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTextBrowser, QVBoxLayout, QWidget,
)

from gui.theme import (
    AI_ACCENT, BG_SECONDARY, BORDER, SUCCESS, TEXT, TEXT_DIM, DANGER,
)


class _ReportWorker(QThread):
    """Background thread for report generation."""
    finished = pyqtSignal(str)  # HTML content
    error = pyqtSignal(str)

    def __init__(self, assistant, parent=None):
        super().__init__(parent)
        self._assistant = assistant

    def run(self):
        try:
            report = self._assistant.generate_report()
            self.finished.emit(report.to_html())
        except Exception as exc:
            self.error.emit(str(exc))


class ReportsPage(QWidget):
    """Export timeline data, generate and preview AI reports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._backend = None
        self._assistant = None
        self._worker = None
        self._last_html = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        header = QLabel("Reports & Export")
        header.setObjectName("heading")
        layout.addWidget(header)

        sub = QLabel("Export forensic timeline data or generate AI investigation reports in JSON, CSV, HTML, or PDF formats.")
        sub.setObjectName("subheading")
        layout.addWidget(sub)

        # Export buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_json = QPushButton("📥  Export Timeline JSON")
        btn_json.setObjectName("primaryBtn")
        btn_json.setMinimumHeight(40)
        btn_json.clicked.connect(self._export_json)
        btn_row.addWidget(btn_json)

        btn_csv = QPushButton("📥  Export Timeline CSV")
        btn_csv.setObjectName("primaryBtn")
        btn_csv.setMinimumHeight(40)
        btn_csv.clicked.connect(self._export_csv)
        btn_row.addWidget(btn_csv)

        layout.addLayout(btn_row)

        # AI Report buttons row
        ai_row = QHBoxLayout()
        ai_row.setSpacing(10)

        self._btn_gen_report = QPushButton("📊  Generate AI Report")
        self._btn_gen_report.setObjectName("aiBtn")
        self._btn_gen_report.setMinimumHeight(40)
        self._btn_gen_report.clicked.connect(self._generate_report)
        ai_row.addWidget(self._btn_gen_report)

        self._btn_export_html = QPushButton("🌐  Export HTML")
        self._btn_export_html.setMinimumHeight(40)
        self._btn_export_html.setEnabled(False)
        self._btn_export_html.clicked.connect(self._export_html)
        ai_row.addWidget(self._btn_export_html)

        self._btn_export_pdf = QPushButton("📄  Export PDF")
        self._btn_export_pdf.setMinimumHeight(40)
        self._btn_export_pdf.setEnabled(False)
        self._btn_export_pdf.clicked.connect(self._export_pdf)
        ai_row.addWidget(self._btn_export_pdf)

        layout.addLayout(ai_row)

        # Status
        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500;")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        # Report preview area
        preview_label = QLabel("Report Preview")
        preview_label.setStyleSheet(
            f"color: {TEXT}; font-size: 14px; font-weight: 600; background: transparent; margin-top: 4px;"
        )
        layout.addWidget(preview_label)

        self._preview = QTextBrowser()
        self._preview.setOpenExternalLinks(True)
        self._preview.setPlaceholderText(
            "Generate an AI report to preview it here."
        )
        self._preview.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 16px;
                font-size: 13px;
            }}
        """)
        layout.addWidget(self._preview, stretch=1)

    def set_backend(self, backend) -> None:
        self._backend = backend

    def set_assistant(self, assistant) -> None:
        self._assistant = assistant

    def _export_json(self) -> None:
        if not self._backend or not self._backend.is_loaded:
            QMessageBox.warning(self, "No Data", "Load evidence first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Timeline JSON", "timeline_export.json",
            "JSON Files (*.json)",
        )
        if path:
            try:
                out = self._backend.export_json(path)
                self._status.setText(f"✓ JSON exported to: {out}")
                self._status.setStyleSheet(f"color: {SUCCESS};")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

    def _export_csv(self) -> None:
        if not self._backend or not self._backend.is_loaded:
            QMessageBox.warning(self, "No Data", "Load evidence first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Timeline CSV", "timeline_export.csv",
            "CSV Files (*.csv)",
        )
        if path:
            try:
                out = self._backend.export_csv(path)
                self._status.setText(f"✓ CSV exported to: {out}")
                self._status.setStyleSheet(f"color: {SUCCESS};")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

    def _generate_report(self) -> None:
        if not self._assistant:
            QMessageBox.warning(
                self, "No Data",
                "Load evidence first. The AI assistant must be initialised.",
            )
            return

        self._btn_gen_report.setEnabled(False)
        self._status.setText("⏳ Compiling AI report details...")
        self._status.setStyleSheet(f"color: {AI_ACCENT};")

        self._worker = _ReportWorker(self._assistant, parent=self)
        self._worker.finished.connect(self._on_report_done)
        self._worker.error.connect(self._on_report_error)
        self._worker.start()

    def _on_report_done(self, html: str) -> None:
        self._last_html = html
        self._preview.setHtml(html)
        self._btn_gen_report.setEnabled(True)
        self._btn_export_html.setEnabled(True)
        self._btn_export_pdf.setEnabled(True)
        self._status.setText("✓ Report generated successfully.")
        self._status.setStyleSheet(f"color: {SUCCESS};")

    def _on_report_error(self, error_text: str) -> None:
        self._btn_gen_report.setEnabled(True)
        self._status.setText(f"✗ Report generation failed: {error_text}")
        self._status.setStyleSheet(f"color: {DANGER};")

    def _export_html(self) -> None:
        if not self._last_html:
            QMessageBox.warning(self, "No Report", "Generate a report first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Report HTML", "investigation_report.html",
            "HTML Files (*.html)",
        )
        if path:
            try:
                Path(path).write_text(self._last_html, encoding="utf-8")
                self._status.setText(f"✓ Report exported to: {path}")
                self._status.setStyleSheet(f"color: {SUCCESS};")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", str(exc))

    def _export_pdf(self) -> None:
        if not self._last_html:
            QMessageBox.warning(self, "No Report", "Generate a report first.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Report PDF", "investigation_report.pdf",
            "PDF Files (*.pdf)",
        )
        if path:
            try:
                doc = QTextDocument()
                doc.setHtml(self._last_html)
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(path)
                doc.print_(printer)

                self._status.setText(f"✓ Report exported to PDF: {path}")
                self._status.setStyleSheet(f"color: {SUCCESS};")
            except Exception as exc:
                QMessageBox.critical(self, "Export Error", f"Failed to export PDF: {exc}")

