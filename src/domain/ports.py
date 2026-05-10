from abc import ABC, abstractmethod
from typing import Tuple, Optional

from .models import VideoUrl, TaskId, ProcessingTask, TranscriptSegment


class VideoDownloaderPort(ABC):
    @abstractmethod
    async def download_audio(self, url: VideoUrl) -> Tuple[bytes, dict]:
        """返回音频字节与元信息 {"title": str, "duration": float}"""
        ...


class SpeechRecognizerPort(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: str, language: str = "zh") -> Tuple[str, list[TranscriptSegment]]:
        """返回原始文本与时间戳片段列表"""
        ...


class LLMServicePort(ABC):
    @abstractmethod
    async def add_punctuation(self, raw_text: str) -> str:
        ...

    @abstractmethod
    async def summarize(self, text: str) -> str:
        ...


class ProcessingTaskRepository(ABC):
    @abstractmethod
    async def save(self, task: ProcessingTask) -> None:
        ...

    @abstractmethod
    async def find_by_id(self, task_id: TaskId) -> Optional[ProcessingTask]:
        ...
