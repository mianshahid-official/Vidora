"""
Unit tests for Windows filename sanitization, disk space checks, and duplicate handling.
"""

import tempfile
from pathlib import Path
from app.utils.file_utils import check_disk_space, get_unique_filepath, sanitize_filename, strip_emojis
from app.utils.string_utils import clean_display_title, parse_duration_string


def test_sanitize_filename_illegal_chars():
    dirty = 'Video: What is <AI>? "New" & 100% / Real | 2026 * Test.mp4'
    clean = sanitize_filename(dirty)
    for bad in '<>:"/\\|?*':
        assert bad not in clean
    assert clean.endswith(".mp4")


def test_sanitize_filename_reserved_names():
    assert sanitize_filename("CON.mp4") == "_CON.mp4"
    assert sanitize_filename("aux.txt") == "_aux.txt"
    assert sanitize_filename("prn") == "_prn"
    assert sanitize_filename("NUL.mkv") == "_NUL.mkv"


def test_strip_emojis_and_symbols():
    text_with_emojis = "🔥 Top 10 Python Tips & Tricks! 🚀 (2026) 💡✨"
    cleaned = strip_emojis(text_with_emojis)
    assert "🔥" not in cleaned
    assert "🚀" not in cleaned
    assert "💡" not in cleaned
    assert "✨" not in cleaned
    assert "Top 10 Python Tips & Tricks! (2026)" in cleaned


def test_clean_display_title():
    raw_title = "🎬 Amazing 4K Video ｜ Episode 1 🔥"
    cleaned = clean_display_title(raw_title)
    assert "🎬" not in cleaned
    assert "🔥" not in cleaned
    assert "｜" not in cleaned
    assert "Amazing 4K Video - Episode 1" in cleaned


def test_parse_duration_string():
    assert parse_duration_string("00:01:30") == 90.0
    assert parse_duration_string("01:30") == 90.0
    assert parse_duration_string("90") == 90.0
    assert parse_duration_string("3665") == 3665.0
    assert parse_duration_string("0") == 0.0
    assert parse_duration_string("invalid") == 0.0
    assert parse_duration_string("") == 0.0


def test_get_unique_filepath():
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "video.mp4"
        # First file doesn't exist
        assert get_unique_filepath(base) == base

        # Create file
        base.touch()
        unique1 = get_unique_filepath(base)
        assert unique1.name == "video (1).mp4"

        # Create unique1
        unique1.touch()
        unique2 = get_unique_filepath(base)
        assert unique2.name == "video (2).mp4"


def test_check_disk_space():
    free_b, total_b, has_space = check_disk_space(".", required_bytes=1024)
    assert free_b > 0
    assert total_b > 0
    assert has_space is True

