"""
First-run setup diagnostics and crash recovery dialog.
"""

from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.dependencies import deps
from app.models.job import DownloadJob


class StartupRecoveryDialog(QDialog):
    """Prompts user on launch if unfinished jobs are detected or dependencies are checked."""

    def __init__(self, interrupted_jobs: List[DownloadJob], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.interrupted_jobs = interrupted_jobs
        self.resume_requested = False

        self.setWindowTitle("Vidora - Session Diagnostics")
        self.resize(560, 360)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("System Readiness & Session Recovery")
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #ffffff;")
        layout.addWidget(title)

        # Dependency Check Box
        dep_frame = QFrame()
        dep_frame.setObjectName("Card")
        dep_layout = QVBoxLayout(dep_frame)
        dep_layout.setSpacing(6)

        statuses = deps.check_all()
        for name, st in statuses.items():
            row = QHBoxLayout()
            lbl_name = QLabel(f"<b>{st.name}:</b>")
            lbl_status = QLabel(f"<font color='{'#22c55e' if st.is_available else '#f87171'}'>{'✓ ' + st.version if st.is_available else '✕ Missing'}</font>")
            lbl_path = QLabel(f"<font color='#8f97aa'>({st.path if st.is_available else st.error_message})</font>")
            lbl_path.setStyleSheet("font-size: 11px;")
            row.addWidget(lbl_name)
            row.addWidget(lbl_status)
            row.addWidget(lbl_path)
            row.addStretch()
            dep_layout.addLayout(row)

        layout.addWidget(dep_frame)

        # Interrupted Jobs Section
        if self.interrupted_jobs:
            rec_frame = QFrame()
            rec_frame.setObjectName("Card")
            rec_layout = QVBoxLayout(rec_frame)

            lbl_rec_title = QLabel(f"<b>Resume Previous Downloads?</b> ({len(self.interrupted_jobs)} incomplete downloads found)")
            lbl_rec_title.setStyleSheet("color: #00d2ff; font-size: 13px;")
            lbl_rec_sub = QLabel("The previous session was closed or interrupted. Partial files (.part) are preserved.")
            lbl_rec_sub.setObjectName("MutedText")

            rec_layout.addWidget(lbl_rec_title)
            rec_layout.addWidget(lbl_rec_sub)
            layout.addWidget(rec_frame)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if self.interrupted_jobs:
            self.btn_ignore = QPushButton("Ignore")
            self.btn_ignore.clicked.connect(self._on_ignore)
            btn_layout.addWidget(self.btn_ignore)

            self.btn_resume = QPushButton(f"Resume All ({len(self.interrupted_jobs)})")
            self.btn_resume.setObjectName("PrimaryBtn")
            self.btn_resume.clicked.connect(self._on_resume)
            btn_layout.addWidget(self.btn_resume)
        else:
            self.btn_continue = QPushButton("Continue to Dashboard")
            self.btn_continue.setObjectName("PrimaryBtn")
            self.btn_continue.clicked.connect(self.accept)
            btn_layout.addWidget(self.btn_continue)

        layout.addLayout(btn_layout)

    def _on_resume(self):
        self.resume_requested = True
        self.accept()

    def _on_ignore(self):
        self.resume_requested = False
        self.accept()
