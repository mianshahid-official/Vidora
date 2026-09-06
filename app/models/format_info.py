"""
Data models representing stream formats extracted from yt-dlp.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FormatItem:
    """Represents a single available stream format from an extractor."""
    format_id: str
    ext: str
    resolution: str = "Audio Only"
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    vcodec: str = "none"
    acodec: str = "none"
    abr: Optional[float] = None  # audio bitrate in kbps
    vbr: Optional[float] = None  # video bitrate in kbps
    tbr: Optional[float] = None  # total bitrate in kbps
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    format_note: str = ""
    dynamic_range: Optional[str] = None  # HDR, SDR
    has_video: bool = False
    has_audio: bool = False
    is_combined: bool = False
    protocol: str = ""
    container: str = ""
    aspect_ratio: Optional[float] = None

    @property
    def stream_type_label(self) -> str:
        if self.has_video and self.has_audio:
            return "VIDEO + AUDIO"
        elif self.has_video:
            return "VIDEO ONLY"
        elif self.has_audio:
            return "AUDIO ONLY"
        return "UNKNOWN"

    @property
    def display_size(self) -> str:
        size = self.filesize or self.filesize_approx
        if not size or size <= 0:
            return "N/A"
        if size >= 1024 * 1024 * 1024:
            return f"{size / (1024**3):.2f} GB"
        if size >= 1024 * 1024:
            return f"{size / (1024**2):.1f} MB"
        return f"{size / 1024:.0f} KB"

    @property
    def display_bitrate(self) -> str:
        br = self.tbr or self.vbr or self.abr
        if br and br > 0:
            return f"{int(br)}k"
        return "N/A"


@dataclass
class MediaMetadata:
    """Represents high-level metadata extracted from a URL before downloading."""
    url: str
    extractor: str
    extractor_key: str
    id: str
    title: str
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    uploader: Optional[str] = None
    uploader_id: Optional[str] = None
    channel: Optional[str] = None
    upload_date: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    description: Optional[str] = None
    webpage_url: Optional[str] = None
    is_live: bool = False
    is_playlist: bool = False
    playlist_count: Optional[int] = None
    formats: list[FormatItem] = field(default_factory=list)
    raw_info: dict = field(default_factory=dict)
