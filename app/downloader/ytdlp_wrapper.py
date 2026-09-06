"""
yt-dlp integration engine with safe stream pairing, pause/resume, and progress hooks.
"""

import os
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yt_dlp

from app.core.config import config_manager
from app.core.constants import QualityPreset
from app.core.dependencies import deps
from app.core.exceptions import FatalDownloadError, RecoverableDownloadError
from app.core.logger import logger
from app.models.job import DownloadJob
from app.utils.file_utils import sanitize_filename


class ProgressCancelledException(Exception):
    """Raised when a download is aborted or paused by user."""
    pass


class YtdlpEngine:
    """Encapsulates yt-dlp downloading operations."""

    def __init__(self, job: DownloadJob):
        self.job = job
        self._is_cancelled = False
        self._is_paused = False

    def cancel(self):
        self._is_cancelled = True
        self.job.is_cancelled = True

    def pause(self):
        self._is_paused = True
        self.job.is_paused = True

    def build_format_string(self) -> str:
        """
        Dynamically constructs the format selection string to ensure video + audio streams
        are paired properly without producing silent videos.
        """
        job = self.job

        # Audio-only or MP3 requested
        if job.is_audio_only or job.quality_preset == QualityPreset.AUDIO_ONLY or job.target_container.lower() == "mp3":
            if job.selected_audio_format_id:
                return job.selected_audio_format_id
            return "bestaudio/best"

        # Explicit format selected by user from dialog
        if job.selected_format_id:
            if job.selected_audio_format_id:
                return f"{job.selected_format_id}+{job.selected_audio_format_id}"
            return f"{job.selected_format_id}+bestaudio/best"

        # Resolution based selection
        res_limit = ""
        if "2160p" in job.resolution:
            res_limit = "[height<=2160]"
        elif "1440p" in job.resolution:
            res_limit = "[height<=1440]"
        elif "1080p" in job.resolution:
            res_limit = "[height<=1080]"
        elif "720p" in job.resolution:
            res_limit = "[height<=720]"
        elif "480p" in job.resolution:
            res_limit = "[height<=480]"
        elif "360p" in job.resolution:
            res_limit = "[height<=360]"

        if job.quality_preset in (QualityPreset.UNIVERSAL_MP4, QualityPreset.TV_LCD_COMPATIBLE):
            return f"bestvideo{res_limit}[vcodec^=avc1]+bestaudio[acodec^=mp4a]/bestvideo{res_limit}[ext=mp4]+bestaudio[ext=m4a]/bestvideo{res_limit}+bestaudio/best{res_limit}/best"

        return f"bestvideo{res_limit}+bestaudio/best{res_limit}/best"

    def get_preview_command(self) -> str:
        """Returns safe read-only preview command string."""
        fmt = self.build_format_string()
        out_tmpl = str(Path(self.job.destination_dir) / "%(title)s.%(ext)s")
        parts = ["yt-dlp", "-f", f'"{fmt}"', "-o", f'"{out_tmpl}"', "--continue"]
        if deps.ffmpeg_path:
            parts.extend(["--ffmpeg-location", f'"{deps.ffmpeg_path}"'])
        parts.append(f'"{self.job.url}"')
        return " ".join(parts)

    def download(
        self,
        progress_callback: Optional[Callable[[DownloadJob], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Executes yt-dlp download with native resume (.part file preservation) and progress reporting.
        Returns final file path downloaded.
        """
        import re
        settings = config_manager.settings
        dest_dir = Path(self.job.destination_dir or settings.downloads_dir).resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        format_str = self.build_format_string()
        out_template = str(dest_dir / (self.job.output_filename or "%(title)s.%(ext)s"))

        finished_files: List[str] = []
        postprocessed_files: List[str] = []

        def ytdlp_hook(d: dict):
            if self._is_cancelled or self._is_paused:
                raise ProgressCancelledException("Download cancelled or paused by user.")

            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                speed = d.get("speed") or 0.0
                eta = d.get("eta")

                self.job.downloaded_bytes = downloaded
                self.job.total_bytes = total
                self.job.speed_bytes_per_sec = speed
                self.job.eta_seconds = eta

                if total > 0:
                    self.job.progress_percent = round((downloaded / total) * 100.0, 1)

                if progress_callback:
                    progress_callback(self.job)

            elif status == "finished":
                filename = d.get("filename")
                if filename:
                    finished_files.append(filename)
                self.job.progress_percent = 100.0
                if progress_callback:
                    progress_callback(self.job)

        def ytdlp_postprocessor_hook(d: dict):
            if d.get("status") == "finished":
                info_dict = d.get("info_dict", {})
                fn = info_dict.get("_filename") or info_dict.get("filepath")
                if fn:
                    postprocessed_files.append(fn)

        # Build yt-dlp options
        ydl_opts: Dict[str, Any] = {
            "format": format_str,
            "outtmpl": out_template,
            "progress_hooks": [ytdlp_hook],
            "postprocessor_hooks": [ytdlp_postprocessor_hook],
            "continuedl": True,
            "nopart": False,  # Keep .part files for safe pause/resume
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": 20,
            "retries": 10,
            "fragment_retries": 10,
        }

        # Merge container configuration
        target_container = (self.job.target_container or "mp4").lower()
        if not self.job.is_audio_only and target_container != "mp3":
            ydl_opts["merge_output_format"] = target_container

        # Speed limit
        if settings.speed_limit_bytes > 0:
            ydl_opts["ratelimit"] = settings.speed_limit_bytes

        # Cookies
        if settings.use_cookies:
            if settings.cookies_source in ("chrome", "firefox", "edge", "opera", "brave", "vivaldi"):
                ydl_opts["cookiesfrombrowser"] = (settings.cookies_source,)
            elif settings.cookies_source == "file" and settings.cookies_file_path:
                ydl_opts["cookiefile"] = settings.cookies_file_path

        # FFmpeg binary
        if deps.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = deps.ffmpeg_path

        # User-agent & Proxy
        if settings.user_agent:
            ydl_opts["user_agent"] = settings.user_agent
        if settings.proxy_url:
            ydl_opts["proxy"] = settings.proxy_url

        try:
            logger.log_download(f"Starting download for '{self.job.title}' with format: '{format_str}'")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.job.url, download=True)
                if info:
                    # Update title and uploader if needed
                    ext_title = info.get("title")
                    if ext_title:
                        from app.utils.file_utils import strip_emojis
                        clean_ext = strip_emojis(ext_title)
                        if not self.job.title or self.job.title in ("Media Download", "Initializing..."):
                            self.job.title = clean_ext or ext_title
                    if info.get("uploader") and not self.job.uploader:
                        self.job.uploader = info.get("uploader")
                    if info.get("duration") and not self.job.duration:
                        self.job.duration = float(info.get("duration", 0.0))

            # -----------------------------------------------------------------
            # Comprehensive Discovery of the Resulting Merged / Downloaded File
            # -----------------------------------------------------------------
            raw_candidates: List[str] = []

            # 1. Post-processor finished files (in reverse order)
            for fn in reversed(postprocessed_files):
                raw_candidates.append(fn)

            # 2. Main info dict filenames
            if info:
                if info.get("_filename"):
                    raw_candidates.append(info["_filename"])
                if info.get("filepath"):
                    raw_candidates.append(info["filepath"])

                # 3. Requested downloads list
                for req in (info.get("requested_downloads") or []):
                    if req.get("_filename"):
                        raw_candidates.append(req["_filename"])
                    if req.get("filepath"):
                        raw_candidates.append(req["filepath"])

                # 4. Prepared filename variants
                try:
                    prep = ydl.prepare_filename(info)
                    raw_candidates.append(prep)
                except Exception:
                    pass

            # 5. Progress finished files
            for fn in reversed(finished_files):
                raw_candidates.append(fn)

            # Expand raw candidates: strip stream ID suffixes (e.g. .f399.mp4 -> .mp4) and test extensions
            candidates: List[str] = []
            for c in raw_candidates:
                if not c:
                    continue
                candidates.append(c)
                # Strip stream suffixes like .f399.mp4, .f140.m4a
                cleaned_c = re.sub(r'\.f\d+\.', '.', c)
                if cleaned_c != c:
                    candidates.append(cleaned_c)
                # Test target container suffix
                target_cand = str(Path(cleaned_c).with_suffix("." + target_container))
                if target_cand not in candidates:
                    candidates.append(target_cand)

            # Find first candidate that actually exists and is non-empty
            final_path: Optional[str] = None
            for cand in candidates:
                if not cand:
                    continue
                p = Path(cand)
                if p.is_file() and p.stat().st_size > 0 and not p.name.endswith((".part", ".ytdl")):
                    # Ensure it's not a lingering unmerged stream file if the merged version exists
                    if re.search(r'\.f\d+\.', p.name):
                        merged_attempt = p.parent / re.sub(r'\.f\d+\.', '.', p.name)
                        if merged_attempt.is_file() and merged_attempt.stat().st_size > 0:
                            final_path = str(merged_attempt.resolve())
                            break
                    final_path = str(p.resolve())
                    break

            # If still not found, search the destination directory for non-part files created/modified recently
            if not final_path:
                existing_files = [f for f in dest_dir.iterdir() if f.is_file() and not f.name.endswith((".part", ".ytdl"))]
                # Filter files modified around this job run
                recent = [f for f in existing_files if f.stat().st_mtime >= (start_time - 60)]
                if recent:
                    recent.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                    final_path = str(recent[0].resolve())
                elif existing_files:
                    search_key = sanitize_filename(self.job.title).lower()[:15]
                    matched = [f for f in existing_files if search_key and search_key in f.name.lower()]
                    if matched:
                        matched.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                        final_path = str(matched[0].resolve())

            if not final_path:
                final_path = str((dest_dir / (self.job.output_filename or f"{sanitize_filename(self.job.title)}.{target_container}")).resolve())

            self.job.final_file_path = final_path
            logger.log_download(f"yt-dlp download finished. Final resolved file: '{final_path}'")
            return self.job.final_file_path

        except ProgressCancelledException:
            logger.log_download(f"Download of '{self.job.title}' was paused/cancelled.")
            raise
        except yt_dlp.utils.DownloadError as de:
            err_msg = str(de)
            logger.log_download(f"yt-dlp DownloadError: {err_msg}", "ERROR")
            if any(k in err_msg.lower() for k in ["private video", "sign in", "copyright", "removed", "not available"]):
                raise FatalDownloadError(err_msg)
            raise RecoverableDownloadError(err_msg)
        except Exception as e:
            logger.log_download(f"Download exception: {e}", "ERROR")
            raise RecoverableDownloadError(str(e))
