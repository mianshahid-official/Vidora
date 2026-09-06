"""
Data models representing download and conversion jobs.
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from app.core.constants import JobStatus, QualityPreset, OutputContainer
from app.models.format_info import MediaMetadata
from app.models.validation_result import ValidationReport


@dataclass
class DownloadJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    title: str = "Initializing..."
    thumbnail_url: str = ""
    uploader: str = ""
    platform: str = "Unknown"
    duration: float = 0.0

    # Format & Profile Selection
    quality_preset: QualityPreset = QualityPreset.UNIVERSAL_MP4
    target_container: str = "mp4"
    selected_format_id: Optional[str] = None
    selected_video_format_id: Optional[str] = None
    selected_audio_format_id: Optional[str] = None
    is_audio_only: bool = False
    is_video_only: bool = False
    resolution: str = "Best Available"
    fps: Optional[float] = None
    custom_ffmpeg_args: list[str] = field(default_factory=list)

    # Destination paths
    destination_dir: str = ""
    output_filename: str = ""
    final_file_path: Optional[str] = None
    temp_file_path: Optional[str] = None

    # State & Progress
    status: JobStatus = JobStatus.QUEUED
    progress_percent: float = 0.0
    downloaded_bytes: int = 0
    total_bytes: int = 0
    speed_bytes_per_sec: float = 0.0
    eta_seconds: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # Encoding / Transcoding Progress
    encoding_percent: float = 0.0
    encoding_fps: float = 0.0
    encoding_speed: float = 0.0

    # Retry & Diagnostics
    retry_count: int = 0
    max_retries: int = 5
    error_message: Optional[str] = None
    last_log_snippet: str = ""
    audio_detected: bool = False
    video_detected: bool = False
    validation_report: Optional[ValidationReport] = None
    metadata: Optional[MediaMetadata] = None

    # Control flags
    is_paused: bool = False
    is_cancelled: bool = False

    @property
    def display_size(self) -> str:
        size = self.total_bytes or self.downloaded_bytes
        if size <= 0:
            return "Calculating..."
        if size >= 1024 * 1024 * 1024:
            return f"{size / (1024**3):.2f} GB"
        if size >= 1024 * 1024:
            return f"{size / (1024**2):.1f} MB"
        return f"{size / 1024:.0f} KB"

    @property
    def display_speed(self) -> str:
        if self.status != JobStatus.DOWNLOADING or self.speed_bytes_per_sec <= 0:
            return ""
        if self.speed_bytes_per_sec >= 1024 * 1024:
            return f"{self.speed_bytes_per_sec / (1024**2):.2f} MB/s"
        return f"{self.speed_bytes_per_sec / 1024:.0f} KB/s"

    @property
    def display_eta(self) -> str:
        if self.status != JobStatus.DOWNLOADING or self.eta_seconds is None or self.eta_seconds < 0:
            return ""
        m, s = divmod(self.eta_seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}h {m:02d}m"
        return f"{m:02d}m {s:02d}s"


@dataclass
class ConvertJob:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    input_file_path: str = ""
    output_file_path: str = ""
    preset_id: str = "audio_mp3_320k"
    target_container: str = "mp3"
    status: JobStatus = JobStatus.QUEUED
    progress_percent: float = 0.0
    current_fps: float = 0.0
    current_speed: float = 0.0
    eta_seconds: Optional[int] = None
    error_message: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    is_paused: bool = False
    is_cancelled: bool = False

    # Trimming options
    trim_enabled: bool = False
    trim_start: str = "00:00:00"
    trim_end: str = ""
    audio_bitrate: str = "320k"

    @property
    def source_path(self) -> str:
        return self.input_file_path

    @source_path.setter
    def source_path(self, val: str):
        self.input_file_path = val

    @property
    def output_path(self) -> str:
        return self.output_file_path

    @output_path.setter
    def output_path(self, val: str):
        self.output_file_path = val
