"""
Application Settings View: Paths, Concurrency, Naming Templates, Network, Cookies, and Dependencies.
"""

from pathlib import Path
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.config import config_manager
from app.core.constants import (
    CONCURRENCY_CHOICES,
    DuplicateAction,
    FilenameTemplatePreset,
    QualityPreset,
)
from app.core.dependencies import deps
from app.models.settings_model import AppSettings


class SettingsView(QWidget):
    """Configuration and preferences management view."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()
        self.load_from_config()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        # Header Title
        title_row = QHBoxLayout()
        title_lbl = QLabel("Settings & Preferences")
        title_lbl.setObjectName("Heading1")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        self.btn_save = QPushButton("💾 Save Settings")
        self.btn_save.setObjectName("PrimaryBtn")
        self.btn_save.clicked.connect(self.save_to_config)
        title_row.addWidget(self.btn_save)

        main_layout.addLayout(title_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        container = QWidget()
        container.setObjectName("scrollAreaWidgetContents")
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(16)

        # 1. Directory Settings Card
        dir_card = QFrame()
        dir_card.setObjectName("Card")
        dc_layout = QVBoxLayout(dir_card)
        dc_layout.setSpacing(12)

        lbl_dir_title = QLabel("📁 Storage & Directories")
        lbl_dir_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        dc_layout.addWidget(lbl_dir_title)

        # Downloads Dir
        dc_layout.addWidget(QLabel("Download Folder:"))
        row_dl = QHBoxLayout()
        self.txt_downloads_dir = QLineEdit()
        self.btn_browse_dl = QPushButton("Browse...")
        self.btn_browse_dl.clicked.connect(self._browse_downloads_dir)
        row_dl.addWidget(self.txt_downloads_dir)
        row_dl.addWidget(self.btn_browse_dl)
        dc_layout.addLayout(row_dl)

        # Temp Dir
        dc_layout.addWidget(QLabel("Temporary Download / Part Files Folder:"))
        row_tmp = QHBoxLayout()
        self.txt_temp_dir = QLineEdit()
        self.btn_browse_tmp = QPushButton("Browse...")
        self.btn_browse_tmp.clicked.connect(self._browse_temp_dir)
        row_tmp.addWidget(self.txt_temp_dir)
        row_tmp.addWidget(self.btn_browse_tmp)
        dc_layout.addLayout(row_tmp)

        layout.addWidget(dir_card)

        # 2. Filename & Naming Template Card
        name_card = QFrame()
        name_card.setObjectName("Card")
        nc_layout = QVBoxLayout(name_card)
        nc_layout.setSpacing(12)

        lbl_name_title = QLabel("🏷 Filename & Duplicate Handling")
        lbl_name_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        nc_layout.addWidget(lbl_name_title)

        row_tmpl = QHBoxLayout()
        vbox_tmpl = QVBoxLayout()
        vbox_tmpl.addWidget(QLabel("Filename Template:"))
        self.cmb_template = QComboBox()
        self.cmb_template.addItem("Title only (%(title)s.%(ext)s)", FilenameTemplatePreset.TITLE.value)
        self.cmb_template.addItem("Title - Uploader (%(title)s - %(uploader)s.%(ext)s)", FilenameTemplatePreset.TITLE_UPLOADER.value)
        self.cmb_template.addItem("Uploader - Title (%(uploader)s - %(title)s.%(ext)s)", FilenameTemplatePreset.UPLOADER_TITLE.value)
        self.cmb_template.addItem("Date - Title (%(upload_date)s - %(title)s.%(ext)s)", FilenameTemplatePreset.DATE_TITLE.value)
        vbox_tmpl.addWidget(self.cmb_template)
        row_tmpl.addLayout(vbox_tmpl)

        vbox_dup = QVBoxLayout()
        vbox_dup.addWidget(QLabel("When file already exists in destination:"))
        self.cmb_dup = QComboBox()
        self.cmb_dup.addItem("Rename with (1), (2)...", DuplicateAction.RENAME.value)
        self.cmb_dup.addItem("Skip existing file", DuplicateAction.SKIP.value)
        self.cmb_dup.addItem("Overwrite existing file", DuplicateAction.OVERWRITE.value)
        vbox_dup.addWidget(self.cmb_dup)
        row_tmpl.addLayout(vbox_dup)

        nc_layout.addLayout(row_tmpl)
        layout.addWidget(name_card)

        # 3. Network & Concurrency Card
        net_card = QFrame()
        net_card.setObjectName("Card")
        net_layout = QVBoxLayout(net_card)
        net_layout.setSpacing(12)

        lbl_net_title = QLabel("⚡ Network, Retries & Concurrency")
        lbl_net_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        net_layout.addWidget(lbl_net_title)

        row_net = QHBoxLayout()
        vbox_conc = QVBoxLayout()
        vbox_conc.addWidget(QLabel("Max Concurrent Downloads:"))
        self.cmb_concurrency = QComboBox()
        for c in CONCURRENCY_CHOICES:
            self.cmb_concurrency.addItem(str(c), c)
        vbox_conc.addWidget(self.cmb_concurrency)
        row_net.addLayout(vbox_conc)

        vbox_retries = QVBoxLayout()
        vbox_retries.addWidget(QLabel("Max Automatic Retries:"))
        self.spn_retries = QSpinBox()
        self.spn_retries.setRange(1, 20)
        self.spn_retries.setValue(5)
        vbox_retries.addWidget(self.spn_retries)
        row_net.addLayout(vbox_retries)

        net_layout.addLayout(row_net)

        # Proxy and User-Agent
        row_proxy = QHBoxLayout()
        vbox_p = QVBoxLayout()
        vbox_p.addWidget(QLabel("Proxy URL (optional):"))
        self.txt_proxy = QLineEdit()
        self.txt_proxy.setPlaceholderText("http://user:pass@127.0.0.1:8080 or socks5://...")
        vbox_p.addWidget(self.txt_proxy)
        row_proxy.addLayout(vbox_p)

        vbox_ua = QVBoxLayout()
        vbox_ua.addWidget(QLabel("Custom User-Agent (optional):"))
        self.txt_ua = QLineEdit()
        self.txt_ua.setPlaceholderText("Mozilla/5.0 (Windows NT 10.0; Win64; x64)...")
        vbox_ua.addWidget(self.txt_ua)
        row_proxy.addLayout(vbox_ua)

        net_layout.addLayout(row_proxy)
        layout.addWidget(net_card)

        # 4. Authentication & Cookies Card
        cookie_card = QFrame()
        cookie_card.setObjectName("Card")
        ck_layout = QVBoxLayout(cookie_card)
        ck_layout.setSpacing(12)

        lbl_ck_title = QLabel("🍪 Authentication & Cookies")
        lbl_ck_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        ck_layout.addWidget(lbl_ck_title)

        self.chk_use_cookies = QCheckBox("Enable Browser / File Cookies for Authenticated Sites")
        ck_layout.addWidget(self.chk_use_cookies)

        row_ck = QHBoxLayout()
        self.cmb_cookie_src = QComboBox()
        self.cmb_cookie_src.addItem("None", "none")
        self.cmb_cookie_src.addItem("Import from Chrome Browser", "chrome")
        self.cmb_cookie_src.addItem("Import from Firefox Browser", "firefox")
        self.cmb_cookie_src.addItem("Import from Edge Browser", "edge")
        self.cmb_cookie_src.addItem("Custom cookies.txt File", "file")
        row_ck.addWidget(self.cmb_cookie_src)

        self.txt_cookie_file = QLineEdit()
        self.txt_cookie_file.setPlaceholderText("Path to cookies.txt file...")
        self.btn_browse_cookie = QPushButton("Browse...")
        self.btn_browse_cookie.clicked.connect(self._browse_cookie_file)
        row_ck.addWidget(self.txt_cookie_file)
        row_ck.addWidget(self.btn_browse_cookie)
        ck_layout.addLayout(row_ck)

        lbl_ck_notice = QLabel("🔒 <b>Security Note:</b> Cookies and credentials are never written to logs or displayed in the user interface.")
        lbl_ck_notice.setObjectName("MutedText")
        ck_layout.addWidget(lbl_ck_notice)

        layout.addWidget(cookie_card)

        # 5. External Dependencies Card
        dep_card = QFrame()
        dep_card.setObjectName("Card")
        dp_layout = QVBoxLayout(dep_card)
        dp_layout.setSpacing(12)

        lbl_dep_title = QLabel("⚙ External Dependencies & Engine")
        lbl_dep_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        dp_layout.addWidget(lbl_dep_title)

        self.lbl_dep_status = QLabel("Checking dependency status...")
        dp_layout.addWidget(self.lbl_dep_status)

        row_dep_btns = QHBoxLayout()
        self.btn_check_deps = QPushButton("🔍 Auto-Detect Dependencies")
        self.btn_check_deps.clicked.connect(self._refresh_dep_status)
        row_dep_btns.addWidget(self.btn_check_deps)

        self.btn_update_ytdlp = QPushButton("⬆ Check & Update yt-dlp")
        self.btn_update_ytdlp.clicked.connect(self._update_ytdlp)
        row_dep_btns.addWidget(self.btn_update_ytdlp)
        row_dep_btns.addStretch()
        dp_layout.addLayout(row_dep_btns)

        layout.addWidget(dep_card)

        layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

        self._refresh_dep_status()

    def load_from_config(self):
        st = config_manager.settings
        self.txt_downloads_dir.setText(st.downloads_dir)
        self.txt_temp_dir.setText(st.temp_dir)
        self.cmb_concurrency.setCurrentText(str(st.max_concurrent_downloads))
        self.spn_retries.setValue(st.max_retries)
        self.txt_proxy.setText(st.proxy_url)
        self.txt_ua.setText(st.user_agent)
        self.chk_use_cookies.setChecked(st.use_cookies)
        self.txt_cookie_file.setText(st.cookies_file_path)

        # Template
        idx = self.cmb_template.findData(st.filename_template)
        if idx >= 0:
            self.cmb_template.setCurrentIndex(idx)

        # Duplicate
        d_idx = self.cmb_dup.findData(st.duplicate_action)
        if d_idx >= 0:
            self.cmb_dup.setCurrentIndex(d_idx)

        # Cookie Source
        c_idx = self.cmb_cookie_src.findData(st.cookies_source)
        if c_idx >= 0:
            self.cmb_cookie_src.setCurrentIndex(c_idx)

    def save_to_config(self):
        st = config_manager.settings
        st.downloads_dir = self.txt_downloads_dir.text().strip()
        st.temp_dir = self.txt_temp_dir.text().strip()
        st.max_concurrent_downloads = self.cmb_concurrency.currentData()
        st.max_retries = self.spn_retries.value()
        st.proxy_url = self.txt_proxy.text().strip()
        st.user_agent = self.txt_ua.text().strip()
        st.use_cookies = self.chk_use_cookies.isChecked()
        st.cookies_source = self.cmb_cookie_src.currentData()
        st.cookies_file_path = self.txt_cookie_file.text().strip()
        st.filename_template = self.cmb_template.currentData()
        st.duplicate_action = self.cmb_dup.currentData()

        config_manager.update_settings(st)
        QMessageBox.information(self, "Settings Saved", "Settings and preferences have been updated successfully.")

    def _browse_downloads_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Default Downloads Folder", self.txt_downloads_dir.text())
        if folder:
            self.txt_downloads_dir.setText(folder)

    def _browse_temp_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Temporary Folder", self.txt_temp_dir.text())
        if folder:
            self.txt_temp_dir.setText(folder)

    def _browse_cookie_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Cookies File", "", "Cookie Files (*.txt *.cookies);;All Files (*)")
        if file_path:
            self.txt_cookie_file.setText(file_path)
            self.cmb_cookie_src.setCurrentIndex(self.cmb_cookie_src.findData("file"))

    def _refresh_dep_status(self):
        status_dict = deps.check_all()
        lines = []
        for name, s in status_dict.items():
            color = "#22c55e" if s.is_available else "#f87171"
            sym = "✓" if s.is_available else "✕"
            lines.append(f"<b>{s.name}:</b> <font color='{color}'>{sym} {s.version}</font> ({s.path or s.error_message})")
        self.lbl_dep_status.setText("<br>".join(lines))

    def _update_ytdlp(self):
        self.btn_update_ytdlp.setEnabled(False)
        self.lbl_dep_status.setText("Checking and updating yt-dlp...")
        success, msg = deps.update_ytdlp()
        self.btn_update_ytdlp.setEnabled(True)
        self._refresh_dep_status()
        QMessageBox.information(self, "yt-dlp Update", msg)
