"""
Structured multi-channel logging system with credential sanitization.
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Callable, Optional

# Regex patterns to sanitize sensitive credentials
SENSITIVE_PATTERNS = [
    re.compile(r'(cookie[s]?\s*[:=]\s*)[^\s;,\'\"]+', re.IGNORECASE),
    re.compile(r'(--add-header\s+["\']?Cookie:[^"\'\n]+)', re.IGNORECASE),
    re.compile(r'(password[s]?\s*[:=]\s*)[^\s;,\'\"]+', re.IGNORECASE),
    re.compile(r'(api[_-]?key\s*[:=]\s*)[^\s;,\'\"]+', re.IGNORECASE),
    re.compile(r'(bearer\s+[a-zA-Z0-9_\-\.]+)', re.IGNORECASE),
    re.compile(r'(token\s*[:=]\s*)[^\s;,\'\"]+', re.IGNORECASE),
]


def sanitize_log_message(msg: str) -> str:
    """Masks credentials, tokens, and sensitive headers in log strings."""
    if not isinstance(msg, str):
        msg = str(msg)
    for pattern in SENSITIVE_PATTERNS:
        msg = pattern.sub(r'\1[REDACTED]', msg)
    return msg


class SanitizingFormatter(logging.Formatter):
    """Logging Formatter that strips out sensitive credentials and tokens."""
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return sanitize_log_message(original)


class LogHub:
    """
    Central logging hub managing log files and real-time subscribers for the UI.
    """
    _instance: Optional['LogHub'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogHub, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.subscribers: list[Callable[[str, str, str], None]] = []
        self.logs_dir = Path("logs").resolve()
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._setup_loggers()

    def _setup_loggers(self):
        fmt = SanitizingFormatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # 1. Main App Logger
        self.app_logger = logging.getLogger("app")
        self.app_logger.setLevel(logging.DEBUG)
        app_handler = RotatingFileHandler(
            self.logs_dir / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        app_handler.setFormatter(fmt)
        self.app_logger.addHandler(app_handler)

        # 2. Download Logger
        self.download_logger = logging.getLogger("download")
        self.download_logger.setLevel(logging.DEBUG)
        dl_handler = RotatingFileHandler(
            self.logs_dir / "download.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        dl_handler.setFormatter(fmt)
        self.download_logger.addHandler(dl_handler)

        # 3. FFmpeg Logger
        self.ffmpeg_logger = logging.getLogger("ffmpeg")
        self.ffmpeg_logger.setLevel(logging.DEBUG)
        ff_handler = RotatingFileHandler(
            self.logs_dir / "ffmpeg.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        ff_handler.setFormatter(fmt)
        self.ffmpeg_logger.addHandler(ff_handler)

        # 4. Error Logger
        self.error_logger = logging.getLogger("error")
        self.error_logger.setLevel(logging.ERROR)
        err_handler = RotatingFileHandler(
            self.logs_dir / "error.log", maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        err_handler.setFormatter(fmt)
        self.error_logger.addHandler(err_handler)

        # Console handler for debugging
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(fmt)
        self.app_logger.addHandler(console_handler)

    def subscribe(self, callback: Callable[[str, str, str], None]):
        """Subscribe a UI handler: callback(channel, level, message)."""
        if callback not in self.subscribers:
            self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str, str, str], None]):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def _notify(self, channel: str, level: str, msg: str):
        sanitized = sanitize_log_message(msg)
        for sub in list(self.subscribers):
            try:
                sub(channel, level, sanitized)
            except Exception:
                pass

    def log_app(self, msg: str, level: str = "INFO"):
        sanitized = sanitize_log_message(msg)
        getattr(self.app_logger, level.lower(), self.app_logger.info)(sanitized)
        if level.upper() in ("ERROR", "CRITICAL"):
            self.error_logger.error(f"[App] {sanitized}")
        self._notify("App", level.upper(), sanitized)

    def log_download(self, msg: str, level: str = "INFO"):
        sanitized = sanitize_log_message(msg)
        getattr(self.download_logger, level.lower(), self.download_logger.info)(sanitized)
        if level.upper() in ("ERROR", "CRITICAL"):
            self.error_logger.error(f"[Download] {sanitized}")
        self._notify("Download", level.upper(), sanitized)

    def log_ffmpeg(self, msg: str, level: str = "INFO"):
        sanitized = sanitize_log_message(msg)
        getattr(self.ffmpeg_logger, level.lower(), self.ffmpeg_logger.info)(sanitized)
        if level.upper() in ("ERROR", "CRITICAL"):
            self.error_logger.error(f"[FFmpeg] {sanitized}")
        self._notify("FFmpeg", level.upper(), sanitized)

    def log_error(self, msg: str, exc_info: bool = False):
        sanitized = sanitize_log_message(msg)
        self.error_logger.error(sanitized, exc_info=exc_info)
        self.app_logger.error(sanitized, exc_info=exc_info)
        self._notify("Error", "ERROR", sanitized)


# Global singleton instance
logger = LogHub()
