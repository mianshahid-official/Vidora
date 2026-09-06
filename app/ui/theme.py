"""
Modern PySide6 Styling and Theme Engine (Dark & Light).
"""

DARK_THEME_QSS = """
/* Global Window and Font Settings */
QMainWindow, QDialog, #CentralWidget, QStackedWidget, QStackedWidget > QWidget {
    background-color: #101218;
    background: #101218;
}
QWidget {
    color: #e6e8ee;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #00d2ff;
    selection-color: #000000;
}

/* Ensure no white background in QScrollArea, viewports, or child containers */
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget,
QScrollArea #scrollAreaWidgetContents, QScrollArea .QWidget, QScrollArea QWidget {
    background-color: transparent;
    background: transparent;
    border: none;
}

/* Global Labels: Always transparent to prevent dark background rectangles */
QLabel {
    background-color: transparent;
    color: #e6e8ee;
}

/* ScrollBars */
QScrollBar:vertical {
    border: none;
    background: #161821;
    width: 8px;
    margin: 0;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2e3346;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #00d2ff;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #161821;
    height: 8px;
    margin: 0;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #2e3346;
    min-width: 25px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #00d2ff;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

/* Sidebar */
#Sidebar {
    background-color: #0c0e14;
    border-right: 1px solid #1e2230;
    min-width: 230px;
    max-width: 230px;
}
#SidebarLogo {
    color: #ffffff;
    font-size: 17px;
    font-weight: 700;
    padding: 18px 12px 14px 12px;
}
#SidebarButton {
    background-color: transparent;
    color: #8f97aa;
    text-align: left;
    padding: 12px 18px;
    border: none;
    border-radius: 8px;
    margin: 3px 10px;
    font-size: 13px;
    font-weight: 600;
}
#SidebarButton:hover {
    background-color: #181d2a;
    color: #00d2ff;
}
#SidebarButton:checked {
    background-color: #17243b;
    color: #00d2ff;
    border-left: 3px solid #00d2ff;
}

/* Cards & Panels */
QFrame#Card, QFrame#Panel {
    background-color: #171a25;
    border: 1px solid #242a3c;
    border-radius: 12px;
    padding: 16px;
}
QFrame#Card QLabel, QFrame#Panel QLabel {
    background-color: transparent;
}
QFrame#CardHover:hover {
    border-color: #00d2ff;
}

/* Status Bar */
QStatusBar {
    background-color: #0c0e14;
    border-top: 1px solid #1e2230;
    padding: 3px 8px;
}
QStatusBar QLabel {
    background-color: transparent;
    padding: 2px 8px;
}
QStatusBar QPushButton {
    background-color: #1c2234;
    color: #00d2ff;
    border: 1px solid #2d3856;
    border-radius: 6px;
    padding: 3px 14px;
    font-weight: 600;
    font-size: 12px;
    margin-right: 10px;
}
QStatusBar QPushButton:hover {
    background-color: #252f48;
    border-color: #00d2ff;
}

/* Inputs & Textareas */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
    background-color: #1a1d28;
    color: #ffffff;
    border: 1px solid #2a2f42;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 13px;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus {
    border: 1px solid #00d2ff;
    background-color: #1e2230;
}

/* Buttons */
QPushButton {
    background-color: #252a3a;
    color: #e6e8ee;
    border: 1px solid #333a50;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #31384e;
    border-color: #00d2ff;
    color: #00d2ff;
}
QPushButton:pressed {
    background-color: #1a1e2b;
}
QPushButton:disabled {
    background-color: #161821;
    color: #4b5266;
    border-color: #1f2330;
}

/* Primary Accent Button */
QPushButton#PrimaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00b4db, stop:1 #0083b0);
    color: #ffffff;
    border: none;
    font-weight: 700;
    padding: 10px 22px;
}
QPushButton#PrimaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00c6ff, stop:1 #0072ff);
}
QPushButton#PrimaryBtn:pressed {
    background-color: #005bb5;
}

/* Danger Button */
QPushButton#DangerBtn {
    background-color: #381a1f;
    color: #ff5252;
    border: 1px solid #5a252d;
}
QPushButton#DangerBtn:hover {
    background-color: #4d2028;
    border-color: #ff5252;
}

/* ComboBox */
QComboBox {
    background-color: #1a1d28;
    color: #ffffff;
    border: 1px solid #2a2f42;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 20px;
}
QComboBox:hover {
    border-color: #00d2ff;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left: none;
}
QComboBox QAbstractItemView {
    background-color: #1a1d28;
    color: #ffffff;
    border: 1px solid #2a2f42;
    selection-background-color: #00d2ff;
    selection-color: #000000;
    padding: 4px;
}

/* Tables */
QTableWidget {
    background-color: #161822;
    gridline-color: #212534;
    border: 1px solid #232736;
    border-radius: 8px;
    selection-background-color: #1e2638;
    selection-color: #00d2ff;
}
QHeaderView::section {
    background-color: #11131a;
    color: #8f97aa;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #232736;
    font-weight: 700;
    font-size: 12px;
}
QTableWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #1c202d;
}

/* Progress Bars */
QProgressBar {
    background-color: #1a1d28;
    border: 1px solid #262b3d;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    font-size: 11px;
    height: 12px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00b4db, stop:1 #0083b0);
    border-radius: 5px;
}

/* Tab Widgets */
QTabWidget::pane {
    border: 1px solid #232736;
    background-color: #181b24;
    border-radius: 8px;
}
QTabBar::tab {
    background-color: #14161f;
    color: #8f97aa;
    padding: 10px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background-color: #181b24;
    color: #00d2ff;
    border-bottom: 2px solid #00d2ff;
}

/* CheckBox & RadioButton */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #e6e8ee;
    font-size: 13px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    background-color: #1a1d28;
    border: 1px solid #2a2f42;
    border-radius: 4px;
}
QRadioButton::indicator {
    border-radius: 9px;
}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #00d2ff;
    border-color: #00d2ff;
}

/* Labels */
QLabel#Heading1 {
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
}
QLabel#Heading2 {
    font-size: 15px;
    font-weight: 600;
    color: #ffffff;
}
QLabel#MutedText {
    color: #8f97aa;
    font-size: 12px;
}
"""

