"""
PhoneTrace -- Main Window
============================

The central application window assembling the menu bar, toolbar,
navigation sidebar, page stack, details panel, and status bar.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QHBoxLayout, QMainWindow, QMessageBox, QSplitter, QStackedWidget,
    QStatusBar, QToolBar, QVBoxLayout, QWidget, QLineEdit,
)

from gui.services.backend import BackendService
from gui.services.case_manager import CaseManager
from gui.services.settings_manager import SettingsManager
from gui.widgets.details_panel import DetailsPanel
from gui.widgets.sidebar import Sidebar

from gui.pages.dashboard import DashboardPage
from gui.pages.cases import CasesPage
from gui.pages.evidence import EvidencePage
from gui.pages.timeline_page import TimelinePage
from gui.pages.correlation import CorrelationPage
from gui.pages.statistics_page import StatisticsPage
from gui.pages.graph_view import GraphView
from gui.pages.ai_assistant_page import AIAssistantPage
from gui.pages.reports import ReportsPage
from gui.pages.settings import SettingsPage

logger = logging.getLogger("gui.MainWindow")


class MainWindow(QMainWindow):
    """PhoneTrace main application window."""

    def __init__(self) -> None:
        super().__init__()

        project_root = Path(__file__).resolve().parent.parent
        self._settings = SettingsManager(project_root)
        self._case_mgr = CaseManager(project_root)
        self._backend = BackendService()

        self.setWindowTitle("PhoneTrace — Digital Forensic Workstation")
        w = self._settings.get("window_width", 1400)
        h = self._settings.get("window_height", 850)
        self.resize(w, h)

        self._build_menu_bar()
        self._build_toolbar()
        self._build_central_widget()
        self._build_status_bar()
        self._connect_signals()

        logger.info("MainWindow initialized.")

    # ------------------------------------------------------------------
    # Menu Bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        menu = self.menuBar()

        # File menu
        file_menu = menu.addMenu("&File")

        act_load = QAction("Load Evidence", self)
        act_load.setShortcut(QKeySequence("Ctrl+L"))
        act_load.setToolTip("Parse evidence and build timeline")
        act_load.triggered.connect(self._load_evidence)
        file_menu.addAction(act_load)

        file_menu.addSeparator()

        act_export_json = QAction("Export JSON", self)
        act_export_json.setShortcut(QKeySequence("Ctrl+E"))
        act_export_json.triggered.connect(
            lambda: self._navigate("reports")
        )
        file_menu.addAction(act_export_json)

        act_export_csv = QAction("Export CSV", self)
        file_menu.addAction(act_export_csv)

        file_menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # View menu
        view_menu = menu.addMenu("&View")

        act_dash = QAction("Dashboard", self)
        act_dash.triggered.connect(lambda: self._navigate("dashboard"))
        view_menu.addAction(act_dash)

        act_timeline = QAction("Timeline", self)
        act_timeline.setShortcut(QKeySequence("Ctrl+T"))
        act_timeline.triggered.connect(lambda: self._navigate("timeline"))
        view_menu.addAction(act_timeline)

        act_corr = QAction("Correlations", self)
        act_corr.triggered.connect(lambda: self._navigate("correlations"))
        view_menu.addAction(act_corr)

        act_stats = QAction("Statistics", self)
        act_stats.triggered.connect(lambda: self._navigate("statistics"))
        view_menu.addAction(act_stats)

        act_graph = QAction("Graph View", self)
        act_graph.triggered.connect(lambda: self._navigate("graph"))
        view_menu.addAction(act_graph)

        # Help menu
        help_menu = menu.addMenu("&Help")
        act_about = QAction("About PhoneTrace", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Cases Page
        self._act_cases = QAction("📁  Cases", self)
        self._act_cases.triggered.connect(lambda: self._navigate("cases"))
        toolbar.addAction(self._act_cases)

        # Load Evidence
        self._act_load = QAction("▶  Load Evidence", self)
        self._act_load.setToolTip("Parse evidence and build timeline (Ctrl+L)")
        self._act_load.triggered.connect(self._load_evidence)
        toolbar.addAction(self._act_load)

        toolbar.addSeparator()

        act_dash = QAction("⊞  Dashboard", self)
        act_dash.triggered.connect(lambda: self._navigate("dashboard"))
        toolbar.addAction(act_dash)

        act_tl = QAction("⏱  Timeline", self)
        act_tl.triggered.connect(lambda: self._navigate("timeline"))
        toolbar.addAction(act_tl)

        act_corr = QAction("⚡  Correlations", self)
        act_corr.triggered.connect(lambda: self._navigate("correlations"))
        toolbar.addAction(act_corr)

        act_graph = QAction("◉  Graph", self)
        act_graph.triggered.connect(lambda: self._navigate("graph"))
        toolbar.addAction(act_graph)

        act_ai = QAction("🤖  AI Assistant", self)
        act_ai.triggered.connect(lambda: self._navigate("ai_assistant"))
        toolbar.addAction(act_ai)

        toolbar.addSeparator()

        # Spacer to push settings to the right
        spacer = QWidget()
        spacer.setSizePolicy(
            spacer.sizePolicy().Policy.Expanding,
            spacer.sizePolicy().Policy.Preferred,
        )
        toolbar.addWidget(spacer)

        # Settings on the right side
        self._act_settings = QAction("⚙  Settings", self)
        self._act_settings.triggered.connect(lambda: self._navigate("settings"))
        toolbar.addAction(self._act_settings)

    # ------------------------------------------------------------------
    # Central area: sidebar + pages + details
    # ------------------------------------------------------------------

    def _build_central_widget(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        h_layout.addWidget(self._sidebar)

        # Splitter for workspace + details
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Stacked pages
        self._stack = QStackedWidget()

        self._dashboard_page = DashboardPage()
        self._cases_page = CasesPage(self._case_mgr)
        self._timeline_page = TimelinePage()
        self._correlation_page = CorrelationPage()
        self._evidence_page = EvidencePage()
        self._statistics_page = StatisticsPage()
        self._graph_page = GraphView()
        self._ai_assistant_page = AIAssistantPage()
        self._reports_page = ReportsPage()
        self._settings_page = SettingsPage(self._settings, self._backend)

        self._pages: dict[str, int] = {}
        for key, page in [
            ("dashboard", self._dashboard_page),
            ("cases", self._cases_page),
            ("timeline", self._timeline_page),
            ("correlations", self._correlation_page),
            ("evidence", self._evidence_page),
            ("statistics", self._statistics_page),
            ("graph", self._graph_page),
            ("ai_assistant", self._ai_assistant_page),
            ("reports", self._reports_page),
            ("settings", self._settings_page),
        ]:
            idx = self._stack.addWidget(page)
            self._pages[key] = idx

        self._splitter.addWidget(self._stack)

        # Details panel
        self._details = DetailsPanel()
        self._splitter.addWidget(self._details)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 1)

        h_layout.addWidget(self._splitter)

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_status_bar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("Ready — Load evidence to begin investigation.")

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._sidebar.page_changed.connect(self._navigate)

        # Pages that emit event_selected
        for page in (
            self._timeline_page, self._correlation_page,
            self._evidence_page, self._graph_page,
            self._ai_assistant_page,
        ):
            if hasattr(page, "event_selected"):
                page.event_selected.connect(self._details.show_event)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _navigate(self, key: str) -> None:
        """Switch the visible page."""
        idx = self._pages.get(key)
        if idx is not None:
            self._stack.setCurrentIndex(idx)
            self._sidebar.set_active(key)
            logger.info("Navigated to: %s", key)

    def _load_evidence(self) -> None:
        """Parse evidence, build timeline, and refresh all pages."""
        self.statusBar().showMessage("Loading evidence...")
        self._act_load.setEnabled(False)

        try:
            self._backend.load()
        except Exception as exc:
            QMessageBox.critical(
                self, "Load Error",
                f"Failed to load evidence:\n{exc}",
            )
            self.statusBar().showMessage("Error loading evidence.")
            self._act_load.setEnabled(True)
            return

        # Refresh all pages
        self._dashboard_page.update_from_backend(self._backend)
        self._timeline_page.load_from_backend(self._backend)
        self._correlation_page.load_from_backend(self._backend)
        self._evidence_page.load_from_backend(self._backend)
        self._statistics_page.update_from_backend(self._backend)
        self._graph_page.load_from_backend(self._backend)
        self._reports_page.set_backend(self._backend)

        # AI Assistant
        provider = self._settings.get("ai_provider", "rule_based")
        api_key = self._settings.get("ai_api_key", "")
        model = self._settings.get("ai_model", "")
        url = self._settings.get("ai_ollama_url", "")

        try:
            self._backend.set_ai_provider(
                provider, api_key, model_name=model, base_url=url
            )
        except Exception as exc:
            logger.warning("Failed to configure AI provider on load: %s", exc)

        self._ai_assistant_page.set_assistant(self._backend.ai_assistant)
        self._reports_page.set_assistant(self._backend.ai_assistant)

        n = len(self._backend.events)
        self.statusBar().showMessage(
            f"Evidence loaded — {n:,} timeline events, "
            f"{len(self._backend.sessions)} sessions, "
            f"{len(self._backend.correlations)} correlations."
        )
        self._act_load.setEnabled(True)
        logger.info("Evidence loaded: %d events.", n)

    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "About PhoneTrace",
            "<h3>PhoneTrace v3.0</h3>"
            "<p>AI-Assisted Digital Forensic Workstation</p>"
            "<p>Phase 6 Redesign Complete</p>"
            "<p>&copy; 2026 PhoneTrace Project</p>",
        )

    def closeEvent(self, event) -> None:
        """Save window configuration on close."""
        self._settings.set("window_width", self.width())
        self._settings.set("window_height", self.height())
        self._settings.save()
        super().closeEvent(event)
