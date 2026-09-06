"""
Repositories for Jobs, History, and Settings persistence.
"""

import json
import time
from typing import Any, List, Optional

from app.core.constants import JobStatus, QualityPreset
from app.database.db import db
from app.models.job import DownloadJob
from app.models.settings_model import AppSettings


class JobRepository:
    """Handles CRUD and state persistence for download jobs."""

    @staticmethod
    def save_job(job: DownloadJob):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO download_jobs (
                id, url, title, platform, uploader, duration, thumbnail_url,
                quality_preset, target_container, selected_format_id,
                selected_video_format_id, selected_audio_format_id,
                is_audio_only, is_video_only, resolution, destination_dir,
                output_filename, final_file_path, temp_file_path, status,
                progress_percent, downloaded_bytes, total_bytes, retry_count,
                created_at, completed_at, error_message, is_paused
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                status=excluded.status,
                progress_percent=excluded.progress_percent,
                downloaded_bytes=excluded.downloaded_bytes,
                total_bytes=excluded.total_bytes,
                final_file_path=excluded.final_file_path,
                temp_file_path=excluded.temp_file_path,
                retry_count=excluded.retry_count,
                completed_at=excluded.completed_at,
                error_message=excluded.error_message,
                is_paused=excluded.is_paused;
            """, (
                job.id, job.url, job.title, job.platform, job.uploader, job.duration, job.thumbnail_url,
                job.quality_preset.value if isinstance(job.quality_preset, QualityPreset) else str(job.quality_preset),
                job.target_container, job.selected_format_id,
                job.selected_video_format_id, job.selected_audio_format_id,
                1 if job.is_audio_only else 0, 1 if job.is_video_only else 0,
                job.resolution, job.destination_dir, job.output_filename,
                job.final_file_path, job.temp_file_path, job.status.value,
                job.progress_percent, job.downloaded_bytes, job.total_bytes, job.retry_count,
                job.created_at, job.completed_at, job.error_message, 1 if job.is_paused else 0
            ))
            conn.commit()

    @staticmethod
    def get_job(job_id: str) -> Optional[DownloadJob]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM download_jobs WHERE id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return JobRepository._row_to_job(row)

    @staticmethod
    def get_interrupted_jobs() -> List[DownloadJob]:
        """Returns valid jobs that were not finished (e.g. downloading, queued, paused, merging, encoding)."""
        terminal_statuses = (JobStatus.COMPLETED.value, JobStatus.CANCELLED.value)
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM download_jobs WHERE status NOT IN (?, ?) AND (url LIKE 'http://%' OR url LIKE 'https://%') ORDER BY created_at ASC",
                terminal_statuses
            )
            rows = cursor.fetchall()
            return [JobRepository._row_to_job(r) for r in rows]

    @staticmethod
    def delete_job(job_id: str):
        with db.get_connection() as conn:
            conn.execute("DELETE FROM download_jobs WHERE id = ?", (job_id,))
            conn.commit()

    @staticmethod
    def clear_all_jobs():
        with db.get_connection() as conn:
            conn.execute("DELETE FROM download_jobs;")
            conn.commit()

    @staticmethod
    def _row_to_job(row) -> DownloadJob:
        return DownloadJob(
            id=row["id"],
            url=row["url"],
            title=row["title"],
            platform=row["platform"] or "Unknown",
            uploader=row["uploader"] or "",
            duration=row["duration"] or 0.0,
            thumbnail_url=row["thumbnail_url"] or "",
            quality_preset=QualityPreset(row["quality_preset"]) if row["quality_preset"] in [p.value for p in QualityPreset] else QualityPreset.TV_LCD_COMPATIBLE,
            target_container=row["target_container"] or "mp4",
            selected_format_id=row["selected_format_id"],
            selected_video_format_id=row["selected_video_format_id"],
            selected_audio_format_id=row["selected_audio_format_id"],
            is_audio_only=bool(row["is_audio_only"]),
            is_video_only=bool(row["is_video_only"]),
            resolution=row["resolution"] or "Best Available",
            destination_dir=row["destination_dir"] or "",
            output_filename=row["output_filename"] or "",
            final_file_path=row["final_file_path"],
            temp_file_path=row["temp_file_path"],
            status=JobStatus(row["status"]) if row["status"] in [s.value for s in JobStatus] else JobStatus.QUEUED,
            progress_percent=row["progress_percent"] or 0.0,
            downloaded_bytes=row["downloaded_bytes"] or 0,
            total_bytes=row["total_bytes"] or 0,
            retry_count=row["retry_count"] or 0,
            created_at=row["created_at"] or time.time(),
            completed_at=row["completed_at"],
            error_message=row["error_message"],
            is_paused=bool(row["is_paused"]),
        )


class HistoryRepository:
    """Handles download history persistence and queries."""

    @staticmethod
    def add_entry(job: DownloadJob, validation_summary: str = ""):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO download_history (
                id, url, title, platform, uploader, duration, thumbnail_url,
                file_path, file_size, resolution, target_format,
                video_codec, audio_codec, container, status,
                created_at, completed_at, validation_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                file_path=excluded.file_path,
                file_size=excluded.file_size,
                status=excluded.status,
                completed_at=excluded.completed_at,
                validation_summary=excluded.validation_summary;
            """, (
                job.id, job.url, job.title, job.platform, job.uploader, job.duration, job.thumbnail_url,
                job.final_file_path or "",
                job.downloaded_bytes or job.total_bytes,
                job.resolution,
                job.target_container,
                job.validation_report.video_codec if job.validation_report else "",
                job.validation_report.audio_codec if job.validation_report else "",
                job.validation_report.container if job.validation_report else job.target_container,
                job.status.value,
                job.created_at,
                job.completed_at or time.time(),
                validation_summary or (job.validation_report.format_log_summary() if job.validation_report else "")
            ))
            conn.commit()

    @staticmethod
    def get_all(limit: int = 200, offset: int = 0) -> List[dict]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM download_history ORDER BY completed_at DESC LIMIT ? OFFSET ?
            """, (limit, offset))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def search(query: str) -> List[dict]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            wildcard = f"%{query}%"
            cursor.execute("""
            SELECT * FROM download_history
            WHERE title LIKE ? OR url LIKE ? OR uploader LIKE ? OR platform LIKE ?
            ORDER BY completed_at DESC
            """, (wildcard, wildcard, wildcard, wildcard))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def find_by_url(url: str) -> Optional[dict]:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM download_history WHERE url = ? ORDER BY completed_at DESC LIMIT 1", (url,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def delete_entry(entry_id: str):
        with db.get_connection() as conn:
            conn.execute("DELETE FROM download_history WHERE id = ?", (entry_id,))
            conn.commit()

    @staticmethod
    def clear_all():
        with db.get_connection() as conn:
            conn.execute("DELETE FROM download_history;")
            conn.commit()


class SettingsRepository:
    """Handles settings persistence in SQLite."""

    @staticmethod
    def load_settings() -> AppSettings:
        settings = AppSettings()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM app_settings")
            rows = cursor.fetchall()
            for row in rows:
                key, raw_val = row["key"], row["value"]
                if hasattr(settings, key):
                    target_type = type(getattr(settings, key))
                    try:
                        if target_type == bool:
                            val = raw_val.lower() in ("true", "1", "yes")
                        elif target_type == int:
                            val = int(raw_val)
                        elif target_type == float:
                            val = float(raw_val)
                        else:
                            val = raw_val
                        setattr(settings, key, val)
                    except Exception:
                        pass
        return settings

    @staticmethod
    def save_settings(settings: AppSettings):
        with db.get_connection() as conn:
            cursor = conn.cursor()
            for key, val in settings.__dict__.items():
                cursor.execute("""
                INSERT INTO app_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value;
                """, (key, str(val)))
            conn.commit()
