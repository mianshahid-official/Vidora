# Vidora

A commercial-grade, multi-threaded desktop media downloader, audio/video converter, and stream analysis workstation for Windows built with **Python 3.12+**, **PySide6**, **yt-dlp**, **FFmpeg**, **FFprobe**, and **SQLite**.

---

## 🌟 Key Features

### 1. 🛡️ Audio Safety & Mute Prevention Guarantee
- **Smart Stream Pairing**: Downloads `bestvideo*+bestaudio/best` with automatic audio format negotiation.
- **Deep FFprobe Post-Download Validation**: Inspects final files before marking them as completed. Verifies container integrity, video stream presence, and audio stream presence when audio is requested.
- **Automatic Audio Recovery**: If an audio stream is missing in a merged file, the engine automatically fetches the standalone best audio stream and merges it.
- **Strict Failure Status**: If audio cannot be verified, the job fails with clear diagnostics (`"Download completed but audio stream was not detected."`) and never silently reports success.

### 2. ⚡ Universal MP4 & Quick Audio-Only MP3 Engine
- **Universal MP4 Mode**: Produces standard MP4 files encoded with H.264 (AVC) video, AAC audio, and universal 8-bit `yuv420p` pixel format with `+faststart` (moov atom optimization) for maximum playback compatibility across all media players and hardware.
- **Quick Audio-Only MP3 Mode**: One-click toggle directly on the homepage dashboard to download audio streams and extract high-bitrate MP3s with ID3 metadata.
- **Native Stream Prioritization & Instant Remuxing**: Prioritizes native AVC1/MP4 streams from YouTube and other platforms for 0-second instant stream copying without lossy re-encoding.
- **10x Faster Transcoding**: When re-encoding is required (e.g. VP9/AV1), optimized `-preset veryfast -crf 21` pipelines run at **90-150 fps** instead of sluggish CPU encoding.

### 3. ✂️ Built-in Media Converter & Audio/Video Trimmer
- **Source Selection**: Convert either previously downloaded files directly from your history or any local file via file browser and drag-and-drop.
- **MP3 Conversion with Bitrate Choices**: High-fidelity conversion to MP3 at **320 kbps (Extreme)**, **256 kbps (Standard)**, **192 kbps (Good)**, or **128 kbps (Compact)**, plus WAV, FLAC, and AAC M4A.
- **Audio & Video Trimming**: Precision start (`-ss`) and end (`-to`) time trimming in `HH:MM:SS` format.
- **Batch Processing**: Queue multiple conversion and trimming jobs with real-time encoding FPS, progress, and speed metrics.

### 4. 🧹 Clean Title & Emoji Stripping Engine
- **Automatic Emoji Removal**: Strips all Unicode emojis, pictographs, symbols, and variation selectors from media titles and generated filenames.
- **Fullwidth Symbol Normalization**: Converts non-standard fullwidth characters (e.g., `｜` $\rightarrow$ `-`, `：` $\rightarrow$ `-`) to safe Windows ASCII standards.
- **Windows Filename Sanitization**: Resolves reserved device names (`CON`, `PRN`, `AUX`, `NUL`), truncates excessive lengths, and prevents duplicate file overwrite collisions.

### 5. 🖼️ Real-Time Async Thumbnail & Metadata Fetching
- **Rich Thumbnail Previews**: Displays high-resolution video thumbnails, video title, uploader, duration, and stream info upon clicking **Fetch Metadata**.
- **Streamlined Workflow**: Intuitive UI with instant single or bulk URL pasting.

### 6. 🌓 Modern Adaptive UI & Theme Switcher
- **Instant Theme Toggle**: One-click `🌓 Switch Theme` button in the sidebar footer to toggle between sleek Dark Mode and clean Light Mode.
- **Zero Background Artifacts**: Custom transparent scroll area and card viewports across all views.
- **Cancellation Countdown**: 5-second countdown on job cancellation with immediate recording into the History table as `CANCELLED`.
- **Clean Status Bar**: Simplified status indicator showing `Requirements: ✓ Ready` and developer attribution (`Developed by Shahid`).

### 7. 📁 Direct Windows Downloads Integration
- Defaults directly to your standard Windows **Downloads** folder (`C:\Users\<User>\Downloads`) with customizable folder organization.

### 8. 🚀 High-Throughput Queue & Crash Recovery
- **Configurable Concurrency**: Enforces simultaneous active downloads (1 to 10 slots, default 3).
- **Safe Pause & Resume**: Retains `.part` files using native yt-dlp resume capabilities.
- **SQLite State Persistence**: Saves job state after every milestone. On restart, seamlessly loads without popup interruptions.
- **Exponential Backoff Retry**: Automatic recovery for transient network interruptions up to 5 retries.

### 9. 🔍 Hardware & Playback Compatibility Inspector
- **Media Inspector**: Drag-and-drop any media file to inspect codecs, bitrate, profile, level, pixel format, and get an instant **Playback Compatibility Report** with actionable recommendations.

---

## 📂 Project Architecture

```
Downloader/
├── app/
│   ├── main.py                  # Entry point, single-instance lock, app icon bootstrap
│   ├── core/                    # App configuration, logging, dependencies, pipeline, compatibility
│   ├── downloader/              # yt-dlp engine, format parser, metadata extractor, rate limiter
│   ├── encoder/                 # FFmpeg subprocess wrapper, presets, smart transcode manager
│   ├── media/                   # FFprobe wrapper, stream validator, media inspector
│   ├── database/                # SQLite connection pool, schema, history & job repositories
│   ├── workers/                 # QThread workers (DownloadWorker, EncodeWorker, QueueManager, ThumbnailLoader)
│   ├── models/                  # Data models (DownloadJob, ConvertJob, FormatItem, Presets, Settings)
│   ├── utils/                   # Windows filename sanitization, emoji stripper, disk space checks, URL parser
│   ├── resources/               # Application icons (icon.png, icon.ico)
│   └── ui/                      # PySide6 modern UI (Dashboard, Queue, History, Converter, Inspector, Settings)
├── config/                      # Local SQLite database & config
├── downloads/                   # Secondary local download directory
├── logs/                        # Multi-channel logs (app.log, download.log, ffmpeg.log, error.log)
├── tests/                       # Automated unit & integration tests (25 passing tests)
├── requirements.txt             # Python package dependencies
├── run.bat                      # Windows launcher script
└── README.md                    # Developer and user manual
```

---

## 🚀 Installation & Getting Started

### 1. Prerequisites
- **Python 3.12 or higher**
- **FFmpeg & FFprobe** installed and available in system `PATH` (or configured in Settings)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
Launch via command line:
```bash
python main.py
```
Or double-click `run.bat` on Windows.

---

## 🧪 Running Automated Tests

Run the complete test suite:
```bash
python -m pytest tests/ -v
```

Tests cover:
- Windows filename sanitization, emoji stripping, and reserved device name safety
- Media Converter presets (MP3 320k/256k/192k/128k, Universal MP4) and time trimming
- Deep stream format parsing & HDR dynamic range detection
- Hardware & playback compatibility matrix
- Mute video prevention and synthetic FFmpeg media validation
- SQLite CRUD, persistence, and session recovery
- Queue concurrency scheduling and job lifecycle

---

## 📦 Packaging for Windows (.exe)

To compile a standalone Windows executable (`.exe`) with PyInstaller:
```bash
pip install pyinstaller
pyinstaller --noconsole --name "Vidora" --icon=app/resources/icon.ico --add-data "app/resources;app/resources" main.py
```
*(Note: Keep this repository in local development until ready for publication).*
