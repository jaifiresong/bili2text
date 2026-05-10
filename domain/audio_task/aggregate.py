import os
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


@dataclass
class TaskDownload:
    """值对象：跨平台内容来源标识。

    示例：
        bilibili  -> SourceIdentifier("bilibili", "BV1xx411c7mD")
        youtube   -> SourceIdentifier("youtube",  "dQw4w9WgXcQ")
    """
    platform: str  # e.g. "bilibili", "youtube"
    external_id: str  # 平台侧唯一ID
    index: int

@dataclass
class TaskTranscription:
    """值对象：音频处理结果。"""
    text: str
    status:str


@dataclass
class AudioTask:
    """聚合根：音频处理任务。

    平台无关的核心领域模型。所有状态变更必须通过领域方法，
    不允许外部直接修改字段。
    """
    task_id: str

    status: int
