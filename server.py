import os
import sys
import re
import json
import uuid
import time
import shutil
import asyncio
import subprocess
import requests
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any, Optional, List, Set

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, Response
from pydantic import BaseModel
import yt_dlp

from douyin_extractor import DouyinExtractor

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
STATIC_DIR = BASE_DIR / "static"
HISTORY_FILE = BASE_DIR / "cleared_history.json"
COOKIES_FILE = BASE_DIR / "cookies.txt"
COOKIE_SETTINGS_FILE = BASE_DIR / "cookie_settings.json"

DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Helper functions for cookie session management
def get_cookie_setting() -> str:
    if COOKIE_SETTINGS_FILE.exists():
        try:
            with open(COOKIE_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("browser", "auto")
        except Exception:
            return "auto"
    return "auto"

def set_cookie_setting(browser: str):
    try:
        with open(COOKIE_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump({"browser": browser}, f)
    except Exception as e:
        print("Error saving cookie settings:", e)

def apply_cookie_opts(ydl_opts: dict, browser_preference: Optional[str] = None):
    pref = browser_preference or get_cookie_setting()
    if pref == "none":
        return
    
    # 1. If custom cookies.txt exists and is non-empty, prioritize it
    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 10:
        ydl_opts['cookiefile'] = str(COOKIES_FILE)
        return

    # 2. Browser session cookies
    if pref in ["chrome", "edge", "firefox", "brave", "opera", "vivaldi"]:
        ydl_opts['cookiesfrombrowser'] = (pref,)
    elif pref == "auto":
        # In auto mode, try Chrome first
        ydl_opts['cookiesfrombrowser'] = ('chrome',)

def extract_info_with_cookie_fallback(ydl_opts: dict, url: str, download: bool = False) -> Any:
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=download)
    except Exception as e:
        err_msg = str(e)
        # If error was due to browser cookie DB lock or DPAPI, retry without cookies smoothly
        if any(k in err_msg for k in ["cookie", "DPAPI", "cookiesfrombrowser", "sqlite", "keyring", "User Data"]):
            fallback_opts = dict(ydl_opts)
            fallback_opts.pop('cookiesfrombrowser', None)
            fallback_opts.pop('cookiefile', None)
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                return ydl.extract_info(url, download=download)
        raise e

# Helper functions for non-destructive history clearing
def get_cleared_files() -> Set[str]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def add_cleared_files(filenames: List[str]):
    existing = get_cleared_files()
    existing.update(filenames)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(list(existing), f, indent=2)
    except Exception as e:
        print("Error saving cleared history:", e)

def remove_from_cleared(filename: str):
    existing = get_cleared_files()
    if filename in existing:
        existing.remove(filename)
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(list(existing), f, indent=2)
        except Exception as e:
            print("Error updating cleared history:", e)

# Helper function to convert subtitles (.srt/.vtt) to clean text transcript
def convert_subtitles_to_clean_text(sub_file: Path, out_txt_file: Path, with_timestamps: bool = True) -> Optional[Path]:
    if not sub_file.exists():
        return None
    try:
        content = sub_file.read_text(encoding='utf-8', errors='ignore')
        content = re.sub(r'^WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
        blocks = re.split(r'\n\s*\n', content)
        clean_lines = []
        seen = set()

        for block in blocks:
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            if not lines:
                continue
            time_idx = -1
            start_time = ''
            for idx, line in enumerate(lines):
                if '-->' in line:
                    time_idx = idx
                    m = re.search(r'(\d{1,2}:\d{2}:\d{2}|\d{2}:\d{2})', line)
                    if m:
                        start_time = m.group(1)
                    break
            if time_idx != -1 and time_idx + 1 < len(lines):
                raw_text = ' '.join(lines[time_idx+1:])
                clean_text = re.sub(r'<[^>]+>', '', raw_text).strip()
                if clean_text and clean_text not in seen:
                    seen.add(clean_text)
                    if with_timestamps and start_time:
                        clean_lines.append(f"[{start_time}] {clean_text}")
                    else:
                        clean_lines.append(clean_text)

        if not clean_lines:
            clean_lines = [content.strip()]

        out_txt_file.write_text('\n'.join(clean_lines), encoding='utf-8')
        return out_txt_file
    except Exception as e:
        print(f"Error converting subtitles to transcript: {e}")
        return None

# Concurrency & Worker Queue Management
MAX_CONCURRENCY = 2  # Default: 2 simultaneous downloads
download_queue: Optional[asyncio.Queue] = None
worker_tasks: List[asyncio.Task] = []

# In-memory tracking of all tasks
tasks: Dict[str, Dict[str, Any]] = {}
douyin_extractor = DouyinExtractor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global download_queue
    download_queue = asyncio.Queue()
    adjust_workers(MAX_CONCURRENCY)
    yield
    for t in worker_tasks:
        t.cancel()

app = FastAPI(title="Vidora", version="2.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    url: str
    browser_cookies: Optional[str] = None

class BatchAnalyzeRequest(BaseModel):
    urls: List[str]
    browser_cookies: Optional[str] = None

class DownloadRequest(BaseModel):
    url: str
    format_type: str = "video"  # "video", "audio", "subtitle", or "transcript"
    quality: str = "best"       # "best", "1080", "720", "480", "360", "mp3_best", "m4a", "transcript_txt"
    format_id: Optional[str] = None
    custom_title: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    subtitle_lang: Optional[str] = None
    include_transcript: Optional[bool] = False
    browser_cookies: Optional[str] = None

class DeleteFileRequest(BaseModel):
    filename: str

class ConcurrencySettings(BaseModel):
    max_concurrency: int

class CookieSettings(BaseModel):
    browser: str  # "auto", "chrome", "edge", "firefox", "brave", "opera", "custom", "none"

class UploadCookiesRequest(BaseModel):
    content: str

def format_bytes(size):
    if not size:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"

def format_duration(seconds):
    if not seconds:
        return None
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def extract_platform(url: str, extractor_key: Optional[str] = None) -> str:
    if DouyinExtractor.is_douyin_url(url):
        return "Douyin"
    if extractor_key:
        return extractor_key
    url_lower = url.lower()
    for site in ["youtube", "tiktok", "instagram", "facebook", "twitter", "x.com", "reddit", "pinterest", "twitch", "vimeo", "soundcloud", "bandcamp", "dailymotion"]:
        if site in url_lower:
            return site.replace(".com", "").capitalize()
    return "Media"

def is_channel_or_profile_url(url: str) -> bool:
    url_l = url.lower().strip()
    if url_l.startswith('@'):
        return True
    if any(k in url_l for k in ['youtube.com/@', 'youtube.com/c/', 'youtube.com/channel/', 'youtube.com/user/', 'youtube.com/shorts', 'youtube.com/videos', '/playlist?list=']):
        return True
    if 'tiktok.com/@' in url_l and '/video/' not in url_l:
        return True
    if 'instagram.com/' in url_l and not any(k in url_l for k in ['/p/', '/reel/', '/tv/']):
        return True
    if 'instagram.com/' in url_l and '/reels' in url_l:
        return True
    return False

def normalize_channel_url(url: str) -> str:
    url = url.strip()
    if url.startswith('@'):
        return f"https://www.youtube.com/{url}"
    return url

def analyze_single_url_sync(url: str, browser_cookies: Optional[str] = None) -> Dict[str, Any]:
    url = normalize_channel_url(url.strip())
    if not url:
        raise ValueError("Empty URL provided")

    # 1. Douyin dedicated handler
    if DouyinExtractor.is_douyin_url(url):
        return douyin_extractor.get_video_info(url)

    # 2. General yt-dlp handler
    is_channel = is_channel_or_profile_url(url)
    url_l = url.lower().rstrip('/')
    is_yt_channel = any(k in url_l for k in ['youtube.com/@', 'youtube.com/c/', 'youtube.com/channel/', 'youtube.com/user/'])
    
    # If it's a YouTube channel root without specific tab, fetch both /videos (long) and /shorts
    if is_yt_channel and not any(k in url_l for k in ['/videos', '/shorts', '/streams', '/playlists', '/featured', '/live']):
        base_clean = url.split('?')[0].rstrip('/')
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'playlistend': 50
        }
        apply_cookie_opts(ydl_opts, browser_cookies)
        items = []
        seen_ids = set()
        channel_title = "YouTube Channel"
        uploader = "Creator"
        thumb_avatar = None

        # A. Fetch long videos
        try:
            info_long = extract_info_with_cookie_fallback(ydl_opts, f"{base_clean}/videos", download=False)
            if info_long:
                channel_title = info_long.get('title') or info_long.get('uploader') or info_long.get('channel') or channel_title
                uploader = info_long.get('uploader') or info_long.get('channel') or uploader
                for entry in info_long.get('entries', [])[:50]:
                    if entry and entry.get('id') and entry['id'] not in seen_ids:
                        seen_ids.add(entry['id'])
                        t = entry.get('thumbnails', [{}])[-1].get('url') if entry.get('thumbnails') else None
                        if not thumb_avatar and t: thumb_avatar = t
                        dur = entry.get('duration')
                        items.append({
                            "id": entry['id'],
                            "url": f"https://www.youtube.com/watch?v={entry['id']}",
                            "title": entry.get('title', 'Video'),
                            "type": "long",
                            "duration": dur,
                            "duration_formatted": format_duration(dur),
                            "thumbnail": t,
                            "uploader": uploader
                        })
        except Exception as e:
            print("Channel long videos fetch error:", e)

        # B. Fetch shorts
        try:
            info_shorts = extract_info_with_cookie_fallback(ydl_opts, f"{base_clean}/shorts", download=False)
            if info_shorts:
                for entry in info_shorts.get('entries', [])[:50]:
                    if entry and entry.get('id') and entry['id'] not in seen_ids:
                        seen_ids.add(entry['id'])
                        t = entry.get('thumbnails', [{}])[-1].get('url') if entry.get('thumbnails') else None
                        if not thumb_avatar and t: thumb_avatar = t
                        dur = entry.get('duration')
                        items.append({
                            "id": entry['id'],
                            "url": f"https://www.youtube.com/shorts/{entry['id']}",
                            "title": entry.get('title', 'Short'),
                            "type": "short",
                            "duration": dur,
                            "duration_formatted": format_duration(dur),
                            "thumbnail": t,
                            "uploader": uploader
                        })
        except Exception as e:
            print("Channel shorts fetch error:", e)

        long_count = len([i for i in items if i['type'] == 'long'])
        short_count = len([i for i in items if i['type'] == 'short'])

        return {
            "is_playlist": True,
            "is_channel": True,
            "url": url,
            "title": channel_title,
            "uploader": uploader,
            "item_count": len(items),
            "long_count": long_count,
            "short_count": short_count,
            "items": items,
            "platform": "YouTube",
            "thumbnail": thumb_avatar
        }

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist' if is_channel else False,
        'skip_download': True,
        'playlistend': 100 if is_channel else 50,
    }
    apply_cookie_opts(ydl_opts, browser_cookies)

    info = extract_info_with_cookie_fallback(ydl_opts, url, download=False)

    if not info:
        raise ValueError("Could not extract media info.")

    # Handle channels, playlists, or multi-entry feeds (YouTube, TikTok, Instagram)
    if 'entries' in info and info['entries']:
        entries_list = list(info['entries'])
        if len(entries_list) > 1 or is_channel:
            playlist_items = []
            long_count = 0
            short_count = 0
            is_tiktok_or_ig = ('tiktok.com' in url_l) or ('instagram.com' in url_l) or ('/shorts' in url_l)

            for item in entries_list[:100]:
                if item:
                    item_url = item.get('webpage_url') or item.get('url') or (f"https://www.youtube.com/watch?v={item.get('id')}" if item.get('id') else "")
                    dur = item.get('duration')
                    is_short = is_tiktok_or_ig or (dur and dur <= 60) or ('/shorts/' in str(item_url)) or ('/reel' in str(item_url))
                    if is_short:
                        short_count += 1
                    else:
                        long_count += 1

                    thumb = item.get('thumbnail')
                    if not thumb and item.get('thumbnails'):
                        thumb = item['thumbnails'][-1].get('url')

                    playlist_items.append({
                        "url": item_url,
                        "id": item.get('id'),
                        "title": item.get('title', 'Media Item'),
                        "duration": dur,
                        "duration_formatted": format_duration(dur),
                        "thumbnail": thumb,
                        "type": "short" if is_short else "long",
                        "uploader": item.get('uploader') or info.get('uploader') or info.get('channel') or 'Creator'
                    })

            channel_title = info.get('title') or info.get('uploader') or info.get('channel') or 'Channel / Profile'
            return {
                "is_playlist": True,
                "is_channel": is_channel,
                "url": url,
                "title": channel_title,
                "uploader": info.get('uploader') or info.get('channel') or 'Channel Creator',
                "item_count": len(playlist_items),
                "long_count": long_count,
                "short_count": short_count,
                "items": playlist_items,
                "platform": info.get('extractor_key') or extract_platform(url),
                "thumbnail": playlist_items[0]["thumbnail"] if playlist_items else None
            }
        else:
            info = entries_list[0]

    title = info.get('title', 'Unknown Media')
    thumbnail = info.get('thumbnail')
    duration = info.get('duration')
    uploader = info.get('uploader') or info.get('channel') or info.get('creator') or 'Unknown'
    view_count = info.get('view_count')
    extractor = info.get('extractor_key') or extract_platform(url)

    # Formats processing
    formats = info.get('formats', [])
    video_options = []
    seen_resolutions = set()

    for f in reversed(formats):
        height = f.get('height')
        vcodec = f.get('vcodec')
        acodec = f.get('acodec')
        ext = f.get('ext', 'mp4')
        filesize = f.get('filesize') or f.get('filesize_approx')

        if vcodec and vcodec != 'none' and height:
            res_key = f"{height}p"
            if res_key not in seen_resolutions:
                seen_resolutions.add(res_key)
                video_options.append({
                    "format_id": f.get('format_id'),
                    "label": res_key,
                    "height": height,
                    "ext": ext,
                    "has_audio": acodec != 'none' and acodec is not None,
                    "filesize_formatted": format_bytes(filesize) if filesize else "Adaptive",
                    "tbr": f.get('tbr')
                })

    video_options.sort(key=lambda x: x.get('height', 0), reverse=True)

    presets = [
        {"id": "best_video", "label": "Best Quality (Auto)", "type": "video", "quality": "best", "icon": "sparkles", "desc": "Highest available resolution with audio"}
    ]

    for v in video_options:
        if v['height'] in [2160, 1440, 1080, 720, 480, 360]:
            presets.append({
                "id": f"video_{v['height']}",
                "label": f"{v['height']}p HD" if v['height'] >= 720 else f"{v['height']}p SD",
                "type": "video",
                "quality": str(v['height']),
                "icon": "video",
                "desc": f"MP4 • {v['filesize_formatted']}"
            })

    presets.append({
        "id": "audio_mp3_best",
        "label": "MP3 High Quality (Tagged)",
        "type": "audio",
        "quality": "mp3_best",
        "icon": "music",
        "desc": "MP3 320 kbps • Auto ID3 Artwork & Tags"
    })
    presets.append({
        "id": "audio_m4a",
        "label": "M4A / AAC Audio",
        "type": "audio",
        "quality": "m4a",
        "icon": "headphones",
        "desc": "Original Audio Stream"
    })
    presets.append({
        "id": "transcript_txt",
        "label": "YouTube Transcript (.txt)",
        "type": "transcript",
        "quality": "txt",
        "icon": "file-text",
        "desc": "Clean text transcript with timestamps"
    })

    subtitles = []
    all_subs = {**info.get('subtitles', {}), **info.get('automatic_captions', {})}
    for lang, sub_list in all_subs.items():
        subtitles.append({
            "lang": lang,
            "name": sub_list[0].get('name', lang) if sub_list else lang,
            "ext": "srt"
        })

    return {
        "is_playlist": False,
        "is_channel": False,
        "url": url,
        "title": title,
        "thumbnail": thumbnail,
        "duration": duration,
        "duration_formatted": format_duration(duration),
        "uploader": uploader,
        "view_count": f"{view_count:,}" if view_count else None,
        "platform": extractor,
        "presets": presets,
        "subtitles": subtitles[:20],
        "has_transcript": len(subtitles) > 0
    }

@app.post("/api/analyze")
async def analyze_url(req: AnalyzeRequest):
    loop = asyncio.get_running_loop()
    try:
        data = await loop.run_in_executor(None, analyze_single_url_sync, req.url, req.browser_cookies)
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/analyze-batch")
async def analyze_batch(req: BatchAnalyzeRequest):
    loop = asyncio.get_running_loop()
    results = []
    
    for u in req.urls:
        u = u.strip()
        if not u:
            continue
        try:
            res = await loop.run_in_executor(None, analyze_single_url_sync, u, req.browser_cookies)
            results.append({"url": u, "status": "success", "data": res})
        except Exception as e:
            results.append({"url": u, "status": "error", "error": str(e)})

    return {"results": results, "count": len(results)}

# Thread-safe synchronous execution of actual download
def execute_download_sync(task_id: str, url: str, format_type: str, quality: str, custom_title: Optional[str], start_time: Optional[str], end_time: Optional[str], subtitle_lang: Optional[str], include_transcript: bool = False, browser_cookies: Optional[str] = None):
    try:
        tasks[task_id]["status"] = "downloading"
        tasks[task_id]["control"] = "active"
        tasks[task_id]["start_time"] = time.time()

        # 1. Douyin Handler
        if DouyinExtractor.is_douyin_url(url):
            try:
                info = douyin_extractor.get_video_info(url)
                title = custom_title or info['title']
                clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', '\u4e00-\u9fff')).rstrip()[:120]
                if not clean_title:
                    clean_title = f"douyin_{task_id[:8]}"

                if format_type == "transcript":
                    # Generate description text file
                    out_path = DOWNLOADS_DIR / f"{clean_title}-transcript.txt"
                    out_path.write_text(f"Title: {title}\nAuthor: {info.get('author')}\n\nDescription:\n{title}", encoding='utf-8')
                    remove_from_cleared(out_path.name)
                    tasks[task_id].update({
                        "status": "completed",
                        "progress": 100.0,
                        "filename": out_path.name,
                        "file_size": out_path.stat().st_size,
                        "file_size_formatted": format_bytes(out_path.stat().st_size),
                        "completed_time": time.time(),
                        "download_url": f"/api/file/{out_path.name}"
                    })
                    return

                if format_type == "audio" and info.get('music_url'):
                    stream_url = info['music_url']
                    target_filename = f"{clean_title}.mp3"
                else:
                    stream_url = info['direct_video_url']
                    target_filename = f"{clean_title}.mp4"

                out_path = DOWNLOADS_DIR / target_filename
                temp_path = DOWNLOADS_DIR / f"temp_{target_filename}"

                tasks[task_id]["message"] = "Connecting to stream..."
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                    'Referer': 'https://www.douyin.com/'
                }
                
                with requests.get(stream_url, headers=headers, stream=True, timeout=30) as r:
                    total = int(r.headers.get('content-length', 0))
                    downloaded = 0
                    last_time = time.time()
                    last_downloaded = 0
                    download_dest = temp_path if (start_time or end_time) else out_path

                    with open(download_dest, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=1024 * 128):
                            # Check pause or cancel
                            ctrl = tasks.get(task_id, {}).get("control")
                            if ctrl == "paused":
                                tasks[task_id]["status"] = "paused"
                                tasks[task_id]["speed_formatted"] = "Paused"
                                return
                            elif ctrl == "cancelled":
                                tasks[task_id]["status"] = "cancelled"
                                if download_dest.exists():
                                    try: download_dest.unlink()
                                    except: pass
                                return

                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                now = time.time()
                                dt = now - last_time
                                if dt >= 0.35:
                                    speed = (downloaded - last_downloaded) / dt
                                    last_time = now
                                    last_downloaded = downloaded
                                    speed_str = f"{format_bytes(speed)}/s"
                                    pct = (downloaded / total * 100) if total > 0 else 50.0
                                    eta_sec = int((total - downloaded) / speed) if speed > 0 and total > downloaded else 0
                                    tasks[task_id].update({
                                        "progress": round(pct, 1),
                                        "downloaded_bytes": downloaded,
                                        "total_bytes": total,
                                        "downloaded_formatted": format_bytes(downloaded),
                                        "total_formatted": format_bytes(total),
                                        "speed_formatted": speed_str,
                                        "eta_formatted": f"{eta_sec}s" if eta_sec > 0 else "...",
                                        "status": "downloading"
                                    })

                if start_time or end_time:
                    tasks[task_id]["message"] = "Trimming clip with FFmpeg..."
                    ffmpeg_cmd = ["ffmpeg", "-y"]
                    if start_time:
                        ffmpeg_cmd.extend(["-ss", start_time])
                    ffmpeg_cmd.extend(["-i", str(temp_path)])
                    if end_time:
                        ffmpeg_cmd.extend(["-to", end_time])
                    ffmpeg_cmd.extend(["-c", "copy", str(out_path)])
                    subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if temp_path.exists():
                        temp_path.unlink()

                # If include_transcript requested
                if include_transcript:
                    t_path = DOWNLOADS_DIR / f"{clean_title}-transcript.txt"
                    t_path.write_text(f"Title: {title}\nAuthor: {info.get('author')}\n\n{title}", encoding='utf-8')
                    remove_from_cleared(t_path.name)

                remove_from_cleared(out_path.name)
                tasks[task_id].update({
                    "status": "completed",
                    "progress": 100.0,
                    "filename": out_path.name,
                    "file_size": out_path.stat().st_size if out_path.exists() else 0,
                    "file_size_formatted": format_bytes(out_path.stat().st_size) if out_path.exists() else "Done",
                    "completed_time": time.time(),
                    "download_url": f"/api/file/{out_path.name}"
                })
                return
            except Exception as e:
                tasks[task_id].update({"status": "failed", "error": f"Douyin download error: {e}", "progress": 0.0})
                return

        # 2. General yt-dlp Handler
        def progress_hook(d):
            ctrl = tasks.get(task_id, {}).get("control")
            if ctrl == "paused":
                raise Exception("DOWNLOAD_PAUSED")
            elif ctrl == "cancelled":
                raise Exception("DOWNLOAD_CANCELLED")

            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                percent = (downloaded / total * 100) if total > 0 else 0
                speed = d.get('speed')
                eta = d.get('eta')

                tasks[task_id].update({
                    "progress": round(percent, 1),
                    "downloaded_bytes": downloaded,
                    "total_bytes": total,
                    "downloaded_formatted": format_bytes(downloaded),
                    "total_formatted": format_bytes(total),
                    "speed_formatted": f"{format_bytes(speed)}/s" if speed else "Calculating...",
                    "eta_formatted": f"{int(eta)}s" if eta else "...",
                    "status": "downloading"
                })
            elif d['status'] == 'finished':
                tasks[task_id]["status"] = "processing"
                tasks[task_id]["progress"] = 99.0
                tasks[task_id]["message"] = "Processing & finalizing media..."

        outtmpl = str(DOWNLOADS_DIR / "%(title).150B-%(id)s.%(ext)s")
        if custom_title:
            clean_title = "".join(c for c in custom_title if c.isalnum() or c in (' ', '-', '_', '\u4e00-\u9fff')).rstrip()[:120]
            outtmpl = str(DOWNLOADS_DIR / f"{clean_title}.%(ext)s")

        ydl_opts = {
            'outtmpl': outtmpl,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'windowsfilenames': True,
        }

        if start_time or end_time:
            start_sec = parse_time_to_seconds(start_time) if start_time else 0
            end_sec = parse_time_to_seconds(end_time) if end_time else None
            
            def time_range_callback(info_dict, ydl):
                yield {'start_time': start_sec, 'end_time': end_sec}
                
            ydl_opts['download_ranges'] = time_range_callback
            ydl_opts['force_keyframes_at_cuts'] = True

        # Handle Transcript Only extraction (.txt)
        if format_type in ["transcript", "subtitle"]:
            lang = subtitle_lang or "en,en-US,auto"
            lang_list = [l.strip() for l in lang.split(',') if l.strip() and l.strip() != 'all']
            if not lang_list:
                lang_list = ['en', 'auto']
            ydl_opts.update({
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': lang_list,
                'subtitlesformat': 'srt/vtt/best',
                'ignoreerrors': True,
            })
        elif format_type == "audio":
            postprocessors = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3' if 'mp3' in quality else 'm4a',
                'preferredquality': '320' if 'mp3' in quality else '192',
            }, {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }]

            if 'mp3' in quality or quality == 'mp3_best':
                postprocessors.append({'key': 'EmbedThumbnail'})
                ydl_opts['writethumbnail'] = True

            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': postprocessors
            })
            if include_transcript:
                ydl_opts.update({
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['en', 'auto'],
                    'subtitlesformat': 'srt/vtt',
                    'ignoreerrors': True,
                })
        else:
            if quality == "best":
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            elif quality.isdigit():
                h = int(quality)
                ydl_opts['format'] = f'bestvideo[height<={h}]+bestaudio/best[height<={h}]/best'
            else:
                ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'

            if include_transcript:
                ydl_opts.update({
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': ['en', 'auto'],
                    'subtitlesformat': 'srt/vtt',
                    'ignoreerrors': True,
                })

        apply_cookie_opts(ydl_opts, browser_cookies)

        info = extract_info_with_cookie_fallback(ydl_opts, url, download=True)
        if not info:
            raise ValueError("Could not download media stream.")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            filename = ydl.prepare_filename(info)

        base, _ = os.path.splitext(filename)

        if format_type == "transcript":
            # Find downloaded subtitle file and convert to clean text
            sub_file = None
            base_p = Path(base)
            p_dir = base_p.parent
            p_stem = base_p.name

            for ext_pat in [f"{p_stem}*.vtt", f"{p_stem}*.srt", f"{p_stem}.*"]:
                for cand in p_dir.glob(ext_pat):
                    if cand.suffix.lower() in ['.vtt', '.srt']:
                        sub_file = cand
                        break
                if sub_file:
                    break
            
            txt_path = Path(f"{base}-transcript.txt")
            if sub_file and sub_file.exists():
                convert_subtitles_to_clean_text(sub_file, txt_path)
                try: sub_file.unlink()
                except: pass
            else:
                # If no subtitle tracks were available, write description/title as text
                txt_path.write_text(f"Title: {info.get('title')}\nUploader: {info.get('uploader')}\n\nDescription:\n{info.get('description', 'No transcript available.')}", encoding='utf-8')

            actual_filename = txt_path.name
            remove_from_cleared(actual_filename)
            tasks[task_id].update({
                "status": "completed",
                "progress": 100.0,
                "filename": actual_filename,
                "file_size": txt_path.stat().st_size if txt_path.exists() else 0,
                "file_size_formatted": format_bytes(txt_path.stat().st_size) if txt_path.exists() else "Done",
                "completed_time": time.time(),
                "download_url": f"/api/file/{actual_filename}"
            })
            return

        if format_type == "audio":
            target_ext = ".mp3" if "mp3" in quality else ".m4a"
            if os.path.exists(base + target_ext):
                filename = base + target_ext
        elif format_type == "subtitle":
            lang = subtitle_lang or "en"
            if os.path.exists(f"{base}.{lang}.srt"):
                filename = f"{base}.{lang}.srt"
            elif os.path.exists(f"{base}.srt"):
                filename = f"{base}.srt"

        file_path = Path(filename)
        actual_filename = file_path.name
        remove_from_cleared(actual_filename)

        # Convert companion transcript if include_transcript was selected
        if include_transcript:
            sub_file = None
            base_p = Path(base)
            p_dir = base_p.parent
            p_stem = base_p.name

            for ext_pat in [f"{p_stem}*.vtt", f"{p_stem}*.srt"]:
                for cand in p_dir.glob(ext_pat):
                    if cand.suffix.lower() in ['.vtt', '.srt']:
                        sub_file = cand
                        break
                if sub_file:
                    break
            if sub_file and sub_file.exists():
                txt_path = Path(f"{base}-transcript.txt")
                convert_subtitles_to_clean_text(sub_file, txt_path)
                remove_from_cleared(txt_path.name)
                try: sub_file.unlink()
                except: pass

        tasks[task_id].update({
            "status": "completed",
            "progress": 100.0,
            "filename": actual_filename,
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "file_size_formatted": format_bytes(file_path.stat().st_size) if file_path.exists() else "Done",
            "completed_time": time.time(),
            "download_url": f"/api/file/{actual_filename}"
        })
    except Exception as e:
        err_msg = str(e)
        if "DOWNLOAD_PAUSED" in err_msg:
            tasks[task_id]["status"] = "paused"
            tasks[task_id]["speed_formatted"] = "Paused"
        elif "DOWNLOAD_CANCELLED" in err_msg:
            tasks[task_id]["status"] = "cancelled"
        else:
            tasks[task_id].update({
                "status": "failed",
                "error": err_msg,
                "progress": 0.0
            })

