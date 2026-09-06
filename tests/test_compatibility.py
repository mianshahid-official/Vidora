"""
Unit tests for the TV / LCD compatibility rule analyzer engine.
"""

from app.core.compatibility import CompatibilityAnalyzer
from app.core.constants import CompatibilityLevel
from app.models.media_info import (
    AudioStreamInfo,
    ContainerInfo,
    MediaProbeResult,
    VideoStreamInfo,
)


def test_tv_compatibility_h264_aac_mp4():
    """H.264 + AAC in MP4 container with yuv420p should evaluate to COMPATIBLE."""
    probe = MediaProbeResult(
        file_path="sample.mp4",
        is_valid=True,
        container=ContainerInfo(format_name="mov,mp4,m4a,3gp,3g2,mj2", duration=120.0, size_bytes=10000000, bitrate=800000, nb_streams=2),
        video_streams=[VideoStreamInfo(index=0, codec_name="h264", profile="High", width=1920, height=1080, fps=30.0, pixel_format="yuv420p")],
        audio_streams=[AudioStreamInfo(index=1, codec_name="aac", channels=2, sample_rate=48000)]
    )

    report = CompatibilityAnalyzer.analyze(probe)
    assert report.level == CompatibilityLevel.COMPATIBLE
    assert report.is_tv_safe is True
    assert "Likely compatible" in report.verdict


def test_tv_compatibility_vp9_opus_webm():
    """VP9 + Opus in WebM container should be flagged as potentially incompatible or incompatible."""
    probe = MediaProbeResult(
        file_path="sample.webm",
        is_valid=True,
        container=ContainerInfo(format_name="matroska,webm", duration=120.0, size_bytes=10000000, bitrate=800000, nb_streams=2),
        video_streams=[VideoStreamInfo(index=0, codec_name="vp9", profile="Profile 0", width=1920, height=1080, fps=30.0, pixel_format="yuv420p")],
        audio_streams=[AudioStreamInfo(index=1, codec_name="opus", channels=2, sample_rate=48000)]
    )

    report = CompatibilityAnalyzer.analyze(probe)
    assert report.level in (CompatibilityLevel.POTENTIALLY_INCOMPATIBLE, CompatibilityLevel.INCOMPATIBLE)
    assert report.is_tv_safe is False
    assert len(report.recommendations) > 0


def test_tv_compatibility_mute_video():
    """Video with no audio stream must fail compatibility checks."""
    probe = MediaProbeResult(
        file_path="mute.mp4",
        is_valid=True,
        container=ContainerInfo(format_name="mov,mp4,m4a", duration=60.0, size_bytes=5000000, bitrate=500000, nb_streams=1),
        video_streams=[VideoStreamInfo(index=0, codec_name="h264", profile="High", width=1920, height=1080, fps=30.0, pixel_format="yuv420p")],
        audio_streams=[]
    )

    report = CompatibilityAnalyzer.analyze(probe)
    assert any("MISSING" in item.value or item.status == "FAIL" for item in report.items)
