"""
Application-wide constants, enums, and default configurations.
"""

from enum import Enum
from pathlib import Path

# Application Metadata
APP_NAME = "Vidora"
APP_VERSION = "1.0.0"
APP_ORGANIZATION = "Vidora"
APP_ID = "com.vidora.media"

# Default Paths
DEFAULT_DOWNLOADS_DIR = (Path.home() / "Downloads").resolve()
DEFAULT_TEMP_DIR = (Path("config") / "temp").resolve()
DEFAULT_CONFIG_DIR = Path("config").resolve()
DEFAULT_LOGS_DIR = Path("logs").resolve()
DEFAULT_DB_PATH = (Path("config") / "downloader.db").resolve()


class JobStatus(str, Enum):
    QUEUED = "Queued"
    FETCHING_METADATA = "Fetching Metadata"
    DOWNLOADING = "Downloading"
    PAUSED = "Paused"
    MERGING = "Merging"
    ENCODING = "Encoding"
    VALIDATING = "Validating"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    INTERRUPTED = "Interrupted"


class QualityPreset(str, Enum):
    UNIVERSAL_MP4 = "Universal MP4 (H.264 / AAC)"
    BEST_QUALITY = "Best Quality (Original)"
    BALANCED = "Balanced MP4"
    MAXIMUM_COMPATIBILITY = "Maximum Compatibility"
    AUDIO_ONLY = "Audio Only (MP3)"
    CUSTOM = "Custom"
    # Alias for legacy compatibility
    TV_LCD_COMPATIBLE = "Universal MP4 (H.264 / AAC)"


class OutputContainer(str, Enum):
    MP4 = "mp4"
    MKV = "mkv"
    WEBM = "webm"
    ORIGINAL = "original"
    MP3 = "mp3"
    M4A = "m4a"
    AAC = "aac"
    WAV = "wav"
    FLAC = "flac"
    OPUS = "opus"


class CompatibilityLevel(str, Enum):
    COMPATIBLE = "Compatible"
    PROBABLY_COMPATIBLE = "Probably Compatible"
    POTENTIALLY_INCOMPATIBLE = "Potentially Incompatible"
    INCOMPATIBLE = "Incompatible"
    UNKNOWN = "Unknown"


class VideoCodec(str, Enum):
    H264 = "h264"
    H265 = "hevc"
    VP9 = "vp9"
    AV1 = "av1"
    VP8 = "vp8"
    OTHER = "other"


class AudioCodec(str, Enum):
    AAC = "aac"
    MP3 = "mp3"
    OPUS = "opus"
    VORBIS = "vorbis"
    FLAC = "flac"
    PCM = "pcm"
    AC3 = "ac3"
    EAC3 = "eac3"
    OTHER = "other"


class DuplicateAction(str, Enum):
    SKIP = "skip"
    RENAME = "rename"
    OVERWRITE = "overwrite"
    ASK = "ask"


class FilenameTemplatePreset(str, Enum):
    TITLE = "%(title)s.%(ext)s"
    TITLE_UPLOADER = "%(title)s - %(uploader)s.%(ext)s"
    UPLOADER_TITLE = "%(uploader)s - %(title)s.%(ext)s"
    DATE_TITLE = "%(upload_date)s - %(title)s.%(ext)s"
    ID_TITLE = "%(id)s - %(title)s.%(ext)s"


# Standard Resolutions
RESOLUTIONS = [
    "Best Available",
    "2160p (4K)",
    "1440p (2K)",
    "1080p (FHD)",
    "720p (HD)",
    "480p (SD)",
    "360p",
    "240p",
]

# Audio Bitrates
AUDIO_BITRATES = [
    "320 kbps (High Quality)",
    "256 kbps (Standard)",
    "192 kbps (Good)",
    "128 kbps (Compact)",
    "64 kbps (Low)",
]

# Speed limits in bytes per second
SPEED_LIMIT_PRESETS = {
    "Unlimited": 0,
    "500 KB/s": 500 * 1024,
    "1 MB/s": 1024 * 1024,
    "2 MB/s": 2 * 1024 * 1024,
    "5 MB/s": 5 * 1024 * 1024,
    "10 MB/s": 10 * 1024 * 1024,
    "20 MB/s": 20 * 1024 * 1024,
}

# Concurrency choices
CONCURRENCY_CHOICES = [1, 2, 3, 4, 5, 6, 8, 10]
DEFAULT_CONCURRENCY = 3
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_BACKOFF_BASE = 2.0  # seconds