# Asynchronous background worker
async def download_worker(worker_id: int):
    while True:
        item = None
        try:
            item = await download_queue.get()
            task_id = item["task_id"]

            # Skip if cancelled or paused while in queue
            if tasks.get(task_id, {}).get("control") in ["paused", "cancelled"]:
                continue
            
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                execute_download_sync,
                task_id,
                item["url"],
                item["format_type"],
                item["quality"],
                item["custom_title"],
                item["start_time"],
                item["end_time"],
                item["subtitle_lang"],
                item.get("include_transcript", False),
                item.get("browser_cookies", None)
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            if item and "task_id" in item:
                t_id = item["task_id"]
                if t_id in tasks:
                    tasks[t_id].update({"status": "failed", "error": str(e), "progress": 0.0})
        finally:
            if item is not None and download_queue is not None:
                download_queue.task_done()

def adjust_workers(target_count: int):
    global worker_tasks
    current_count = len(worker_tasks)
    if target_count > current_count:
        for i in range(current_count, target_count):
            t = asyncio.create_task(download_worker(i + 1))
            worker_tasks.append(t)
    elif target_count < current_count:
        to_cancel = worker_tasks[target_count:]
        worker_tasks = worker_tasks[:target_count]
        for t in to_cancel:
            t.cancel()

