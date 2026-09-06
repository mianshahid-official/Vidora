"""
SQLite Database engine with connection management, WAL mode, and schema migrations.
"""

import sqlite3
from pathlib import Path
from typing import Optional

from app.core.constants import DEFAULT_DB_PATH
from app.core.logger import logger


class Database:
    """Thread-safe SQLite database manager."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a new sqlite3 connection with Row factory and foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    def init_schema(self):
        """Initializes tables and indexes."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Download History Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_history (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                platform TEXT,
                uploader TEXT,
                duration REAL,
                thumbnail_url TEXT,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                resolution TEXT,
                target_format TEXT,
                video_codec TEXT,
                audio_codec TEXT,
                container TEXT,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                completed_at REAL,
                validation_summary TEXT
            );
            """)

            # 2. Download Jobs Persistence (for Resume & Crash Recovery)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS download_jobs (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                platform TEXT,
                uploader TEXT,
                duration REAL,
                thumbnail_url TEXT,
                quality_preset TEXT,
                target_container TEXT,
                selected_format_id TEXT,
                selected_video_format_id TEXT,
                selected_audio_format_id TEXT,
                is_audio_only INTEGER DEFAULT 0,
                is_video_only INTEGER DEFAULT 0,
                resolution TEXT,
                destination_dir TEXT,
                output_filename TEXT,
                final_file_path TEXT,
                temp_file_path TEXT,
                status TEXT NOT NULL,
                progress_percent REAL DEFAULT 0.0,
                downloaded_bytes INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                created_at REAL NOT NULL,
                completed_at REAL,
                error_message TEXT,
                is_paused INTEGER DEFAULT 0
            );
            """)

            # 3. Settings Key-Value Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """)

            # Indexes for fast querying
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_completed ON download_history(completed_at DESC);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_url ON download_history(url);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON download_jobs(status);")

            conn.commit()
            logger.log_app("Database initialized successfully at: " + str(self.db_path))


# Global database singleton
db = Database()
