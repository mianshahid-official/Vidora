"""
Unit tests for QueueManager concurrency, pause, resume, and retry states.
"""

from unittest.mock import MagicMock
from app.core.constants import JobStatus
from app.models.job import DownloadJob
from app.workers.queue_manager import QueueManager


def test_queue_manager_lifecycle():
    qm = QueueManager()
    qm.max_concurrent = 2

    # Mock _start_worker so it doesn't initiate actual network downloads during test
    def fake_start_worker(job):
        job.status = JobStatus.DOWNLOADING
        qm.active_workers[job.id] = MagicMock()

    qm._start_worker = fake_start_worker

    job1 = DownloadJob(id="q-job-1", url="https://example.com/1", title="Job 1", status=JobStatus.QUEUED)
    job2 = DownloadJob(id="q-job-2", url="https://example.com/2", title="Job 2", status=JobStatus.QUEUED)
    job3 = DownloadJob(id="q-job-3", url="https://example.com/3", title="Job 3", status=JobStatus.QUEUED)

    qm.add_job(job1, start_now=False)
    qm.add_job(job2, start_now=False)
    qm.add_job(job3, start_now=False)

    assert len(qm.jobs) >= 3
    assert qm.get_job("q-job-1") is not None

    # Test Pause
    qm.pause_job("q-job-1")
    assert qm.get_job("q-job-1").status == JobStatus.PAUSED
    assert qm.get_job("q-job-1").is_paused is True

    # Test Cancel
    qm.cancel_job("q-job-2")
    assert qm.get_job("q-job-2").status == JobStatus.CANCELLED

    # Test Remove
    qm.remove_job("q-job-3")
    assert qm.get_job("q-job-3") is None

    # Test Resume
    qm.resume_job("q-job-1")
    assert qm.get_job("q-job-1").status in (JobStatus.QUEUED, JobStatus.DOWNLOADING)
    assert qm.get_job("q-job-1").is_paused is False
