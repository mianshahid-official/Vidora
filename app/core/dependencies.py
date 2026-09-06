"""
Dependency detector, path resolver, and manager for yt-dlp, FFmpeg, and FFprobe.
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.logger import logger


@dataclass
class DependencyStatus:
    name: str
    is_available: bool
    version: str
    path: str
    error_message: Optional[str] = None


class DependencyManager:
    """Manages detection and inspection of required external tools."""

    def __init__(self, custom_ffmpeg_dir: Optional[str] = None):
        self.custom_ffmpeg_dir = custom_ffmpeg_dir
        self._ffmpeg_path: Optional[str] = None
        self._ffprobe_path: Optional[str] = None
        self._ytdlp_path: Optional[str] = None
        self.refresh()

    def refresh(self):
        """Re-detects all dependencies."""
        self._ffmpeg_path = self._find_binary("ffmpeg")
        self._ffprobe_path = self._find_binary("ffprobe")
        self._ytdlp_path = self._find_ytdlp()

    def _find_binary(self, binary_name: str) -> Optional[str]:
        # 1. Custom directory if specified
        if self.custom_ffmpeg_dir:
            cand = Path(self.custom_ffmpeg_dir) / (binary_name + (".exe" if os.name == "nt" else ""))
            if cand.is_file() and os.access(cand, os.X_OK):
                return str(cand.resolve())

        # 2. Local app bin directory if bundled
        local_bin = Path("bin") / (binary_name + (".exe" if os.name == "nt" else ""))
        if local_bin.is_file() and os.access(local_bin, os.X_OK):
            return str(local_bin.resolve())

        # 3. System PATH
        found = shutil.which(binary_name)
        if found:
            return str(Path(found).resolve())

        return None

    def _find_ytdlp(self) -> Optional[str]:
        # Check if yt-dlp is importable in current python environment
        try:
            import yt_dlp
            return yt_dlp.__file__
        except ImportError:
            # Fallback to binary in PATH
            found = shutil.which("yt-dlp")
            return str(Path(found).resolve()) if found else None

    @property
    def ffmpeg_path(self) -> Optional[str]:
        return self._ffmpeg_path

    @property
    def ffprobe_path(self) -> Optional[str]:
        return self._ffprobe_path

    @property
    def ytdlp_path(self) -> Optional[str]:
        return self._ytdlp_path

    def get_ffmpeg_status(self) -> DependencyStatus:
        if not self._ffmpeg_path:
            return DependencyStatus("FFmpeg", False, "Missing", "", "FFmpeg executable not found in PATH or configured directory.")
        try:
            res = subprocess.run([self._ffmpeg_path, "-version"], capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if res.returncode == 0:
                first_line = res.stdout.splitlines()[0] if res.stdout else "Available"
                version = first_line.split("version")[-1].split("Copyright")[0].strip() if "version" in first_line else first_line
                return DependencyStatus("FFmpeg", True, version, self._ffmpeg_path)
            return DependencyStatus("FFmpeg", False, "Error", self._ffmpeg_path, f"Returned non-zero exit code: {res.returncode}")
        except Exception as e:
            return DependencyStatus("FFmpeg", False, "Error", self._ffmpeg_path, str(e))

    def get_ffprobe_status(self) -> DependencyStatus:
        if not self._ffprobe_path:
            return DependencyStatus("FFprobe", False, "Missing", "", "FFprobe executable not found in PATH or configured directory.")
        try:
            res = subprocess.run([self._ffprobe_path, "-version"], capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if res.returncode == 0:
                first_line = res.stdout.splitlines()[0] if res.stdout else "Available"
                version = first_line.split("version")[-1].split("Copyright")[0].strip() if "version" in first_line else first_line
                return DependencyStatus("FFprobe", True, version, self._ffprobe_path)
            return DependencyStatus("FFprobe", False, "Error", self._ffprobe_path, f"Returned non-zero exit code: {res.returncode}")
        except Exception as e:
            return DependencyStatus("FFprobe", False, "Error", self._ffprobe_path, str(e))

    def get_ytdlp_status(self) -> DependencyStatus:
        try:
            import yt_dlp
            version = getattr(yt_dlp, "__version__", "Installed")
            return DependencyStatus("yt-dlp", True, version, getattr(yt_dlp, "__file__", "Python Package"))
        except ImportError:
            pass

        if self._ytdlp_path:
            try:
                res = subprocess.run([self._ytdlp_path, "--version"], capture_output=True, text=True, timeout=5, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                if res.returncode == 0:
                    version = res.stdout.strip()
                    return DependencyStatus("yt-dlp", True, version, self._ytdlp_path)
            except Exception as e:
                return DependencyStatus("yt-dlp", False, "Error", self._ytdlp_path, str(e))

        return DependencyStatus("yt-dlp", False, "Missing", "", "yt-dlp python package or binary not found.")

    def check_all(self) -> dict[str, DependencyStatus]:
        self.refresh()
        return {
            "ffmpeg": self.get_ffmpeg_status(),
            "ffprobe": self.get_ffprobe_status(),
            "ytdlp": self.get_ytdlp_status(),
        }

    def update_ytdlp(self) -> tuple[bool, str]:
        """Attempts to update yt-dlp via python pip."""
        try:
            logger.log_app("Attempting to update yt-dlp...")
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if res.returncode == 0:
                logger.log_app("yt-dlp updated successfully: " + res.stdout)
                return True, "yt-dlp updated successfully!\n" + res.stdout
            else:
                logger.log_app(f"yt-dlp update failed: {res.stderr}", "ERROR")
                return False, f"Update failed (code {res.returncode}):\n{res.stderr}"
        except Exception as e:
            logger.log_app(f"yt-dlp update exception: {e}", "ERROR")
            return False, f"Failed to run update: {e}"


# Global manager singleton
deps = DependencyManager()
