"""
Unit tests for SQLite database schema, job persistence, and history queries.
"""

import sys
import tempfile
import time
from pathlib import Path
from app.core.constants import JobStatus, QualityPreset
from app.database.db import Database
from app.models.job import DownloadJob


def test_job_and_history_persistence():
    kwargs = {"ignore_cleanup_errors": True} if sys.version_info >= (3, 10) else {}
    with tempfile.TemporaryDirectory(**kwargs) as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        test_db = Database(db_path)

        # Create sample job
        job = DownloadJob(
            id="test-job-1",
            url="https://www.youtube.com/watch?v=sample",
            title="Sample Download",
            platform="YouTube",
            uploader="Test Channel",
            duration=120.0,
            quality_preset=QualityPreset.TV_LCD_COMPATIBLE,
            target_container="mp4",
            resolution="1080p (FHD)",
            destination_dir=str(tmpdir),
            status=JobStatus.DOWNLOADING,
            progress_percent=45.0,
            downloaded_bytes=4500000,
            total_bytes=10000000
        )

        # Test save & retrieve job
        conn = test_db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO download_jobs (id, url, title, platform, uploader, duration, quality_preset, target_container, resolution, destination_dir, status, progress_percent, downloaded_bytes, total_bytes, retry_count, created_at, is_paused)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job.id, job.url, job.title, job.platform, job.uploader, job.duration, job.quality_preset.value, job.target_container, job.resolution, job.destination_dir, job.status.value, job.progress_percent, job.downloaded_bytes, job.total_bytes, job.retry_count, job.created_at, 0))
            conn.commit()

            cursor.execute("SELECT * FROM download_jobs WHERE id = ?", (job.id,))
            row = cursor.fetchone()
            assert row is not None
            assert row["title"] == "Sample Download"
            assert row["status"] == JobStatus.DOWNLOADING.value

            # Test History entry
            cursor.execute("""
            INSERT INTO download_history (id, url, title, platform, uploader, file_path, file_size, resolution, target_format, status, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (job.id, job.url, job.title, job.platform, job.uploader, "path/to/file.mp4", 10000000, "1080p", "mp4", "Completed", time.time(), time.time()))
            conn.commit()

            cursor.execute("SELECT * FROM download_history WHERE url = ?", (job.url,))
            hist_row = cursor.fetchone()
            assert hist_row is not None
            assert hist_row["title"] == "Sample Download"
        finally:
            conn.close()
