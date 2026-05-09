from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskStatus(str, Enum):
    """任务状态值对象"""
    PENDING = "pending"
    RESOLVING = "resolving"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    PUNCTUATING = "punctuating"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class SourceIdentifier:
    """值对象：跨平台内容来源标识。

    示例：
        bilibili  -> SourceIdentifier("bilibili", "BV1xx411c7mD")
        youtube   -> SourceIdentifier("youtube",  "dQw4w9WgXcQ")
    """
    platform: str      # e.g. "bilibili", "youtube"
    external_id: str   # 平台侧唯一ID


@dataclass(frozen=True)
class SegmentInfo:
    """值对象：音频/视频分段信息。

    对应 B 站分 P、YouTube 章节、播客多集等跨平台概念。
    """
    index: int
    title: str
    duration: int = 0


@dataclass
class AudioTask:
    """聚合根：音频处理任务。

    平台无关的核心领域模型。所有状态变更必须通过领域方法，
    不允许外部直接修改字段。
    """
    task_id: str
    source: SourceIdentifier = field(default_factory=lambda: SourceIdentifier("", ""))
    title: str = ""
    selected_segments: list[int] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    message: str = ""
    progress: int = 0
    current_segment: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # ---------- 不变式 ----------
    @property
    def total_segments(self) -> int:
        return len(self.selected_segments)

    def _assert_progress_range(self, value: int) -> None:
        if not (0 <= value <= 100):
            raise ValueError(f"progress 必须在 0-100 之间，收到 {value}")

    # ---------- 领域方法：生命周期 ----------
    def start_resolution(self) -> None:
        self.status = TaskStatus.RESOLVING
        self.message = "开始解析媒体信息..."

    def resolve_completed(self, source: SourceIdentifier, title: str) -> None:
        self.source = source
        self.title = title
        self.status = TaskStatus.DOWNLOADING

    # ---------- 领域方法：下载 ----------
    def mark_downloading(self, segment_index: int) -> None:
        self.status = TaskStatus.DOWNLOADING
        self.current_segment = segment_index

    def skip_download(self) -> None:
        pass  # 状态不变，仅由应用层设置 message

    # ---------- 领域方法：转录 ----------
    def mark_transcribing(self, segment_index: int) -> None:
        self.status = TaskStatus.TRANSCRIBING
        self.current_segment = segment_index

    def skip_transcription(self) -> None:
        pass

    # ---------- 领域方法：加标点 ----------
    def mark_punctuating(self, segment_index: int) -> None:
        self.status = TaskStatus.PUNCTUATING
        self.current_segment = segment_index

    def skip_punctuation(self) -> None:
        pass

    # ---------- 领域方法：总结 ----------
    def mark_summarizing(self, segment_index: int) -> None:
        self.status = TaskStatus.SUMMARIZING
        self.current_segment = segment_index

    def skip_summarization(self) -> None:
        pass

    # ---------- 领域方法：进度与完成 ----------
    def update_progress(self, current_idx: int, total: int) -> None:
        if total <= 0:
            self.progress = 0
        else:
            self.progress = int((current_idx / total) * 100)
        self._assert_progress_range(self.progress)

    def complete(self) -> None:
        if self.status == TaskStatus.FAILED:
            raise RuntimeError("失败状态的任务不能转为完成")
        self.status = TaskStatus.COMPLETED
        self.progress = 100
        self.message = "全部完成"
        self.completed_at = datetime.now()

    def fail(self, reason: str) -> None:
        self.status = TaskStatus.FAILED
        self.message = f"失败: {reason}"
