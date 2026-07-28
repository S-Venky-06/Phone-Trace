"""
PhoneTrace -- AI Assistant Page
==================================

Interactive chat-style interface for the AI investigation assistant.
Provides quick-action buttons, a query input, and a scrollable
response display area.
Running in a background QThread to keep the GUI responsive.
"""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from gui.theme import (
    ACCENT,
    AI_ACCENT,
    BG_SECONDARY,
    BG_PRIMARY,
    BG_ELEVATED,
    BG_CARD,
    BORDER,
    DANGER,
    SELECTION,
    SUCCESS,
    TEXT,
    TEXT_DIM,
    WARNING,
)

logger = logging.getLogger("gui.AIAssistantPage")


class _AIWorker(QThread):
    """Runs AI operations in a background thread."""

    finished = pyqtSignal(str, str)  # (result_text, operation_name)
    error = pyqtSignal(str, str)     # (error_text, operation_name)

    def __init__(self, func, operation_name: str, parent=None):
        super().__init__(parent)
        self._func = func
        self._op = operation_name

    def run(self):
        try:
            result = self._func()
            self.finished.emit(str(result), self._op)
        except Exception as exc:
            self.error.emit(str(exc), self._op)


class AIAssistantPage(QWidget):
    """AI Investigation Assistant page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._assistant = None
        self._worker: Optional[_AIWorker] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        # Header
        header = QLabel("AI Investigation Assistant")
        header.setObjectName("heading")
        layout.addWidget(header)

        sub = QLabel(
            "Ask questions about the forensic evidence or run automated analysis."
        )
        sub.setObjectName("subheading")
        layout.addWidget(sub)

        # Provider status bar
        status_frame = QFrame()
        status_frame.setStyleSheet(
            f"QFrame {{ background-color: {BG_CARD}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(16, 10, 16, 10)

        self._provider_label = QLabel("Provider: —")
        self._provider_label.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500; background: transparent;"
        )
        status_layout.addWidget(self._provider_label)

        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 14px; background: transparent;"
        )
        status_layout.addWidget(self._status_dot)

        self._status_text = QLabel("No data loaded")
        self._status_text.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500; background: transparent;"
        )
        status_layout.addWidget(self._status_text)
        status_layout.addStretch()

        layout.addWidget(status_frame)

        # Quick action buttons
        actions_label = QLabel("Forensic Assistants")
        actions_label.setStyleSheet(
            f"color: {TEXT}; font-size: 14px; font-weight: 600; background: transparent; margin-top: 4px;"
        )
        layout.addWidget(actions_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_alibi = self._make_action_btn(
            "🔍 Verify Alibi", "Verify suspect's alibi against GPS evidence"
        )
        self._btn_alibi.clicked.connect(self._on_check_alibi)
        btn_row.addWidget(self._btn_alibi)

        self._btn_anomaly = self._make_action_btn(
            "⚠ Detect Anomalies", "Find unusual patterns in the evidence"
        )
        self._btn_anomaly.clicked.connect(self._on_detect_anomalies)
        btn_row.addWidget(self._btn_anomaly)

        self._btn_narrative = self._make_action_btn(
            "📝 Generate Narrative", "Create a chronological investigation story"
        )
        self._btn_narrative.clicked.connect(self._on_generate_narrative)
        btn_row.addWidget(self._btn_narrative)

        self._btn_report = self._make_action_btn(
            "📊 Generate Report", "Create a full HTML investigation report"
        )
        self._btn_report.clicked.connect(self._on_generate_report)
        btn_row.addWidget(self._btn_report)

        layout.addLayout(btn_row)

        # Response area
        self._response_area = QTextEdit()
        self._response_area.setReadOnly(True)
        self._response_area.setPlaceholderText(
            "AI responses will appear here. Load evidence and ask a question "
            "or use the quick action buttons above."
        )
        self._response_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 16px;
                font-family: {TEXT};
                font-size: 13px;
                line-height: 1.5;
            }}
        """)
        layout.addWidget(self._response_area, stretch=1)

        # Query input row
        input_frame = QFrame()
        input_frame.setStyleSheet(
            f"QFrame {{ background-color: {BG_CARD}; "
            f"border: 1px solid {BORDER}; border-radius: 10px; }}"
        )
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(10)

        self._query_input = QLineEdit()
        self._query_input.setPlaceholderText(
            "Ask about the evidence... (e.g., 'Who called during the incident?')"
        )
        self._query_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG_SECONDARY};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {AI_ACCENT};
            }}
        """)
        self._query_input.returnPressed.connect(self._on_ask)
        input_layout.addWidget(self._query_input, stretch=1)

        self._btn_send = QPushButton("Ask AI  🤖")
        self._btn_send.setObjectName("aiBtn")
        self._btn_send.setMinimumHeight(40)
        self._btn_send.setMinimumWidth(100)
        self._btn_send.clicked.connect(self._on_ask)
        input_layout.addWidget(self._btn_send)

        layout.addWidget(input_frame)

        # Loading indicator
        self._loading_label = QLabel("")
        self._loading_label.setStyleSheet(
            f"color: {AI_ACCENT}; font-size: 13px; font-weight: 600;"
        )
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._loading_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_assistant(self, assistant) -> None:
        """Set the AI assistant instance."""
        self._assistant = assistant
        self._update_status()

    def _update_status(self) -> None:
        """Refresh the provider status display."""
        if self._assistant is None:
            self._provider_label.setText("Provider: —")
            self._status_dot.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 14px; background: transparent;"
            )
            self._status_text.setText("No data loaded")
            return

        self._provider_label.setText(
            f"Provider: {self._assistant.current_provider_name}"
        )

        if self._assistant.is_provider_available():
            self._status_dot.setStyleSheet(
                f"color: {SUCCESS}; font-size: 14px; background: transparent;"
            )
            self._status_text.setText("Connected")
            self._status_text.setStyleSheet(
                f"color: {SUCCESS}; font-size: 13px; font-weight: 500; background: transparent;"
            )
        else:
            self._status_dot.setStyleSheet(
                f"color: {DANGER}; font-size: 14px; background: transparent;"
            )
            self._status_text.setText("Unavailable")
            self._status_text.setStyleSheet(
                f"color: {DANGER}; font-size: 13px; font-weight: 500; background: transparent;"
            )

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    def _on_ask(self) -> None:
        """Handle free-form question."""
        query = self._query_input.text().strip()
        if not query:
            return
        if not self._assistant:
            self._show_no_data()
            return

        self._query_input.clear()
        self._append_user_message(query)
        self._run_async(
            lambda: self._assistant.ask(query),
            "query",
        )

    def _on_check_alibi(self) -> None:
        if not self._assistant:
            self._show_no_data()
            return
        self._append_system_message("Verifying suspect alibi claims...")
        self._run_async(
            lambda: self._assistant.check_alibi(),
            "alibi_check",
        )

    def _on_detect_anomalies(self) -> None:
        if not self._assistant:
            self._show_no_data()
            return
        self._append_system_message("Analyzing forensic timelines for anomalies...")
        self._run_async(
            lambda: self._assistant.detect_anomalies(),
            "anomaly_detection",
        )

    def _on_generate_narrative(self) -> None:
        if not self._assistant:
            self._show_no_data()
            return
        self._append_system_message("Compiling investigator timeline narrative...")
        self._run_async(
            lambda: self._assistant.generate_narrative(),
            "narrative",
        )

    def _on_generate_report(self) -> None:
        if not self._assistant:
            self._show_no_data()
            return
        self._append_system_message("Compiling AI investigation report (HTML format)...")
        self._run_async(
            lambda: self._assistant.generate_report(),
            "report",
        )

    # ------------------------------------------------------------------
    # Async execution
    # ------------------------------------------------------------------

    def _run_async(self, func, operation_name: str) -> None:
        """Run an AI operation in a background thread."""
        if self._worker is not None and self._worker.isRunning():
            self._loading_label.setText("⏳ AI Agent is currently busy...")
            return

        self._set_busy(True)
        self._worker = _AIWorker(func, operation_name, parent=self)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.error.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_done(self, result: str, operation: str) -> None:
        """Handle completed AI operation."""
        self._set_busy(False)

        if operation == "report":
            try:
                if self._assistant:
                    report = self._assistant.generate_report()
                    html = report.to_html()
                    self._response_area.setHtml(html)
                    self._append_system_message(
                        "✓ Investigation report loaded into memory."
                    )
                    return
            except Exception:
                pass
            self._append_ai_response(result)
        elif operation == "narrative":
            self._append_ai_response(result)
        else:
            self._append_ai_response(result)

    def _on_worker_error(self, error_text: str, operation: str) -> None:
        """Handle AI operation error."""
        self._set_busy(False)
        self._append_error(f"Failed to execute {operation}: {error_text}")

    def _set_busy(self, busy: bool) -> None:
        """Toggle UI busy state."""
        self._btn_send.setEnabled(not busy)
        self._btn_alibi.setEnabled(not busy)
        self._btn_anomaly.setEnabled(not busy)
        self._btn_narrative.setEnabled(not busy)
        self._btn_report.setEnabled(not busy)
        self._query_input.setEnabled(not busy)

        if busy:
            self._loading_label.setText("🤖 AI Assistant is processing context...")
        else:
            self._loading_label.setText("")

    # ------------------------------------------------------------------
    # Message formatting
    # ------------------------------------------------------------------

    def _append_user_message(self, text: str) -> None:
        self._response_area.append(
            f'<p style="color: {ACCENT}; font-weight: 600; margin-top: 14px;">'
            f'● Investigator</p>'
            f'<p style="color: {TEXT}; margin-left: 14px;">{text}</p>'
        )

    def _append_system_message(self, text: str) -> None:
        self._response_area.append(
            f'<p style="color: {TEXT_DIM}; font-style: italic; '
            f'margin-top: 8px;">  {text}</p>'
        )

    def _append_ai_response(self, text: str) -> None:
        """Display an AI response."""
        display = str(text)

        if "answer=" in display and "AIResponse" in display:
            try:
                start = display.index("answer='") + len("answer='")
                end = display.index("'", start)
                display = display[start:end]
            except (ValueError, IndexError):
                pass

        html_text = display.replace("\n", "<br>")
        html_text = html_text.replace("  •", "&nbsp;&nbsp;•")

        self._response_area.append(
            f'<p style="color: {AI_ACCENT}; font-weight: 600; margin-top: 14px;">'
            f'◆ AI Assistant</p>'
            f'<div style="color: {TEXT}; margin-left: 14px; '
            f'padding: 8px; border-left: 3px solid {AI_ACCENT}; '
            f'margin-bottom: 8px;">{html_text}</div>'
        )

    def _append_error(self, text: str) -> None:
        self._response_area.append(
            f'<p style="color: {DANGER}; font-weight: 600; margin-top: 8px;">'
            f'✕ {text}</p>'
        )

    def _show_no_data(self) -> None:
        QMessageBox.warning(
            self, "No Data",
            "Load evidence first (Ctrl+L) before using the AI assistant.",
        )

    @staticmethod
    def _make_action_btn(text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG_CARD};
                color: {TEXT};
                border: 1px solid {BORDER};
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: 500;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {BG_ELEVATED};
                border-color: {AI_ACCENT};
                color: {TEXT};
            }}
            QPushButton:disabled {{
                color: {TEXT_DIM};
                background-color: {BG_SECONDARY};
                border-color: {BORDER};
            }}
        """)
        return btn
