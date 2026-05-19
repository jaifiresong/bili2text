"""领域模型层（Domain Models）。

本模块包含所有核心业务实体、值对象与枚举。
设计原则：
- 纯 Python 标准库，不依赖任何外部框架（FastAPI、Whisper、OpenAI 等）。
- 聚合根（ProcessingTask）封装全部状态转换逻辑，形成天然的状态机。
- 值对象（VideoUrl、TaskId、TranscriptSegment）不可变，确保数据一致性。
"""

from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, computed_field, ConfigDict
from datetime import datetime
from enum import Enum
from typing import Optional, List
import re
from uuid import uuid4

from efficient.util_hash import md5


# ============ 值对象（Value Objects） ============
# 值对象特点：不可变、通过属性值判等、无唯一标识。
class VideoUrl(BaseModel):
    model_config = ConfigDict(frozen=True)  # 类似 dataclass frozen=True
    value: str

    @computed_field
    @property
    def id(self) -> str:
        """自动计算 md5"""
        return md5(self.value)


@dataclass(frozen=True)
class TranscriptSegment:
    """语音转录时间轴片段值对象。

    Attributes:
        start: 片段起始时间（秒）。
        end: 片段结束时间（秒）。
        text: 该时间段内的识别文本。
    """
    start: float
    end: float
    text: str


# ============ 枚举（Enums） ============

class TaskStatus(Enum):
    """任务生命周期状态枚举。

    状态顺序即流水线处理顺序：
    CREATED -> DOWNLOADING -> TRANSCRIBING -> PUNCTUATING -> SUMMARIZING -> COMPLETED
    FAILED 为任意步骤都可能进入的终态。
    """
    CREATED = "created"
    DOWNLOADING = "downloading"
    TRANSCRIBING = "transcribing"
    PUNCTUATING = "punctuating"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============ 聚合根（Aggregate Root） ============
class VideoInfoItem(BaseModel):
    # model_config = ConfigDict(frozen=True)  # 类似 dataclass frozen=True
    cid: int
    page: int
    part: str

    audio_path: Optional[str] = None  # 原始音频
    txt_raw_path: Optional[str] = None  # 原始转录的文本
    txt_punctuation_path: Optional[str] = None  # 加了标点的文件
    txt_summarize_path: Optional[str] = None  # 总结后的文本


class VideoInfo(BaseModel):
    bvid: str
    title: str
    aid: int
    cid: int
    url: VideoUrl
    pages: List[VideoInfoItem]

    @computed_field
    @property
    def id(self) -> str:
        """自动计算 md5"""
        return md5(self.bvid)


@dataclass
class ProcessingTask:
    video_id: str
    pages: list  # 选中的 VideoInfoItem 的 page [1,2,3]

    task_id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


if '__main__' == __name__:
    r = VideoUrl(value='https://www.bilibili.com/video/BV1fMwvzDECY/')
    print(r)
    print(r.model_dump())
    print(r.model_dump_json())
