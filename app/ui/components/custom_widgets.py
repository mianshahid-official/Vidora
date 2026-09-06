"""
Custom PySide6 reusable UI components (Badges, Stat Cards, Drag & Drop Zones).
"""

from typing import Callable, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.core.constants import CompatibilityLevel, JobStatus


class StatusBadge(QLabel):
    """Pill badge showing job status with appropriate theme color."""

    COLOR_MAP = {
        JobStatus.COMPLETED.value: ("#052e16", "#22c55e", "#15803d"),
        JobStatus.DOWNLOADING.value: ("#082f49", "#00d2ff", "#0369a1"),
        JobStatus.ENCODING.value: ("#2e1065", "#c084fc", "#7e22ce"),
        JobStatus.MERGING.value: ("#172554", "#60a5fa", "#1d4ed8"),
        JobStatus.VALIDATING.value: ("#3b0764", "#e879f9", "#a21caf"),
        JobStatus.QUEUED.value: ("#1f2937", "#9ca3af", "#4b5563"),
        JobStatus.PAUSED.value: ("#451a03", "#fbbf24", "#b45309"),
        JobStatus.FAILED.value: ("#450a0a", "#f87171", "#b91c1c"),
        JobStatus.CANCELLED.value: ("#1c1917", "#a8a29e", "#57534e"),
        JobStatus.FETCHING_METADATA.value: ("#082f49", "#38bdf8", "#0284c7"),
    }

    def __init__(self, status_text: str = "Queued", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(22)
        self.set_status(status_text)

    def set_status(self, status: str):
        self.setText(f" {status} ")
        bg, fg, border = self.COLOR_MAP.get(status, ("#1f2937", "#9ca3af", "#4b5563"))
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 11px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)


class CompatibilityBadge(QLabel):
    """Pill badge showing hardware/media compatibility verdict."""

    LEVEL_MAP = {
        CompatibilityLevel.COMPATIBLE: ("#052e16", "#22c55e", "✓ Universal Compatible"),
        CompatibilityLevel.PROBABLY_COMPATIBLE: ("#172554", "#60a5fa", "✓ Probably Compatible"),
        CompatibilityLevel.POTENTIALLY_INCOMPATIBLE: ("#451a03", "#fbbf24", "⚠ Potential Issue"),
        CompatibilityLevel.INCOMPATIBLE: ("#450a0a", "#f87171", "✕ Incompatible"),
    }

    def __init__(self, level: CompatibilityLevel = CompatibilityLevel.UNKNOWN, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(24)
        self.set_level(level)

    def set_level(self, level: CompatibilityLevel):
        bg, fg, text = self.LEVEL_MAP.get(level, ("#1f2937", "#9ca3af", "Unknown"))
        self.setText(f"  {text}  ")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg};
                color: {fg};
                border: 1px solid {fg};
                border-radius: 12px;
                padding: 2px 12px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)


class StatCard(QFrame):
    """Modern dashboard stat card showing key metrics."""

    def __init__(self, title: str, initial_value: str = "0", icon_char: str = "📊", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFixedHeight(95)
        self.setStyleSheet("QFrame#Card { background-color: #171a25; border: 1px solid #242a3c; border-radius: 12px; }")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # Text side
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        self.title_lbl = QLabel(title.upper())
        self.title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; letter-spacing: 0.5px; color: #8f97aa; background: transparent;")

        self.val_lbl = QLabel(initial_value)
        self.val_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #ffffff; background: transparent; padding-bottom: 2px;")

        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.val_lbl)
        layout.addLayout(text_layout, 1)

        # Icon side
        self.icon_lbl = QLabel(icon_char)
        self.icon_lbl.setStyleSheet("font-size: 24px; color: #00d2ff; background: transparent;")
        layout.addWidget(self.icon_lbl, alignment=Qt.AlignRight | Qt.AlignVCenter)

    def set_value(self, value: str):
        self.val_lbl.setText(value)


class DragDropZone(QFrame):
    """Interactive drag and drop target area for files."""

    files_dropped = Signal(list)  # list of file path strings

    def __init__(self, title: str = "Drag & Drop Media Files Here", subtitle: str = "or click to select files", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName("Card")
        self.setMinimumHeight(130)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)

        self.icon_lbl = QLabel("📁")
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        self.icon_lbl.setStyleSheet("font-size: 32px; color: #00d2ff;")

        self.title_lbl = QLabel(title)
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #ffffff;")

        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setAlignment(Qt.AlignCenter)
        self.sub_lbl.setObjectName("MutedText")

        layout.addWidget(self.icon_lbl)
        layout.addWidget(self.title_lbl)
        layout.addWidget(self.sub_lbl)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet("QFrame#Card { border: 2px dashed #00d2ff; background-color: #1e2536; }")

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet("")
        files = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                files.append(url.toLocalFile())
        if files:
            self.files_dropped.emit(files)
