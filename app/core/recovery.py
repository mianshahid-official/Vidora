"""
Audio missing recovery strategy and pipeline repair.
"""

from pathlib import Path
from typing import Optional
import yt_dlp

from app.core.config import config_manager
from app.core.dependencies import deps
from app.core.logger import logger
from app.encoder.transcoder import TranscoderManager
from app.media.validator import MediaValidator
from app.models.job import DownloadJob
from app.models.validation_result import ValidationReport
from app.utils.file_utils import get_unique_filepath, safe_remove


class AudioRecoveryService:
    """
    Automatic recovery engine when a downloaded video has no audio stream.
    Downloads standalone bestaudio stream and merges it into the video container.
    """

    @staticmethod
    def attempt_audio_recovery(job: DownloadJob, muted_video_path: str) -> tuple[bool, str, Optional[ValidationReport]]:
        logger.log_download(f"Attempting automated audio recovery for job: '{job.title}'...")

        settings = config_manager.settings
        temp_dir = Path(settings.temp_dir).resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)

        audio_temp_path = str(temp_dir / f"recovery_audio_{job.id}.%(ext)s")
        merged_output_path = str(Path(muted_video_path).with_stem(Path(muted_video_path).stem + "_recovered"))

        # 1. Download standalone best audio stream
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": audio_temp_path,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 20,
        }
        if deps.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = deps.ffmpeg_path
        if settings.use_cookies and settings.cookies_file_path:
            ydl_opts["cookiefile"] = settings.cookies_file_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([job.url])

            # Look for actual downloaded audio file (might have .m4a, .webm, .opus ext)
            actual_audio_files = list(temp_dir.glob(f"recovery_audio_{job.id}*"))
            if not actual_audio_files:
                logger.log_download("Recovery failed: Standalone audio stream could not be downloaded.", "ERROR")
                return False, muted_video_path, None

            actual_audio_file = str(actual_audio_files[0])

            # 2. Merge video + audio using TranscoderManager
            transcoder = TranscoderManager()
            transcoder.merge_video_audio(
                video_path=muted_video_path,
                audio_path=actual_audio_file,
                output_path=merged_output_path,
                target_container=job.target_container or "mp4"
            )

            # 3. Validate merged output
            report = MediaValidator.validate_file(
                merged_output_path,
                require_video=True,
                require_audio=True
            )

            if report.is_valid and report.has_audio:
                # Replace original muted file with recovered file
                try:
                    safe_remove(muted_video_path)
                    safe_remove(actual_audio_file)
                    p_recovered = Path(merged_output_path)
                    p_final = Path(muted_video_path)
                    p_recovered.rename(p_final)
                    final_path = str(p_final.resolve())
                except Exception:
                    final_path = merged_output_path

                logger.log_download(f"Audio recovery SUCCEEDED for '{job.title}'. Audio stream recovered and merged.")
                return True, final_path, report
            else:
                logger.log_download(f"Recovery validation failed: {report.error_message}", "ERROR")
                return False, muted_video_path, report

        except Exception as e:
            logger.log_download(f"Exception during audio recovery: {e}", "ERROR")
            return False, muted_video_path, None
        finally:
            # Clean temporary recovery audio file
            for f in temp_dir.glob(f"recovery_audio_{job.id}*"):
                safe_remove(str(f))