LIGHT_THEME_QSS = """
QMainWindow, QDialog, #CentralWidget, QStackedWidget, QStackedWidget > QWidget {
    background-color: #f5f7fb;
    background: #f5f7fb;
}
QWidget {
    color: #212529;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #0072ff;
    selection-color: #ffffff;
}
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget,
QScrollArea #scrollAreaWidgetContents, QScrollArea .QWidget, QScrollArea QWidget {
    background-color: transparent;
    background: transparent;
    border: none;
}
QLabel {
    background-color: transparent;
    color: #212529;
}
#Sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
    min-width: 230px;
    max-width: 230px;
}
#SidebarLogo {
    color: #1a202c;
    font-size: 17px;
    font-weight: 700;
    padding: 18px 12px 14px 12px;
}
#SidebarButton {
    background-color: transparent;
    color: #64748b;
    text-align: left;
    padding: 12px 18px;
    border: none;
    border-radius: 8px;
    margin: 3px 10px;
    font-size: 13px;
    font-weight: 600;
}
#SidebarButton:hover {
    background-color: #f1f5f9;
    color: #0072ff;
}
#SidebarButton:checked {
    background-color: #e0f2fe;
    color: #0072ff;
    border-left: 3px solid #0072ff;
}
QFrame#Card, QFrame#Panel {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
}
QFrame#Card QLabel, QFrame#Panel QLabel {
    background-color: transparent;
}
QStatusBar {
    background-color: #ffffff;
    border-top: 1px solid #e2e8f0;
    padding: 3px 8px;
}
QStatusBar QLabel {
    background-color: transparent;
    padding: 2px 8px;
}
QStatusBar QPushButton {
    background-color: #e0f2fe;
    color: #0072ff;
    border: 1px solid #bae6fd;
    border-radius: 6px;
    padding: 3px 14px;
    font-weight: 600;
    font-size: 12px;
    margin-right: 10px;
}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox {
    background-color: #ffffff;
    color: #1a202c;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 9px 12px;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #0072ff;
}
QPushButton {
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #f8fafc;
    border-color: #0072ff;
    color: #0072ff;
}
QPushButton#PrimaryBtn {
    background-color: #0072ff;
    color: #ffffff;
    border: none;
    font-weight: 700;
    padding: 10px 22px;
}
QPushButton#PrimaryBtn:hover {
    background-color: #005bb5;
}
QPushButton#DangerBtn {
    background-color: #fee2e2;
    color: #dc2626;
    border: 1px solid #fca5a5;
}
QTableWidget {
    background-color: #ffffff;
    gridline-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-weight: 700;
}
QProgressBar {
    background-color: #e2e8f0;
    border: none;
    border-radius: 6px;
    text-align: center;
    color: #1a202c;
    font-size: 11px;
    height: 12px;
}
QProgressBar::chunk {
    background-color: #0072ff;
    border-radius: 6px;
}
QLabel#Heading1 {
    font-size: 20px;
    font-weight: 700;
    color: #0f172a;
}
QLabel#Heading2 {
    font-size: 15px;
    font-weight: 600;
    color: #1e293b;
}
QLabel#MutedText {
    color: #64748b;
    font-size: 12px;
}
"""


def get_stylesheet(theme: str = "dark") -> str:
    return DARK_THEME_QSS if theme.lower() == "dark" else LIGHT_THEME_QSS
