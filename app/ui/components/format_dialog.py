"""
Format Selection Dialog for detailed stream inspection and selection.
"""

from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models.format_info import FormatItem, MediaMetadata


class FormatDialog(QDialog):
    """Rich table format selector dialog."""

    def __init__(self, metadata: MediaMetadata, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.metadata = metadata
        self.selected_format: Optional[FormatItem] = None
        self.radio_buttons: list[QRadioButton] = []

        self.setWindowTitle(f"Available Formats - {metadata.title[:50]}")
        self.resize(960, 520)

        self._setup_ui()
        self._populate_table(self.metadata.formats)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Info
        header_layout = QHBoxLayout()
        title_lbl = QLabel(f"<b>Title:</b> {self.metadata.title}")
        title_lbl.setStyleSheet("font-size: 14px; color: #ffffff;")
        header_layout.addWidget(title_lbl)
        layout.addLayout(header_layout)

        # Filter buttons
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))

        self.btn_all = QPushButton("All Formats")
        self.btn_all.setCheckable(True)
        self.btn_all.setChecked(True)
        self.btn_all.clicked.connect(lambda: self._filter_formats("all"))

        self.btn_combined = QPushButton("Video + Audio")
        self.btn_combined.setCheckable(True)
        self.btn_combined.clicked.connect(lambda: self._filter_formats("combined"))

        self.btn_video = QPushButton("Video Only")
        self.btn_video.setCheckable(True)
        self.btn_video.clicked.connect(lambda: self._filter_formats("video"))

        self.btn_audio = QPushButton("Audio Only")
        self.btn_audio.setCheckable(True)
        self.btn_audio.clicked.connect(lambda: self._filter_formats("audio"))

        self.filter_group = QButtonGroup(self)
        self.filter_group.addButton(self.btn_all)
        self.filter_group.addButton(self.btn_combined)
        self.filter_group.addButton(self.btn_video)
        self.filter_group.addButton(self.btn_audio)

        filter_layout.addWidget(self.btn_all)
        filter_layout.addWidget(self.btn_combined)
        filter_layout.addWidget(self.btn_video)
        filter_layout.addWidget(self.btn_audio)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Select", "ID", "Type", "Resolution", "FPS",
            "Video Codec", "Audio Codec", "Bitrate", "Est. Size", "Container", "Note"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self._on_cell_clicked)
        layout.addWidget(self.table)

        # Bottom Buttons
        btn_box = QHBoxLayout()
        self.info_lbl = QLabel("Select a format stream above. If video-only is selected, best compatible audio will be automatically merged.")
        self.info_lbl.setObjectName("MutedText")
        btn_box.addWidget(self.info_lbl)
        btn_box.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_select = QPushButton("Select Format")
        self.btn_select.setObjectName("PrimaryBtn")
        self.btn_select.clicked.connect(self.accept)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_select)
        layout.addLayout(btn_box)

    def _filter_formats(self, mode: str):
        if mode == "combined":
            fmts = [f for f in self.metadata.formats if f.has_video and f.has_audio]
        elif mode == "video":
            fmts = [f for f in self.metadata.formats if f.has_video and not f.has_audio]
        elif mode == "audio":
            fmts = [f for f in self.metadata.formats if f.has_audio and not f.has_video]
        else:
            fmts = self.metadata.formats
        self._populate_table(fmts)

    def _populate_table(self, formats: List[FormatItem]):
        self.table.setRowCount(len(formats))
        self.displayed_formats = formats
        self.radio_buttons.clear()

        for row, fmt in enumerate(formats):
            # Radio button
            radio = QRadioButton()
            radio.clicked.connect(lambda checked, r=row: self._select_row(r))
            self.radio_buttons.append(radio)

            radio_widget = QWidget()
            radio_layout = QHBoxLayout(radio_widget)
            radio_layout.addWidget(radio)
            radio_layout.setAlignment(Qt.AlignCenter)
            radio_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 0, radio_widget)

            # Columns
            self.table.setItem(row, 1, QTableWidgetItem(fmt.format_id))

            # Stream type styling
            type_item = QTableWidgetItem(fmt.stream_type_label)
            if fmt.is_combined:
                type_item.setForeground(Qt.green)
            elif fmt.has_video:
                type_item.setForeground(Qt.cyan)
            else:
                type_item.setForeground(Qt.yellow)
            self.table.setItem(row, 2, type_item)

            self.table.setItem(row, 3, QTableWidgetItem(fmt.resolution))
            self.table.setItem(row, 4, QTableWidgetItem(f"{fmt.fps:.0f}" if fmt.fps else "-"))
            self.table.setItem(row, 5, QTableWidgetItem(fmt.vcodec))
            self.table.setItem(row, 6, QTableWidgetItem(fmt.acodec))
            self.table.setItem(row, 7, QTableWidgetItem(fmt.display_bitrate))
            self.table.setItem(row, 8, QTableWidgetItem(fmt.display_size))
            self.table.setItem(row, 9, QTableWidgetItem(fmt.ext.upper()))
            self.table.setItem(row, 10, QTableWidgetItem(fmt.format_note or fmt.dynamic_range or ""))

        if formats:
            self._select_row(0)

    def _on_cell_clicked(self, row: int, col: int):
        self._select_row(row)

    def _select_row(self, row: int):
        if 0 <= row < len(self.displayed_formats):
            self.selected_format = self.displayed_formats[row]
            for i, r in enumerate(self.radio_buttons):
                r.setChecked(i == row)
            self.table.selectRow(row)
