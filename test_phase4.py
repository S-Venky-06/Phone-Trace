"""
PhoneTrace -- Phase 4 GUI Test Suite
=======================================

Tests for the GUI services, widgets, pages, and main window.
GUI tests that require QApplication use a module-level app instance.

Run with:
    python -m unittest test_phase4 -v
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ===================================================================
# Create QApplication once for all tests
# ===================================================================
from PyQt6.QtWidgets import QApplication

_app = QApplication.instance()
if _app is None:
    _app = QApplication([])


# ===================================================================
# SettingsManager Tests
# ===================================================================

class TestSettingsManager(unittest.TestCase):
    """Test settings persistence."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(
            dir=str(_PROJECT_ROOT), prefix="test_settings_"
        )

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_defaults(self):
        from gui.services.settings_manager import SettingsManager
        sm = SettingsManager(self._tmpdir)
        self.assertEqual(sm.get("timezone"), "Asia/Kolkata")
        self.assertEqual(sm.get("theme"), "dark")
        self.assertEqual(sm.get("session_gap_minutes"), 15)

    def test_set_and_save(self):
        from gui.services.settings_manager import SettingsManager
        sm = SettingsManager(self._tmpdir)
        sm.set("timezone", "UTC")
        sm.save()

        sm2 = SettingsManager(self._tmpdir)
        self.assertEqual(sm2.get("timezone"), "UTC")

    def test_reset(self):
        from gui.services.settings_manager import SettingsManager
        sm = SettingsManager(self._tmpdir)
        sm.set("timezone", "UTC")
        sm.save()
        sm.reset()
        self.assertEqual(sm.get("timezone"), "Asia/Kolkata")

    def test_all_settings(self):
        from gui.services.settings_manager import SettingsManager
        sm = SettingsManager(self._tmpdir)
        s = sm.all_settings
        self.assertIn("timezone", s)
        self.assertIn("theme", s)


# ===================================================================
# CaseManager Tests
# ===================================================================

