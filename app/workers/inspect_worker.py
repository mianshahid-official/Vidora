"""
Async metadata extractor and local file inspection workers.
"""

from PySide6.QtCore import QObject, QThread, Signal

from app.downloader.extractor import MetadataExtractor
from app.media.inspector import MediaInspectorService
from app.models.format_info import MediaMetadata


class MetadataWorker(QThread):
    """Worker for fetching URL metadata and formats in the background."""

    metadata_ready = Signal(object)  # MediaMetadata
    error_occurred = Signal(str)

    def __init__(self, url: str, process_formats: bool = True, parent: QObject = None):
        super().__init__(parent)
        self.url = url
        self.process_formats = process_formats

    def run(self):
        try:
            meta = MetadataExtractor.extract_info(self.url, process_formats=self.process_formats)
            self.metadata_ready.emit(meta)
        except Exception as e:
            self.error_occurred.emit(str(e))


class FileInspectWorker(QThread):
    """Worker for deep media analysis of local files in the background."""

    inspection_ready = Signal(object)  # InspectionResult
    error_occurred = Signal(str)

    def __init__(self, file_path: str, parent: QObject = None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        try:
            result = MediaInspectorService.inspect(self.file_path)
            self.inspection_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))
