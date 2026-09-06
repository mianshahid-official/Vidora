"""
Data model for post-download FFprobe media validation results.
"""

from dataclasses import dataclass, field
from typing import Optional
from app.models.media_info import MediaProbeResult


@dataclass
class ValidationReport:
    """Detailed report of post-download validation."""
    is_valid: bool
    file_exists: bool
    file_size: int
    has_video: bool
    has_audio: bool
    video_codec: str = "none"
    audio_codec: str = "none"
    resolution: str = "N/A"
    duration: float = 0.0
    container: str = "unknown"
    error_message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    probe_result: Optional[MediaProbeResult] = None

    def format_log_summary(self) -> str:
        """Formats clean multiline log details as required."""
        lines = [
            f"File: {self.container} ({self.file_size / (1024*1024):.2f} MB)",
            f"Video Stream: {'Present (' + self.video_codec + ', ' + self.resolution + ')' if self.has_video else 'None'}",
            f"Audio Stream: {'Present (' + self.audio_codec + ')' if self.has_audio else 'None'}",
            f"Container: {self.container}",
            f"Duration: {self.duration:.1f}s",
            f"Status: {'PASSED' if self.is_valid else 'FAILED (' + str(self.error_message) + ')'}",
        ]
        return "\n".join(lines)
