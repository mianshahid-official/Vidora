"""
Download & Processing Pipeline Orchestrator.
"""

import time
from pathlib import Path
from typing import Callable, Optional

from app.core.config import config_manager
from app.core.constants import DuplicateAction, JobStatus, QualityPreset
from app.core.exceptions import (
    AudioMissingError,
    FatalDownloadError,
    RecoverableDownloadError,
    ValidationFailedError,
)
from app.core.logger import logger
from app.core.recovery import AudioRecoveryService
from app.database.repositories import HistoryRepository, JobRepository
from app.downloader.ytdlp_wrapper import ProgressCancelledException, YtdlpEngine
from app.encoder.transcoder import TranscoderManager
from app.media.validator import MediaValidator
from app.models.job import DownloadJob
from app.utils.file_utils import check_disk_space, get_unique_filepath, safe_remove


class DownloadPipeline:
    """
    Executes the multi-stage download and validation workflow:
    Download -> Merge -> Remux/Transcode (if TV/LCD mode) -> FFprobe Validate -> Audio Recovery (if needed) -> Complete.
    """

    def __init__(self, job: DownloadJob):
        self.job = job
        self.ytdlp_engine = YtdlpEngine(job)
        self.transcoder = TranscoderManager()

    def cancel(self):
        self.ytdlp_engine.cancel()
        self.transcoder.cancel_all()
        self.job.is_cancelled = True
        self.job.status = JobStatus.CANCELLED
        JobRepository.save_job(self.job)

    def pause(self):
        self.ytdlp_engine.pause()
        self.transcoder.cancel_all()
        self.job.is_paused = True
        self.job.status = JobStatus.PAUSED
        JobRepository.save_job(self.job)

    def execute(
        self,
        progress_callback: Optional[Callable[[DownloadJob], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> DownloadJob:
        settings = config_manager.settings
        job = self.job

        try:
            # 1. Disk Space Verification
            free_b, total_b, has_space = check_disk_space(job.destination_dir or settings.downloads_dir, job.total_bytes)
            if not has_space and settings.warn_low_disk_space:
                logger.log_download(f"Warning: Low disk space for destination ({free_b / (1024**3):.2f} GB free).", "WARN")

            # 2. Start Download
            job.status = JobStatus.DOWNLOADING
            JobRepository.save_job(job)
            if progress_callback:
                progress_callback(job)

            downloaded_file = self.ytdlp_engine.download(
                progress_callback=progress_callback,
                log_callback=log_callback
            )

            if job.is_cancelled or job.is_paused:
                return job

            # 3. Post-processing: Universal MP4 or MP3 conversion
            final_path = downloaded_file
            is_mp3_target = (job.is_audio_only or job.target_container.lower() == "mp3" or job.quality_preset == QualityPreset.AUDIO_ONLY)

            if is_mp3_target and not downloaded_file.lower().endswith(".mp3"):
                job.status = JobStatus.ENCODING
                JobRepository.save_job(job)
                if progress_callback:
                    progress_callback(job)

                out_mp3_path = str(Path(downloaded_file).with_suffix(".mp3"))
                if out_mp3_path == downloaded_file:
                    out_mp3_path = str(Path(downloaded_file).parent / f"{Path(downloaded_file).stem}_clean.mp3")

                def encode_progress(pct, fps, speed, eta):
                    job.encoding_percent = pct
                    job.encoding_fps = fps
                    job.encoding_speed = speed
                    job.eta_seconds = eta
                    if progress_callback:
                        progress_callback(job)

                converted_mp3 = self.transcoder.convert_to_mp3(
                    input_path=downloaded_file,
                    output_path=out_mp3_path,
                    bitrate="320k",
                    progress_callback=encode_progress,
                    log_callback=log_callback
                )

                if converted_mp3 and Path(converted_mp3).is_file() and converted_mp3 != downloaded_file:
                    safe_remove(downloaded_file)
                    final_path = converted_mp3

            elif job.quality_preset in (QualityPreset.UNIVERSAL_MP4, QualityPreset.TV_LCD_COMPATIBLE) and not job.is_audio_only:
                job.status = JobStatus.ENCODING
                JobRepository.save_job(job)
                if progress_callback:
                    progress_callback(job)

                out_norm_path = str(Path(downloaded_file).with_suffix(".universal.mp4"))
                if out_norm_path != downloaded_file:
                    out_norm_path = str(get_unique_filepath(Path(out_norm_path)))

                def encode_progress(pct, fps, speed, eta):
                    job.encoding_percent = pct
                    job.encoding_fps = fps
                    job.encoding_speed = speed
                    job.eta_seconds = eta
                    if progress_callback:
                        progress_callback(job)

                processed_file = self.transcoder.apply_universal_mp4_pipeline(
                    input_file=downloaded_file,
                    output_file=out_norm_path,
                    progress_callback=encode_progress,
                    log_callback=log_callback
                )

                if processed_file != downloaded_file and Path(processed_file).exists():
                    safe_remove(downloaded_file)
                    clean_final = str(Path(downloaded_file).with_suffix(".mp4"))
                    if Path(clean_final).exists() and clean_final != processed_file:
                        safe_remove(clean_final)
                    Path(processed_file).rename(Path(clean_final))
                    final_path = clean_final

            job.final_file_path = final_path

            # 4. Mandatory Post-Download Media Validation
            job.status = JobStatus.VALIDATING
            JobRepository.save_job(job)
            if progress_callback:
                progress_callback(job)

            require_audio = not job.is_video_only
            require_video = not job.is_audio_only

            report = MediaValidator.validate_file(
                final_path,
                require_video=require_video,
                require_audio=require_audio
            )
            job.validation_report = report

            # 5. MUTE RECOVERY: If video has no audio, attempt automatic recovery
            if not report.is_valid and require_audio and not report.has_audio:
                logger.log_download("Mute video detected! Triggering automatic audio recovery...")
                recovered, recovered_path, new_report = AudioRecoveryService.attempt_audio_recovery(job, final_path)
                if recovered and new_report and new_report.is_valid:
                    job.final_file_path = recovered_path
                    job.validation_report = new_report
                    report = new_report
                else:
                    job.status = JobStatus.FAILED
                    job.error_message = "Download completed but audio stream was not detected."
                    JobRepository.save_job(job)
                    if progress_callback:
                        progress_callback(job)
                    return job

            # 6. Final Status Evaluation
            if report.is_valid:
                job.status = JobStatus.COMPLETED
                job.completed_at = time.time()
                job.progress_percent = 100.0
                job.error_message = None
                # Persist to history and jobs db
                HistoryRepository.add_entry(job)
                JobRepository.save_job(job)
                logger.log_download(f"Job completed successfully: '{job.title}'")
            else:
                job.status = JobStatus.FAILED
                job.error_message = report.error_message or "Validation failed."
                JobRepository.save_job(job)
                logger.log_download(f"Job failed validation: {job.error_message}", "ERROR")

            if progress_callback:
                progress_callback(job)
            return job

        except ProgressCancelledException:
            # Paused or Cancelled
            if job.is_paused:
                job.status = JobStatus.PAUSED
            else:
                job.status = JobStatus.CANCELLED
            JobRepository.save_job(job)
            if progress_callback:
                progress_callback(job)
            return job

        except (FatalDownloadError, RecoverableDownloadError) as de:
            job.status = JobStatus.FAILED
            job.error_message = str(de)
            JobRepository.save_job(job)
            if progress_callback:
                progress_callback(job)
            return job

        except Exception as e:
            logger.log_error(f"Unexpected pipeline exception for '{job.title}': {e}", exc_info=True)
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            JobRepository.save_job(job)
            if progress_callback:
                progress_callback(job)
            return job
