"""
Main Dashboard View: URL Input, Analysis Preview, Mode Switcher, and Download Triggers.
"""

from typing import List, Optional
from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QBitmap, QGuiApplication, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import config_manager
from app.core.constants import (
    RESOLUTIONS,
    JobStatus,
    OutputContainer,
    QualityPreset,
)
from app.models.format_info import FormatItem, MediaMetadata
from app.models.job import DownloadJob
from app.ui.components.command_dialog import CommandPreviewDialog
from app.utils.file_utils import sanitize_filename, strip_emojis
from app.utils.string_utils import clean_display_title, format_duration
from app.utils.url_utils import detect_platform, extract_urls_from_text, parse_urls_from_file
from app.workers.inspect_worker import MetadataWorker
from app.workers.queue_manager import queue_manager


class ThumbnailLoaderWorker(QThread):
    """Fetches video thumbnail image in background."""
    thumbnail_loaded = Signal(bytes)

    def __init__(self, url: str, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            import urllib.request
            req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                self.thumbnail_loaded.emit(data)
        except Exception:
            pass


class DashboardView(QWidget):
    """Main dashboard for adding single, multiple, or batch URL downloads."""

    navigate_to_queue = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_metadata: Optional[MediaMetadata] = None
        self.meta_worker: Optional[MetadataWorker] = None
        self.thumb_worker: Optional[ThumbnailLoaderWorker] = None

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Title
        title_row = QHBoxLayout()
        title_lbl = QLabel("Dashboard")
        title_lbl.setObjectName("Heading1")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self.btn_preview_cmd = QPushButton("Inspect Generated Command")
        self.btn_preview_cmd.clicked.connect(self._show_command_preview)
        title_row.addWidget(self.btn_preview_cmd)
        main_layout.addLayout(title_row)

        # 1. URL Input Card
        url_card = QFrame()
        url_card.setObjectName("Card")
        url_layout = QVBoxLayout(url_card)
        url_layout.setSpacing(10)

        url_header = QHBoxLayout()
        url_lbl = QLabel("Enter Media URL(s) - Supports Single, Multiple, Playlists & Channels")
        url_lbl.setStyleSheet("font-weight: 700; color: #ffffff;")
        url_header.addWidget(url_lbl)
        url_header.addStretch()

        self.btn_paste = QPushButton("📋 Paste")
        self.btn_paste.clicked.connect(self._paste_clipboard)
        self.btn_import_file = QPushButton("📁 Import File (.txt, .csv)")
        self.btn_import_file.clicked.connect(self._import_url_file)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self._clear_input)

        url_header.addWidget(self.btn_paste)
        url_header.addWidget(self.btn_import_file)
        url_header.addWidget(self.btn_clear)
        url_layout.addLayout(url_header)

        self.url_input = QPlainTextEdit()
        self.url_input.setPlaceholderText("Paste one or more video/audio URLs here (e.g. YouTube, Vimeo, Dailymotion, Twitter, SoundCloud...)\nEach URL on a new line.")
        self.url_input.setFixedHeight(75)
        url_layout.addWidget(self.url_input)

        # Analyze / Action row
        action_row = QHBoxLayout()
        self.btn_analyze = QPushButton("🔍 Fetch Metadata")
        self.btn_analyze.clicked.connect(self._start_metadata_analysis)
        self.status_analyze_lbl = QLabel("")
        self.status_analyze_lbl.setObjectName("MutedText")

        action_row.addWidget(self.btn_analyze)
        action_row.addWidget(self.status_analyze_lbl)
        action_row.addStretch()
        url_layout.addLayout(action_row)

        main_layout.addWidget(url_card)

        # 2. Metadata & Format Preview Card (Visible when metadata fetched)
        self.preview_card = QFrame()
        self.preview_card.setObjectName("Card")
        prev_layout = QHBoxLayout(self.preview_card)
        prev_layout.setSpacing(16)

        # Left: Thumbnail
        self.preview_thumb = QLabel("🎬")
        self.preview_thumb.setFixedSize(150, 95)
        self.preview_thumb.setAlignment(Qt.AlignCenter)
        self.preview_thumb.setStyleSheet("background-color: #12141a; border-radius: 8px; font-size: 32px; border: 1px solid #232736;")
        prev_layout.addWidget(self.preview_thumb)

        # Center: Metadata text
        meta_text_layout = QVBoxLayout()
        meta_text_layout.setSpacing(4)
        self.lbl_prev_title = QLabel("No URL analyzed yet")
        self.lbl_prev_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")
        self.lbl_prev_uploader = QLabel("Uploader: - • Platform: -")
        self.lbl_prev_uploader.setObjectName("MutedText")
        self.lbl_prev_stats = QLabel("Duration: 00:00 • Audio: Available")
        self.lbl_prev_stats.setObjectName("MutedText")

        meta_text_layout.addWidget(self.lbl_prev_title)
        meta_text_layout.addWidget(self.lbl_prev_uploader)
        meta_text_layout.addWidget(self.lbl_prev_stats)
        prev_layout.addLayout(meta_text_layout, 1)

        main_layout.addWidget(self.preview_card)

        # 3. Output Configuration & Download Triggers Card
        config_card = QFrame()
        config_card.setObjectName("Card")
        cfg_layout = QVBoxLayout(config_card)
        cfg_layout.setSpacing(14)

        # Quick Mode Selector (Video MP4 vs Audio Only MP3)
        mode_header = QHBoxLayout()
        cfg_title = QLabel("Download Mode & Quality Settings")
        cfg_title.setStyleSheet("font-weight: 700; color: #ffffff;")
        mode_header.addWidget(cfg_title)
        mode_header.addStretch()

        self.radio_video = QRadioButton("🎥 Video (MP4)")
        self.radio_video.setChecked(True)
        self.radio_video.toggled.connect(self._on_mode_toggled)

        self.radio_audio = QRadioButton("🎵 Audio Only (MP3)")
        self.radio_audio.toggled.connect(self._on_mode_toggled)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_video)
        self.mode_group.addButton(self.radio_audio)

        mode_header.addWidget(self.radio_video)
        mode_header.addWidget(self.radio_audio)
        cfg_layout.addLayout(mode_header)

        opts_row = QHBoxLayout()
        opts_row.setSpacing(14)

        # Preset
        vbox_preset = QVBoxLayout()
        vbox_preset.addWidget(QLabel("Output Mode / Preset:"))
        self.cmb_preset = QComboBox()
        for p in QualityPreset:
            self.cmb_preset.addItem(p.value, p)
        self.cmb_preset.setCurrentText(QualityPreset.UNIVERSAL_MP4.value)
        self.cmb_preset.currentIndexChanged.connect(self._on_preset_changed)
        vbox_preset.addWidget(self.cmb_preset)
        opts_row.addLayout(vbox_preset)

        # Resolution
        self.vbox_res = QVBoxLayout()
        self.lbl_res = QLabel("Resolution:")
        self.vbox_res.addWidget(self.lbl_res)
        self.cmb_res = QComboBox()
        for r in RESOLUTIONS:
            self.cmb_res.addItem(r)
        self.cmb_res.setCurrentText(config_manager.settings.default_resolution)
        self.vbox_res.addWidget(self.cmb_res)
        opts_row.addLayout(self.vbox_res)

        # Container
        vbox_cont = QVBoxLayout()
        vbox_cont.addWidget(QLabel("Container Format:"))
        self.cmb_container = QComboBox()
        for c in ["MP4", "MKV", "WebM", "MP3", "M4A", "AAC", "WAV", "FLAC"]:
            self.cmb_container.addItem(c)
        vbox_cont.addWidget(self.cmb_container)
        opts_row.addLayout(vbox_cont)

        cfg_layout.addLayout(opts_row)

        # Notice on Mode
        self.lbl_compat_notice = QLabel("🎬 <b>Standard MP4 Mode:</b> Automatically produces H.264 + AAC in MP4 with universal playback compatibility.")
        self.lbl_compat_notice.setStyleSheet("color: #00d2ff; font-size: 12px; background-color: #121c2b; padding: 8px 12px; border-radius: 6px;")
        cfg_layout.addWidget(self.lbl_compat_notice)

        # Trigger Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_add_queue = QPushButton("➕ Add to Queue")
        self.btn_add_queue.clicked.connect(lambda: self._create_jobs(start_now=False))
        btn_row.addWidget(self.btn_add_queue)

        self.btn_download_now = QPushButton("🚀 Download Now")
        self.btn_download_now.setObjectName("PrimaryBtn")
        self.btn_download_now.clicked.connect(lambda: self._create_jobs(start_now=True))
        btn_row.addWidget(self.btn_download_now)

        cfg_layout.addLayout(btn_row)
        main_layout.addWidget(config_card)

        main_layout.addStretch()

    def _paste_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        text = clipboard.text()
        if text:
            existing = self.url_input.toPlainText()
            self.url_input.setPlainText((existing + "\n" + text).strip() if existing else text)

    def _import_url_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import URLs from File", "", "Text & CSV Files (*.txt *.csv)")
        if file_path:
            urls = parse_urls_from_file(file_path)
            if urls:
                self.url_input.setPlainText("\n".join(urls))
                self.status_analyze_lbl.setText(f"Loaded {len(urls)} URLs from file.")

    def _clear_input(self):
        self.url_input.clear()
        self.current_metadata = None
        self.preview_thumb.setText("🎬")
        self.preview_thumb.setPixmap(QPixmap())
        self.lbl_prev_title.setText("No URL analyzed yet")
        self.lbl_prev_uploader.setText("Uploader: - • Platform: -")
        self.lbl_prev_stats.setText("Duration: 00:00 • Formats Available: 0")
        self.status_analyze_lbl.setText("")

    def _start_metadata_analysis(self):
        text = self.url_input.toPlainText()
        urls = extract_urls_from_text(text)
        if not urls:
            self.status_analyze_lbl.setText("<font color='#f87171'>Please enter at least one valid URL.</font>")
            return

        target_url = urls[0]
        self.btn_analyze.setEnabled(False)
        self.status_analyze_lbl.setText(f"Fetching metadata...")

        self.meta_worker = MetadataWorker(target_url, process_formats=True)
        self.meta_worker.metadata_ready.connect(self._on_metadata_ready)
        self.meta_worker.error_occurred.connect(self._on_metadata_error)
        self.meta_worker.start()

    def _on_metadata_ready(self, metadata: MediaMetadata):
        self.btn_analyze.setEnabled(True)
        self.current_metadata = metadata
        clean_title = strip_emojis(metadata.title) or metadata.title
        self.lbl_prev_title.setText(clean_display_title(clean_title, 70))
        self.lbl_prev_uploader.setText(f"Uploader: {strip_emojis(metadata.uploader or 'Unknown')} • Platform: {metadata.extractor_key}")
        self.lbl_prev_stats.setText(f"Duration: {format_duration(metadata.duration)} • Audio Stream: Included")
        self.status_analyze_lbl.setText("✓ Metadata fetched successfully.")

        # Load thumbnail image asynchronously
        if metadata.thumbnail:
            self.thumb_worker = ThumbnailLoaderWorker(metadata.thumbnail)
            self.thumb_worker.thumbnail_loaded.connect(self._set_thumbnail_image)
            self.thumb_worker.start()

    def _set_thumbnail_image(self, data: bytes):
        pix = QPixmap()
        if pix.loadFromData(data):
            scaled = pix.scaled(150, 95, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            rounded = QPixmap(150, 95)
            rounded.fill(Qt.transparent)
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, 150, 95, 8, 8)
            painter.setClipPath(path)
            x_offset = max(0, (scaled.width() - 150) // 2)
            y_offset = max(0, (scaled.height() - 95) // 2)
            painter.drawPixmap(0, 0, scaled, x_offset, y_offset, 150, 95)
            painter.end()
            self.preview_thumb.setPixmap(rounded)

    def _on_metadata_error(self, err: str):
        self.btn_analyze.setEnabled(True)
        self.status_analyze_lbl.setText(f"<font color='#f87171'>✕ Error: {err[:60]}</font>")

    def _on_mode_toggled(self):
        if self.radio_audio.isChecked():
            self.cmb_container.setCurrentText("MP3")
            self.cmb_preset.setCurrentText(QualityPreset.AUDIO_ONLY.value)
            self.cmb_res.setEnabled(False)
            self.lbl_compat_notice.setText("🎵 <b>Audio Mode:</b> Extracts audio and converts to high-quality 320 kbps MP3.")
        else:
            self.cmb_container.setCurrentText("MP4")
            self.cmb_preset.setCurrentText(QualityPreset.UNIVERSAL_MP4.value)
            self.cmb_res.setEnabled(True)
            self.lbl_compat_notice.setText("🎬 <b>Standard MP4 Mode:</b> Automatically produces H.264 + AAC in MP4 with universal playback compatibility.")

    def _on_preset_changed(self):
        preset = self.cmb_preset.currentData()
        if preset == QualityPreset.AUDIO_ONLY:
            self.radio_audio.setChecked(True)
            self.cmb_container.setCurrentText("MP3")
            self.cmb_res.setEnabled(False)
            self.lbl_compat_notice.setText("🎵 <b>Audio Mode:</b> Extracts audio and converts to high-quality 320 kbps MP3.")
        else:
            if not self.radio_video.isChecked():
                self.radio_video.setChecked(True)
            self.cmb_res.setEnabled(True)
            if preset in (QualityPreset.UNIVERSAL_MP4, QualityPreset.TV_LCD_COMPATIBLE):
                self.cmb_container.setCurrentText("MP4")
                self.lbl_compat_notice.setText("🎬 <b>Standard MP4 Mode:</b> Automatically produces H.264 + AAC in MP4 with universal playback compatibility.")
            elif preset == QualityPreset.MAXIMUM_COMPATIBILITY:
                self.cmb_container.setCurrentText("MP4")
                self.lbl_compat_notice.setText("📺 <b>Max Compatibility:</b> Conservative H.264 Main + AAC 128k for older media players.")
            else:
                self.lbl_compat_notice.setText("⚡ <b>Best Quality / Balanced:</b> Preserves source stream quality without unnecessary re-encoding.")

    def _create_jobs(self, start_now: bool = True):
        text = self.url_input.toPlainText()
        raw_urls = extract_urls_from_text(text)
        urls = [u for u in raw_urls if u.startswith(("http://", "https://"))]
        if not urls:
            self.status_analyze_lbl.setText("<font color='#f87171'>Please enter at least one valid URL.</font>")
            return

        is_audio = self.radio_audio.isChecked()
        preset = QualityPreset.AUDIO_ONLY if is_audio else self.cmb_preset.currentData()
        res = self.cmb_res.currentText() if not is_audio else "Audio Only"
        container = "mp3" if is_audio else self.cmb_container.currentText().lower()

        created_jobs: List[DownloadJob] = []
        for u in urls:
            raw_title = self.current_metadata.title if (self.current_metadata and self.current_metadata.url == u) else "Media Download"
            title = strip_emojis(raw_title) or raw_title
            uploader = self.current_metadata.uploader if (self.current_metadata and self.current_metadata.url == u) else ""
            duration = self.current_metadata.duration if (self.current_metadata and self.current_metadata.url == u) else 0.0
            thumb = self.current_metadata.thumbnail if (self.current_metadata and self.current_metadata.url == u) else ""

            job = DownloadJob(
                url=u,
                title=title,
                thumbnail_url=thumb,
                platform=detect_platform(u),
                uploader=strip_emojis(uploader) or uploader,
                duration=duration,
                quality_preset=preset,
                target_container=container,
                resolution=res,
                is_audio_only=is_audio,
                destination_dir=config_manager.settings.downloads_dir,
                status=JobStatus.QUEUED
            )
            created_jobs.append(job)

        queue_manager.add_jobs_batch(created_jobs)
        self.status_analyze_lbl.setText(f"Added {len(created_jobs)} item(s) to Queue.")
        self.navigate_to_queue.emit()

    def _show_command_preview(self):
        text = self.url_input.toPlainText()
        urls = extract_urls_from_text(text)
        sample_url = urls[0] if urls else "https://example.com/video"

        is_audio = self.radio_audio.isChecked()
        preset = QualityPreset.AUDIO_ONLY if is_audio else self.cmb_preset.currentData()
        job = DownloadJob(
            url=sample_url,
            title="Sample Media",
            quality_preset=preset,
            target_container="mp3" if is_audio else self.cmb_container.currentText().lower(),
            resolution=self.cmb_res.currentText() if not is_audio else "Audio Only",
            is_audio_only=is_audio,
            destination_dir=config_manager.settings.downloads_dir
        )
        from app.downloader.ytdlp_wrapper import YtdlpEngine
        ytdlp_engine = YtdlpEngine(job)
        ytdlp_cmd = ytdlp_engine.get_preview_command()
        if is_audio:
            ffmpeg_cmd = "ffmpeg -i INPUT.m4a -vn -c:a libmp3lame -b:a 320k -ar 44100 OUTPUT.mp3"
        else:
            ffmpeg_cmd = "ffmpeg -i INPUT.mp4 -c:v libx264 -pix_fmt yuv420p -profile:v high -level 4.1 -c:a aac -b:a 192k -ar 48000 -movflags +faststart OUTPUT.mp4"

        dlg = CommandPreviewDialog(ytdlp_cmd, ffmpeg_cmd, self)
        dlg.exec()
