"""
PhoneTrace -- Main Window
============================

The central application window assembling the menu bar, toolbar,
navigation sidebar, page stack, details panel, and status bar.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QKeySequence, QMouseEvent
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QMainWindow, QMessageBox, QSplitter,
    QStackedWidget, QStatusBar, QToolBar, QWidget, QLabel, QPushButton, QVBoxLayout
)

from gui.services.backend import BackendService
from gui.services.case_manager import CaseInfo, CaseManager
from gui.services.bookmark_manager import BookmarkManager
from gui.services.settings_manager import SettingsManager
from gui.widgets.case_selection_dialog import CaseSelectionDialog
from gui.widgets.details_panel import DetailsPanel
from gui.widgets.sidebar import Sidebar

from gui.pages.dashboard import DashboardPage
from gui.pages.cases import CasesPage
from gui.pages.evidence import EvidencePage
from gui.pages.timeline_page import TimelinePage
from gui.pages.correlation import CorrelationPage
from gui.pages.map_view import MapView
from gui.pages.statistics_page import StatisticsPage
from gui.pages.bookmarks_page import BookmarksPage
from gui.pages.graph_view import GraphView
from gui.pages.ai_assistant_page import AIAssistantPage
from gui.pages.reports import ReportsPage
from gui.pages.settings import SettingsPage

logger = logging.getLogger("gui.MainWindow")

class LoaderThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, backend, evidence_dir, parent=None):
        super().__init__(parent)
        self._backend = backend
        self._evidence_dir = evidence_dir

    def run(self):
        try:
            self._backend.load(evidence_dir=self._evidence_dir if self._evidence_dir else None)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent
        self.setFixedHeight(35)
        self.setStyleSheet("background-color: #0F1117; border-bottom: 1px solid #2D333B;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0)
        
        # We will embed the menu bar into the title bar in the main window
        self.menu_layout = QHBoxLayout()
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.menu_layout)
        
        layout.addStretch()
        
        btn_min = QPushButton("🗕")
        btn_min.setFixedSize(30, 30)
        btn_min.clicked.connect(self.parent_window.showMinimized)
        
        btn_max = QPushButton("🗖")
        btn_max.setFixedSize(30, 30)
        btn_max.clicked.connect(self._toggle_max)
        
        btn_close = QPushButton("🗙")
        btn_close.setFixedSize(30, 30)
        btn_close.clicked.connect(self.parent_window.close)
        
        for btn in (btn_min, btn_max, btn_close):
            btn.setStyleSheet("QPushButton { background: transparent; border: none; color: #7D8590; font-size: 14px; }"
                              "QPushButton:hover { background: #22272E; color: #E6EDF3; }")
            layout.addWidget(btn)
            
        btn_close.setStyleSheet("QPushButton { background: transparent; border: none; color: #7D8590; font-size: 14px; }"
                                "QPushButton:hover { background: #E81123; color: white; }")
        
        self.dragPos = QPoint()

    def _toggle_max(self):
        if self.parent_window.isMaximized():
            self.parent_window.showNormal()
        else:
            self.parent_window.showMaximized()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.parent_window.move(self.parent_window.pos() + event.globalPosition().toPoint() - self.dragPos)
            self.dragPos = event.globalPosition().toPoint()


class MainWindow(QMainWindow):
    """PhoneTrace main application window."""

    def __init__(self, active_case: Optional[CaseInfo] = None) -> None:
        super().__init__()

        project_root = Path(__file__).resolve().parent.parent
        self._settings = SettingsManager(project_root)
        self._case_mgr = CaseManager(project_root)
        self._bookmark_mgr = BookmarkManager(project_root)
        self._backend = BackendService()

        # Frameless Window Hint
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)

        self.setWindowTitle("PhoneTrace — Digital Forensic Workstation")
        w = self._settings.get("window_width", 1400)
        h = self._settings.get("window_height", 850)
        self.resize(w, h)

        self._build_menu_bar()
        self._build_toolbar()
        self._build_central_widget()
        self._build_status_bar()
        self._connect_signals()

        # If an active case was passed, initialize and load evidence
        if active_case:
            self._on_case_opened(active_case)
        elif self._case_mgr.active_case:
            self._on_case_opened(self._case_mgr.active_case)
        else:
            self._navigate("dashboard")

        logger.info("MainWindow initialized.")

    # ------------------------------------------------------------------
    # Menu Bar
    # ------------------------------------------------------------------

    def _build_menu_bar(self) -> None:
        self._title_bar = CustomTitleBar(self)
        self.setMenuWidget(self._title_bar)

        menu = self.menuBar()
        self._title_bar.menu_layout.addWidget(menu)

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

        # Cases Page action opens Case Selection Dialog
        self._act_cases = QAction("📁  Cases", self)
        self._act_cases.triggered.connect(self._open_case_selector)
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
        self._map_page = MapView()
        self._evidence_page = EvidencePage()
        self._statistics_page = StatisticsPage()
        self._bookmarks_page = BookmarksPage(self._bookmark_mgr)
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
            ("map", self._map_page),
            ("evidence", self._evidence_page),
            ("statistics", self._statistics_page),
            ("bookmarks", self._bookmarks_page),
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
        self._sidebar.page_changed.connect(self._on_sidebar_navigate)
        self._cases_page.case_opened.connect(self._on_case_opened)
        self._details.bookmark_requested.connect(self._on_bookmark_requested)

        # Pages that emit event_selected
        for page in (
            self._timeline_page, self._correlation_page,
            self._evidence_page, self._graph_page,
            self._ai_assistant_page, self._bookmarks_page,
        ):
            if hasattr(page, "event_selected"):
                page.event_selected.connect(self._details.show_event)

    def _on_bookmark_requested(self, event) -> None:
        if not event:
            return
        eid = getattr(event, "event_id", str(id(event)))
        ts_str = event.timestamp.strftime("%Y-%m-%d %H:%M:%S") if hasattr(event, "timestamp") and event.timestamp else ""
        self._bookmark_mgr.add_bookmark(
            event_id=eid,
            title=getattr(event, "title", "Event"),
            artifact_type=getattr(event, "artifact_type", "event"),
            timestamp_str=ts_str,
            tag="Suspicious",
        )
        self._bookmarks_page.refresh()
        self.statusBar().showMessage(f"★ Bookmarked event: {getattr(event, 'title', 'Event')}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_sidebar_navigate(self, key: str) -> None:
        """Handle sidebar item click."""
        if key == "cases":
            self._open_case_selector()
        else:
            self._navigate(key)

    def _open_case_selector(self) -> None:
        """Pop up the standalone Case Selection Dialog."""
        dlg = CaseSelectionDialog(self._case_mgr, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_case:
            self._on_case_opened(dlg.selected_case)

    def _navigate(self, key: str) -> None:
        """Switch the visible page."""
        idx = self._pages.get(key)
        if idx is not None:
            self._stack.setCurrentIndex(idx)
            self._sidebar.set_active(key)
            logger.info("Navigated to: %s", key)

    def _on_case_opened(self, case_info) -> None:
        """Handle opening a case from CasesPage."""
        if not case_info:
            return
        
        self._dashboard_page.set_case_info(case_info)
        evidence_dir = getattr(case_info, "evidence_dir", "")
        self._load_evidence(evidence_dir=evidence_dir)
        self._navigate("dashboard")

    def _load_evidence(self, evidence_dir: str = "") -> None:
        """Parse evidence, build timeline, and refresh all pages asynchronously."""
        self.statusBar().showMessage("Loading evidence... This may take a moment.")
        self._act_load.setEnabled(False)

        # Update case info on dashboard if active case exists
        active_case = self._case_mgr.active_case
        if active_case:
            self._dashboard_page.set_case_info(active_case)

        self._loader_thread = LoaderThread(self._backend, evidence_dir, self)
        self._loader_thread.finished.connect(self._on_load_finished)
        self._loader_thread.error.connect(self._on_load_error)
        self._loader_thread.start()

    def _on_load_error(self, err_msg: str) -> None:
        QMessageBox.critical(
            self, "Load Error",
            f"Failed to load evidence:\n{err_msg}",
        )
        self.statusBar().showMessage("Error loading evidence.")
        self._act_load.setEnabled(True)

    def _on_load_finished(self) -> None:
        # Refresh all pages
        self._dashboard_page.update_from_backend(self._backend)
        self._timeline_page.load_from_backend(self._backend)
        self._correlation_page.load_from_backend(self._backend)
        self._map_page.load_from_backend(self._backend)
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
