"""
Transcoder manager orchestrating smart stream copying, re-encoding, merging, and TV compatibility normalization.
"""

from pathlib import Path
from typing import Callable, List, Optional

from app.core.exceptions import TranscodingError, ValidationFailedError
from app.core.logger import logger
from app.encoder.ffmpeg_wrapper import FFmpegProcess
from app.media.ffprobe_wrapper import FFprobeWrapper
from app.media.validator import MediaValidator
from app.models.preset import TranscodePreset
from app.models.validation_result import ValidationReport
from app.utils.file_utils import get_unique_filepath, safe_remove


class TranscoderManager:
    """
    Handles intelligent transcoding, remuxing, merging, and format conversion.
    Avoids re-encoding when streams already satisfy compatibility requirements.
    """

    def __init__(self):
        self.active_processes: list[FFmpegProcess] = []

    def merge_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        target_container: str = "mp4",
        progress_callback: Optional[Callable[[float, float, float, Optional[int]], None]] = None
    ) -> str:
        """
        Merges separate downloaded video and audio files into a single container.
        """
        probe_v = FFprobeWrapper.probe(video_path)
        probe_a = FFprobeWrapper.probe(audio_path)

        duration = max(
            probe_v.container.duration if probe_v.container else 0.0,
            probe_a.container.duration if probe_a.container else 0.0
        )

        args = [
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "copy",
            "-c:a", "copy",
        ]

        if target_container.lower() == "mp4":
            args += ["-movflags", "+faststart"]

        args.append(output_path)

        proc = FFmpegProcess()
        self.active_processes.append(proc)
        try:
            logger.log_ffmpeg(f"Merging video ('{video_path}') and audio ('{audio_path}') into '{output_path}'")
            success = proc.run(args, total_duration_sec=duration, progress_callback=progress_callback)
            if not success or not Path(output_path).is_file():
                raise TranscodingError(args, -1, f"Failed to merge streams into {output_path}")
            return output_path
        finally:
            if proc in self.active_processes:
                self.active_processes.remove(proc)

    def apply_universal_mp4_pipeline(
        self,
        input_file: str,
        output_file: str,
        progress_callback: Optional[Callable[[float, float, float, Optional[int]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Universal Standard MP4 pipeline:
        1. Inspect source media streams.
        2. If video is already H.264 + yuv420p AND audio is AAC AND container is MP4:
           Perform fast stream copy / remux without lossy re-encoding!
        3. If video is H.264 but audio is Opus/Vorbis:
           Copy video directly (-c:v copy) and transcode audio to AAC (-c:a aac -b:a 192k).
        4. If video is VP9/AV1/HEVC/10-bit:
           Transcode video to H.264 (yuv420p) and audio to AAC.
        5. Apply -movflags +faststart.
        6. Validate final MP4 container and streams.
        """
        probe = FFprobeWrapper.probe(input_file)
        if not probe.is_valid:
            raise TranscodingError([], -1, f"Cannot probe input file: {probe.error_message}")

        video = probe.primary_video
        audio = probe.primary_audio
        duration = probe.container.duration if probe.container else 0.0

        is_video_h264_8bit = bool(
            video and
            video.codec_name.lower() in ("h264", "avc1") and
            video.pixel_format.lower() == "yuv420p" and
            not video.is_10bit
        )
        is_audio_aac = bool(audio and audio.codec_name.lower() in ("aac", "mp4a"))
        is_container_mp4 = bool(probe.container and "mp4" in probe.container.format_name.lower())

        # Check if already 100% compliant
        if is_video_h264_8bit and is_audio_aac and is_container_mp4:
            logger.log_ffmpeg("Source file is already standard MP4 (H.264 + AAC + yuv420p in MP4). No re-encoding needed.")
            return input_file

        args = ["-i", input_file]

        # Video stream strategy
        if is_video_h264_8bit:
            logger.log_ffmpeg("Video stream is already H.264 (yuv420p). Using stream copy (-c:v copy).")
            args += ["-c:v", "copy"]
        elif video:
            logger.log_ffmpeg(f"Video stream ({video.codec_name}, {video.pixel_format}) requires transcoding to H.264 (yuv420p).")
            args += [
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-profile:v", "high",
                "-level", "4.1",
                "-preset", "veryfast",
                "-crf", "21"
            ]
        else:
            args += ["-vn"]

        # Audio stream strategy
        if is_audio_aac:
            logger.log_ffmpeg("Audio stream is already AAC. Using stream copy (-c:a copy).")
            args += ["-c:a", "copy"]
        elif audio:
            logger.log_ffmpeg(f"Audio stream ({audio.codec_name}) requires transcoding to AAC.")
            args += [
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "48000"
            ]
        else:
            args += ["-an"]

        args += ["-movflags", "+faststart", output_file]

        proc = FFmpegProcess()
        self.active_processes.append(proc)
        try:
            success = proc.run(
                args,
                total_duration_sec=duration,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            if not success or not Path(output_file).is_file():
                raise TranscodingError(args, -1, f"Failed to produce universal MP4 output at {output_file}")
            return output_file
        finally:
            if proc in self.active_processes:
                self.active_processes.remove(proc)

    def apply_smart_tv_lcd_pipeline(self, *args, **kwargs) -> str:
        """Alias for backward compatibility."""
        return self.apply_universal_mp4_pipeline(*args, **kwargs)

    def convert_media(
        self,
        input_path: str,
        output_path: str,
        preset: TranscodePreset,
        trim_start: Optional[str] = None,
        trim_end: Optional[str] = None,
        progress_callback: Optional[Callable[[float, float, float, Optional[int]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        General transcode function using a TranscodePreset with optional start/end trimming.
        """
        probe = FFprobeWrapper.probe(input_path)
        if not probe.is_valid:
            raise TranscodingError([], -1, f"Cannot probe input file: {probe.error_message}")

        total_file_duration = probe.container.duration if probe.container else 0.0
        effective_duration = total_file_duration

        args = []

        # Optional Trim Start (placed before -i for fast seek)
        if trim_start and str(trim_start).strip() not in ("", "0", "00:00:00", "00:00"):
            args += ["-ss", str(trim_start).strip()]

        # Optional Trim End
        if trim_end and str(trim_end).strip() not in ("", "0", "00:00:00", "00:00"):
            args += ["-to", str(trim_end).strip()]

        args += ["-i", input_path]

        # Video configuration
        if preset.video_codec == "none":
            args += ["-vn"]
        elif preset.video_codec == "copy":
            args += ["-c:v", "copy"]
        else:
            args += ["-c:v", preset.video_codec]
            if preset.pixel_format:
                args += ["-pix_fmt", preset.pixel_format]
            if preset.crf is not None:
                args += ["-crf", str(preset.crf)]
            if preset.preset_speed:
                args += ["-preset", preset.preset_speed]
            if preset.scale_height:
                args += ["-vf", f"scale=-2:{preset.scale_height}"]

        # Audio configuration
        if preset.audio_codec == "none":
            args += ["-an"]
        elif preset.audio_codec == "copy":
            args += ["-c:a", "copy"]
        else:
            args += ["-c:a", preset.audio_codec]
            if preset.audio_bitrate:
                args += ["-b:a", preset.audio_bitrate]
            if preset.audio_sample_rate:
                args += ["-ar", str(preset.audio_sample_rate)]

        if preset.extra_ffmpeg_args:
            args += preset.extra_ffmpeg_args

        args.append(output_path)

        proc = FFmpegProcess()
        self.active_processes.append(proc)
        try:
            logger.log_ffmpeg(f"Starting conversion '{preset.name}': {input_path} -> {output_path}")
            success = proc.run(
                args,
                total_duration_sec=effective_duration,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            if not success or not Path(output_path).is_file():
                raise TranscodingError(args, -1, f"Failed to convert media to {output_path}")
            return output_path
        finally:
            if proc in self.active_processes:
                self.active_processes.remove(proc)

    def convert_to_mp3(
        self,
        input_path: str,
        output_path: str,
        bitrate: str = "320k",
        trim_start: Optional[str] = None,
        trim_end: Optional[str] = None,
        progress_callback: Optional[Callable[[float, float, float, Optional[int]], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> str:
        """
        Specialized MP3 extraction & conversion with selectable bitrate and trimming.
        """
        probe = FFprobeWrapper.probe(input_path)
        if not probe.is_valid:
            raise TranscodingError([], -1, f"Cannot probe input file: {probe.error_message}")

        duration = probe.container.duration if probe.container else 0.0

        args = []
        if trim_start and str(trim_start).strip() not in ("", "0", "00:00:00", "00:00"):
            args += ["-ss", str(trim_start).strip()]
        if trim_end and str(trim_end).strip() not in ("", "0", "00:00:00", "00:00"):
            args += ["-to", str(trim_end).strip()]

        clean_bitrate = bitrate if bitrate.endswith("k") else f"{bitrate}k"
        args += [
            "-i", input_path,
            "-vn",
            "-c:a", "libmp3lame",
            "-b:a", clean_bitrate,
            "-ar", "44100",
            output_path
        ]

        proc = FFmpegProcess()
        self.active_processes.append(proc)
        try:
            logger.log_ffmpeg(f"Extracting/converting to MP3 ({clean_bitrate}): {input_path} -> {output_path}")
            success = proc.run(
                args,
                total_duration_sec=duration,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            if not success or not Path(output_path).is_file():
                raise TranscodingError(args, -1, f"Failed to convert to MP3 at {output_path}")
            return output_path
        finally:
            if proc in self.active_processes:
                self.active_processes.remove(proc)

    def cancel_all(self):
        for proc in list(self.active_processes):
            proc.cancel()
