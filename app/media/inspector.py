"""
Media Inspector service providing full stream decomposition and TV compatibility reports.
"""

from dataclasses import dataclass
from typing import Optional

from app.core.compatibility import CompatibilityAnalyzer, CompatibilityReport
from app.media.ffprobe_wrapper import FFprobeWrapper
from app.models.media_info import MediaProbeResult


@dataclass
class InspectionResult:
    probe: MediaProbeResult
    compatibility: CompatibilityReport


class MediaInspectorService:
    """Provides high-level analysis of local media files."""

    @staticmethod
    def inspect(file_path: str) -> InspectionResult:
        probe = FFprobeWrapper.probe(file_path)
        compat = CompatibilityAnalyzer.analyze(probe)
        return InspectionResult(probe=probe, compatibility=compat)
