"""
Download Queue View: Active downloads list, batch actions, speed limits, and concurrency controls.
"""

from typing import Dict, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.config import config_manager
from app.core.constants import CONCURRENCY_CHOICES, SPEED_LIMIT_PRESETS
from app.models.job import DownloadJob
from app.ui.components.custom_widgets import StatCard
from app.ui.components.job_card import JobCard
from app.utils.file_utils import check_disk_space
from app.utils.string_utils import format_bytes, format_speed
from app.workers.queue_manager import queue_manager


class QueueView(QWidget):
    """View displaying active, queued, and completed downloads."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.cards: Dict[str, JobCard] = {}

        self._setup_ui()
        self._connect_signals()

        # Timer to refresh total disk space & speed
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._refresh_system_stats)
        self.stats_timer.start(2000)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Title
        title_row = QHBoxLayout()
        title_lbl = QLabel("Download Queue")
        title_lbl.setObjectName("Heading1")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        main_layout.addLayout(title_row)

        # 1. Stat Cards Row
        stat_row = QHBoxLayout()
        stat_row.setSpacing(12)

        self.card_total = StatCard("Total Jobs", "0", "📋")
        self.card_active = StatCard("Active", "0", "⚡")
        self.card_speed = StatCard("Speed", "0 KB/s", "🚀")
        self.card_disk = StatCard("Free Space", "Checking...", "💾")

        stat_row.addWidget(self.card_total)
        stat_row.addWidget(self.card_active)
        stat_row.addWidget(self.card_speed)
        stat_row.addWidget(self.card_disk)
        main_layout.addLayout(stat_row)

        # 2. Controls Bar (Batch Actions & Concurrency)
        ctrl_card = QFrame()
        ctrl_card.setObjectName("Card")
        ctrl_layout = QHBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(12, 8, 12, 8)
        ctrl_layout.setSpacing(10)

        self.btn_resume_all = QPushButton("▶ Resume All")
        self.btn_resume_all.setCursor(Qt.PointingHandCursor)
        self.btn_resume_all.clicked.connect(queue_manager.resume_all)

        self.btn_pause_all = QPushButton("⏸ Pause All")
        self.btn_pause_all.setCursor(Qt.PointingHandCursor)
        self.btn_pause_all.clicked.connect(queue_manager.pause_all)

        self.btn_cancel_all = QPushButton("⏹ Cancel All")
        self.btn_cancel_all.setCursor(Qt.PointingHandCursor)
        self.btn_cancel_all.clicked.connect(queue_manager.cancel_all)

        self.btn_retry_failed = QPushButton("🔄 Retry Failed")
        self.btn_retry_failed.setCursor(Qt.PointingHandCursor)
        self.btn_retry_failed.clicked.connect(queue_manager.retry_failed)

        self.btn_clear_done = QPushButton("🧹 Clear Completed")
        self.btn_clear_done.setCursor(Qt.PointingHandCursor)
        self.btn_clear_done.clicked.connect(queue_manager.clear_completed)

        self.btn_clear_all = QPushButton("🗑 Clear All")
        self.btn_clear_all.setCursor(Qt.PointingHandCursor)
        self.btn_clear_all.clicked.connect(self._clear_all_jobs)

        ctrl_layout.addWidget(self.btn_resume_all)
        ctrl_layout.addWidget(self.btn_pause_all)
        ctrl_layout.addWidget(self.btn_cancel_all)
        ctrl_layout.addWidget(self.btn_retry_failed)
        ctrl_layout.addWidget(self.btn_clear_done)
        ctrl_layout.addWidget(self.btn_clear_all)
        ctrl_layout.addStretch()

        # Concurrency limit selector
        ctrl_layout.addWidget(QLabel("Simultaneous Downloads:"))
        self.cmb_concurrency = QComboBox()
        for c in CONCURRENCY_CHOICES:
            self.cmb_concurrency.addItem(str(c), c)
        self.cmb_concurrency.setCurrentText(str(config_manager.settings.max_concurrent_downloads))
        self.cmb_concurrency.currentIndexChanged.connect(self._on_concurrency_changed)
        ctrl_layout.addWidget(self.cmb_concurrency)

        # Speed limit selector
        ctrl_layout.addWidget(QLabel("Speed Limit:"))
        self.cmb_speed = QComboBox()
        for label, val in SPEED_LIMIT_PRESETS.items():
            self.cmb_speed.addItem(label, val)
        self.cmb_speed.currentIndexChanged.connect(self._on_speed_changed)
        ctrl_layout.addWidget(self.cmb_speed)

        main_layout.addWidget(ctrl_card)

        # 3. Scrollable List of JobCards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.list_container = QWidget()
        self.list_container.setObjectName("scrollAreaWidgetContents")
        self.list_container.setStyleSheet("background: transparent;")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch()

        self.scroll_area.setWidget(self.list_container)
        main_layout.addWidget(self.scroll_area, 1)

        # Initial refresh
        self._refresh_system_stats()

    def _connect_signals(self):
        queue_manager.job_added.connect(self._on_job_added)
        queue_manager.job_updated.connect(self._on_job_updated)
        queue_manager.job_finished.connect(self._on_job_updated)
        queue_manager.job_removed.connect(self._on_job_removed)
        queue_manager.stats_updated.connect(self._on_stats_updated)

    def _on_job_added(self, job: DownloadJob):
        if job.id in self.cards:
            return

        card = JobCard(job)
        card.pause_requested.connect(queue_manager.pause_job)
        card.resume_requested.connect(queue_manager.resume_job)
        card.cancel_requested.connect(queue_manager.cancel_job)
        card.retry_requested.connect(queue_manager.retry_job)
        card.remove_requested.connect(queue_manager.remove_job)

        self.cards[job.id] = card
        # Insert before stretch at end
        self.list_layout.insertWidget(self.list_layout.count() - 1, card)

    def _on_job_updated(self, job: DownloadJob):
        if job.id in self.cards:
            self.cards[job.id].update_data(job)
        else:
            self._on_job_added(job)

    def _on_job_removed(self, job_id: str):
        if job_id in self.cards:
            card = self.cards.pop(job_id)
            self.list_layout.removeWidget(card)
            card.deleteLater()

    def _on_stats_updated(self, total: int, active: int, queued: int, completed: int):
        self.card_total.set_value(str(total))
        self.card_active.set_value(f"{active} Active / {queued} Queued")

    def _refresh_system_stats(self):
        # Calculate active aggregate speed
        total_speed = sum(j.speed_bytes_per_sec for j in queue_manager.jobs if j.id in queue_manager.active_workers)
        self.card_speed.set_value(format_speed(total_speed))

        # Check disk space
        free_b, tot_b, _ = check_disk_space(config_manager.settings.downloads_dir)
        self.card_disk.set_value(f"{free_b / (1024**3):.1f} GB Free")

    def _on_concurrency_changed(self):
        limit = self.cmb_concurrency.currentData()
        st = config_manager.settings
        st.max_concurrent_downloads = limit
        config_manager.update_settings(st)

    def _on_speed_changed(self):
        rate = self.cmb_speed.currentData()
        st = config_manager.settings
        st.speed_limit_bytes = rate
        config_manager.update_settings(st)

    def _clear_all_jobs(self):
        queue_manager.cancel_all()
        for j in list(queue_manager.jobs):
            queue_manager.remove_job(j.id)
