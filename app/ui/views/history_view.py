"""
Download History View: Searchable table of past completed downloads with file actions.
"""

import datetime
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database.repositories import HistoryRepository
from app.models.job import DownloadJob
from app.utils.string_utils import format_bytes
from app.utils.system_utils import open_file, show_in_file_manager
from app.workers.queue_manager import queue_manager


class HistoryView(QWidget):
    """View showing persisted download history."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self.refresh_history()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Title & Search
        top_row = QHBoxLayout()
        title_lbl = QLabel("Download History")
        title_lbl.setObjectName("Heading1")
        top_row.addWidget(title_lbl)
        top_row.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search history by title, uploader, or URL...")
        self.search_input.setFixedWidth(280)
        self.search_input.textChanged.connect(self._on_search)
        top_row.addWidget(self.search_input)

        self.btn_refresh = QPushButton("🔄 Refresh")
        self.btn_refresh.clicked.connect(self.refresh_history)
        top_row.addWidget(self.btn_refresh)

        self.btn_clear = QPushButton("Clear All History")
        self.btn_clear.clicked.connect(self._clear_history)
        top_row.addWidget(self.btn_clear)

        main_layout.addLayout(top_row)

        # History Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Title", "Platform", "Date", "Size", "Resolution", "Format", "Audio Codec", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in [1, 2, 3, 4, 5, 6, 7]:
            self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        main_layout.addWidget(self.table)

    def refresh_history(self):
        entries = HistoryRepository.get_all(limit=300)
        self._populate_table(entries)

    def _on_search(self, query: str):
        if not query.strip():
            self.refresh_history()
            return
        entries = HistoryRepository.search(query.strip())
        self._populate_table(entries)

    def _populate_table(self, entries: List[dict]):
        self.table.setRowCount(len(entries))

        for row, item in enumerate(entries):
            st = item.get("status", "Completed")
            is_cancelled = st == "Cancelled"
            is_failed = st == "Failed"

            # Title
            title_text = item.get("title", "Unknown")
            self.table.setItem(row, 0, QTableWidgetItem(title_text))
            self.table.setItem(row, 1, QTableWidgetItem(item.get("platform", "Unknown")))

            # Date
            comp_time = item.get("completed_at") or item.get("created_at")
            date_str = datetime.datetime.fromtimestamp(comp_time).strftime("%Y-%m-%d %H:%M") if comp_time else "-"
            self.table.setItem(row, 2, QTableWidgetItem(date_str))

            # Size
            size_b = item.get("file_size", 0)
            size_str = format_bytes(size_b) if size_b > 0 else "-"
            self.table.setItem(row, 3, QTableWidgetItem(size_str))

            # Resolution & Format
            self.table.setItem(row, 4, QTableWidgetItem(item.get("resolution") or "-"))
            self.table.setItem(row, 5, QTableWidgetItem((item.get("target_format") or item.get("container") or "mp4").upper()))

            # Status / Audio Codec
            if is_cancelled:
                status_item = QTableWidgetItem("⏹ Cancelled")
                status_item.setForeground(Qt.gray)
                self.table.setItem(row, 6, status_item)
            elif is_failed:
                status_item = QTableWidgetItem("✕ Failed")
                status_item.setForeground(Qt.red)
                self.table.setItem(row, 6, status_item)
            else:
                acodec = item.get("audio_codec") or "AAC"
                audio_item = QTableWidgetItem(f"{acodec.upper()} ✓")
                audio_item.setForeground(Qt.green)
                self.table.setItem(row, 6, audio_item)

            # Actions Widget
            actions_widget = QWidget()
            act_layout = QHBoxLayout(actions_widget)
            act_layout.setContentsMargins(4, 2, 4, 2)
            act_layout.setSpacing(6)

            file_path = item.get("file_path", "")
            has_file = bool(file_path and Path(file_path).is_file())

            if has_file:
                btn_play = QPushButton("▶ Play")
                btn_play.setFixedHeight(26)
                btn_play.clicked.connect(lambda _, fp=file_path: open_file(fp))

                btn_folder = QPushButton("📁 Folder")
                btn_folder.setFixedHeight(26)
                btn_folder.clicked.connect(lambda _, fp=file_path: show_in_file_manager(fp))

                act_layout.addWidget(btn_play)
                act_layout.addWidget(btn_folder)
            else:
                lbl_na = QLabel("No file")
                lbl_na.setObjectName("MutedText")
                lbl_na.setStyleSheet("font-size: 11px;")
                act_layout.addWidget(lbl_na)

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(26, 26)
            btn_del.setCursor(Qt.PointingHandCursor)
            btn_del.clicked.connect(lambda _, eid=item.get("id"): self._delete_entry(eid))
            act_layout.addWidget(btn_del)

            self.table.setCellWidget(row, 7, actions_widget)


    def _delete_entry(self, entry_id: str):
        HistoryRepository.delete_entry(entry_id)
        self.refresh_history()

    def _clear_history(self):
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all download history records?\n(This will not delete downloaded files on your hard drive).",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            HistoryRepository.clear_all()
            self.refresh_history()
