"""
Download speed limiting configuration.
"""

from typing import Optional


class SpeedLimiter:
    """Manages rate limit values for yt-dlp."""

    @staticmethod
    def get_ratelimit_bytes(limit_setting: int) -> Optional[int]:
        """Returns rate limit in bytes/sec or None for unlimited."""
        return limit_setting if limit_setting > 0 else None
