"""
Command Preview Dialog for inspecting generated yt-dlp and FFmpeg CLI commands.
"""

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CommandPreviewDialog(QDialog):
    """Read-only dialog for inspecting backend commands."""

    def __init__(self, ytdlp_cmd: str, ffmpeg_cmd: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Command Preview (Advanced Inspection)")
        self.resize(700, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Title
        title_lbl = QLabel("Generated Execution Commands")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        layout.addWidget(title_lbl)

        # yt-dlp Section
        layout.addWidget(QLabel("<b>yt-dlp Download Command:</b>"))
        self.txt_ytdlp = QPlainTextEdit(ytdlp_cmd)
        self.txt_ytdlp.setReadOnly(True)
        self.txt_ytdlp.setStyleSheet("background-color: #11131a; font-family: 'Consolas', monospace; font-size: 12px;")
        layout.addWidget(self.txt_ytdlp)

        # FFmpeg Section (if applicable)
        if ffmpeg_cmd:
            layout.addWidget(QLabel("<b>FFmpeg Processing / Transcoding Command:</b>"))
            self.txt_ffmpeg = QPlainTextEdit(ffmpeg_cmd)
            self.txt_ffmpeg.setReadOnly(True)
            self.txt_ffmpeg.setStyleSheet("background-color: #11131a; font-family: 'Consolas', monospace; font-size: 12px;")
            layout.addWidget(self.txt_ffmpeg)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_copy_ytdlp = QPushButton("Copy yt-dlp Command")
        self.btn_copy_ytdlp.clicked.connect(lambda: self._copy(self.txt_ytdlp.toPlainText()))
        btn_layout.addWidget(self.btn_copy_ytdlp)

        if ffmpeg_cmd:
            self.btn_copy_ff = QPushButton("Copy FFmpeg Command")
            self.btn_copy_ff.clicked.connect(lambda: self._copy(self.txt_ffmpeg.toPlainText()))
            btn_layout.addWidget(self.btn_copy_ff)

        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("PrimaryBtn")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def _copy(self, text: str):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)
