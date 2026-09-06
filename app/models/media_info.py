"""
Data models representing deep media stream inspection from FFprobe.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VideoStreamInfo:
    index: int
    codec_name: str
    codec_long_name: str = ""
    profile: str = ""
    level: Optional[int] = None
    width: int = 0
    height: int = 0
    fps: float = 0.0
    pixel_format: str = ""
    bitrate: Optional[int] = None
    duration: Optional[float] = None
    nb_frames: Optional[int] = None
    aspect_ratio: str = ""
    color_space: str = ""
    is_hdr: bool = False
    is_10bit: bool = False


@dataclass
class AudioStreamInfo:
    index: int
    codec_name: str
    codec_long_name: str = ""
    channels: int = 0
    channel_layout: str = ""
    sample_rate: int = 0
    bitrate: Optional[int] = None
    duration: Optional[float] = None
    language: str = ""


@dataclass
class ContainerInfo:
    format_name: str
    format_long_name: str = ""
    duration: float = 0.0
    size_bytes: int = 0
    bitrate: int = 0
    nb_streams: int = 0
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class MediaProbeResult:
    file_path: str
    is_valid: bool
    container: Optional[ContainerInfo] = None
    video_streams: list[VideoStreamInfo] = field(default_factory=list)
    audio_streams: list[AudioStreamInfo] = field(default_factory=list)
    error_message: Optional[str] = None
    raw_data: dict = field(default_factory=dict)

    @property
    def has_video(self) -> bool:
        return len(self.video_streams) > 0

    @property
    def has_audio(self) -> bool:
        return len(self.audio_streams) > 0

    @property
    def primary_video(self) -> Optional[VideoStreamInfo]:
        return self.video_streams[0] if self.video_streams else None

    @property
    def primary_audio(self) -> Optional[AudioStreamInfo]:
        return self.audio_streams[0] if self.audio_streams else None
