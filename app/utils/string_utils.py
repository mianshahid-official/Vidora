import re
from typing import Optional
from app.utils.file_utils import strip_emojis


def format_bytes(num_bytes: Optional[int]) -> str:
    """Formats raw byte counts to human-readable strings (e.g. 15.4 MB, 1.25 GB)."""
    if num_bytes is None or num_bytes <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0 or unit == "TB":
            return f"{num_bytes:.2f} {unit}" if unit in ["MB", "GB", "TB"] else f"{num_bytes:.0f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"


def format_speed(bytes_per_sec: Optional[float]) -> str:
    """Formats download speed to human-readable string (e.g. 3.4 MB/s)."""
    if not bytes_per_sec or bytes_per_sec <= 0:
        return "0 KB/s"
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.2f} MB/s"
    if bytes_per_sec >= 1024:
        return f"{bytes_per_sec / 1024:.0f} KB/s"
    return f"{bytes_per_sec:.0f} B/s"


def format_duration(seconds: Optional[float]) -> str:
    """Formats seconds into HH:MM:SS or MM:SS."""
    if seconds is None or seconds <= 0:
        return "00:00"
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_duration_string(time_str: str) -> float:
    """Parses 'HH:MM:SS' or 'MM:SS' or 'SS' string into float seconds."""
    if not time_str:
        return 0.0
    parts = time_str.strip().split(":")
    try:
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 1:
            return float(parts[0])
    except ValueError:
        pass
    return 0.0


def format_eta(eta_seconds: Optional[int]) -> str:
    """Formats remaining ETA seconds."""
    if eta_seconds is None or eta_seconds < 0:
        return "--:--"
    m, s = divmod(eta_seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h {m:02d}m"
    return f"{m:02d}m {s:02d}s"


def clean_display_title(title: str, max_len: int = 70) -> str:
    """Strips emojis, normalizes symbols, and truncates titles cleanly if too long."""
    if not title:
        return ""
    clean = strip_emojis(title)
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

    clean = re.sub(r'[\s_]+', ' ', clean)
    clean = re.sub(r'\s*-\s*', ' - ', clean)
    clean = clean.strip(' .-_')
    if len(clean) <= max_len:
        return clean
    return clean[:max_len - 3] + "..."
