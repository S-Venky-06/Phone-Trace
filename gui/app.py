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

from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow
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

    window = MainWindow()
    window.show()

    logger.info("PhoneTrace ready.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
