"""
Media Inspector View: Deep stream analysis and TV / LCD compatibility rule engine.
"""

from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.compatibility import CompatibilityReport
from app.media.inspector import InspectionResult
from app.models.media_info import MediaProbeResult
from app.ui.components.custom_widgets import CompatibilityBadge, DragDropZone
from app.utils.string_utils import format_bytes, format_duration
from app.workers.inspect_worker import FileInspectWorker


class InspectorView(QWidget):
    """Deep media inspector and TV compatibility evaluator."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.inspect_worker: Optional[FileInspectWorker] = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Title
        title_row = QHBoxLayout()
        title_lbl = QLabel("Media Inspector & Stream Analyzer")
        title_lbl.setObjectName("Heading1")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self.btn_select_file = QPushButton("📁 Select Media File...")
        self.btn_select_file.setCursor(Qt.PointingHandCursor)
        self.btn_select_file.clicked.connect(self._browse_file)
        title_row.addWidget(self.btn_select_file)

        main_layout.addLayout(title_row)

        # 1. Drag & Drop Zone
        self.drop_zone = DragDropZone(
            title="Drop Any Video or Audio File Here",
            subtitle="Analyzes streams, codecs, bitrates, pixel formats, and container metadata"
        )
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        main_layout.addWidget(self.drop_zone)

        # Scrollable content area for results
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.content_widget = QWidget()
        self.content_widget.setObjectName("scrollAreaWidgetContents")
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(14)

        # 2. Compatibility Verdict Card
        self.compat_card = QFrame()
        self.compat_card.setObjectName("Card")
        compat_layout = QVBoxLayout(self.compat_card)
        compat_layout.setSpacing(10)

        compat_header = QHBoxLayout()
        self.lbl_compat_title = QLabel("Hardware & Playback Compatibility Analysis")
        self.lbl_compat_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        self.badge_compat = CompatibilityBadge()

        compat_header.addWidget(self.lbl_compat_title)
        compat_header.addStretch()
        compat_header.addWidget(self.badge_compat)
        compat_layout.addLayout(compat_header)

        self.lbl_compat_summary = QLabel("Analyze a media file to inspect hardware and codec compatibility.")
        self.lbl_compat_summary.setWordWrap(True)
        self.lbl_compat_summary.setObjectName("MutedText")
        compat_layout.addWidget(self.lbl_compat_summary)

        # Compatibility checklist table
        self.compat_table = QTableWidget()
        self.compat_table.setColumnCount(4)
        self.compat_table.setHorizontalHeaderLabels(["Attribute", "Stream Value", "Status", "Evaluation Details"])
        self.compat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.compat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.compat_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.compat_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.compat_table.verticalHeader().setVisible(False)
        self.compat_table.setFixedHeight(160)
        compat_layout.addWidget(self.compat_table)

        self.content_layout.addWidget(self.compat_card)

        # 3. Stream Details Grid (Container, Video, Audio)
        streams_grid = QGridLayout()
        streams_grid.setSpacing(14)

        # Container Card
        self.card_container = QFrame()
        self.card_container.setObjectName("Card")
        cc_layout = QVBoxLayout(self.card_container)
        cc_title = QLabel("📦 Container Info")
        cc_title.setStyleSheet("font-weight: 700; color: #ffffff;")
        cc_layout.addWidget(cc_title)
        self.lbl_container_details = QLabel("No file loaded")
        self.lbl_container_details.setObjectName("MutedText")
        cc_layout.addWidget(self.lbl_container_details)
        streams_grid.addWidget(self.card_container, 0, 0)

        # Video Stream Card
        self.card_video = QFrame()
        self.card_video.setObjectName("Card")
        cv_layout = QVBoxLayout(self.card_video)
        cv_title = QLabel("🎬 Video Stream")
        cv_title.setStyleSheet("font-weight: 700; color: #ffffff;")
        cv_layout.addWidget(cv_title)
        self.lbl_video_details = QLabel("No video stream detected")
        self.lbl_video_details.setObjectName("MutedText")
        cv_layout.addWidget(self.lbl_video_details)
        streams_grid.addWidget(self.card_video, 0, 1)

        # Audio Stream Card
        self.card_audio = QFrame()
        self.card_audio.setObjectName("Card")
        ca_layout = QVBoxLayout(self.card_audio)
        ca_title = QLabel("🔊 Audio Stream")
        ca_title.setStyleSheet("font-weight: 700; color: #ffffff;")
        ca_layout.addWidget(ca_title)
        self.lbl_audio_details = QLabel("No audio stream detected")
        self.lbl_audio_details.setObjectName("MutedText")
        ca_layout.addWidget(self.lbl_audio_details)
        streams_grid.addWidget(self.card_audio, 1, 0, 1, 2)

        self.content_layout.addLayout(streams_grid)

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area, 1)

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Media File for Inspection", "", "Media Files (*.mp4 *.mkv *.webm *.avi *.mov *.mp3 *.m4a *.aac *.flac *.wav)")
        if file_path:
            self._inspect_file(file_path)

    def _on_files_dropped(self, files: List[str]):
        if files:
            self._inspect_file(files[0])

    def _inspect_file(self, file_path: str):
        self.lbl_compat_summary.setText(f"Analyzing '{Path(file_path).name}' with FFprobe...")
        self.inspect_worker = FileInspectWorker(file_path)
        self.inspect_worker.inspection_ready.connect(self._on_inspection_ready)
        self.inspect_worker.error_occurred.connect(self._on_inspection_error)
        self.inspect_worker.start()

    def _on_inspection_ready(self, res: InspectionResult):
        probe = res.probe
        compat = res.compatibility

        # 1. Compatibility card
        self.badge_compat.set_level(compat.level)
        self.lbl_compat_summary.setText(f"<b>{compat.verdict}</b>: {compat.summary_text}")

        # Checklist table
        self.compat_table.setRowCount(len(compat.items))
        for row, item in enumerate(compat.items):
            self.compat_table.setItem(row, 0, QTableWidgetItem(item.attribute))
            self.compat_table.setItem(row, 1, QTableWidgetItem(item.value))

            status_item = QTableWidgetItem(item.status)
            if item.status == "PASS":
                status_item.setForeground(Qt.green)
                status_item.setText("✓ Pass")
            elif item.status == "WARN":
                status_item.setForeground(Qt.yellow)
                status_item.setText("⚠ Warn")
            else:
                status_item.setForeground(Qt.red)
                status_item.setText("✕ Fail")

            self.compat_table.setItem(row, 2, status_item)
            self.compat_table.setItem(row, 3, QTableWidgetItem(item.message))

        # 2. Container Card
        if probe.container:
            c = probe.container
            c_lines = [
                f"<b>Format:</b> {c.format_name.upper()}",
                f"<b>Size:</b> {format_bytes(c.size_bytes)}",
                f"<b>Duration:</b> {format_duration(c.duration)}",
                f"<b>Bitrate:</b> {int(c.bitrate / 1000)} kbps" if c.bitrate else "<b>Bitrate:</b> N/A",
                f"<b>Total Streams:</b> {c.nb_streams}",
            ]
            self.lbl_container_details.setText("<br>".join(c_lines))

        # 3. Video Card
        if probe.has_video:
            v = probe.primary_video
            v_lines = [
                f"<b>Codec:</b> {v.codec_name.upper()} ({v.profile})",
                f"<b>Resolution:</b> {v.width}x{v.height} ({v.aspect_ratio or 'Standard'})",
                f"<b>Framerate:</b> {v.fps} fps",
                f"<b>Pixel Format:</b> {v.pixel_format} ({'10-bit HDR' if v.is_10bit else '8-bit SDR'})",
                f"<b>Bitrate:</b> {int(v.bitrate / 1000)} kbps" if v.bitrate else "<b>Bitrate:</b> N/A",
            ]
            self.lbl_video_details.setText("<br>".join(v_lines))
        else:
            self.lbl_video_details.setText("<i>No video stream in this file.</i>")

        # 4. Audio Card
        if probe.has_audio:
            a = probe.primary_audio
            a_lines = [
                f"<b>Codec:</b> {a.codec_name.upper()}",
                f"<b>Channels:</b> {a.channels} ({a.channel_layout or 'Stereo'})",
                f"<b>Sample Rate:</b> {a.sample_rate} Hz",
                f"<b>Bitrate:</b> {int(a.bitrate / 1000)} kbps" if a.bitrate else "<b>Bitrate:</b> N/A",
                f"<b>Language:</b> {a.language or 'Default'}",
            ]
            self.lbl_audio_details.setText("<br>".join(a_lines))
        else:
            self.lbl_audio_details.setText("<font color='#f87171'><b>✕ NO AUDIO STREAM (MUTE)</b></font>")

    def _on_inspection_error(self, err: str):
        self.lbl_compat_summary.setText(f"<font color='#f87171'>✕ Inspection error: {err}</font>")
