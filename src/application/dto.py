from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskStatusDTO:
    """任务状态数据传输对象，隔离领域实体与外部接口"""
    task_id: str
    status: str
    progress_percent: int
    video_url: str
    raw_transcript: Optional[str] = None
    punctuated_text: Optional[str] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
