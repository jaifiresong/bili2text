"""领域事件（Domain Events）与内存事件总线。

事件用于解耦领域模型内部的状态变化与外部副作用（如 SSE 推送、日志记录、消息通知）。
本模块采用纯内存实现，足够支撑当前规模；若后续需要分布式扩展，可替换为 RabbitMQ / Redis PubSub 等。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """领域事件基类。

    所有事件均为不可变数据对象，携带事件发生时间（occurred_on）。
    事件本身不包含任何业务逻辑，仅描述"发生了什么"。

    使用 ``kw_only=True`` 避免子类中必填字段与基类默认字段冲突
    （Python dataclass 限制：默认字段不能出现在非默认字段之前）。
    """
    occurred_on: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True, kw_only=True)
class TaskCreatedEvent(DomainEvent):
    """任务已成功创建并持久化后发出的事件。"""
    task_id: str
    video_url: str


@dataclass(frozen=True, kw_only=True)
class TaskStatusChangedEvent(DomainEvent):
    """任务状态发生变更时发出的事件。

    这是 SSE 实时进度的核心数据来源，presentation 层订阅此事件后
    将其推送到对应 task_id 的异步队列中。
    """
    task_id: str
    new_status: str
    progress_percent: int


@dataclass(frozen=True, kw_only=True)
class TaskCompletedEvent(DomainEvent):
    """任务完整处理流程成功结束后发出的事件。"""
    task_id: str


@dataclass(frozen=True, kw_only=True)
class TaskFailedEvent(DomainEvent):
    """任务在任意步骤失败并置为 FAILED 后发出的事件。"""
    task_id: str
    error: str


class SimpleEventBus:
    """轻量级内存事件总线（发布-订阅模式）。

    设计要点：
    - 按事件类型（type）维护处理器列表，支持同一事件多个消费者。
    - publish 为异步方法，允许处理器执行 IO 操作（如发送 SSE）。
    - 当前为单进程内存实现，不涉及序列化与网络传输。

    使用示例：
        bus = SimpleEventBus()
        bus.subscribe(TaskStatusChangedEvent, async_handler)
        await bus.publish(TaskStatusChangedEvent(task_id="...", ...))
    """

    def __init__(self):
        # _handlers 结构：{事件类型: [处理器1, 处理器2, ...]}
        self._handlers: dict[type, List[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """订阅指定类型的事件。

        Args:
            event_type: 事件类（如 TaskStatusChangedEvent）。
            handler: 异步回调函数，签名应为 ``async def handler(event: DomainEvent) -> None``。
        """
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: DomainEvent) -> None:
        """发布事件，顺序调用所有已订阅的处理器。

        注意：当前实现为顺序串行调用；若处理器之间无依赖且需要并行，
        可在此使用 ``asyncio.gather`` 并发执行。
        """
        for handler in self._handlers.get(type(event), []):
            await handler(event)
