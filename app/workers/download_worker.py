"""
PySide6 QThread worker for executing download and validation pipelines.
"""

from PySide6.QtCore import QObject, QThread, Signal

from app.core.pipeline import DownloadPipeline
from app.models.job import DownloadJob


class DownloadWorker(QThread):
    """Worker thread running a single DownloadPipeline instance."""

    job_progress = Signal(object)  # DownloadJob
    job_status = Signal(object)    # DownloadJob
    job_finished = Signal(object)  # DownloadJob
    log_message = Signal(str, str) # channel, message

    def __init__(self, job: DownloadJob, parent: QObject = None):
        super().__init__(parent)
        self.job = job
        self.pipeline = DownloadPipeline(job)

    def run(self):
        def on_progress(updated_job: DownloadJob):
            self.job_progress.emit(updated_job)

        def on_log(msg: str):
            self.log_message.emit("Download", msg)

        try:
            self.pipeline.execute(progress_callback=on_progress, log_callback=on_log)
        except Exception as e:
            self.job.error_message = str(e)
        finally:
            self.job_finished.emit(self.job)

    def pause(self):
        self.pipeline.pause()

    def cancel(self):
        self.pipeline.cancel()
