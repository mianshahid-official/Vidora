"""
Application settings configuration model.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.core.constants import (
    DEFAULT_CONCURRENCY,
    DEFAULT_MAX_RETRIES,
    DuplicateAction,
    FilenameTemplatePreset,
    QualityPreset,
)


@dataclass
class AppSettings:
    # Directories
    downloads_dir: str = str((Path.home() / "Downloads").resolve())
    temp_dir: str = str((Path("config") / "temp").resolve())
    custom_ffmpeg_dir: str = ""

    # Concurrency and Network
    max_concurrent_downloads: int = DEFAULT_CONCURRENCY
    max_retries: int = DEFAULT_MAX_RETRIES
    speed_limit_bytes: int = 0  # 0 = unlimited
    user_agent: str = ""
    proxy_url: str = ""
    use_cookies: bool = False
    cookies_source: str = "none"  # "chrome", "firefox", "edge", "file", "none"
    cookies_file_path: str = ""

    # Default Formats & Quality
    default_quality_preset: str = QualityPreset.TV_LCD_COMPATIBLE.value
    default_container: str = "mp4"
    default_resolution: str = "Best Available"
    default_audio_quality: str = "320 kbps (High Quality)"

    # Organization & Naming
    filename_template: str = FilenameTemplatePreset.TITLE.value
    duplicate_action: str = DuplicateAction.RENAME.value
    folder_organization: str = "single"  # "single", "platform", "uploader", "date"

    # UI Preferences
    theme_mode: str = "dark"  # "dark" or "light"
    show_command_preview: bool = False
    auto_resume_previous_jobs: bool = True
    auto_check_ytdlp_updates: bool = True
    warn_low_disk_space: bool = True
    min_free_disk_space_gb: float = 2.0
