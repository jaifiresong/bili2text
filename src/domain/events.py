from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Callable, List


@dataclass(frozen=True)
class DomainEvent:
    occurred_on: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class TaskCreatedEvent(DomainEvent):
    task_id: str
    video_url: str


@dataclass(frozen=True)
class TaskStatusChangedEvent(DomainEvent):
    task_id: str
    new_status: str
    progress_percent: int


@dataclass(frozen=True)
class TaskCompletedEvent(DomainEvent):
    task_id: str


@dataclass(frozen=True)
class TaskFailedEvent(DomainEvent):
    task_id: str
    error: str


class SimpleEventBus:
    """轻量级内存事件总线，足够支撑 SSE 推送与后续扩展"""

    def __init__(self):
        self._handlers: dict[type, List[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), []):
            await handler(event)
