"""
Centralized Download Queue and Concurrency Manager.
"""

from typing import Dict, List, Optional
from PySide6.QtCore import QObject, Signal

from app.core.config import config_manager
from app.core.constants import JobStatus
from app.core.logger import logger
from app.database.repositories import HistoryRepository, JobRepository
from app.models.job import DownloadJob
from app.workers.download_worker import DownloadWorker


class QueueManager(QObject):
    """
    Coordinates simultaneous downloads, state persistence, retry scheduling,
    and pause/resume lifecycle.
    """

    job_added = Signal(object)        # DownloadJob
    job_updated = Signal(object)      # DownloadJob
    job_finished = Signal(object)     # DownloadJob
    job_removed = Signal(str)         # job_id
    stats_updated = Signal(int, int, int, int) # total, active, queued, completed

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.jobs: List[DownloadJob] = []
        self.active_workers: Dict[str, DownloadWorker] = {}
        self.max_concurrent = config_manager.settings.max_concurrent_downloads
        config_manager.add_listener(self._on_settings_changed)

    def _on_settings_changed(self, new_settings):
        if self.max_concurrent != new_settings.max_concurrent_downloads:
            self.max_concurrent = new_settings.max_concurrent_downloads
            logger.log_app(f"Queue concurrency limit updated to {self.max_concurrent}")
            self._schedule_next()

    def add_job(self, job: DownloadJob, start_now: bool = True):
        """Adds a new job to the queue."""
        if any(j.id == job.id for j in self.jobs):
            return

        self.jobs.append(job)
        JobRepository.save_job(job)
        self.job_added.emit(job)
        self._emit_stats()

        if start_now:
            self._schedule_next()

    def add_jobs_batch(self, new_jobs: List[DownloadJob]):
        """Adds multiple jobs simultaneously."""
        for j in new_jobs:
            self.add_job(j, start_now=False)
        self._schedule_next()

    def pause_job(self, job_id: str):
        job = self.get_job(job_id)
        if not job:
            return

        job.status = JobStatus.PAUSED
        job.is_paused = True
        if job_id in self.active_workers:
            worker = self.active_workers[job_id]
            worker.pause()

        JobRepository.save_job(job)
        self.job_updated.emit(job)
        self._emit_stats()
        self._schedule_next()

    def resume_job(self, job_id: str):
        job = self.get_job(job_id)
        if not job:
            return

        job.status = JobStatus.QUEUED
        job.is_paused = False
        job.is_cancelled = False
        JobRepository.save_job(job)
        self.job_updated.emit(job)
        self._emit_stats()
        self._schedule_next()

    def cancel_job(self, job_id: str):
        job = self.get_job(job_id)
        if not job:
            return

        job.status = JobStatus.CANCELLED
        job.is_cancelled = True
        job.error_message = "Cancelled by user"
        if job_id in self.active_workers:
            self.active_workers[job_id].cancel()

        JobRepository.save_job(job)
        HistoryRepository.add_entry(job)
        self.job_updated.emit(job)
        self._emit_stats()
        self._schedule_next()

    def retry_job(self, job_id: str):
        job = self.get_job(job_id)
        if not job:
            return

        job.status = JobStatus.QUEUED
        job.retry_count += 1
        job.error_message = None
        job.is_paused = False
        job.is_cancelled = False
        JobRepository.save_job(job)
        self.job_updated.emit(job)
        self._emit_stats()
        self._schedule_next()

    def remove_job(self, job_id: str):
        if job_id in self.active_workers:
            self.cancel_job(job_id)

        self.jobs = [j for j in self.jobs if j.id != job_id]
        JobRepository.delete_job(job_id)
        self.job_removed.emit(job_id)
        self._emit_stats()
        self._schedule_next()

    def pause_all(self):
        for job in self.jobs:
            if job.status in (JobStatus.DOWNLOADING, JobStatus.QUEUED, JobStatus.ENCODING):
                self.pause_job(job.id)

    def resume_all(self):
        for job in self.jobs:
            if job.status in (JobStatus.PAUSED, JobStatus.INTERRUPTED):
                self.resume_job(job.id)

    def cancel_all(self):
        for job in self.jobs:
            if job.status not in (JobStatus.COMPLETED, JobStatus.CANCELLED):
                self.cancel_job(job.id)

    def retry_failed(self):
        for job in self.jobs:
            if job.status == JobStatus.FAILED:
                self.retry_job(job.id)

    def clear_completed(self):
        completed_ids = [j.id for j in self.jobs if j.status == JobStatus.COMPLETED]
        for cid in completed_ids:
            self.remove_job(cid)

    def get_job(self, job_id: str) -> Optional[DownloadJob]:
        for j in self.jobs:
            if j.id == job_id:
                return j
        return None

    def _schedule_next(self):
        """Dispatches queued jobs if under concurrency limit."""
        while len(self.active_workers) < self.max_concurrent:
            # Find next queued job
            next_job = next((j for j in self.jobs if j.status == JobStatus.QUEUED and not j.is_paused and not j.is_cancelled), None)
            if not next_job:
                break

            self._start_worker(next_job)

        self._emit_stats()

    def _start_worker(self, job: DownloadJob):
        job.status = JobStatus.DOWNLOADING
        worker = DownloadWorker(job)
        self.active_workers[job.id] = worker

        worker.job_progress.connect(self._on_worker_progress)
        worker.job_finished.connect(self._on_worker_finished)
        worker.start()
        logger.log_app(f"Started worker for job: '{job.title}' (Active: {len(self.active_workers)}/{self.max_concurrent})")

    def _on_worker_progress(self, updated_job: DownloadJob):
        self.job_updated.emit(updated_job)
        self._emit_stats()

    def _on_worker_finished(self, finished_job: DownloadJob):
        if finished_job.id in self.active_workers:
            del self.active_workers[finished_job.id]

        self.job_finished.emit(finished_job)
        self._emit_stats()
        # Schedule next pending job
        self._schedule_next()

    def _emit_stats(self):
        total = len(self.jobs)
        active = len(self.active_workers)
        queued = sum(1 for j in self.jobs if j.status == JobStatus.QUEUED)
        completed = sum(1 for j in self.jobs if j.status == JobStatus.COMPLETED)
        self.stats_updated.emit(total, active, queued, completed)

    def restore_interrupted_jobs(self) -> List[DownloadJob]:
        """Loads non-completed jobs from SQLite database after crash/restart."""
        interrupted = JobRepository.get_interrupted_jobs()
        for j in interrupted:
            if not any(existing.id == j.id for existing in self.jobs):
                j.status = JobStatus.PAUSED
                j.is_paused = True
                self.jobs.append(j)
                self.job_added.emit(j)
        self._emit_stats()
        return interrupted


# Global singleton instance
queue_manager = QueueManager()
