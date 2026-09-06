"""
FFprobe wrapper for deep stream and container inspection.
"""

import json
import subprocess
from pathlib import Path
from typing import Optional

from app.core.dependencies import deps
from app.core.exceptions import ProbeError
from app.core.logger import logger
from app.models.media_info import (
    AudioStreamInfo,
    ContainerInfo,
    MediaProbeResult,
    VideoStreamInfo,
)


class FFprobeWrapper:
    """Invokes ffprobe with JSON output and parses all stream and format properties."""

    @staticmethod
    def probe(file_path: str) -> MediaProbeResult:
        ffprobe_bin = deps.ffprobe_path
        if not ffprobe_bin:
            return MediaProbeResult(
                file_path=file_path,
                is_valid=False,
                error_message="FFprobe executable is not configured or found."
            )

        p = Path(file_path).resolve()
        if not p.is_file() or p.stat().st_size == 0:
            return MediaProbeResult(
                file_path=file_path,
                is_valid=False,
                error_message=f"File does not exist or is 0 bytes: {file_path}"
            )

        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries",
            "format=format_name,format_long_name,duration,size,bit_rate,nb_streams:stream=index,codec_name,codec_long_name,codec_type,profile,level,width,height,r_frame_rate,avg_frame_rate,pix_fmt,bit_rate,duration,nb_frames,display_aspect_ratio,color_space,channels,channel_layout,sample_rate:stream_tags=language",
            "-of", "json",
            str(p)
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode != 0:
                err_text = res.stderr.strip() or f"ffprobe exited with code {res.returncode}"
                return MediaProbeResult(
                    file_path=file_path,
                    is_valid=False,
                    error_message=err_text
                )

            data = json.loads(res.stdout)
            return FFprobeWrapper._parse_ffprobe_json(file_path, data)

        except subprocess.TimeoutExpired:
            return MediaProbeResult(
                file_path=file_path,
                is_valid=False,
                error_message="FFprobe inspection timed out."
            )
        except Exception as e:
            return MediaProbeResult(
                file_path=file_path,
                is_valid=False,
                error_message=str(e)
            )

    @staticmethod
    def _parse_ffprobe_json(file_path: str, data: dict) -> MediaProbeResult:
        format_data = data.get("format", {})
        streams_data = data.get("streams", [])

        container = ContainerInfo(
            format_name=format_data.get("format_name", "unknown"),
            format_long_name=format_data.get("format_long_name", ""),
            duration=float(format_data.get("duration", 0.0) or 0.0),
            size_bytes=int(format_data.get("size", 0) or 0),
            bitrate=int(format_data.get("bit_rate", 0) or 0),
            nb_streams=int(format_data.get("nb_streams", len(streams_data)) or 0),
            tags=format_data.get("tags", {})
        )

        video_streams: list[VideoStreamInfo] = []
        audio_streams: list[AudioStreamInfo] = []

        for s in streams_data:
            codec_type = s.get("codec_type", "").lower()
            if codec_type == "video":
                # Calculate FPS
                fps = 0.0
                r_fps = s.get("r_frame_rate", "")
                if "/" in r_fps:
                    num, den = r_fps.split("/")
                    if float(den) > 0:
                        fps = float(num) / float(den)
                elif r_fps:
                    try:
                        fps = float(r_fps)
                    except ValueError:
                        pass

                pix_fmt = s.get("pix_fmt", "")
                is_10bit = "10" in pix_fmt or "12" in pix_fmt
                color_space = s.get("color_space", "")
                is_hdr = "bt2020" in color_space.lower() or "smpte2084" in color_space.lower() or "arib-std-b67" in color_space.lower()

                level = None
                raw_level = s.get("level")
                if raw_level is not None:
                    try:
                        level = int(raw_level)
                    except ValueError:
                        pass

                video_streams.append(VideoStreamInfo(
                    index=int(s.get("index", len(video_streams))),
                    codec_name=s.get("codec_name", "unknown"),
                    codec_long_name=s.get("codec_long_name", ""),
                    profile=s.get("profile", ""),
                    level=level,
                    width=int(s.get("width", 0) or 0),
                    height=int(s.get("height", 0) or 0),
                    fps=round(fps, 2),
                    pixel_format=pix_fmt,
                    bitrate=int(s.get("bit_rate", 0)) if s.get("bit_rate") else None,
                    duration=float(s.get("duration", 0.0)) if s.get("duration") else None,
                    nb_frames=int(s.get("nb_frames", 0)) if s.get("nb_frames") else None,
                    aspect_ratio=s.get("display_aspect_ratio", ""),
                    color_space=color_space,
                    is_hdr=is_hdr,
                    is_10bit=is_10bit
                ))

            elif codec_type == "audio":
                tags = s.get("tags", {})
                audio_streams.append(AudioStreamInfo(
                    index=int(s.get("index", len(audio_streams))),
                    codec_name=s.get("codec_name", "unknown"),
                    codec_long_name=s.get("codec_long_name", ""),
                    channels=int(s.get("channels", 0) or 0),
                    channel_layout=s.get("channel_layout", ""),
                    sample_rate=int(s.get("sample_rate", 0) or 0),
                    bitrate=int(s.get("bit_rate", 0)) if s.get("bit_rate") else None,
                    duration=float(s.get("duration", 0.0)) if s.get("duration") else None,
                    language=tags.get("language", "")
                ))

        return MediaProbeResult(
            file_path=file_path,
            is_valid=True,
            container=container,
            video_streams=video_streams,
            audio_streams=audio_streams,
            raw_data=data
        )
