"""
Modern Queue Item Card widget for displaying individual download progress and controls.
"""

from typing import Callable, Optional
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import JobStatus
from app.models.job import DownloadJob
from app.ui.components.custom_widgets import StatusBadge
from app.utils.string_utils import clean_display_title, format_bytes, format_duration, format_speed
from app.utils.system_utils import open_file, show_in_file_manager


class JobCard(QFrame):
    """Card representing a single active/queued download job."""

    pause_requested = Signal(str)   # job_id
    resume_requested = Signal(str)  # job_id
    cancel_requested = Signal(str)  # job_id
    retry_requested = Signal(str)   # job_id
    remove_requested = Signal(str)  # job_id

    def __init__(self, job: DownloadJob, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.job = job
        self.setObjectName("Card")
        self.setFixedHeight(120)
        self.cancel_timer: Optional[QTimer] = None
        self.cancel_countdown: int = 5

        self._setup_ui()
        self.update_data(job)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(14)

        # Left: Thumbnail / Platform Box
        self.thumb_box = QLabel("🎬")
        self.thumb_box.setFixedSize(110, 75)
        self.thumb_box.setAlignment(Qt.AlignCenter)
        self.thumb_box.setStyleSheet("background-color: #12141a; border-radius: 6px; font-size: 28px; border: 1px solid #232736;")
        main_layout.addWidget(self.thumb_box)

        # Center: Details & Progress
        center_layout = QVBoxLayout()
        center_layout.setSpacing(4)

        # Top row: Title + Status Badge
        title_row = QHBoxLayout()
        self.title_lbl = QLabel()
        self.title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #ffffff;")
        self.status_badge = StatusBadge(self.job.status.value)

        title_row.addWidget(self.title_lbl, 1)
        title_row.addWidget(self.status_badge)
        center_layout.addLayout(title_row)

        # Meta row: Platform, Resolution, Quality preset (without Audio: Included)
        self.meta_lbl = QLabel()
        self.meta_lbl.setObjectName("MutedText")
        center_layout.addWidget(self.meta_lbl)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        center_layout.addWidget(self.progress_bar)

        # Bottom stats row: Downloaded / Total, Speed, ETA
        self.stats_lbl = QLabel()
        self.stats_lbl.setObjectName("MutedText")
        self.stats_lbl.setStyleSheet("font-size: 11px;")
        center_layout.addWidget(self.stats_lbl)

        main_layout.addLayout(center_layout, 1)

        # Right: Action Buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)
        btn_layout.setAlignment(Qt.AlignCenter)

        self.btn_pause_resume = QPushButton("Pause")
        self.btn_pause_resume.setFixedSize(80, 28)
        self.btn_pause_resume.clicked.connect(self._on_pause_resume_clicked)
        btn_layout.addWidget(self.btn_pause_resume)

        self.btn_action = QPushButton("Cancel")
        self.btn_action.setFixedSize(80, 28)
        self.btn_action.clicked.connect(self._on_action_clicked)
        btn_layout.addWidget(self.btn_action)

        main_layout.addLayout(btn_layout)

    def update_data(self, job: DownloadJob):
        self.job = job
        self.title_lbl.setText(clean_display_title(job.title, 55))
        self.status_badge.set_status(job.status.value)
        self.progress_bar.setValue(int(job.progress_percent))

        # Update Meta (No redundant "Audio: Included")
        preset_str = job.quality_preset.value if hasattr(job.quality_preset, "value") else str(job.quality_preset)
        if job.is_audio_only or job.target_container.lower() == "mp3":
            format_tag = "Audio Only (MP3)"
        else:
            format_tag = f"{job.resolution} • {preset_str}"

        self.meta_lbl.setText(f"{job.platform} • {format_tag}")

        # Update Stats & Buttons based on Status
        if job.status == JobStatus.DOWNLOADING:
            dl_str = format_bytes(job.downloaded_bytes)
            tot_str = format_bytes(job.total_bytes) if job.total_bytes > 0 else "Unknown"
            spd_str = format_speed(job.speed_bytes_per_sec)
            eta_str = f"ETA: {job.display_eta}" if job.display_eta else ""
            self.stats_lbl.setText(f"{dl_str} / {tot_str} ({job.progress_percent:.1f}%) • {spd_str} {eta_str}")

            self.btn_pause_resume.setText("Pause")
            self.btn_pause_resume.setVisible(True)
            self.btn_action.setText("Cancel")
            self.btn_action.setVisible(True)

        elif job.status == JobStatus.ENCODING:
            self.stats_lbl.setText(f"Transcoding / Remuxing: {job.encoding_percent:.1f}% ({job.encoding_fps:.0f} fps)")
            self.btn_pause_resume.setVisible(False)
            self.btn_action.setText("Cancel")

        elif job.status == JobStatus.VALIDATING:
            self.stats_lbl.setText("Running FFprobe validation and audio check...")
            self.btn_pause_resume.setVisible(False)
            self.btn_action.setVisible(False)

        elif job.status == JobStatus.COMPLETED:
            size_str = format_bytes(job.downloaded_bytes or job.total_bytes)
            self.stats_lbl.setText(f"<font color='#22c55e'>✓ Completed ({size_str}) - Ready</font>")
            self.btn_pause_resume.setText("Play")
            self.btn_pause_resume.setVisible(True)
            self.btn_action.setText("Folder")
            self.btn_action.setVisible(True)

        elif job.status == JobStatus.FAILED:
            err = job.error_message or "Unknown Error"
            self.stats_lbl.setText(f"<font color='#f87171'>✕ Failed: {err[:50]}</font>")
            self.btn_pause_resume.setText("Retry")
            self.btn_pause_resume.setVisible(True)
            self.btn_action.setText("Remove")
            self.btn_action.setVisible(True)

        elif job.status == JobStatus.CANCELLED:
            if not self.cancel_timer:
                self.cancel_countdown = 5
                self.cancel_timer = QTimer(self)
                self.cancel_timer.timeout.connect(self._on_cancel_tick)
                self.cancel_timer.start(1000)
            self.stats_lbl.setText(f"<font color='#f87171'>⏹ Cancelled • Moving to history in {self.cancel_countdown}s...</font>")
            self.btn_pause_resume.setVisible(False)
            self.btn_action.setText("Dismiss")
            self.btn_action.setVisible(True)

        elif job.status == JobStatus.PAUSED:
            self.stats_lbl.setText("Paused - Partial files preserved")
            self.btn_pause_resume.setText("Resume")
            self.btn_pause_resume.setVisible(True)
            self.btn_action.setText("Cancel")
            self.btn_action.setVisible(True)

        else: # QUEUED / FETCHING
            self.stats_lbl.setText(f"Queued (Waiting for download slot)")
            self.btn_pause_resume.setVisible(False)
            self.btn_action.setText("Cancel")
            self.btn_action.setVisible(True)

    def _on_cancel_tick(self):
        self.cancel_countdown -= 1
        if self.cancel_countdown <= 0:
            if self.cancel_timer:
                self.cancel_timer.stop()
                self.cancel_timer = None
            self.remove_requested.emit(self.job.id)
        else:
            self.stats_lbl.setText(f"<font color='#f87171'>⏹ Cancelled • Moving to history in {self.cancel_countdown}s...</font>")

    def _on_pause_resume_clicked(self):
        if self.job.status == JobStatus.DOWNLOADING:
            self.pause_requested.emit(self.job.id)
        elif self.job.status == JobStatus.PAUSED:
            self.resume_requested.emit(self.job.id)
        elif self.job.status == JobStatus.FAILED:
            self.retry_requested.emit(self.job.id)
        elif self.job.status == JobStatus.COMPLETED:
            if self.job.final_file_path:
                open_file(self.job.final_file_path)

    def _on_action_clicked(self):
        if self.job.status == JobStatus.COMPLETED:
            if self.job.final_file_path:
                show_in_file_manager(self.job.final_file_path)
        elif self.job.status in (JobStatus.FAILED, JobStatus.CANCELLED):
            if self.cancel_timer:
                self.cancel_timer.stop()
                self.cancel_timer = None
            self.remove_requested.emit(self.job.id)
        else:
            self.cancel_requested.emit(self.job.id)
