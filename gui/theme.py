"""
PhoneTrace -- Professional Forensic Workstation Theme
=======================================================

Clean, information-dense dark theme inspired by professional
digital forensics software, modern IDEs, and cybersecurity SOC dashboards.

Design language:
    - Minimalistic and information-dense
    - Dark-first with muted, professional accents
    - 8–12 px rounded corners, soft shadows, subtle borders
    - Inter / Segoe UI typography
    - No neon glow, no gaming aesthetics
"""

# ===================================================================
# Color Palette
# ===================================================================

# Backgrounds (darkest → lightest)
BG_PRIMARY   = "#0F1117"   # Main application background
BG_SECONDARY = "#161B22"   # Secondary panels, table backgrounds
BG_SIDEBAR   = "#111827"   # Sidebar background
BG_CARD      = "#1C2128"   # Cards, panels, group boxes
BG_ELEVATED  = "#22272E"   # Hovered / elevated cards, dropdowns

# Borders & divisions
BORDER       = "#2D333B"   # Subtle structural borders
BORDER_FOCUS = "#3B82F6"   # Focus ring (same as ACCENT)

# Text
TEXT         = "#E6EDF3"   # Primary text (high contrast)
TEXT_DIM     = "#7D8590"   # Secondary text, labels, metadata

# Accents
ACCENT       = "#3B82F6"   # Primary blue — buttons, selected nav, links
AI_ACCENT    = "#8B5CF6"   # AI features — assistant, summaries, findings
SUCCESS      = "#22C55E"   # Verified evidence, completed ops, successful parsing
WARNING      = "#F59E0B"   # Missing metadata, incomplete evidence
DANGER       = "#EF4444"   # Hash mismatch, failed parsing, corrupted evidence
SELECTION    = "#1F3A5F"   # Table / list selection highlight

# Artifact Type Colors (consistent across timeline, graph, badges)
ARTIFACT_COLORS = {
    "call":      "#38BDF8",
    "sms":       "#14B8A6",
    "browser":   "#F97316",
    "gps":       "#10B981",
    "photo":     "#A855F7",
    "file":      "#EAB308",
    "app_usage": "#EC4899",
    "unknown":   "#64748B",
}

# Legacy aliases (backward compatibility for existing pages)
BG_DARKEST  = BG_PRIMARY
BG_DARKER   = BG_SECONDARY
BG_DARK     = BG_PRIMARY
BG_MID      = BG_CARD
BG_LIGHT    = BG_ELEVATED
ACCENT_ALT  = AI_ACCENT
BORDER_GLOW = ACCENT

# ===================================================================
# Font family
# ===================================================================
FONT_FAMILY = '"Inter", "Segoe UI", system-ui, sans-serif'

# ===================================================================
# Stylesheet
# ===================================================================

