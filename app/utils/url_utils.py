"""
URL parsing, validation, platform identification, and bulk file extraction.
"""

import csv
import re
from pathlib import Path
from typing import List, Tuple
from urllib.parse import urlparse

# URL extraction pattern
URL_REGEX = re.compile(
    r'(https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9][a-zA-Z0-9-]+[a-zA-Z0-9]\.[^\s]{2,}|'
    r'https?:\/\/(?:www\.|(?!www))[a-zA-Z0-9]+\.[^\s]{2,})',
    re.IGNORECASE
)

PLATFORM_PATTERNS = [
    (re.compile(r'(?:youtube\.com|youtu\.be)', re.I), "YouTube"),
    (re.compile(r'vimeo\.com', re.I), "Vimeo"),
    (re.compile(r'dailymotion\.com|dai\.ly', re.I), "Dailymotion"),
    (re.compile(r'(?:twitter\.com|x\.com)', re.I), "Twitter / X"),
    (re.compile(r'tiktok\.com', re.I), "TikTok"),
    (re.compile(r'reddit\.com', re.I), "Reddit"),
    (re.compile(r'facebook\.com|fb\.watch', re.I), "Facebook"),
    (re.compile(r'instagram\.com', re.I), "Instagram"),
    (re.compile(r'soundcloud\.com', re.I), "SoundCloud"),
    (re.compile(r'twitch\.tv', re.I), "Twitch"),
    (re.compile(r'bilibili\.com', re.I), "Bilibili"),
    (re.compile(r'bandcamp\.com', re.I), "Bandcamp"),
]


def is_valid_url(url: str) -> bool:
    """Checks if a string is a valid HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    return bool(parsed.scheme in ("http", "https") and parsed.netloc)


def detect_platform(url: str) -> str:
    """Identifies the media platform from the URL hostname."""
    if not url:
        return "Unknown"
    for pattern, name in PLATFORM_PATTERNS:
        if pattern.search(url):
            return name
    parsed = urlparse(url)
    if parsed.netloc:
        domain = parsed.netloc.replace("www.", "")
        return domain.capitalize()
    return "Web Media"


def extract_urls_from_text(text: str) -> List[str]:
    """Extracts all valid unique URLs from a multiline or raw text block."""
    if not text:
        return []
    found = URL_REGEX.findall(text)
    urls = []
    seen = set()
    for u in found:
        cleaned = u.strip().rstrip('.,;\'")')
        if is_valid_url(cleaned) and cleaned not in seen:
            seen.add(cleaned)
            urls.append(cleaned)
    return urls


def parse_urls_from_file(file_path: str) -> List[str]:
    """
    Parses URLs from a text (.txt) or CSV (.csv) file.
    Supports single or multi-column files.
    """
    path = Path(file_path)
    if not path.is_file():
        return []

    urls: List[str] = []
    seen = set()

    try:
        if path.suffix.lower() == ".csv":
            with open(path, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    for cell in row:
                        extracted = extract_urls_from_text(cell)
                        for u in extracted:
                            if u not in seen:
                                seen.add(u)
                                urls.append(u)
        else:
            with open(path, mode="r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                urls = extract_urls_from_text(content)
    except Exception:
        pass

    return urls
