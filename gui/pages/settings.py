"""
PhoneTrace -- Settings Page
==============================

Editable settings form with save/reset.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea,
    QSpinBox, QVBoxLayout, QWidget,
)

from gui.services.settings_manager import SettingsManager
from gui.theme import DANGER, SUCCESS, TEXT_DIM, AI_ACCENT, BORDER, BG_CARD


class SettingsPage(QWidget):
    """Form-based settings editor."""

    def __init__(self, settings: SettingsManager, backend=None, parent=None):
        super().__init__(parent)
        self._sm = settings
        self._backend = backend

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(20)

        header = QLabel("Settings")
        header.setObjectName("heading")
        main_layout.addWidget(header)

        # -- General --
        general = QGroupBox("General Configuration")
        gen_form = QFormLayout(general)
        gen_form.setSpacing(10)

        self._timezone = QLineEdit()
        gen_form.addRow("Timezone:", self._timezone)

        self._theme = QComboBox()
        self._theme.addItems(["dark", "light"])
        gen_form.addRow("Theme:", self._theme)

        self._export_folder = QLineEdit()
        self._export_folder.setPlaceholderText("Default: project root")
        gen_form.addRow("Export Folder:", self._export_folder)

        self._log_level = QComboBox()
        self._log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        gen_form.addRow("Logging Level:", self._log_level)

        main_layout.addWidget(general)

        # -- Correlation --
        corr = QGroupBox("Threshold Configurations")
        corr_form = QFormLayout(corr)
        corr_form.setSpacing(10)

        self._session_gap = QSpinBox()
        self._session_gap.setRange(1, 120)
        self._session_gap.setSuffix(" min")
        corr_form.addRow("Session Gap:", self._session_gap)

        self._corr_window = QSpinBox()
        self._corr_window.setRange(1, 120)
        self._corr_window.setSuffix(" min")
        corr_form.addRow("Correlation Window:", self._corr_window)

        self._gps_thresh = QDoubleSpinBox()
        self._gps_thresh.setRange(0.1, 50.0)
        self._gps_thresh.setDecimals(2)
        self._gps_thresh.setSuffix(" km")
        corr_form.addRow("GPS Movement Threshold:", self._gps_thresh)

        self._loc_prox = QDoubleSpinBox()
        self._loc_prox.setRange(10, 5000)
        self._loc_prox.setDecimals(0)
        self._loc_prox.setSuffix(" m")
        corr_form.addRow("Location Proximity:", self._loc_prox)

        self._comm_cluster = QSpinBox()
        self._comm_cluster.setRange(1, 60)
        self._comm_cluster.setSuffix(" min")
        corr_form.addRow("Comm. Cluster Window:", self._comm_cluster)

        main_layout.addWidget(corr)

        # -- AI Configuration --
        ai_group = QGroupBox("AI Assistant Configuration")
        ai_form = QFormLayout(ai_group)
        ai_form.setSpacing(10)

        self._ai_provider = QComboBox()
        self._ai_provider.addItems([
            "rule_based", "gemini", "openai", "ollama",
        ])
        ai_form.addRow("AI Provider:", self._ai_provider)

        self._ai_api_key = QLineEdit()
        self._ai_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._ai_api_key.setPlaceholderText("Required for Gemini / OpenAI")
        ai_form.addRow("API Key:", self._ai_api_key)

        self._ai_ollama_url = QLineEdit()
        self._ai_ollama_url.setPlaceholderText("http://localhost:11434")
        ai_form.addRow("Ollama URL:", self._ai_ollama_url)

        self._ai_model = QLineEdit()
        self._ai_model.setPlaceholderText(
            "e.g. gemini-2.0-flash, gpt-4o-mini, llama3.1"
        )
        ai_form.addRow("Model Name:", self._ai_model)

        btn_test = QPushButton("Test Connection")
        btn_test.setObjectName("aiBtn")
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.clicked.connect(self._test_ai_connection)
        ai_form.addRow("", btn_test)

        self._ai_status = QLabel("")
        self._ai_status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500;")
        ai_form.addRow("", self._ai_status)

        main_layout.addWidget(ai_group)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("primaryBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_save)

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setObjectName("dangerBtn")
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self._reset)
        btn_row.addWidget(btn_reset)

        btn_row.addStretch()
        main_layout.addLayout(btn_row)

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {TEXT_DIM}; font-size: 13px; font-weight: 500;")
        main_layout.addWidget(self._status)

        main_layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        self._load_values()

    def _load_values(self) -> None:
        """Load current settings into the form."""
        self._timezone.setText(str(self._sm.get("timezone", "")))
        idx = self._theme.findText(str(self._sm.get("theme", "dark")))
        if idx >= 0:
            self._theme.setCurrentIndex(idx)
        self._export_folder.setText(str(self._sm.get("export_folder", "")))
        idx = self._log_level.findText(str(self._sm.get("logging_level", "INFO")))
        if idx >= 0:
            self._log_level.setCurrentIndex(idx)
        self._session_gap.setValue(int(self._sm.get("session_gap_minutes", 15)))
        self._corr_window.setValue(int(self._sm.get("correlation_time_window", 15)))
        self._gps_thresh.setValue(float(self._sm.get("gps_movement_threshold_km", 0.5)))
        self._loc_prox.setValue(float(self._sm.get("location_proximity_m", 200)))
        self._comm_cluster.setValue(int(self._sm.get("communication_cluster_minutes", 10)))

        # Load AI settings
        ai_provider = str(self._sm.get("ai_provider", "rule_based"))
        idx = self._ai_provider.findText(ai_provider)
        if idx >= 0:
            self._ai_provider.setCurrentIndex(idx)
        self._ai_api_key.setText(str(self._sm.get("ai_api_key", "")))
        self._ai_ollama_url.setText(str(self._sm.get("ai_ollama_url", "")))
        self._ai_model.setText(str(self._sm.get("ai_model", "")))

    def _save(self) -> None:
        """Persist current form values."""
        self._sm.set("timezone", self._timezone.text())
        self._sm.set("theme", self._theme.currentText())
        self._sm.set("export_folder", self._export_folder.text())
        self._sm.set("logging_level", self._log_level.currentText())
        self._sm.set("session_gap_minutes", self._session_gap.value())
        self._sm.set("correlation_time_window", self._corr_window.value())
        self._sm.set("gps_movement_threshold_km", self._gps_thresh.value())
        self._sm.set("location_proximity_m", self._loc_prox.value())
        self._sm.set("communication_cluster_minutes", self._comm_cluster.value())

        # Save AI settings
        self._sm.set("ai_provider", self._ai_provider.currentText())
        self._sm.set("ai_api_key", self._ai_api_key.text())
        self._sm.set("ai_ollama_url", self._ai_ollama_url.text())
        self._sm.set("ai_model", self._ai_model.text())

        self._sm.save()

        # Update active AI provider in backend if loaded
        if self._backend and self._backend.ai_assistant:
            try:
                self._backend.set_ai_provider(
                    self._ai_provider.currentText(),
                    self._ai_api_key.text(),
                    model_name=self._ai_model.text(),
                    base_url=self._ai_ollama_url.text(),
                )
            except Exception as exc:
                QMessageBox.warning(self, "AI Config Error", f"Failed to apply AI config: {exc}")

        self._status.setText("✓ Settings saved successfully.")
        self._status.setStyleSheet(f"color: {SUCCESS};")

    def _reset(self) -> None:
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Reset all settings to defaults?",
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._sm.reset()
            self._load_values()
            self._status.setText("Settings reset to defaults.")
            self._status.setStyleSheet(f"color: {TEXT_DIM};")

    def _test_ai_connection(self) -> None:
        provider_name = self._ai_provider.currentText()
        api_key = self._ai_api_key.text()
        model_name = self._ai_model.text()
        base_url = self._ai_ollama_url.text()

        self._ai_status.setText("Testing connection...")
        self._ai_status.setStyleSheet(f"color: {TEXT_DIM};")

        try:
            from ai_engine.assistant import _PROVIDER_REGISTRY
            cls = _PROVIDER_REGISTRY.get(provider_name)
            if cls is None:
                raise ValueError(f"Unknown provider: {provider_name}")

            # Instantiate
            if cls.requires_api_key:
                if not api_key:
                    raise ValueError(f"API Key is required for {provider_name}")
                prov = cls(api_key=api_key, model_name=model_name)
            elif provider_name == "ollama":
                prov = cls(base_url=base_url or "http://localhost:11434", model_name=model_name or "llama3.1")
            else:
                prov = cls()

            if prov.is_available():
                self._ai_status.setText("✓ Connection successful! Provider is available.")
                self._ai_status.setStyleSheet(f"color: {SUCCESS};")
            else:
                self._ai_status.setText("✗ Connection failed. Provider is unavailable.")
                self._ai_status.setStyleSheet(f"color: {DANGER};")
        except Exception as exc:
            self._ai_status.setText(f"✗ Connection failed: {exc}")
            self._ai_status.setStyleSheet(f"color: {DANGER};")
