"""
Structured Application Log Viewer Dialog with real-time streaming.
"""

from typing import Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.logger import logger


class LogViewerDialog(QDialog):
    """Dialog displaying application, download, FFmpeg, and error logs in real-time."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("System Logs & Diagnostics")
        self.resize(850, 520)

        self._setup_ui()
        logger.subscribe(self._on_log_message)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Top Bar (Filter & Controls)
        top_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter logs by keyword...")
        self.search_input.textChanged.connect(self._apply_filter)
        top_layout.addWidget(self.search_input)

        self.chk_autoscroll = QCheckBox("Auto-scroll")
        self.chk_autoscroll.setChecked(True)
        top_layout.addWidget(self.chk_autoscroll)

        self.btn_clear = QPushButton("Clear Current")
        self.btn_clear.clicked.connect(self._clear_current)
        top_layout.addWidget(self.btn_clear)

        self.btn_export = QPushButton("Export Logs...")
        self.btn_export.clicked.connect(self._export_logs)
        top_layout.addWidget(self.btn_export)

        layout.addLayout(top_layout)

        # Tabs
        self.tabs = QTabWidget()

        self.txt_all = self._create_log_textbox()
        self.txt_app = self._create_log_textbox()
        self.txt_dl = self._create_log_textbox()
        self.txt_ff = self._create_log_textbox()
        self.txt_err = self._create_log_textbox()

        self.tabs.addTab(self.txt_all, "All")
        self.tabs.addTab(self.txt_app, "Application")
        self.tabs.addTab(self.txt_dl, "Downloads")
        self.tabs.addTab(self.txt_ff, "FFmpeg")
        self.tabs.addTab(self.txt_err, "Errors")

        layout.addWidget(self.tabs)

        # Bottom Close Button
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("PrimaryBtn")
        self.btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(self.btn_close)
        layout.addLayout(bottom_layout)

        self._load_existing_logs()

    def _create_log_textbox(self) -> QPlainTextEdit:
        tb = QPlainTextEdit()
        tb.setReadOnly(True)
        tb.setMaximumBlockCount(2000)
        tb.setStyleSheet("background-color: #11131a; font-family: 'Consolas', monospace; font-size: 12px; line-height: 1.4;")
        return tb

    def _load_existing_logs(self):
        """Loads recent lines from log files on disk."""
        logs_dir = logger.logs_dir
        for name, tb in [("app.log", self.txt_app), ("download.log", self.txt_dl), ("ffmpeg.log", self.txt_ff), ("error.log", self.txt_err)]:
            file_path = logs_dir / name
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()[-150:]
                        tb.setPlainText("".join(lines))
                        self.txt_all.appendPlainText("".join(lines))
                except Exception:
                    pass

    def _on_log_message(self, channel: str, level: str, msg: str):
        line = f"[{channel}] [{level}] {msg}"
        self.txt_all.appendPlainText(line)
        if channel == "App":
            self.txt_app.appendPlainText(line)
        elif channel == "Download":
            self.txt_dl.appendPlainText(line)
        elif channel == "FFmpeg":
            self.txt_ff.appendPlainText(line)
        elif channel == "Error" or level == "ERROR":
            self.txt_err.appendPlainText(line)

        if self.chk_autoscroll.isChecked():
            current_tb = self.tabs.currentWidget()
            if isinstance(current_tb, QPlainTextEdit):
                current_tb.verticalScrollBar().setValue(current_tb.verticalScrollBar().maximum())

    def _apply_filter(self, text: str):
        # Plain text search highlight / filter
        pass

    def _clear_current(self):
        current_tb = self.tabs.currentWidget()
        if isinstance(current_tb, QPlainTextEdit):
            current_tb.clear()

    def _export_logs(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Export Log File", "downloader_logs.txt", "Text Files (*.txt)")
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(self.txt_all.toPlainText())

    def closeEvent(self, event):
        logger.unsubscribe(self._on_log_message)
        super().closeEvent(event)