def parse_time_to_seconds(t_str: str) -> float:
    parts = t_str.strip().split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 1:
        return float(parts[0])
    return 0.0

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    global download_queue
    if download_queue is None:
        download_queue = asyncio.Queue()
        adjust_workers(MAX_CONCURRENCY)

    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "id": task_id,
        "url": req.url,
        "title": req.custom_title or req.url,
        "format_type": req.format_type,
        "quality": req.quality,
        "custom_title": req.custom_title,
        "start_time": req.start_time,
        "end_time": req.end_time,
        "subtitle_lang": req.subtitle_lang,
        "include_transcript": req.include_transcript,
        "browser_cookies": req.browser_cookies,
        "status": "queued",
        "control": "active",
        "progress": 0.0,
        "created_at": time.time()
    }

    # Put task in queue
    await download_queue.put({
        "task_id": task_id,
        "url": req.url,
        "format_type": req.format_type,
        "quality": req.quality,
        "custom_title": req.custom_title,
        "start_time": req.start_time,
        "end_time": req.end_time,
        "subtitle_lang": req.subtitle_lang,
        "include_transcript": req.include_transcript,
        "browser_cookies": req.browser_cookies
    })

    return {"task_id": task_id, "status": "queued"}

@app.post("/api/task/pause/{task_id}")
async def pause_task(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task["control"] = "paused"
    task["status"] = "paused"
    task["speed_formatted"] = "Paused"
    return {"status": "ok", "task_id": task_id}

@app.post("/api/task/resume/{task_id}")
async def resume_task(task_id: str):
    global download_queue
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task["control"] = "active"
    task["status"] = "queued"
    
    if download_queue is not None:
        await download_queue.put({
            "task_id": task_id,
            "url": task["url"],
            "format_type": task.get("format_type", "video"),
            "quality": task.get("quality", "best"),
            "custom_title": task.get("custom_title"),
            "start_time": task.get("start_time"),
            "end_time": task.get("end_time"),
            "subtitle_lang": task.get("subtitle_lang"),
            "include_transcript": task.get("include_transcript", False),
            "browser_cookies": task.get("browser_cookies", None)
        })

    return {"status": "ok", "task_id": task_id}

@app.post("/api/task/cancel/{task_id}")
async def cancel_task(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task["control"] = "cancelled"
    task["status"] = "cancelled"
    return {"status": "ok", "task_id": task_id}

@app.get("/api/progress/{task_id}")
async def get_progress(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Calculate queue position if queued
    if task.get("status") == "queued":
        queued_tasks = [t for t in tasks.values() if t.get("status") == "queued"]
        queued_tasks.sort(key=lambda x: x.get("created_at", 0))
        for idx, qt in enumerate(queued_tasks):
            if qt.get("id") == task_id:
                task["queue_position"] = idx + 1
                break

    return task

@app.get("/api/settings/cookies")
async def get_cookies_settings():
    has_custom = COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 10
    return {
        "browser": get_cookie_setting(),
        "has_custom_cookies": has_custom,
        "custom_cookies_size": COOKIES_FILE.stat().st_size if has_custom else 0
    }

@app.post("/api/settings/cookies")
async def save_cookies_settings(req: CookieSettings):
    set_cookie_setting(req.browser)
    return {"status": "ok", "browser": req.browser}

@app.post("/api/upload-cookies")
async def upload_cookies(req: UploadCookiesRequest):
    try:
        COOKIES_FILE.write_text(req.content.strip(), encoding="utf-8")
        set_cookie_setting("custom")
        return {"status": "success", "message": "Cookies saved successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/delete-cookies")
async def delete_cookies_file():
    try:
        if COOKIES_FILE.exists():
            COOKIES_FILE.unlink()
        set_cookie_setting("auto")
        return {"status": "success", "message": "Custom cookies file removed. Reset to Auto mode."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/settings/concurrency")
async def get_concurrency_settings():
    active_downloads = len([t for t in tasks.values() if t.get("status") in ["downloading", "processing"]])
    queued_downloads = len([t for t in tasks.values() if t.get("status") == "queued"])
    return {
        "max_concurrency": MAX_CONCURRENCY,
        "active_downloads": active_downloads,
        "queued_downloads": queued_downloads
    }

@app.get("/api/tasks")
async def get_all_tasks():
    return tasks

@app.post("/api/settings/concurrency")
async def set_concurrency_settings(req: ConcurrencySettings):
    global MAX_CONCURRENCY
    limit = max(1, min(10, req.max_concurrency))
    MAX_CONCURRENCY = limit
    adjust_workers(MAX_CONCURRENCY)
    return {"status": "ok", "max_concurrency": MAX_CONCURRENCY}

@app.get("/api/downloads")
async def list_downloads():
    cleared = get_cleared_files()
    files = []
    for f in DOWNLOADS_DIR.glob("*"):
        if f.is_file() and not f.name.endswith(".part") and not f.name.endswith(".ytdl") and not f.name.startswith("temp_"):
            if f.name in cleared:
                continue
            stat = f.stat()
            ext = f.suffix.lower().lstrip(".")
            is_audio = ext in ["mp3", "m4a", "wav", "flac", "ogg", "aac"]
            is_video = ext in ["mp4", "mkv", "webm", "avi", "mov"]
            is_sub = ext in ["srt", "vtt"]
            is_txt = ext in ["txt"]

            media_type = "audio" if is_audio else ("video" if is_video else ("subtitle" if is_sub else ("transcript" if is_txt else "file")))

            files.append({
                "filename": f.name,
                "size": stat.st_size,
                "size_formatted": format_bytes(stat.st_size),
                "modified": stat.st_mtime,
                "modified_formatted": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "extension": ext,
                "type": media_type,
                "download_url": f"/api/file/{f.name}",
                "stream_url": f"/api/stream/{f.name}"
            })

    files.sort(key=lambda x: x["modified"], reverse=True)
    return {"downloads": files, "count": len(files), "directory": str(DOWNLOADS_DIR)}

@app.get("/api/stream/{filename}")
async def stream_media_file(filename: str, request: Request):
    file_path = DOWNLOADS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    ext = file_path.suffix.lower().lstrip(".")
    content_types = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mkv": "video/x-matroska",
        "mp3": "audio/mpeg",
        "m4a": "audio/mp4",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "txt": "text/plain; charset=utf-8",
        "srt": "text/plain; charset=utf-8",
        "vtt": "text/vtt; charset=utf-8"
    }
    content_type = content_types.get(ext, "application/octet-stream")

    if range_header:
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
        length = end - start + 1

        def file_iterator():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk_size = min(remaining, 1024 * 512)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": content_type,
        }
        return StreamingResponse(file_iterator(), status_code=206, headers=headers)

    return FileResponse(path=str(file_path), media_type=content_type)

@app.get("/api/file/{filename}")
async def get_downloaded_file(filename: str):
    file_path = DOWNLOADS_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/octet-stream"
    )

@app.post("/api/open-folder")
async def open_downloads_folder():
    try:
        if sys.platform == "win32":
            os.startfile(str(DOWNLOADS_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(DOWNLOADS_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(DOWNLOADS_DIR)])
        return {"status": "ok", "path": str(DOWNLOADS_DIR)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/delete-file")
async def delete_downloaded_file(req: DeleteFileRequest):
    file_path = DOWNLOADS_DIR / req.filename
    if file_path.exists() and file_path.is_file():
        try:
            file_path.unlink()
            remove_from_cleared(req.filename)
            return {"status": "success", "message": f"Deleted {req.filename}"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not delete: {e}")
    raise HTTPException(status_code=404, detail="File not found")

@app.post("/api/clear-history")
async def clear_all_history():
    try:
        # Non-destructive: mark all current files as cleared without deleting them from disk!
        current_files = [f.name for f in DOWNLOADS_DIR.glob("*") if f.is_file()]
        add_cleared_files(current_files)

        # Clear completed/failed tasks from memory
        to_remove = [k for k, v in tasks.items() if v.get("status") in ["completed", "failed", "cancelled"]]
        for k in to_remove:
            del tasks[k]

        return {
            "status": "success",
            "cleared_count": len(current_files),
            "message": "History cleared from the app. All files remain safe on your hard drive."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount frontend static files
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("  Vidora - Universal Media & Video Workstation")
    print(f"  Max Concurrent Downloads: {MAX_CONCURRENCY}")
    print("  Running on: http://localhost:8000")
    print("="*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
