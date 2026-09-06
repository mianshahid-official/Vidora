"""
Custom exceptions for Vidora.
"""


class DownloaderException(Exception):
    """Base exception for all downloader-related errors."""
    pass


class DependencyNotFoundError(DownloaderException):
    """Raised when a required external binary (yt-dlp, FFmpeg, FFprobe) is missing."""
    def __init__(self, binary_name: str, message: str = ""):
        self.binary_name = binary_name
        msg = message or f"Required dependency '{binary_name}' was not found on the system."
        super().__init__(msg)


class AudioMissingError(DownloaderException):
    """Raised when media validation fails because a requested audio stream is absent."""
    def __init__(self, file_path: str, details: str = ""):
        self.file_path = file_path
        self.details = details
        msg = f"Download completed but audio stream was not detected in '{file_path}'."
        if details:
            msg += f" Details: {details}"
        super().__init__(msg)


class ValidationFailedError(DownloaderException):
    """Raised when post-download FFprobe validation fails (invalid container, 0 bytes, corrupted streams)."""
    def __init__(self, file_path: str, reason: str):
        self.file_path = file_path
        self.reason = reason
        super().__init__(f"Validation failed for '{file_path}': {reason}")


class RecoverableDownloadError(DownloaderException):
    """Errors that can be safely retried (e.g. temporary network timeout, 429 throttling)."""
    pass


class FatalDownloadError(DownloaderException):
    """Errors that should NOT be retried (e.g. video removed, private video, DRM protected)."""
    pass


class TranscodingError(DownloaderException):
    """Raised when FFmpeg remuxing, merging, or transcoding fails."""
    def __init__(self, command: list[str], returncode: int, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"FFmpeg process failed with exit code {returncode}.\nError details:\n{stderr[-1000:]}")


class ProbeError(DownloaderException):
    """Raised when FFprobe fails to inspect media."""
    pass
