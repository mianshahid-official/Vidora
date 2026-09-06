"""
File management, Windows filename sanitization, disk space, and duplicate handling.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional, Tuple

# Windows forbidden characters in filenames
FORBIDDEN_CHARS_PATTERN = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Unicode Emoji range pattern
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F200-\U0001F251"  # enclosed ideographic supplement
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA70-\U0001FAFF"  # symbols & pictographs ext-A
    "\U00002600-\U000026FF"  # misc symbols
    "\U00002B00-\U00002BFF"  # misc symbols & arrows
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"              # zero width joiner
    "]+",
    flags=re.UNICODE
)

RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"
}


def strip_emojis(text: str) -> str:
    """Removes all emojis and pictographs from a string and normalizes spacing."""
    if not text:
        return ""
    clean = EMOJI_PATTERN.sub("", text)
    # Collapse multiple spaces created by removed emojis
    clean = re.sub(r' +', ' ', clean)
    return clean.strip()


def sanitize_filename(filename: str, max_length: int = 200, replacement: str = "_") -> str:
    """
    Sanitizes a string to be a clean, safe, valid Windows filename without emojis.
    Strips illegal characters, fullwidth punctuation, trims trailing spaces/dots,
    and handles reserved device names.
    """
    if not filename:
        return "download"

    # 1. Strip emojis
    clean = strip_emojis(filename)

    # 2. Normalize fullwidth symbols to standard ASCII
    fullwidth_replacements = {
        '｜': '-',
        '／': '-',
        '＼': '-',
        '：': '-',
        '＊': '_',
        '？': '',
        '＂': '',
        '＜': '',
        '＞': '',
        '・': '-',
        '~': '-',
    }
    for fw, rep in fullwidth_replacements.items():
        clean = clean.replace(fw, rep)

    # 3. Replace forbidden characters
    clean = FORBIDDEN_CHARS_PATTERN.sub(replacement, clean)

    # 4. Collapse multiple consecutive underscores, hyphens, or spaces
    clean = re.sub(r'[\s_]+', ' ', clean)
    clean = re.sub(r'\s*-\s*', ' - ', clean)
    clean = re.sub(r'-\s*-+', '-', clean)
    clean = clean.strip(' .-_')

    if not clean:
        clean = "download"

    # 5. Check Windows reserved filenames
    base_name = clean.split('.')[0].upper()
    if base_name in RESERVED_NAMES:
        clean = f"_{clean}"

    # 6. Truncate length while preserving extension if present
    if len(clean) > max_length:
        parts = clean.rsplit('.', 1)
        if len(parts) == 2 and len(parts[1]) <= 10:
            ext = "." + parts[1]
            allowed_base = max_length - len(ext)
            clean = parts[0][:allowed_base].rstrip(' .') + ext
        else:
            clean = clean[:max_length].rstrip(' .')

    return clean


def get_unique_filepath(target_path: Path) -> Path:
    """
    If the file exists, returns a unique filename like 'video (1).mp4', 'video (2).mp4'.
    """
    if not target_path.exists():
        return target_path

    parent = target_path.parent
    stem = target_path.stem
    suffix = target_path.suffix

    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def check_disk_space(directory_path: str, required_bytes: Optional[int] = None) -> Tuple[int, int, bool]:
    """
    Checks total and free disk space in bytes for the specified directory.
    Returns: (free_bytes, total_bytes, has_enough_space)
    """
    try:
        path = Path(directory_path).resolve()
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(path)
        free_bytes = usage.free
        total_bytes = usage.total
        has_enough = True
        if required_bytes and required_bytes > 0:
            # Leave at least 500MB safety buffer
            has_enough = free_bytes >= (required_bytes + 500 * 1024 * 1024)
        return free_bytes, total_bytes, has_enough
    except Exception:
        # Fallback if drive not accessible
        return 10 * 1024**3, 100 * 1024**3, True


def find_partial_files(base_path: Path) -> list[Path]:
    """Finds any associated .part or .ytdl files for a given target path."""
    parent = base_path.parent
    if not parent.exists():
        return []
    stem = base_path.name
    results = []
    for cand in parent.glob(f"{stem}*.part*"):
        results.append(cand)
    for cand in parent.glob(f"{stem}*.ytdl*"):
        results.append(cand)
    return results


def safe_remove(file_path: Optional[str]):
    """Safely removes a file if it exists, without throwing exceptions."""
    if not file_path:
        return
    try:
        p = Path(file_path)
        if p.is_file():
            p.unlink(missing_ok=True)
    except Exception:
        pass
