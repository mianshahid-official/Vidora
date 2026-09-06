"""
Unit tests for TranscoderManager and Smart TV/LCD Pipeline decision logic.
"""

import subprocess
import tempfile
from pathlib import Path
from app.core.dependencies import deps
from app.encoder.transcoder import TranscoderManager
from app.media.ffprobe_wrapper import FFprobeWrapper


def test_smart_tv_lcd_pipeline_execution():
    """Generates an incompatible WebM (VP9 + Opus) video and tests smart conversion to TV-compatible MP4 (H.264 + AAC + yuv420p)."""
    ffmpeg_bin = deps.ffmpeg_path
    if not ffmpeg_bin:
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        input_webm = str(Path(tmpdir) / "source_vp9_opus.webm")
        output_mp4 = str(Path(tmpdir) / "output_tv_compat.mp4")

        # Generate VP9 + Opus in WebM container
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-c:v", "libvpx-vp9",
            "-c:a", "libopus",
            input_webm
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        # Run Smart TV/LCD Pipeline
        tm = TranscoderManager()
        final_file = tm.apply_smart_tv_lcd_pipeline(input_webm, output_mp4)

        assert Path(final_file).is_file()

        # Probe final file to verify H.264 + AAC + yuv420p
        probe = FFprobeWrapper.probe(final_file)
        assert probe.is_valid is True
        assert probe.primary_video is not None
        assert probe.primary_video.codec_name in ("h264", "avc1")
        assert probe.primary_video.pixel_format == "yuv420p"
        assert probe.primary_audio is not None
        assert probe.primary_audio.codec_name == "aac"
        assert "mp4" in probe.container.format_name.lower()
