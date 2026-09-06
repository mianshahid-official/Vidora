"""
Post-download media validation pipeline and mute prevention guard.
"""

from pathlib import Path
from typing import Optional

from app.core.exceptions import AudioMissingError, ValidationFailedError
from app.core.logger import logger
from app.media.ffprobe_wrapper import FFprobeWrapper
from app.models.validation_result import ValidationReport


class MediaValidator:
    """
    Validates completed downloads to strictly prevent mute videos, corrupted files,
    or missing streams before marking any job as Completed.
    """

    @staticmethod
    def validate_file(
        file_path: str,
        require_video: bool = True,
        require_audio: bool = True
    ) -> ValidationReport:
        p = Path(file_path).resolve()

        # 1. Existence and size checks
        if not p.exists():
            return ValidationReport(
                is_valid=False,
                file_exists=False,
                file_size=0,
                has_video=False,
                has_audio=False,
                error_message=f"Output file does not exist on disk: {file_path}"
            )

        file_size = p.stat().st_size
        if file_size == 0:
            return ValidationReport(
                is_valid=False,
                file_exists=True,
                file_size=0,
                has_video=False,
                has_audio=False,
                error_message=f"Output file is 0 bytes (corrupted or empty): {file_path}"
            )

        # 2. FFprobe deep inspection
        probe = FFprobeWrapper.probe(str(p))
        if not probe.is_valid or not probe.container:
            return ValidationReport(
                is_valid=False,
                file_exists=True,
                file_size=file_size,
                has_video=False,
                has_audio=False,
                error_message=f"FFprobe could not read container format. Error: {probe.error_message}",
                probe_result=probe
            )

        has_video = probe.has_video
        has_audio = probe.has_audio

        video_codec = probe.primary_video.codec_name if probe.primary_video else "none"
        audio_codec = probe.primary_audio.codec_name if probe.primary_audio else "none"
        resolution = f"{probe.primary_video.width}x{probe.primary_video.height}" if probe.primary_video else "N/A"
        duration = probe.container.duration

        warnings = []

        # 3. Video Stream requirement check
        if require_video and not has_video:
            return ValidationReport(
                is_valid=False,
                file_exists=True,
                file_size=file_size,
                has_video=False,
                has_audio=has_audio,
                video_codec=video_codec,
                audio_codec=audio_codec,
                resolution=resolution,
                duration=duration,
                container=probe.container.format_name,
                error_message="Video stream was requested, but no valid video stream was detected in the final file.",
                probe_result=probe
            )

        # 4. CRITICAL AUDIO SAFETY CHECK: Never produce mute videos
        if require_audio and not has_audio:
            msg = "Download completed but audio stream was not detected."
            logger.log_download(f"CRITICAL VALIDATION FAILURE for '{file_path}': {msg}", "ERROR")
            return ValidationReport(
                is_valid=False,
                file_exists=True,
                file_size=file_size,
                has_video=has_video,
                has_audio=False,
                video_codec=video_codec,
                audio_codec="none",
                resolution=resolution,
                duration=duration,
                container=probe.container.format_name,
                error_message=msg,
                probe_result=probe
            )

        report = ValidationReport(
            is_valid=True,
            file_exists=True,
            file_size=file_size,
            has_video=has_video,
            has_audio=has_audio,
            video_codec=video_codec,
            audio_codec=audio_codec,
            resolution=resolution,
            duration=duration,
            container=probe.container.format_name,
            warnings=warnings,
            probe_result=probe
        )

        logger.log_download(f"Media validation passed successfully for '{p.name}'.\n{report.format_log_summary()}")
        return report
