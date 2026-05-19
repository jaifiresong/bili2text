"""应用层数据传输对象（DTO）。

DTO 用于隔离领域模型与外部 API 契约：
- 领域实体（ProcessingTask）包含值对象、datetime 等内部类型；
- DTO 将所有字段扁平化为字符串/整数/可选字符串，方便序列化为 JSON。

这样当领域模型结构调整时，只要 DTO 映射逻辑不变，API 契约就不会被破坏。
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TaskStatusDTO:
    """任务状态数据传输对象。

    Attributes:
        task_id: 任务唯一标识（UUID 字符串）。
        status: 当前生命周期状态名称（如 "downloading"）。
        progress_percent: 进度百分比（0-100），供前端进度条使用。
        video_url: 原始 B站视频链接。
        raw_transcript: Whisper 原始识别文本（未完成时为 None）。
        punctuated_text: LLM 加标点后的文本（未完成时为 None）。
        summary: LLM 生成的摘要（未完成时为 None）。
        error_message: 失败原因（未失败时为 None）。
        created_at: 创建时间 ISO 格式字符串。
        updated_at: 最后更新时间 ISO 格式字符串。
    """
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
