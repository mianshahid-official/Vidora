"""
Metadata extractor for single URLs, playlists, and channels using yt-dlp.
"""

from typing import Optional
import yt_dlp

from app.core.config import config_manager
from app.core.dependencies import deps
from app.core.exceptions import FatalDownloadError, RecoverableDownloadError
from app.core.logger import logger
from app.downloader.format_parser import FormatParser
from app.models.format_info import MediaMetadata
from app.utils.url_utils import detect_platform


class MetadataExtractor:
    """Extracts media metadata, formats, and thumbnails without downloading."""

    @staticmethod
    def extract_info(url: str, process_formats: bool = True) -> MediaMetadata:
        settings = config_manager.settings
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": not process_formats,
            "socket_timeout": 15,
        }

        # Check for cookies configuration
        if settings.use_cookies:
            if settings.cookies_source in ("chrome", "firefox", "edge", "opera", "brave", "vivaldi"):
                ydl_opts["cookiesfrombrowser"] = (settings.cookies_source,)
            elif settings.cookies_source == "file" and settings.cookies_file_path:
                ydl_opts["cookiefile"] = settings.cookies_file_path

        # User-agent and Proxy
        if settings.user_agent:
            ydl_opts["user_agent"] = settings.user_agent
        if settings.proxy_url:
            ydl_opts["proxy"] = settings.proxy_url

        if deps.ffmpeg_path:
            ydl_opts["ffmpeg_location"] = deps.ffmpeg_path

        try:
            logger.log_app(f"Extracting metadata for URL: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if not info:
                raise FatalDownloadError(f"No metadata could be retrieved for '{url}'.")

            # Handle playlists/multi-entries
            is_playlist = info.get("_type") == "playlist" or "entries" in info
            playlist_count = len(info.get("entries", [])) if is_playlist else None

            # For playlist root, extract first entry for preview if available
            entry = info
            if is_playlist and info.get("entries"):
                entries = list(info["entries"])
                if entries and entries[0]:
                    entry = entries[0]

            duration = float(entry.get("duration", 0.0) or 0.0)
            raw_formats = entry.get("formats", [])
            parsed_formats = FormatParser.parse_formats(raw_formats, duration=duration) if process_formats else []

            title = entry.get("title", "Unknown Title") or info.get("title", "Unknown Playlist")
            uploader = entry.get("uploader") or entry.get("channel") or info.get("uploader") or ""
            platform = detect_platform(url)

            # Choose best thumbnail
            thumbnail = entry.get("thumbnail") or info.get("thumbnail")
            if not thumbnail and entry.get("thumbnails"):
                thumbnail = entry["thumbnails"][-1].get("url")

            metadata = MediaMetadata(
                url=url,
                extractor=entry.get("extractor", info.get("extractor", "generic")),
                extractor_key=entry.get("extractor_key", info.get("extractor_key", "Generic")),
                id=str(entry.get("id", info.get("id", ""))),
                title=title,
                duration=duration,
                thumbnail=thumbnail,
                uploader=uploader,
                uploader_id=entry.get("uploader_id"),
                channel=entry.get("channel"),
                upload_date=entry.get("upload_date"),
                view_count=entry.get("view_count"),
                like_count=entry.get("like_count"),
                description=entry.get("description", ""),
                webpage_url=entry.get("webpage_url", url),
                is_live=bool(entry.get("is_live", False)),
                is_playlist=is_playlist,
                playlist_count=playlist_count,
                formats=parsed_formats,
                raw_info=entry
            )

            logger.log_app(f"Successfully extracted: '{metadata.title}' ({len(metadata.formats)} formats found)")
            return metadata

        except yt_dlp.utils.DownloadError as de:
            err_msg = str(de)
            logger.log_error(f"yt-dlp extract error for '{url}': {err_msg}")
            if any(k in err_msg.lower() for k in ["private video", "sign in", "copyright", "removed", "not available"]):
                raise FatalDownloadError(err_msg)
            raise RecoverableDownloadError(err_msg)
        except Exception as e:
            logger.log_error(f"Unexpected extraction error for '{url}': {e}", exc_info=True)
            raise RecoverableDownloadError(str(e))
