"""
PySide6 QThread worker for standalone media file transcoding.
"""

import time
from pathlib import Path
from PySide6.QtCore import QObject, QThread, Signal

from app.core.constants import JobStatus
from app.encoder.profiles import ProfileManager
from app.encoder.transcoder import TranscoderManager
from app.media.validator import MediaValidator
from app.models.job import ConvertJob


class EncodeWorker(QThread):
    """Worker thread running a standalone conversion job."""

    job_progress = Signal(object)  # ConvertJob
    job_finished = Signal(object)  # ConvertJob
    log_message = Signal(str)

    def __init__(self, job: ConvertJob, parent: QObject = None):
        super().__init__(parent)
        self.job = job
        self.transcoder = TranscoderManager()

    def run(self):
        job = self.job
        job.status = JobStatus.ENCODING

        preset = ProfileManager.get_preset_by_id(job.preset_id)
        if not preset:
            preset = ProfileManager.get_preset_by_id("tv_lcd_compatible")

        def on_progress(pct, fps, speed, eta):
            job.progress_percent = pct
            job.current_fps = fps
            job.current_speed = speed
            job.eta_seconds = eta
            self.job_progress.emit(job)

        def on_log(msg: str):
            self.log_message.emit(msg)

        try:
            trim_start = job.trim_start if job.trim_enabled else None
            trim_end = job.trim_end if job.trim_enabled else None

            if job.preset_id in ("universal_mp4", "tv_lcd_compatible"):
                output = self.transcoder.apply_universal_mp4_pipeline(
                    input_file=job.input_file_path,
                    output_file=job.output_file_path,
                    progress_callback=on_progress,
                    log_callback=on_log
                )
            elif "mp3" in job.preset_id or job.target_container.lower() == "mp3":
                output = self.transcoder.convert_to_mp3(
                    input_path=job.input_file_path,
                    output_path=job.output_file_path,
                    bitrate=job.audio_bitrate or "320k",
                    trim_start=trim_start,
                    trim_end=trim_end,
                    progress_callback=on_progress,
                    log_callback=on_log
                )
            else:
                output = self.transcoder.convert_media(
                    input_path=job.input_file_path,
                    output_path=job.output_file_path,
                    preset=preset,
                    trim_start=trim_start,
                    trim_end=trim_end,
                    progress_callback=on_progress,
                    log_callback=on_log
                )

            # Validate output
            report = MediaValidator.validate_file(
                output,
                require_video=(preset.video_codec != "none" and job.target_container.lower() not in ("mp3", "m4a", "wav", "flac", "aac")),
                require_audio=(preset.audio_codec != "none")
            )

            if report.is_valid:
                job.status = JobStatus.COMPLETED
                job.progress_percent = 100.0
                job.completed_at = time.time()
            else:
                job.status = JobStatus.FAILED
                job.error_message = report.error_message

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
        finally:
            self.job_finished.emit(job)

    def cancel(self):
        self.job.is_cancelled = True
        self.job.status = JobStatus.CANCELLED
        self.transcoder.cancel_all()
