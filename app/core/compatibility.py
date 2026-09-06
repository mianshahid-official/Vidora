"""
TV / LCD / Media Player Media Compatibility Analyzer Engine.
"""

from dataclasses import dataclass, field
from typing import List, Optional

from app.core.constants import CompatibilityLevel
from app.models.media_info import MediaProbeResult, VideoStreamInfo, AudioStreamInfo


@dataclass
class CompatibilityCheckItem:
    attribute: str
    value: str
    status: str  # "PASS", "WARN", "FAIL"
    message: str


@dataclass
class CompatibilityReport:
    level: CompatibilityLevel
    verdict: str
    summary_text: str
    items: List[CompatibilityCheckItem] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    @property
    def is_tv_safe(self) -> bool:
        return self.level in (CompatibilityLevel.COMPATIBLE, CompatibilityLevel.PROBABLY_COMPATIBLE)


class CompatibilityAnalyzer:
    """Analyzes media streams against common TV/LCD hardware decoder capabilities."""

    @staticmethod
    def analyze(probe: MediaProbeResult) -> CompatibilityReport:
        if not probe.is_valid or not probe.container:
            return CompatibilityReport(
                level=CompatibilityLevel.INCOMPATIBLE,
                verdict="Incompatible / Corrupted",
                summary_text="Media inspection failed or file is invalid.",
                recommendations=["Ensure the file exists and is not corrupted."]
            )

        items: List[CompatibilityCheckItem] = []
        recommendations: List[str] = []
        fail_count = 0
        warn_count = 0

        # 1. Container check
        container_fmt = probe.container.format_name.lower()
        if "mp4" in container_fmt or "m4a" in container_fmt or "mov" in container_fmt:
            items.append(CompatibilityCheckItem("Container", "MP4", "PASS", "Universal TV/LCD container support."))
        elif "matroska" in container_fmt or "mkv" in container_fmt:
            items.append(CompatibilityCheckItem("Container", "MKV", "WARN", "Supported on many newer TVs, but may fail on older media players."))
            warn_count += 1
            recommendations.append("Remux into MP4 container for wider standalone TV player compatibility.")
        elif "webm" in container_fmt:
            items.append(CompatibilityCheckItem("Container", "WebM", "FAIL", "WebM is rarely supported by TV USB media players."))
            fail_count += 1
            recommendations.append("Convert to MP4 container.")
        else:
            items.append(CompatibilityCheckItem("Container", container_fmt, "WARN", f"Container '{container_fmt}' may not be supported by TVs."))
            warn_count += 1

        # 2. Video Stream checks
        video = probe.primary_video
        if video:
            codec = video.codec_name.lower()
            # Video Codec
            if codec in ("h264", "avc1", "avc"):
                items.append(CompatibilityCheckItem("Video Codec", f"H.264 / AVC ({video.profile})", "PASS", "Universally supported by almost all TV chipsets."))
            elif codec in ("hevc", "h265"):
                items.append(CompatibilityCheckItem("Video Codec", "H.265 / HEVC", "WARN", "Supported on 4K TVs, but fails on older 1080p LCD TVs."))
                warn_count += 1
                recommendations.append("Transcode video to H.264 if targeting older TVs or media boxes.")
            elif codec in ("vp9", "vp8"):
                items.append(CompatibilityCheckItem("Video Codec", video.codec_name.upper(), "FAIL", "VP8/VP9 hardware decoders are uncommon on standard TV USB players."))
                fail_count += 1
                recommendations.append("Transcode VP9 video to H.264 for TV playback.")
            elif codec in ("av1", "av01"):
                items.append(CompatibilityCheckItem("Video Codec", "AV1", "FAIL", "AV1 is not supported by older or budget TVs."))
                fail_count += 1
                recommendations.append("Transcode AV1 video to H.264.")
            else:
                items.append(CompatibilityCheckItem("Video Codec", codec.upper(), "FAIL", f"Codec '{codec}' is unsupported on most TVs."))
                fail_count += 1
                recommendations.append(f"Transcode {codec} to H.264.")

            # Pixel Format & Bit Depth
            pix = video.pixel_format.lower()
            if pix == "yuv420p":
                items.append(CompatibilityCheckItem("Pixel Format", "yuv420p (8-bit)", "PASS", "Standard 8-bit chroma sub-sampling supported by all hardware decoders."))
            elif video.is_10bit or "10" in pix or "12" in pix:
                items.append(CompatibilityCheckItem("Pixel Format", f"{pix} (10-bit/HDR)", "FAIL", "10-bit video frequently causes black screens or stutter on standard TVs."))
                fail_count += 1
                recommendations.append("Re-encode with 8-bit yuv420p pixel format.")
            else:
                items.append(CompatibilityCheckItem("Pixel Format", pix, "WARN", f"Unusual pixel format '{pix}' may cause playback errors."))
                warn_count += 1

            # Resolution & Frame Rate
            res_str = f"{video.width}x{video.height}"
            if video.height <= 1080:
                items.append(CompatibilityCheckItem("Resolution", f"{res_str} ({video.fps} fps)", "PASS", "Standard HD/Full HD resolution."))
            elif video.height <= 2160:
                items.append(CompatibilityCheckItem("Resolution", f"{res_str} ({video.fps} fps)", "WARN", "4K resolution requires a 4K TV/display."))
                warn_count += 1
            else:
                items.append(CompatibilityCheckItem("Resolution", f"{res_str}", "FAIL", "Ultra-high resolution (>4K) unsupported by TVs."))
                fail_count += 1

            if video.fps > 60:
                items.append(CompatibilityCheckItem("Frame Rate", f"{video.fps} fps", "WARN", "High frame rate (>60 fps) may drop frames on TV players."))
                warn_count += 1

        else:
            # Audio-only file
            items.append(CompatibilityCheckItem("Video Stream", "None", "PASS", "Audio-only media."))

        # 3. Audio Stream checks
        audio = probe.primary_audio
        if audio:
            acodec = audio.codec_name.lower()
            if acodec in ("aac", "mp4a"):
                items.append(CompatibilityCheckItem("Audio Codec", "AAC", "PASS", "AAC audio is universally supported across all TVs and media receivers."))
            elif acodec in ("mp3", "libmp3lame"):
                items.append(CompatibilityCheckItem("Audio Codec", "MP3", "PASS", "MP3 audio is widely supported."))
            elif acodec in ("ac3", "eac3"):
                items.append(CompatibilityCheckItem("Audio Codec", "Dolby Digital (AC-3)", "PASS", "Supported on TV/Home Theater systems."))
            elif acodec in ("opus", "vorbis"):
                items.append(CompatibilityCheckItem("Audio Codec", audio.codec_name.upper(), "FAIL", f"{audio.codec_name.upper()} audio frequently fails or plays mute on TV USB players."))
                fail_count += 1
                recommendations.append("Convert audio stream to AAC.")
            elif acodec in ("flac", "alac"):
                items.append(CompatibilityCheckItem("Audio Codec", audio.codec_name.upper(), "WARN", "Lossless audio is unsupported on some older TVs."))
                warn_count += 1
                recommendations.append("Convert audio stream to AAC for universal compatibility.")
            else:
                items.append(CompatibilityCheckItem("Audio Codec", acodec.upper(), "WARN", f"Audio codec '{acodec}' may not be supported."))
                warn_count += 1

            # Sample rate
            if audio.sample_rate in (44100, 48000):
                items.append(CompatibilityCheckItem("Audio Sample Rate", f"{audio.sample_rate} Hz", "PASS", "Standard TV audio sample rate."))
            elif audio.sample_rate > 0:
                items.append(CompatibilityCheckItem("Audio Sample Rate", f"{audio.sample_rate} Hz", "WARN", "Unusual audio sample rate."))
                warn_count += 1

        elif probe.has_video:
            # Video exists but audio missing!
            items.append(CompatibilityCheckItem("Audio Stream", "MISSING (Mute)", "FAIL", "No audio stream detected in video."))
            fail_count += 2
            recommendations.append("Merge with compatible audio stream.")

        # Verdict Determination
        if fail_count == 0 and warn_count == 0:
            level = CompatibilityLevel.COMPATIBLE
            verdict = "Likely compatible with most TVs"
            summary = "This media complies with universal TV / LCD playback standards (H.264 + AAC + yuv420p in MP4)."
        elif fail_count == 0:
            level = CompatibilityLevel.PROBABLY_COMPATIBLE
            verdict = "Probably compatible with modern TVs"
            summary = "Compatible with most modern Smart TVs, but older TV chipsets or media boxes may have partial limitations."
        elif fail_count <= 2:
            level = CompatibilityLevel.POTENTIALLY_INCOMPATIBLE
            verdict = "Potential compatibility issue detected"
            summary = "One or more streams (e.g. VP9, Opus, WebM container, or 10-bit color) may fail to decode on standard TV USB players."
        else:
            level = CompatibilityLevel.INCOMPATIBLE
            verdict = "Likely incompatible with TV USB playback"
            summary = "Multiple codecs or container formats are unsupported on typical TV hardware decoders."

        return CompatibilityReport(
            level=level,
            verdict=verdict,
            summary_text=summary,
            items=items,
            recommendations=recommendations
        )
