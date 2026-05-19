from abc import ABC, abstractmethod
from typing import Optional, List

from domain import VideoInfo, ProcessingTask


class VideoInfoRepository(ABC):

    @abstractmethod
    async def save(self, video_info: VideoInfo) -> None: ...

    @abstractmethod
    async def find(self, *args, **kwargs) -> Optional[VideoInfo]: ...

    @abstractmethod
    async def find_all(self) -> List[VideoInfo]: ...


class ProcessingTaskRepository(ABC):
    @abstractmethod
    async def save(self, processing_task: ProcessingTask) -> None: ...

    @abstractmethod
    async def find(self, *args, **kwargs) -> Optional[ProcessingTask]: ...

    @abstractmethod
    async def find_all(self) -> List[ProcessingTask]: ...
