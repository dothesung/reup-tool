"""Reup Tool — models."""
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    STT = "stt"
    WAITING_SUB = "waiting_sub"  # Cho user sua sub Viet
    DUBBING = "dubbing"
    BURNING = "burning"
    UPLOADING = "uploading"
    DONE = "done"
    FAILED = "failed"

class Job:
    def __init__(self, id, url, title="", status=JobStatus.PENDING):
        self.id = id
        self.url = url
        self.title = title
        self.status = status
        self.workdir = ""
        self.frost = None
        self.cover = None
        self.preset = "review_phim"
        self.drive_link = None
        self.caption_link = None
        self.error = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
