from typing import Optional

from src.domain.models import ProcessingTask, TaskId
from src.domain.ports import ProcessingTaskRepository


class InMemoryTaskRepository(ProcessingTaskRepository):
    """内存仓储（开发/演示用），生产环境可替换为 SQLAlchemyRepository"""

    def __init__(self):
        self._store: dict[str, ProcessingTask] = {}

    async def save(self, task: ProcessingTask) -> None:
        self._store[task.task_id.value] = task

    async def find_by_id(self, task_id: TaskId) -> Optional[ProcessingTask]:
        return self._store.get(task_id.value)
