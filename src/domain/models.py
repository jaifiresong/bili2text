from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import re
from uuid import uuid4

from .exceptions import InvalidVideoUrlError


# ============ 值对象 ============

@dataclass(frozen=True)
class VideoUrl:
    """B站视频URL值对象，自校验"""
    value: str

    def __post_init__(self):
        if not self._is_valid(self.value):
            raise InvalidVideoUrlError(f"无效的B站URL: {self.value}")

    @staticmethod
    def _is_valid(url: str) -> bool:
        return bool(re.match(r"https?://(www\.)?bilibili\.com/video/[BVbv][\w]+", url))

    @property
    def video_id(self) -> str:
        match = re.search(r"/video/([BVbv][\w]+)", self.value)
        return match.group(1) if match else ""


@dataclass(frozen=True)
class TaskId:
    """任务唯一标识"""
    value: str

    @classmethod
    def generate(cls) -> "TaskId":
        return cls(value=str(uuid4()))


@dataclass(frozen=True)
class TranscriptSegment:
    """转录片段"""
    start: float
    end: float
    text: str


# ============ 枚举 ============

class TaskStatus(Enum):
    CREATED = "created"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    PUNCTUATING = "punctuating"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============ 聚合根 ============

@dataclass
class ProcessingTask:
    """
    处理任务聚合根。
    核心原则：不持有其他聚合/实体实例，只存原始值或路径。
    """
    task_id: TaskId
    video_url: VideoUrl
    status: TaskStatus = TaskStatus.CREATED
    audio_path: Optional[str] = None
    raw_transcript: Optional[str] = None
    transcript_segments: list[TranscriptSegment] = field(default_factory=list)
    punctuated_text: Optional[str] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # --- 状态转换（领域逻辑，内聚在聚合根内） ---
    def start_download(self) -> None:
        self._transition_to(TaskStatus.DOWNLOADING)

    def finish_download(self, audio_path: str) -> None:
        self.audio_path = audio_path
        self._transition_to(TaskStatus.TRANSCRIBING)

    def finish_transcription(self, raw_text: str, segments: list[TranscriptSegment]) -> None:
        self.raw_transcript = raw_text
        self.transcript_segments = segments
        self._transition_to(TaskStatus.PUNCTUATING)

    def finish_punctuation(self, text: str) -> None:
        self.punctuated_text = text
        self._transition_to(TaskStatus.SUMMARIZING)

    def finish_summary(self, text: str) -> None:
        self.summary = text
        self._transition_to(TaskStatus.COMPLETED)

    def fail(self, error: str) -> None:
        self.error_message = error
        self.status = TaskStatus.FAILED
        self.updated_at = datetime.now()

    def _transition_to(self, new_status: TaskStatus) -> None:
        self.status = new_status
        self.updated_at = datetime.now()

    @property
    def progress_percent(self) -> int:
        mapping = {
            TaskStatus.CREATED: 5,
            TaskStatus.DOWNLOADING: 20,
            TaskStatus.TRANSCRIBING: 50,
            TaskStatus.PUNCTUATING: 70,
            TaskStatus.SUMMARIZING: 90,
            TaskStatus.COMPLETED: 100,
            TaskStatus.FAILED: 100,
        }
        return mapping.get(self.status, 0)

    @property
    def is_terminal(self) -> bool:
        return self.status in (TaskStatus.COMPLETED, TaskStatus.FAILED)
