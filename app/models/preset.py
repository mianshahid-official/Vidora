"""
Encoding and output presets configuration models.
"""

from dataclasses import dataclass
from typing import Optional
from app.core.constants import OutputContainer, QualityPreset


@dataclass
class TranscodePreset:
    id: str
    name: str
    description: str
    container: OutputContainer
    video_codec: str  # libx264, libx265, copy, none
    audio_codec: str  # aac, libmp3lame, copy, none
    pixel_format: Optional[str] = "yuv420p"
    crf: Optional[int] = 20
    preset_speed: str = "medium"
    audio_bitrate: str = "192k"
    audio_sample_rate: Optional[int] = 48000
    extra_ffmpeg_args: list[str] = None
    scale_height: Optional[int] = None  # 1080, 720, etc.

    def __post_init__(self):
        if self.extra_ffmpeg_args is None:
            self.extra_ffmpeg_args = []

    @property
    def is_audio_only(self) -> bool:
        return self.video_codec in ("none", "") or self.container in (
            OutputContainer.MP3, OutputContainer.M4A, OutputContainer.WAV,
            OutputContainer.FLAC, OutputContainer.OGG, OutputContainer.OPUS
        )


# Pre-built standard presets
BUILTIN_PRESETS = [
    TranscodePreset(
        id="universal_mp4",
        name="Universal MP4 (H.264 / AAC)",
        description="Standard MP4 (H.264 + AAC + yuv420p + faststart) with maximum playback compatibility across all devices.",
        container=OutputContainer.MP4,
        video_codec="libx264",
        audio_codec="aac",
        pixel_format="yuv420p",
        crf=20,
        preset_speed="medium",
        audio_bitrate="192k",
        audio_sample_rate=48000,
        extra_ffmpeg_args=["-profile:v", "high", "-level", "4.1", "-movflags", "+faststart"],
    ),
    TranscodePreset(
        id="maximum_compatibility",
        name="Maximum Compatibility (Legacy)",
        description="Conservative MP4 (H.264 Main + AAC 128k) for legacy devices and older hardware.",
        container=OutputContainer.MP4,
        video_codec="libx264",
        audio_codec="aac",
        pixel_format="yuv420p",
        crf=22,
        preset_speed="medium",
        audio_bitrate="128k",
        audio_sample_rate=44100,
        extra_ffmpeg_args=["-profile:v", "main", "-level", "3.1", "-movflags", "+faststart"],
    ),
    TranscodePreset(
        id="original_best_quality",
        name="Original / Best Quality",
        description="Preserves source stream formats without unnecessary re-encoding.",
        container=OutputContainer.ORIGINAL,
        video_codec="copy",
        audio_codec="copy",
        pixel_format=None,
    ),
    TranscodePreset(
        id="balanced_mp4",
        name="Balanced MP4",
        description="High quality MP4 with efficient encoding and reasonable file size.",
        container=OutputContainer.MP4,
        video_codec="libx264",
        audio_codec="aac",
        pixel_format="yuv420p",
        crf=22,
        preset_speed="faster",
        audio_bitrate="192k",
        extra_ffmpeg_args=["-movflags", "+faststart"],
    ),
    TranscodePreset(
        id="h264_1080p",
        name="H.264 1080p Full HD",
        description="Downscales or limits video to 1080p H.264 with AAC audio.",
        container=OutputContainer.MP4,
        video_codec="libx264",
        audio_codec="aac",
        pixel_format="yuv420p",
        crf=20,
        scale_height=1080,
        extra_ffmpeg_args=["-movflags", "+faststart"],
    ),
    TranscodePreset(
        id="h264_720p",
        name="H.264 720p HD",
        description="Downscales video to 720p H.264 with AAC audio.",
        container=OutputContainer.MP4,
        video_codec="libx264",
        audio_codec="aac",
        pixel_format="yuv420p",
        crf=21,
        scale_height=720,
        extra_ffmpeg_args=["-movflags", "+faststart"],
    ),
    TranscodePreset(
        id="audio_mp3_320k",
        name="MP3 Audio (320 kbps High Quality)",
        description="Extracts and converts audio to high-bitrate 320k MP3.",
        container=OutputContainer.MP3,
        video_codec="none",
        audio_codec="libmp3lame",
        audio_bitrate="320k",
        audio_sample_rate=44100,
    ),
    TranscodePreset(
        id="audio_mp3_256k",
        name="MP3 Audio (256 kbps Standard)",
        description="Extracts and converts audio to 256k MP3.",
        container=OutputContainer.MP3,
        video_codec="none",
        audio_codec="libmp3lame",
        audio_bitrate="256k",
        audio_sample_rate=44100,
    ),
    TranscodePreset(
        id="audio_mp3_192k",
        name="MP3 Audio (192 kbps Good)",
        description="Extracts and converts audio to standard 192k MP3.",
        container=OutputContainer.MP3,
        video_codec="none",
        audio_codec="libmp3lame",
        audio_bitrate="192k",
        audio_sample_rate=44100,
    ),
    TranscodePreset(
        id="audio_mp3_128k",
        name="MP3 Audio (128 kbps Compact)",
        description="Extracts and converts audio to compact 128k MP3.",
        container=OutputContainer.MP3,
        video_codec="none",
        audio_codec="libmp3lame",
        audio_bitrate="128k",
        audio_sample_rate=44100,
    ),
    TranscodePreset(
        id="audio_aac_256k",
        name="AAC Audio (256 kbps M4A)",
        description="Extracts and converts audio to clean M4A/AAC.",
        container=OutputContainer.M4A,
        video_codec="none",
        audio_codec="aac",
        audio_bitrate="256k",
    ),
    TranscodePreset(
        id="audio_wav",
        name="WAV Audio (Lossless PCM)",
        description="Lossless uncompressed audio.",
        container=OutputContainer.WAV,
        video_codec="none",
        audio_codec="pcm_s16le",
        audio_bitrate="",
        audio_sample_rate=44100,
    ),
    TranscodePreset(
        id="audio_flac",
        name="FLAC Audio (Lossless Compressed)",
        description="Lossless compressed audio.",
        container=OutputContainer.FLAC,
        video_codec="none",
        audio_codec="flac",
        audio_bitrate="",
        audio_sample_rate=44100,
    ),
]
