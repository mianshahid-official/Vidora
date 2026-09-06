"""
Modern Sidebar Navigation Component.
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import APP_NAME, APP_VERSION


class Sidebar(QWidget):
    """Sidebar navigation bar with view switching signals."""

    view_changed = Signal(int)  # index of view in stacked widget
    theme_toggled = Signal()    # theme toggle requested

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 16)
        layout.setSpacing(4)

        # Brand / Logo Header
        header_frame = QFrame()
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(16, 18, 16, 14)
        h_layout.setSpacing(2)

        logo_title = QLabel("⚡ Vidora")
        logo_title.setObjectName("SidebarLogo")
        logo_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffffff;")

        sub_title = QLabel(f"Media Suite v{APP_VERSION}")
        sub_title.setObjectName("MutedText")
        sub_title.setStyleSheet("font-size: 11px; padding-left: 2px;")

        h_layout.addWidget(logo_title)
        h_layout.addWidget(sub_title)
        layout.addWidget(header_frame)

        # Navigation Buttons Group
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_dashboard = self._create_nav_btn("🚀  Dashboard", 0, checked=True)
        self.btn_queue = self._create_nav_btn("📥  Download Queue", 1)
        self.btn_history = self._create_nav_btn("📜  History", 2)
        self.btn_converter = self._create_nav_btn("🔄  Media Converter", 3)
        self.btn_inspector = self._create_nav_btn("🔍  Media Inspector", 4)
        self.btn_settings = self._create_nav_btn("⚙  Settings", 5)

        layout.addWidget(self.btn_dashboard)
        layout.addWidget(self.btn_queue)
        layout.addWidget(self.btn_history)
        layout.addWidget(self.btn_converter)
        layout.addWidget(self.btn_inspector)
        layout.addWidget(self.btn_settings)

        layout.addStretch()

        # Bottom Controls & Developer Footer
        bottom_frame = QFrame()
        b_layout = QVBoxLayout(bottom_frame)
        b_layout.setContentsMargins(12, 10, 12, 0)
        b_layout.setSpacing(8)

        # Theme Switcher Button
        self.btn_theme_toggle = QPushButton("🌓 Switch Theme")
        self.btn_theme_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_theme_toggle.setStyleSheet("""
            QPushButton {
                background-color: #1a1e2b;
                color: #00d2ff;
                border: 1px solid #28324a;
                border-radius: 8px;
                padding: 7px 12px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #242d42;
                border-color: #00d2ff;
            }
        """)
        self.btn_theme_toggle.clicked.connect(lambda: self.theme_toggled.emit())
        b_layout.addWidget(self.btn_theme_toggle)

        # Developer Attribution
        lbl_dev = QLabel("Developed by Shahid")
        lbl_dev.setStyleSheet("color: #717d96; font-size: 11px; font-weight: 600; padding-left: 4px;")
        b_layout.addWidget(lbl_dev)

        layout.addWidget(bottom_frame)

    def _create_nav_btn(self, text: str, view_idx: int, checked: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("SidebarButton")
        btn.setCheckable(True)
        btn.setChecked(checked)
        btn.clicked.connect(lambda: self.view_changed.emit(view_idx))
        self.btn_group.addButton(btn)
        return btn

    def set_active_index(self, index: int):
        buttons = [
            self.btn_dashboard, self.btn_queue, self.btn_history,
            self.btn_converter, self.btn_inspector, self.btn_settings
        ]
        if 0 <= index < len(buttons):
            buttons[index].setChecked(True)

