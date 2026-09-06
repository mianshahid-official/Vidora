"""
Unit tests for yt-dlp format tree parsing and stream categorization.
"""

from app.downloader.format_parser import FormatParser


def test_format_parser_categorization():
    raw_formats = [
        {
            "format_id": "137",
            "ext": "mp4",
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "vcodec": "avc1.640028",
            "acodec": "none",
            "tbr": 4500,
            "filesize": 50000000,
        },
        {
            "format_id": "140",
            "ext": "m4a",
            "vcodec": "none",
            "acodec": "mp4a.40.2",
            "abr": 128,
            "filesize": 5000000,
        },
        {
            "format_id": "18",
            "ext": "mp4",
            "width": 640,
            "height": 360,
            "fps": 30,
            "vcodec": "avc1.42001E",
            "acodec": "mp4a.40.2",
            "tbr": 600,
            "filesize": 10000000,
        },
    ]

    items = FormatParser.parse_formats(raw_formats, duration=60.0)
    assert len(items) == 3

    # Check Combined item
    combined = next(f for f in items if f.format_id == "18")
    assert combined.is_combined is True
    assert combined.stream_type_label == "VIDEO + AUDIO"
    assert combined.resolution == "360p"

    # Check Video Only item
    video_only = next(f for f in items if f.format_id == "137")
    assert video_only.has_video is True
    assert video_only.has_audio is False
    assert video_only.stream_type_label == "VIDEO ONLY"
    assert video_only.resolution == "1080p (FHD)"

    # Check Audio Only item
    audio_only = next(f for f in items if f.format_id == "140")
    assert audio_only.has_audio is True
    assert audio_only.has_video is False
    assert audio_only.stream_type_label == "AUDIO ONLY"
    assert audio_only.resolution == "Audio Only"
