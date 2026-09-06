"""
Unit tests for URL parsing and platform detection.
"""

import tempfile
from pathlib import Path
from app.utils.url_utils import detect_platform, extract_urls_from_text, is_valid_url, parse_urls_from_file


def test_is_valid_url():
    assert is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_url("http://vimeo.com/123456") is True
    assert is_valid_url("not a url") is False
    assert is_valid_url("") is False
    assert is_valid_url("ftp://example.com") is False


def test_detect_platform():
    assert detect_platform("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "YouTube"
    assert detect_platform("https://youtu.be/dQw4w9WgXcQ") == "YouTube"
    assert detect_platform("https://vimeo.com/11223344") == "Vimeo"
    assert detect_platform("https://twitter.com/user/status/12345") == "Twitter / X"
    assert detect_platform("https://x.com/user/status/12345") == "Twitter / X"
    assert detect_platform("https://soundcloud.com/artist/track") == "SoundCloud"
    assert detect_platform("https://dailymotion.com/video/x7abc") == "Dailymotion"


def test_extract_urls_from_text():
    raw_text = """
    Check these videos out:
    https://www.youtube.com/watch?v=test1
    Some random text here
    https://vimeo.com/123456. And another one: https://youtu.be/test2, check it.
    https://www.youtube.com/watch?v=test1
    """
    urls = extract_urls_from_text(raw_text)
    assert len(urls) == 3
    assert "https://www.youtube.com/watch?v=test1" in urls
    assert "https://vimeo.com/123456" in urls
    assert "https://youtu.be/test2" in urls


def test_parse_urls_from_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("https://www.youtube.com/watch?v=1\nhttps://www.youtube.com/watch?v=2\n")
        txt_path = f.name

    urls = parse_urls_from_file(txt_path)
    assert len(urls) == 2
    assert "https://www.youtube.com/watch?v=1" in urls
    assert "https://www.youtube.com/watch?v=2" in urls
    Path(txt_path).unlink(missing_ok=True)
