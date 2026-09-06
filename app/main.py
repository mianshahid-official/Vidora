"""
Application Bootstrap and Entry Point for Vidora.
"""

import os
import sys
from pathlib import Path

# Ensure application root directory is on Python path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.core.config import config_manager
from app.core.constants import APP_ID, APP_NAME, APP_ORGANIZATION, APP_VERSION
from app.core.dependencies import deps
from app.core.logger import logger
from app.database.db import db
from app.ui.components.startup_dialog import StartupRecoveryDialog
from app.ui.main_window import MainWindow
from app.workers.queue_manager import queue_manager


def main():
    """Main application execution routine."""
    # Ensure Windows taskbar grouping uses App ID
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass

    # Initialize PySide6 Application
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORGANIZATION)

    logger.log_app(f"Starting {APP_NAME} v{APP_VERSION} on Python {sys.version.split()[0]}...")

    # Ensure required default folders exist
    Path(config_manager.settings.downloads_dir).mkdir(parents=True, exist_ok=True)
    Path(config_manager.settings.temp_dir).mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Set Application Icon
    icon_path = PROJECT_ROOT / "app" / "resources" / "icon.png"
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

    # 1. Dependency verification
    dep_statuses = deps.check_all()
    for name, st in dep_statuses.items():
        if st.is_available:
            logger.log_app(f"Dependency [{st.name}]: Ready (v{st.version}) at {st.path}")
        else:
            logger.log_app(f"Dependency [{st.name}]: MISSING - {st.error_message}", "WARN")

    # 2. Seamless Session Recovery (No popup dialog)
    interrupted_jobs = queue_manager.restore_interrupted_jobs()
    if interrupted_jobs:
        logger.log_app(f"Loaded {len(interrupted_jobs)} paused jobs from previous session.")

    # 3. Launch Main Window Directly
    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()

    logger.log_app("UI loaded and running.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
