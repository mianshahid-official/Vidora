"""
FFmpeg subprocess runner with real-time stderr progress parsing and cancellation.
"""

import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

from app.core.dependencies import deps
from app.core.exceptions import TranscodingError
from app.core.logger import logger

# Regex patterns for FFmpeg progress line parsing
TIME_PATTERN = re.compile(r'time=(\d+):(\d+):(\d+\.\d+|\d+)')
FPS_PATTERN = re.compile(r'fps=\s*(\d+(?:\.\d+)?)')
SPEED_PATTERN = re.compile(r'speed=\s*(\d+(?:\.\d+)?)x')


class FFmpegProcess:
    """Executes an FFmpeg command while streaming progress and handling cancellation."""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._cancelled: bool = False
        self._paused: bool = False

    def cancel(self):
        self._cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                # Give it a moment to terminate gracefully, otherwise kill
                time.sleep(0.5)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception:
                pass

    def run(
        self,
        args: List[str],
        total_duration_sec: Optional[float] = None,
        progress_callback: Optional[Callable[[float, float, float, Optional[int]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> bool:
        """
        Executes FFmpeg with the given argument list.
        progress_callback(percent: float, fps: float, speed: float, eta_sec: Optional[int])
        """
        ffmpeg_bin = deps.ffmpeg_path
        if not ffmpeg_bin:
            raise TranscodingError(args, -1, "FFmpeg binary was not found.")

        cmd = [ffmpeg_bin, "-y", "-hide_banner"] + args
        cmd_str = " ".join(f'"{a}"' if " " in a else a for a in cmd)
        logger.log_ffmpeg(f"Executing FFmpeg: {cmd_str}")

        stderr_lines = []

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            # Read stderr line by line
            for line in self.process.stderr:
                if self._cancelled:
                    break

                stripped = line.strip()
                if not stripped:
                    continue

                stderr_lines.append(stripped)
                if log_callback:
                    log_callback(stripped)

                # Parse progress
                if "time=" in stripped:
                    time_match = TIME_PATTERN.search(stripped)
                    fps_match = FPS_PATTERN.search(stripped)
                    speed_match = SPEED_PATTERN.search(stripped)

                    current_sec = 0.0
                    fps = 0.0
                    speed = 1.0
                    eta_sec = None

                    if time_match:
                        h = float(time_match.group(1))
                        m = float(time_match.group(2))
                        s = float(time_match.group(3))
                        current_sec = h * 3600 + m * 60 + s

                    if fps_match:
                        try:
                            fps = float(fps_match.group(1))
                        except ValueError:
                            pass

                    if speed_match:
                        try:
                            speed = float(speed_match.group(1))
                        except ValueError:
                            pass

                    percent = 0.0
                    if total_duration_sec and total_duration_sec > 0:
                        percent = min(99.9, max(0.0, (current_sec / total_duration_sec) * 100.0))
                        remaining_sec = max(0.0, total_duration_sec - current_sec)
                        if speed > 0:
                            eta_sec = int(remaining_sec / speed)

                    if progress_callback:
                        progress_callback(percent, fps, speed, eta_sec)

            self.process.wait()
            ret_code = self.process.returncode

            if self._cancelled:
                logger.log_ffmpeg("FFmpeg operation was cancelled by user.")
                return False

            if ret_code != 0:
                full_err = "\n".join(stderr_lines[-30:])
                logger.log_ffmpeg(f"FFmpeg failed with code {ret_code}:\n{full_err}", "ERROR")
                raise TranscodingError(cmd, ret_code, full_err)

            if progress_callback:
                progress_callback(100.0, 0.0, 0.0, 0)

            logger.log_ffmpeg("FFmpeg operation finished successfully.")
            return True

        except Exception as e:
            if not self._cancelled:
                logger.log_ffmpeg(f"FFmpeg execution error: {e}", "ERROR")
                raise e
            return False
        finally:
            self.process = None
