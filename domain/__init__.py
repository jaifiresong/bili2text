"""领域层（Domain Layer）公开接口。

通过统一导出常用实体、值对象、事件和端口，简化上层模块的导入语句。
"""

from .models import (
    ProcessingTask,
    TaskStatus,
    TranscriptSegment,
    VideoInfo,
    VideoUrl,
)
from .events import (
    DomainEvent,
    SimpleEventBus,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskFailedEvent,
    TaskStatusChangedEvent,
)
from .ports import (
    LLMServicePort,

    SpeechRecognizerPort,
    VideoDownloaderPort,

)
from .exceptions import (
    DomainException,
    InvalidVideoUrlError,
    TaskAlreadyProcessingError,
    TaskNotFoundError,
)

__all__ = [
    # 实体 / 值对象 / 枚举
    "ProcessingTask",
    "TaskStatus",
    "TranscriptSegment",
    "VideoInfo",
    "VideoUrl",
    # 事件
    "DomainEvent",
    "SimpleEventBus",
    "TaskCompletedEvent",
    "TaskCreatedEvent",
    "TaskFailedEvent",
    "TaskStatusChangedEvent",
    # 端口（抽象接口）
    "LLMServicePort",
    "ProcessingTaskRepository",
    "SpeechRecognizerPort",
    "VideoDownloaderPort",
    "VideoInfoRepository",
    # 异常
    "DomainException",
    "InvalidVideoUrlError",
    "TaskAlreadyProcessingError",
    "TaskNotFoundError",
]
