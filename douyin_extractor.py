import re
import time
import requests
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs

class DouyinExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://www.douyin.com/',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        self.last_cookie_time = 0

    def refresh_cookies(self):
        now = time.time()
        # Refresh every 15 minutes if needed
        if now - self.last_cookie_time > 900 or not self.session.cookies.get('ttwid'):
            try:
                self.session.get('https://www.douyin.com/discover', timeout=8)
                self.session.cookies.set(
                    's_v_web_id',
                    'verify_lt88319j_7BvL5w3k_9jK2_4K6K_9dJ0_7bH4k8m5w9q1',
                    domain='.douyin.com'
                )
                self.last_cookie_time = now
            except Exception as e:
                print(f"[DouyinExtractor] Cookie refresh warning: {e}")

    @staticmethod
    def is_douyin_url(url: str) -> bool:
        url_lower = url.lower()
        return 'douyin.com' in url_lower or 'iesdouyin.com' in url_lower or 'v.douyin.com' in url_lower

    def extract_video_id(self, url: str) -> Optional[str]:
        # Resolve shortlinks like v.douyin.com/xxx
        if 'v.douyin.com' in url:
            try:
                res = self.session.head(url, allow_redirects=True, timeout=8)
                url = res.url
            except Exception:
                pass

        # Match modal_id query parameter (e.g. ?modal_id=7673087416256826643)
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if 'modal_id' in query_params:
            return query_params['modal_id'][0]

        # Match /video/1234567890
        m = re.search(r'/video/(\d+)', url)
        if m:
            return m.group(1)

        # Match /share/video/1234567890
        m = re.search(r'/share/video/(\d+)', url)
        if m:
            return m.group(1)

        # Match raw digits if length > 15
        digits = re.findall(r'\d{17,21}', url)
        if digits:
            return digits[0]

        return None

    def get_video_info(self, url: str) -> Dict[str, Any]:
        self.refresh_cookies()
        vid = self.extract_video_id(url)
        if not vid:
            raise ValueError("Could not extract Douyin video ID from the provided URL.")

        api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={vid}&aid=1128&version_name=23.5.0&device_platform=android&os_version=2333"
        r = self.session.get(api_url, timeout=10)
        
        if r.status_code != 200:
            raise ValueError(f"Douyin API returned HTTP status {r.status_code}")

        data = r.json()
        if 'aweme_detail' not in data or not data['aweme_detail']:
            raise ValueError("Video not found or access restricted by Douyin.")

        ad = data['aweme_detail']
        title = ad.get('desc', f'Douyin Video {vid}').strip() or f'Douyin Video {vid}'
        author = ad.get('author', {}).get('nickname', 'Douyin Creator')
        duration = ad.get('duration', 0) / 1000.0 if ad.get('duration') else None
        
        # Thumbnail
        thumbnail = None
        cover_list = ad.get('video', {}).get('cover', {}).get('url_list', [])
        if cover_list:
            thumbnail = cover_list[0]

        # Play URLs
        play_urls = ad.get('video', {}).get('play_addr', {}).get('url_list', [])
        if not play_urls:
            raise ValueError("No video stream found for this Douyin post.")

        direct_video_url = play_urls[0]
        video_size = ad.get('video', {}).get('play_addr', {}).get('data_size', 0)

        # Music URL
        music_url = ad.get('music', {}).get('play_url', {}).get('url_list', [None])[0]

        # Format presets
        presets = [
            {
                "id": "douyin_hd",
                "label": "Original HD (No Watermark)",
                "type": "video",
                "quality": "best",
                "icon": "sparkles",
                "desc": f"MP4 Direct Stream • {self.format_bytes(video_size)}"
            }
        ]

        if music_url:
            presets.append({
                "id": "douyin_music",
                "label": "Original Audio (MP3)",
                "type": "audio",
                "quality": "mp3_best",
                "icon": "music",
                "desc": "Direct Music Stream • MP3 320k"
            })

        return {
            "url": url,
            "title": title,
            "thumbnail": thumbnail,
            "duration": duration,
            "duration_formatted": self.format_duration(duration),
            "uploader": author,
            "view_count": None,
            "platform": "Douyin",
            "is_douyin": True,
            "direct_video_url": direct_video_url,
            "music_url": music_url,
            "presets": presets,
            "subtitles": []
        }

    @staticmethod
    def format_bytes(size):
        if not size:
            return "Adaptive"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

    @staticmethod
    def format_duration(seconds):
        if not seconds:
            return None
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"
