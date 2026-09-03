"""
PhoneTrace -- Application Entry Point
========================================

Launch the PhoneTrace forensic investigation GUI.

Run with::

    python -m gui.app
"""

import logging
import sys
from pathlib import Path

# Ensure project root on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication, QDialog
from gui.main_window import MainWindow
from gui.services.case_manager import CaseManager
from gui.widgets.case_selection_dialog import CaseSelectionDialog
from gui.theme import DARK_STYLESHEET


def main() -> None:
    """Create and launch the PhoneTrace application."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logger = logging.getLogger("gui.app")
    logger.info("Starting PhoneTrace...")

    app = QApplication(sys.argv)
    app.setApplicationName("PhoneTrace")
    app.setOrganizationName("PhoneTrace")

    # Apply dark theme
    app.setStyleSheet(DARK_STYLESHEET)

    # Load custom fonts
    from PyQt6.QtGui import QFontDatabase, QFont
    font_dir = _PROJECT_ROOT / "assets" / "fonts"
    reg_id = QFontDatabase.addApplicationFont(str(font_dir / "Roboto-Regular.ttf"))
    med_id = QFontDatabase.addApplicationFont(str(font_dir / "Roboto-Medium.ttf"))
    
    if reg_id != -1:
        families = QFontDatabase.applicationFontFamilies(reg_id)
        if families:
            app.setFont(QFont(families[0], 10))
            logger.info(f"Loaded custom font: {families[0]}")

    # Initialize Splash Screen
    from gui.widgets.splash_screen import PhoneTraceSplashScreen
    splash = PhoneTraceSplashScreen()
    splash.show()
    splash.show_message("Loading modules and settings...")

    # Initialize CaseManager to prompt user for case selection first
    case_mgr = CaseManager(_PROJECT_ROOT)
    
    splash.show_message("Waiting for case selection...")
    dlg = CaseSelectionDialog(case_mgr)
    
    # Hide splash while dialog is active (since dialog is modal)
    splash.hide()
    
    if dlg.exec() != QDialog.DialogCode.Accepted or not dlg.selected_case:
        logger.info("No case selected. Exiting PhoneTrace.")
        sys.exit(0)

    selected_case = dlg.selected_case
    logger.info("Opened case: %s (%s)", selected_case.name, selected_case.case_id)
    
    splash.show()
    splash.show_message("Initializing workspace...")

    window = MainWindow(active_case=selected_case)
    window.show()
    
    splash.finish(window)

    logger.info("PhoneTrace ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
