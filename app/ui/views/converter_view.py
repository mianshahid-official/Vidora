"""
Standalone Media Converter View: Convert downloaded or local media to MP3/other formats with start/end trimming.
"""

from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.config import config_manager
from app.core.constants import JobStatus
from app.database.repositories import HistoryRepository
from app.encoder.profiles import ProfileManager
from app.media.ffprobe_wrapper import FFprobeWrapper
from app.models.job import ConvertJob
from app.ui.components.custom_widgets import DragDropZone, StatusBadge
from app.utils.file_utils import sanitize_filename, strip_emojis
from app.utils.string_utils import clean_display_title, format_bytes, format_duration
from app.utils.system_utils import open_file, show_in_file_manager
from app.workers.encode_worker import EncodeWorker


class ConverterView(QWidget):
    """Standalone batch media converter and MP3 extractor with trimming."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.jobs: List[ConvertJob] = []
        self.workers: Dict[str, EncodeWorker] = {}
        self.selected_file_path: Optional[str] = None
        self.source_duration: float = 0.0

        self._setup_ui()
        self._load_downloaded_files_list()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(14)

        # Header Title
        title_row = QHBoxLayout()
        title_lbl = QLabel("Media Converter & MP3 Extractor")
        title_lbl.setObjectName("Heading1")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self.btn_convert_all = QPushButton("▶ Convert Queue")
        self.btn_convert_all.setObjectName("PrimaryBtn")
        self.btn_convert_all.setCursor(Qt.PointingHandCursor)
        self.btn_convert_all.clicked.connect(self._start_all_conversions)
        title_row.addWidget(self.btn_convert_all)
        main_layout.addLayout(title_row)

        # Scrollable panel for Converter controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("background: transparent; border: none;")

        content_widget = QWidget()
        content_widget.setObjectName("scrollAreaWidgetContents")
        content_widget.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(14)

        # 1. File Source Selection Card
        src_card = QFrame()
        src_card.setObjectName("Card")
        src_layout = QVBoxLayout(src_card)
        src_layout.setSpacing(10)

        src_lbl = QLabel("1. Select Source Media File")
        src_lbl.setStyleSheet("font-weight: 700; color: #ffffff;")
        src_layout.addWidget(src_lbl)

        # Dropdown to pick from downloads + Browse button
        src_pick_row = QHBoxLayout()
        src_pick_row.setSpacing(10)

        self.cmb_downloaded = QComboBox()
        self.cmb_downloaded.setMinimumWidth(320)
        self.cmb_downloaded.currentIndexChanged.connect(self._on_downloaded_selected)
        src_pick_row.addWidget(self.cmb_downloaded, 1)

        self.btn_refresh_downloads = QPushButton("🔄 Refresh")
        self.btn_refresh_downloads.setCursor(Qt.PointingHandCursor)
        self.btn_refresh_downloads.clicked.connect(self._load_downloaded_files_list)
        src_pick_row.addWidget(self.btn_refresh_downloads)

        self.btn_browse = QPushButton("📁 Browse Local File...")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.clicked.connect(self._browse_file)
        src_pick_row.addWidget(self.btn_browse)

        src_layout.addLayout(src_pick_row)

        # File info preview bar
        self.lbl_file_info = QLabel("No file selected yet.")
        self.lbl_file_info.setObjectName("MutedText")
        src_layout.addWidget(self.lbl_file_info)

        content_layout.addWidget(src_card)

        # 2. Format & Trimming Configuration Card
        cfg_card = QFrame()
        cfg_card.setObjectName("Card")
        cfg_layout = QVBoxLayout(cfg_card)
        cfg_layout.setSpacing(12)

        cfg_lbl = QLabel("2. Output Format & Trimming Settings")
        cfg_lbl.setStyleSheet("font-weight: 700; color: #ffffff;")
        cfg_layout.addWidget(cfg_lbl)

        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(14)

        # Target Format
        vbox_fmt = QVBoxLayout()
        vbox_fmt.addWidget(QLabel("Target Format:"))
        self.cmb_format = QComboBox()
        for f in ["MP3 (Audio Only)", "WAV (Lossless Audio)", "AAC (M4A Audio)", "FLAC (Lossless)", "MP4 (Universal Video)", "MKV (Video)"]:
            self.cmb_format.addItem(f)
        self.cmb_format.currentIndexChanged.connect(self._on_format_changed)
        vbox_fmt.addWidget(self.cmb_format)
        fmt_row.addLayout(vbox_fmt)

        # MP3 Bitrate
        self.vbox_bitrate = QVBoxLayout()
        self.lbl_bitrate = QLabel("MP3 Audio Bitrate:")
        self.vbox_bitrate.addWidget(self.lbl_bitrate)
        self.cmb_bitrate = QComboBox()
        self.cmb_bitrate.addItem("320 kbps (High Quality)", "320k")
        self.cmb_bitrate.addItem("256 kbps (Standard)", "256k")
        self.cmb_bitrate.addItem("192 kbps (Good)", "192k")
        self.cmb_bitrate.addItem("128 kbps (Compact)", "128k")
        self.vbox_bitrate.addWidget(self.cmb_bitrate)
        fmt_row.addLayout(self.vbox_bitrate)

        cfg_layout.addLayout(fmt_row)

        # Trimming Section
        trim_box = QFrame()
        trim_box.setStyleSheet("background-color: #12141a; border: 1px solid #232736; border-radius: 8px; padding: 10px;")
        trim_layout = QVBoxLayout(trim_box)
        trim_layout.setSpacing(8)

        self.chk_trim = QCheckBox("✂ Enable Start & End Time Trimming")
        self.chk_trim.setCursor(Qt.PointingHandCursor)
        self.chk_trim.toggled.connect(self._on_trim_toggled)
        trim_layout.addWidget(self.chk_trim)

        self.trim_controls_layout = QHBoxLayout()
        self.trim_controls_layout.setSpacing(12)

        self.lbl_start = QLabel("Start Time (HH:MM:SS):")
        self.txt_start = QLineEdit("00:00:00")
        self.txt_start.setFixedWidth(110)
        self.txt_start.setEnabled(False)

        self.lbl_end = QLabel("End Time (HH:MM:SS):")
        self.txt_end = QLineEdit("00:00:00")
        self.txt_end.setFixedWidth(110)
        self.txt_end.setEnabled(False)

        self.lbl_duration_info = QLabel("Total: 00:00")
        self.lbl_duration_info.setObjectName("MutedText")

        self.trim_controls_layout.addWidget(self.lbl_start)
        self.trim_controls_layout.addWidget(self.txt_start)
        self.trim_controls_layout.addWidget(self.lbl_end)
        self.trim_controls_layout.addWidget(self.txt_end)
        self.trim_controls_layout.addWidget(self.lbl_duration_info)
        self.trim_controls_layout.addStretch()

        trim_layout.addLayout(self.trim_controls_layout)
        cfg_layout.addWidget(trim_box)

        # Add to Queue / Convert Now Buttons
        act_row = QHBoxLayout()
        act_row.addStretch()

        self.btn_add_queue = QPushButton("➕ Add to Conversion List")
        self.btn_add_queue.setCursor(Qt.PointingHandCursor)
        self.btn_add_queue.clicked.connect(self._add_current_to_queue)
        act_row.addWidget(self.btn_add_queue)

        self.btn_convert_now = QPushButton("🚀 Convert to MP3 Now")
        self.btn_convert_now.setObjectName("PrimaryBtn")
        self.btn_convert_now.setCursor(Qt.PointingHandCursor)
        self.btn_convert_now.clicked.connect(self._convert_now)
        act_row.addWidget(self.btn_convert_now)

        cfg_layout.addLayout(act_row)
        content_layout.addWidget(cfg_card)

        # 3. Drag & Drop File Zone
        self.drop_zone = DragDropZone(
            title="Or Drag & Drop Any Media File Here to Convert",
            subtitle="Supports MP4, MKV, WebM, AVI, MOV, FLV, TS, MP3, WAV, FLAC, M4A"
        )
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        content_layout.addWidget(self.drop_zone)

        # 4. Conversion Queue Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Input File", "Target Format", "Progress", "Speed / FPS", "Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 140)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(180)
        content_layout.addWidget(self.table)

        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area, 1)

    def _load_downloaded_files_list(self):
        self.cmb_downloaded.blockSignals(True)
        self.cmb_downloaded.clear()
        self.cmb_downloaded.addItem("-- Choose from Downloaded Files --", None)

        history = HistoryRepository.get_all(limit=50)
        added_paths = set()

        for h in history:
            fp = h.get("file_path")
            if fp and Path(fp).is_file() and fp not in added_paths:
                clean_name = strip_emojis(Path(fp).name)
                self.cmb_downloaded.addItem(f"🎬 {clean_display_title(clean_name, 50)} ({format_bytes(h.get('file_size'))})", fp)
                added_paths.add(fp)

        # Also check downloads directory for any existing files
        dl_dir = Path(config_manager.settings.downloads_dir)
        if dl_dir.exists():
            for f in sorted(dl_dir.glob("*.*"), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file() and str(f) not in added_paths and not f.name.endswith((".part", ".ytdl", ".db", ".log")):
                    clean_name = strip_emojis(f.name)
                    self.cmb_downloaded.addItem(f"📁 {clean_display_title(clean_name, 50)} ({format_bytes(f.stat().st_size)})", str(f.resolve()))
                    added_paths.add(str(f))

        self.cmb_downloaded.blockSignals(False)

    def _on_downloaded_selected(self):
        path = self.cmb_downloaded.currentData()
        if path and Path(path).is_file():
            self._set_selected_file(path)

    def _browse_file(self):
        fp, _ = QFileDialog.getOpenFileName(
            self,
            "Select Media File to Convert",
            config_manager.settings.downloads_dir,
            "Media Files (*.mp4 *.mkv *.webm *.avi *.mov *.flv *.ts *.mp3 *.m4a *.aac *.flac *.wav)"
        )
        if fp:
            self._set_selected_file(fp)

    def _on_files_dropped(self, files: List[str]):
        if files:
            self._set_selected_file(files[0])

    def _set_selected_file(self, file_path: str):
        p = Path(file_path)
        if not p.is_file():
            return

        self.selected_file_path = str(p.resolve())
        probe = FFprobeWrapper.probe(self.selected_file_path)

        if probe.is_valid:
            dur = probe.container.duration if probe.container else 0.0
            self.source_duration = dur
            v_info = f"{probe.primary_video.codec_name.upper()} {probe.primary_video.width}x{probe.primary_video.height}" if probe.has_video else "No Video"
            a_info = f"{probe.primary_audio.codec_name.upper()} ({probe.primary_audio.channels} ch)" if probe.has_audio else "No Audio"
            self.lbl_file_info.setText(f"✓ <b>{clean_display_title(strip_emojis(p.name), 60)}</b> • Duration: {format_duration(dur)} • {v_info} • {a_info}")

            self.txt_start.setText("00:00:00")
            self.txt_end.setText(format_duration(dur) if dur > 0 else "00:00:00")
            self.lbl_duration_info.setText(f"Total: {format_duration(dur)}")
        else:
            self.lbl_file_info.setText(f"📁 <b>{p.name}</b> ({format_bytes(p.stat().st_size)})")

    def _on_format_changed(self):
        text = self.cmb_format.currentText()
        is_mp3 = "MP3" in text
        self.vbox_bitrate.setEnabled(is_mp3)
        self.btn_convert_now.setText(f"🚀 Convert to {text.split()[0]} Now")

    def _on_trim_toggled(self, checked: bool):
        self.txt_start.setEnabled(checked)
        self.txt_end.setEnabled(checked)

    def _build_job_from_ui(self) -> Optional[ConvertJob]:
        if not self.selected_file_path or not Path(self.selected_file_path).is_file():
            self.lbl_file_info.setText("<font color='#f87171'>Please select a valid media file first.</font>")
            return None

        p = Path(self.selected_file_path)
        fmt_text = self.cmb_format.currentText()

        ext = "mp3"
        preset_id = "audio_mp3_320k"

        if "MP3" in fmt_text:
            ext = "mp3"
            br = self.cmb_bitrate.currentData()
            preset_id = f"audio_mp3_{br}"
        elif "WAV" in fmt_text:
            ext = "wav"
            preset_id = "audio_wav"
        elif "AAC" in fmt_text:
            ext = "m4a"
            preset_id = "audio_aac_256k"
        elif "FLAC" in fmt_text:
            ext = "flac"
            preset_id = "audio_flac"
        elif "MP4" in fmt_text:
            ext = "mp4"
            preset_id = "universal_mp4"
        elif "MKV" in fmt_text:
            ext = "mkv"
            preset_id = "original_best_quality"

        out_name = f"{sanitize_filename(p.stem)}_converted.{ext}"
        out_path = str(p.parent / out_name)

        job = ConvertJob(
            input_file_path=self.selected_file_path,
            output_file_path=out_path,
            preset_id=preset_id,
            target_container=ext,
            status=JobStatus.QUEUED,
            trim_enabled=self.chk_trim.isChecked(),
            trim_start=self.txt_start.text().strip() if self.chk_trim.isChecked() else "00:00:00",
            trim_end=self.txt_end.text().strip() if self.chk_trim.isChecked() else "",
            audio_bitrate=self.cmb_bitrate.currentData() if "MP3" in fmt_text else "320k"
        )
        return job

    def _add_current_to_queue(self):
        job = self._build_job_from_ui()
        if job:
            self.jobs.append(job)
            self._refresh_table()
            self.lbl_file_info.setText(f"✓ Added <b>{Path(job.input_file_path).name}</b> to conversion queue.")

    def _convert_now(self):
        job = self._build_job_from_ui()
        if job:
            self.jobs.append(job)
            self._refresh_table()
            self._start_job(job)

    def _refresh_table(self):
        self.table.setRowCount(len(self.jobs))

        for row, job in enumerate(self.jobs):
            # Input file
            self.table.setItem(row, 0, QTableWidgetItem(clean_display_title(strip_emojis(Path(job.input_file_path).name), 45)))

            # Preset / Format
            trim_tag = f" [✂ {job.trim_start} - {job.trim_end}]" if job.trim_enabled else ""
            self.table.setItem(row, 1, QTableWidgetItem(f"{job.target_container.upper()}{trim_tag}"))

            # Progress Bar
            pbar = QProgressBar()
            pbar.setRange(0, 100)
            pbar.setValue(int(job.progress_percent))
            self.table.setCellWidget(row, 2, pbar)

            # Speed
            spd_text = f"{job.current_fps:.0f} fps ({job.current_speed:.1f}x)" if job.status == JobStatus.ENCODING else "-"
            self.table.setItem(row, 3, QTableWidgetItem(spd_text))

            # Status Badge
            badge = StatusBadge(job.status.value)
            badge_widget = QWidget()
            bw_layout = QHBoxLayout(badge_widget)
            bw_layout.addWidget(badge)
            bw_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 4, badge_widget)

            # Actions
            act_widget = QWidget()
            act_layout = QHBoxLayout(act_widget)
            act_layout.setContentsMargins(2, 2, 2, 2)
            act_layout.setSpacing(4)

            if job.status == JobStatus.COMPLETED:
                btn_play = QPushButton("▶")
                btn_play.setToolTip("Play Converted File")
                btn_play.setFixedSize(26, 26)
                btn_play.clicked.connect(lambda _, op=job.output_file_path: open_file(op))
                btn_folder = QPushButton("📁")
                btn_folder.setToolTip("Show in Folder")
                btn_folder.setFixedSize(26, 26)
                btn_folder.clicked.connect(lambda _, op=job.output_file_path: show_in_file_manager(op))
                act_layout.addWidget(btn_play)
                act_layout.addWidget(btn_folder)
            elif job.status == JobStatus.ENCODING:
                btn_cancel = QPushButton("⏹")
                btn_cancel.setFixedSize(26, 26)
                btn_cancel.clicked.connect(lambda _, jid=job.id: self._cancel_job(jid))
                act_layout.addWidget(btn_cancel)
            else:
                btn_start = QPushButton("▶")
                btn_start.setFixedSize(26, 26)
                btn_start.clicked.connect(lambda _, j=job: self._start_job(j))
                act_layout.addWidget(btn_start)

            self.table.setCellWidget(row, 5, act_widget)

    def _start_job(self, job: ConvertJob):
        if job.id in self.workers:
            return

        worker = EncodeWorker(job)
        self.workers[job.id] = worker
        worker.job_progress.connect(self._on_worker_progress)
        worker.job_finished.connect(self._on_worker_finished)
        worker.start()
        self._refresh_table()

    def _cancel_job(self, job_id: str):
        if job_id in self.workers:
            self.workers[job_id].cancel()

    def _start_all_conversions(self):
        for job in self.jobs:
            if job.status == JobStatus.QUEUED:
                self._start_job(job)

    def _on_worker_progress(self, job: ConvertJob):
        self._refresh_table()

    def _on_worker_finished(self, job: ConvertJob):
        if job.id in self.workers:
            del self.workers[job.id]
        self._refresh_table()

