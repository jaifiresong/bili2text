"""基础设施层 —— 仓储实现。

当前仅提供内存实现，用于开发与快速演示。
生产环境应实现基于数据库（PostgreSQL / SQLite / MongoDB）的持久化版本，
并在此模块中替换 ``InMemoryTaskRepository``，或在 Container 中注入新实现。
"""

import os
from typing import Optional, List

from tinydb import TinyDB, Query

from domain.models import ProcessingTask, VideoInfo
from domain.repositories import VideoInfoRepository, ProcessingTaskRepository


class TinyDBVideoInfoRepository(VideoInfoRepository):
    """基于 TinyDB 的视频信息仓储。

    使用 JSON 文件持久化视频元数据，避免重复解析 URL。
    """

    def __init__(self, db_path: str = "./storage/video_info.json"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._db = TinyDB(db_path)
        self._table = self._db.table("video_info")

    async def save(self, video_info: VideoInfo) -> None:
        self._table.upsert(
            video_info.model_dump(),
            Query().url.id == video_info.url.id
        )

    async def find(self, **kwargs) -> Optional[VideoInfo]:
        row = None
        if val := kwargs.get('url_id'):
            row = self._table.get(Query().url.id == val)
        if val := kwargs.get('id'):
            row = self._table.get(Query().id == val)
        if row:
            return VideoInfo.model_validate(row)
        return None

    async def find_by_id(self, video_id: str) -> Optional[VideoInfo]:
        row = self._table.get(Query().id == video_id)
        if row:
            return VideoInfo.model_validate(row)
        return None

    async def find_all(self) -> list[VideoInfo]:
        rows = self._table.all()
        return [VideoInfo.model_validate(row) for row in rows]


class InMemoryProcessingTaskRepository(ProcessingTaskRepository):
    """基于内存字典的任务仓储，进程重启后数据丢失。"""

    def __init__(self):
        self._tasks: dict[str, ProcessingTask] = {}

    async def save(self, task: ProcessingTask) -> None:
        self._tasks[task.task_id] = task

    async def find(self, task_id: str) -> Optional[ProcessingTask]:
        return self._tasks.get(task_id)

    async def find_all(self) -> list[ProcessingTask]:
        return list(self._tasks.values())