DARK_STYLESHEET = f"""
/* ---------------------------------------------------------------- */
/* Global Widget Defaults                                           */
/* ---------------------------------------------------------------- */
QWidget {{
    background-color: {BG_PRIMARY};
    color: {TEXT};
    font-family: {FONT_FAMILY};
    font-size: 13px;
}}

/* ---------------------------------------------------------------- */
/* Main Window                                                      */
/* ---------------------------------------------------------------- */
QMainWindow {{
    background-color: {BG_PRIMARY};
}}

QSplitter::handle {{
    background-color: {BORDER};
}}
QSplitter::handle:horizontal {{
    width: 1px;
}}
QSplitter::handle:vertical {{
    height: 1px;
}}

/* ---------------------------------------------------------------- */
/* Menu Bar                                                         */
/* ---------------------------------------------------------------- */
QMenuBar {{
    background-color: {BG_PRIMARY};
    color: {TEXT_DIM};
    border-bottom: 1px solid {BORDER};
    padding: 4px 8px;
    font-size: 13px;
}}
QMenuBar::item {{
    padding: 5px 10px;
    border-radius: 6px;
}}
QMenuBar::item:selected {{
    background-color: {BG_ELEVATED};
    color: {TEXT};
}}
QMenu {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
}}
QMenu::item {{
    padding: 7px 28px 7px 12px;
    border-radius: 6px;
    font-size: 13px;
}}
QMenu::item:selected {{
    background-color: {SELECTION};
    color: {TEXT};
}}
QMenu::separator {{
    height: 1px;
    background-color: {BORDER};
    margin: 4px 8px;
}}

/* ---------------------------------------------------------------- */
/* Toolbar                                                          */
/* ---------------------------------------------------------------- */
QToolBar {{
    background-color: {BG_PRIMARY};
    border-bottom: 1px solid {BORDER};
    spacing: 4px;
    padding: 4px 10px;
}}
QToolButton {{
    background: transparent;
    color: {TEXT_DIM};
    border: none;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 500;
    font-size: 12px;
}}
QToolButton:hover {{
    background-color: {BG_ELEVATED};
    color: {TEXT};
}}
QToolButton:pressed {{
    background-color: {SELECTION};
    color: {ACCENT};
}}
QToolButton:checked {{
    background-color: {SELECTION};
    color: {ACCENT};
}}

/* ---------------------------------------------------------------- */
/* Status Bar                                                       */
/* ---------------------------------------------------------------- */
QStatusBar {{
    background-color: {BG_PRIMARY};
    color: {TEXT_DIM};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 2px 8px;
}}

/* ---------------------------------------------------------------- */
/* Buttons                                                          */
/* ---------------------------------------------------------------- */
QPushButton {{
    background-color: {BG_CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 500;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: {BG_ELEVATED};
    border-color: {ACCENT};
    color: {TEXT};
}}
QPushButton:pressed {{
    background-color: {SELECTION};
}}
QPushButton:disabled {{
    color: {TEXT_DIM};
    background-color: {BG_SECONDARY};
    border-color: {BORDER};
    opacity: 0.6;
}}
QPushButton#primaryBtn {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primaryBtn:hover {{
    background-color: #2563EB;
    border-color: #2563EB;
}}
QPushButton#primaryBtn:pressed {{
    background-color: #1D4ED8;
}}
QPushButton#dangerBtn {{
    border-color: {DANGER};
    color: {DANGER};
    background-color: transparent;
}}
QPushButton#dangerBtn:hover {{
    background-color: {DANGER};
    color: white;
}}
QPushButton#aiBtn {{
    border-color: {AI_ACCENT};
    color: {AI_ACCENT};
    background-color: transparent;
    font-weight: 600;
}}
QPushButton#aiBtn:hover {{
    background-color: {AI_ACCENT};
    color: white;
}}

/* ---------------------------------------------------------------- */
/* Input Widgets                                                    */
/* ---------------------------------------------------------------- */
QLineEdit {{
    background-color: {BG_SECONDARY};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: {SELECTION};
}}
QLineEdit:focus {{
    border-color: {ACCENT};
}}
QLineEdit:disabled {{
    color: {TEXT_DIM};
    background-color: {BG_PRIMARY};
}}

QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {{
    background-color: {BG_SECONDARY};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
}}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
    border-color: {ACCENT};
}}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {ACCENT};
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    selection-background-color: {SELECTION};
    outline: none;
}}

/* ---------------------------------------------------------------- */
/* Scroll Bars                                                      */
/* ---------------------------------------------------------------- */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {TEXT_DIM};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {BORDER};
    border-radius: 4px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {TEXT_DIM};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: transparent;
}}

/* ---------------------------------------------------------------- */
/* Tables & Lists                                                   */
/* ---------------------------------------------------------------- */
QTableWidget, QTableView {{
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
QTableWidget::item, QTableView::item {{
    padding: 8px 12px;
    border: none;
}}
QTableWidget::item:hover, QTableView::item:hover {{
    background-color: {BG_ELEVATED};
}}
QHeaderView::section {{
    background-color: {BG_PRIMARY};
    color: {TEXT_DIM};
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: 10px 14px;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

QTreeWidget {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 10px;
    alternate-background-color: {BG_PRIMARY};
    selection-background-color: {SELECTION};
    padding: 4px;
    outline: none;
}}
QTreeWidget::item {{
    padding: 6px 8px;
    border-radius: 6px;
    margin: 1px 2px;
}}
QTreeWidget::item:hover {{
    background-color: {BG_ELEVATED};
}}
QTreeWidget::item:selected {{
    background-color: {SELECTION};
    color: {TEXT};
}}
QTreeWidget::branch {{
    background: transparent;
}}

/* ---------------------------------------------------------------- */
/* Text Editors                                                     */
/* ---------------------------------------------------------------- */
QTextEdit, QPlainTextEdit {{
    background-color: {BG_SECONDARY};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px;
    selection-background-color: {SELECTION};
    font-size: 13px;
}}

QTextBrowser {{
    background-color: {BG_SECONDARY};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 12px;
}}

/* ---------------------------------------------------------------- */
/* Group Boxes                                                      */
/* ---------------------------------------------------------------- */
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 18px;
    padding: 20px 14px 14px 14px;
    font-weight: 600;
    font-size: 13px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px;
    color: {TEXT};
}}

/* ---------------------------------------------------------------- */
/* Scroll Area                                                      */
/* ---------------------------------------------------------------- */
QScrollArea {{
    border: none;
    background: transparent;
}}

/* ---------------------------------------------------------------- */
/* Tab Widget                                                       */
/* ---------------------------------------------------------------- */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background-color: {BG_SECONDARY};
}}
QTabBar::tab {{
    background-color: {BG_CARD};
    color: {TEXT_DIM};
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 18px;
    margin-right: 2px;
    font-weight: 500;
}}
QTabBar::tab:selected {{
    background-color: {BG_SECONDARY};
    color: {TEXT};
    border-color: {BORDER};
}}
QTabBar::tab:hover {{
    background-color: {BG_ELEVATED};
    color: {TEXT};
}}

/* ---------------------------------------------------------------- */
/* Typography Helpers                                               */
/* ---------------------------------------------------------------- */
QLabel#heading {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT};
    letter-spacing: -0.3px;
    background: transparent;
}}
QLabel#subheading {{
    font-size: 13px;
    color: {TEXT_DIM};
    font-weight: 400;
    background: transparent;
}}

/* ---------------------------------------------------------------- */
/* Progress Bar                                                     */
/* ---------------------------------------------------------------- */
QProgressBar {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 5px;
    text-align: center;
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_DIM};
    min-height: 10px;
    max-height: 10px;
}}
QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 4px;
}}

/* ---------------------------------------------------------------- */
/* Tool Tips                                                        */
/* ---------------------------------------------------------------- */
QToolTip {{
    background-color: {BG_ELEVATED};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ---------------------------------------------------------------- */
/* Message Box                                                      */
/* ---------------------------------------------------------------- */
QMessageBox {{
    background-color: {BG_CARD};
}}
QMessageBox QLabel {{
    color: {TEXT};
    background: transparent;
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}
"""

