from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.core.config import config_manager
from app.core.constants import APP_NAME, APP_VERSION
from app.core.dependencies import deps
from app.ui.components.log_dialog import LogViewerDialog
from app.ui.sidebar import Sidebar
from app.ui.theme import get_stylesheet
from app.ui.views.converter_view import ConverterView
from app.ui.views.dashboard_view import DashboardView
from app.ui.views.history_view import HistoryView
from app.ui.views.inspector_view import InspectorView
from app.ui.views.queue_view import QueueView
from app.ui.views.settings_view import SettingsView
from app.utils.string_utils import format_speed
from app.workers.queue_manager import queue_manager


class MainWindow(QMainWindow):
    """Main window integrating sidebar navigation, stacked views, and status bar."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1140, 740)
        self.setMinimumSize(940, 600)

        # Window Icon
        icon_path = Path(__file__).resolve().parent.parent / "resources" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._setup_ui()
        self._setup_shortcuts()
        self._apply_theme()

        # Update status bar timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_status_bar)
        self.status_timer.start(1500)

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar
        self.sidebar = Sidebar()
        self.sidebar.view_changed.connect(self._switch_view)
        self.sidebar.theme_toggled.connect(self._toggle_theme)
        main_layout.addWidget(self.sidebar)

        # 2. Stacked Views Container
        self.stack = QStackedWidget()

        self.dashboard_view = DashboardView()
        self.dashboard_view.navigate_to_queue.connect(lambda: self._switch_view(1))

        self.queue_view = QueueView()
        self.history_view = HistoryView()
        self.converter_view = ConverterView()
        self.inspector_view = InspectorView()
        self.settings_view = SettingsView()

        self.stack.addWidget(self.dashboard_view) # Index 0
        self.stack.addWidget(self.queue_view)     # Index 1
        self.stack.addWidget(self.history_view)   # Index 2
        self.stack.addWidget(self.converter_view) # Index 3
        self.stack.addWidget(self.inspector_view) # Index 4
        self.stack.addWidget(self.settings_view)  # Index 5

        main_layout.addWidget(self.stack, 1)

        # 3. Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setSizeGripEnabled(False)
        self.setStatusBar(self.status_bar)

        self.lbl_queue_status = QLabel("Queue: 0 items (Idle)")
        self.lbl_speed_status = QLabel("Speed: 0 KB/s")
        self.lbl_deps_status = QLabel("Requirements: ✓ Ready")
        self.lbl_deps_status.setStyleSheet("color: #22c55e; font-weight: 700; padding: 0 8px;")

        self.btn_open_logs = QPushButton("📋 View System Logs")
        self.btn_open_logs.setFixedHeight(26)
        self.btn_open_logs.setCursor(Qt.PointingHandCursor)
        self.btn_open_logs.clicked.connect(self._open_log_viewer)

        self.status_bar.addWidget(self.lbl_queue_status, 1)
        self.status_bar.addPermanentWidget(self.lbl_speed_status)
        self.status_bar.addPermanentWidget(self.lbl_deps_status)
        self.status_bar.addPermanentWidget(self.btn_open_logs)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self._switch_view(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self._switch_view(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self._switch_view(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self._switch_view(3))
        QShortcut(QKeySequence("Ctrl+5"), self, lambda: self._switch_view(4))
        QShortcut(QKeySequence("Ctrl+6"), self, lambda: self._switch_view(5))
        QShortcut(QKeySequence("Ctrl+L"), self, self._open_log_viewer)

    def _switch_view(self, index: int):
        self.stack.setCurrentIndex(index)
        self.sidebar.set_active_index(index)
        if index == 2:
            self.history_view.refresh_history()

    def _toggle_theme(self):
        current = config_manager.settings.theme_mode.lower()
        new_theme = "light" if current == "dark" else "dark"
        st = config_manager.settings
        st.theme_mode = new_theme
        config_manager.update_settings(st)
        self._apply_theme()

    def _apply_theme(self):
        theme = config_manager.settings.theme_mode
        self.setStyleSheet(get_stylesheet(theme))

    def _open_log_viewer(self):
        dlg = LogViewerDialog(self)
        dlg.exec()

    def _update_status_bar(self):
        total_active = len(queue_manager.active_workers)
        total_jobs = len(queue_manager.jobs)
        total_speed = sum(j.speed_bytes_per_sec for j in queue_manager.jobs if j.id in queue_manager.active_workers)

        if total_active > 0:
            self.lbl_queue_status.setText(f"Queue: {total_active} active download(s) of {total_jobs} total")
            self.lbl_speed_status.setText(f"Speed: {format_speed(total_speed)}")
        else:
            self.lbl_queue_status.setText(f"Queue: {total_jobs} item(s) (Idle)")
            self.lbl_speed_status.setText("Speed: 0 KB/s")