class TestCaseManager(unittest.TestCase):
    """Test case management."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(
            dir=str(_PROJECT_ROOT), prefix="test_cases_"
        )

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_create_case(self):
        from gui.services.case_manager import CaseManager
        cm = CaseManager(self._tmpdir)
        case = cm.create_case("Test Case", "Inspector")
        self.assertEqual(case.name, "Test Case")
        self.assertIn("CASE-", case.case_id)
        self.assertEqual(len(cm.cases), 1)

    def test_open_case(self):
        from gui.services.case_manager import CaseManager
        cm = CaseManager(self._tmpdir)
        case = cm.create_case("Test", "Inspector")
        cm.open_case(case.case_id)
        self.assertEqual(cm.active_case.case_id, case.case_id)

    def test_close_case(self):
        from gui.services.case_manager import CaseManager
        cm = CaseManager(self._tmpdir)
        case = cm.create_case("Test", "Inspector")
        cm.close_case(case.case_id)
        self.assertIsNone(cm.active_case)
        self.assertEqual(cm.cases[0].status, "Closed")

    def test_delete_case(self):
        from gui.services.case_manager import CaseManager
        cm = CaseManager(self._tmpdir)
        case = cm.create_case("Test", "Inspector")
        cm.delete_case(case.case_id)
        self.assertEqual(len(cm.cases), 0)

    def test_search(self):
        from gui.services.case_manager import CaseManager
        cm = CaseManager(self._tmpdir)
        cm.create_case("Alpha Case", "Smith")
        cm.create_case("Beta Case", "Jones")
        results = cm.search("alpha")
        self.assertEqual(len(results), 1)

    def test_persistence(self):
        from gui.services.case_manager import CaseManager
        cm = CaseManager(self._tmpdir)
        cm.create_case("Persistent", "Test")
        cm2 = CaseManager(self._tmpdir)
        self.assertEqual(len(cm2.cases), 1)


# ===================================================================
# BackendService Tests
# ===================================================================

class TestBackendService(unittest.TestCase):
    """Test the backend facade."""

    @classmethod
    def setUpClass(cls):
        from gui.services.backend import BackendService
        cls.svc = BackendService()
        cls.svc.load()

    def test_loaded(self):
        self.assertTrue(self.svc.is_loaded)

    def test_events(self):
        self.assertGreater(len(self.svc.events), 3000)

    def test_sessions(self):
        self.assertGreater(len(self.svc.sessions), 0)

    def test_correlations(self):
        self.assertGreater(len(self.svc.correlations), 0)

    def test_statistics(self):
        self.assertIsNotNone(self.svc.statistics)
        self.assertGreater(self.svc.statistics.total_events, 0)

    def test_search(self):
        results = self.svc.search("Priya")
        self.assertGreater(len(results), 0)

    def test_filter_by_artifact(self):
        calls = self.svc.filter_by_artifact("call")
        self.assertGreater(len(calls), 0)
        self.assertTrue(all(e.artifact_type == "call" for e in calls))

    def test_export_json(self):
        tmpdir = tempfile.mkdtemp(dir=str(_PROJECT_ROOT), prefix="test_exp_")
        try:
            path = self.svc.export_json(os.path.join(tmpdir, "test.json"))
            self.assertTrue(path.is_file())
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.assertGreater(len(data), 100)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_export_csv(self):
        tmpdir = tempfile.mkdtemp(dir=str(_PROJECT_ROOT), prefix="test_exp_")
        try:
            path = self.svc.export_csv(os.path.join(tmpdir, "test.csv"))
            self.assertTrue(path.is_file())
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ===================================================================
# Widget Tests
# ===================================================================

class TestStatCard(unittest.TestCase):
    """Test StatCard widget."""

    def test_creation(self):
        from gui.widgets.stat_card import StatCard
        card = StatCard("\u260E", "Calls", "42")
        self.assertIsNotNone(card)

    def test_set_value(self):
        from gui.widgets.stat_card import StatCard
        card = StatCard("\u260E", "Calls", "0")
        card.set_value("100")
        self.assertEqual(card._value_lbl.text(), "100")


class TestSearchBar(unittest.TestCase):
    """Test SearchBar widget."""

    def test_creation(self):
        from gui.widgets.search_bar import SearchBar
        bar = SearchBar("Search...")
        self.assertIsNotNone(bar)

    def test_text_property(self):
        from gui.widgets.search_bar import SearchBar
        bar = SearchBar()
        self.assertEqual(bar.text, "")


class TestSidebar(unittest.TestCase):
    """Test Sidebar widget."""

    def test_creation(self):
        from gui.widgets.sidebar import Sidebar
        sb = Sidebar()
        self.assertIsNotNone(sb)

    def test_set_active(self):
        from gui.widgets.sidebar import Sidebar
        sb = Sidebar()
        sb.set_active("timeline")
        # Should not raise


class TestDetailsPanel(unittest.TestCase):
    """Test DetailsPanel widget."""

    def test_creation(self):
        from gui.widgets.details_panel import DetailsPanel
        panel = DetailsPanel()
        self.assertIsNotNone(panel)

    def test_show_none_event(self):
        from gui.widgets.details_panel import DetailsPanel
        panel = DetailsPanel()
        panel.show_event(None)
        # Should not raise

    def test_show_real_event(self):
        from gui.widgets.details_panel import DetailsPanel
        from gui.services.backend import BackendService
        svc = BackendService()
        svc.load()
        panel = DetailsPanel()
        panel.show_event(svc.events[0])
        # Should not raise


# ===================================================================
# Page Tests
# ===================================================================

class TestDashboardPage(unittest.TestCase):
    """Test Dashboard page."""

    def test_creation(self):
        from gui.pages.dashboard import DashboardPage
        page = DashboardPage()
        self.assertIsNotNone(page)

    def test_update(self):
        from gui.pages.dashboard import DashboardPage
        from gui.services.backend import BackendService
        svc = BackendService()
        svc.load()
        page = DashboardPage()
        page.update_from_backend(svc)
        # Cards should show non-zero values


class TestTimelinePage(unittest.TestCase):
    """Test Timeline page."""

    def test_creation(self):
        from gui.pages.timeline_page import TimelinePage
        page = TimelinePage()
        self.assertIsNotNone(page)

    def test_load(self):
        from gui.pages.timeline_page import TimelinePage
        from gui.services.backend import BackendService
        svc = BackendService()
        svc.load()
        page = TimelinePage()
        page.load_from_backend(svc)


class TestCorrelationPage(unittest.TestCase):
    """Test Correlation page."""

    def test_creation(self):
        from gui.pages.correlation import CorrelationPage
        page = CorrelationPage()
        self.assertIsNotNone(page)

    def test_load(self):
        from gui.pages.correlation import CorrelationPage
        from gui.services.backend import BackendService
        svc = BackendService()
        svc.load()
        page = CorrelationPage()
        page.load_from_backend(svc)


class TestEvidencePage(unittest.TestCase):
    """Test Evidence page."""

    def test_creation(self):
        from gui.pages.evidence import EvidencePage
        page = EvidencePage()
        self.assertIsNotNone(page)

    def test_load(self):
        from gui.pages.evidence import EvidencePage
        from gui.services.backend import BackendService
        svc = BackendService()
        svc.load()
        page = EvidencePage()
        page.load_from_backend(svc)


class TestStatisticsPage(unittest.TestCase):
    """Test Statistics page."""

    def test_creation(self):
        from gui.pages.statistics_page import StatisticsPage
        page = StatisticsPage()
        self.assertIsNotNone(page)

    def test_update(self):
        from gui.pages.statistics_page import StatisticsPage
        from gui.services.backend import BackendService
        svc = BackendService()
        svc.load()
        page = StatisticsPage()
        page.update_from_backend(svc)


class TestGraphView(unittest.TestCase):
    """Test Graph View page."""

    def test_creation(self):
        from gui.pages.graph_view import GraphView
        page = GraphView()
        self.assertIsNotNone(page)

    def test_load(self):
        from gui.pages.graph_view import GraphView
        from gui.services.backend import BackendService
        svc = BackendService()
        svc.load()
        page = GraphView()
        page.load_from_backend(svc)
        # Verify nodes and scene items are created
        self.assertGreater(len(page._nodes), 0)
        self.assertGreater(len(page._scene.items()), 0)


class TestReportsPage(unittest.TestCase):
    """Test Reports page."""

    def test_creation(self):
        from gui.pages.reports import ReportsPage
        page = ReportsPage()
        self.assertIsNotNone(page)


class TestSettingsPage(unittest.TestCase):
    """Test Settings page."""

    def test_creation(self):
        from gui.services.settings_manager import SettingsManager
        from gui.pages.settings import SettingsPage
        tmpdir = tempfile.mkdtemp(dir=str(_PROJECT_ROOT), prefix="test_sp_")
        try:
            sm = SettingsManager(tmpdir)
            page = SettingsPage(sm)
            self.assertIsNotNone(page)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ===================================================================
# MainWindow Tests
# ===================================================================

class TestMainWindow(unittest.TestCase):
    """Test MainWindow creation and navigation."""

    def test_creation(self):
        from gui.main_window import MainWindow
        win = MainWindow()
        self.assertIsNotNone(win)

    def test_navigation(self):
        from gui.main_window import MainWindow
        win = MainWindow()
        for key in ["dashboard", "cases", "timeline", "correlations",
                     "evidence", "statistics", "graph", "reports", "settings"]:
            win._navigate(key)
        # All pages should be reachable without error


if __name__ == "__main__":
    unittest.main()
