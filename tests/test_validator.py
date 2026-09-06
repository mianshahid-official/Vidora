"""
Unit & Integration tests for MediaValidator and Mute Video Prevention.
"""

import subprocess
import tempfile
from pathlib import Path
from app.core.dependencies import deps
from app.media.validator import MediaValidator


def test_validator_nonexistent_file():
    report = MediaValidator.validate_file("nonexistent_file_path_12345.mp4")
    assert report.is_valid is False
    assert report.file_exists is False
    assert "does not exist" in (report.error_message or "").lower()


def test_validator_zero_byte_file():
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        path = f.name

    try:
        report = MediaValidator.validate_file(path)
        assert report.is_valid is False
        assert report.file_size == 0
        assert "0 bytes" in (report.error_message or "").lower()
    finally:
        Path(path).unlink(missing_ok=True)


def test_validator_real_synthetic_media():
    """Generates a real 1-second video with AAC audio using FFmpeg and validates it."""
    ffmpeg_bin = deps.ffmpeg_path
    if not ffmpeg_bin:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = str(Path(tmpdir) / "test_valid.mp4")
        # Generate 1-second video with lavfi test source + sine audio
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            out_file
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        report = MediaValidator.validate_file(out_file, require_video=True, require_audio=True)
        assert report.is_valid is True
        assert report.has_video is True
        assert report.has_audio is True
        assert report.video_codec in ("h264", "avc1")
        assert report.audio_codec == "aac"


def test_validator_catches_mute_video():
    """Generates a real 1-second video without audio and ensures validator catches it."""
    ffmpeg_bin = deps.ffmpeg_path
    if not ffmpeg_bin:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        out_mute = str(Path(tmpdir) / "test_mute.mp4")
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an",
            out_mute
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        # When audio is required:
        report = MediaValidator.validate_file(out_mute, require_video=True, require_audio=True)
        assert report.is_valid is False
        assert report.has_audio is False
        assert "audio stream was not detected" in (report.error_message or "").lower()
