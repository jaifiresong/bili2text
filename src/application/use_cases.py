from pathlib import Path
from typing import Tuple

from src.domain.models import VideoUrl, TaskId, ProcessingTask
from src.domain.events import (
    SimpleEventBus,
    TaskCreatedEvent,
    TaskStatusChangedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
)
from src.domain.ports import (
    ProcessingTaskRepository,
    VideoDownloaderPort,
    SpeechRecognizerPort,
    LLMServicePort,
)
from .dto import TaskStatusDTO


class SubmitVideoUseCase:
    """用例：提交视频URL，创建处理任务"""

    def __init__(self, repo: ProcessingTaskRepository, event_bus: SimpleEventBus):
        self._repo = repo
        self._event_bus = event_bus

    async def execute(self, url_str: str) -> TaskId:
        video_url = VideoUrl(url_str)
        task = ProcessingTask(task_id=TaskId.generate(), video_url=video_url)
        await self._repo.save(task)
        await self._event_bus.publish(
            TaskCreatedEvent(task_id=task.task_id.value, video_url=video_url.value)
        )
        return task.task_id


class ProcessVideoUseCase:
    """用例：执行完整的视频处理流水线（编排逻辑放在应用层）"""

    def __init__(
        self,
        task_repo: ProcessingTaskRepository,
        downloader: VideoDownloaderPort,
        recognizer: SpeechRecognizerPort,
        llm: LLMServicePort,
        event_bus: SimpleEventBus,
    ):
        self._repo = task_repo
        self._downloader = downloader
        self._recognizer = recognizer
        self._llm = llm
        self._event_bus = event_bus

    async def execute(self, task_id: TaskId) -> None:
        task = await self._repo.find_by_id(task_id)
        if not task:
            return

        try:
            # 1. 下载音频
            task.start_download()
            await self._repo.save(task)
            await self._emit_status(task)

            audio_bytes, meta = await self._downloader.download_audio(task.video_url)
            audio_path = f"./storage/audio/{task_id.value}.mp3"
            Path(audio_path).parent.mkdir(parents=True, exist_ok=True)
            Path(audio_path).write_bytes(audio_bytes)
            task.finish_download(audio_path)
            await self._repo.save(task)
            await self._emit_status(task)

            # 2. 语音转录
            raw_text, segments = await self._recognizer.transcribe(audio_path)
            task.finish_transcription(raw_text, segments)
            await self._repo.save(task)
            await self._emit_status(task)

            # 3. LLM 加标点
            punctuated = await self._llm.add_punctuation(raw_text)
            task.finish_punctuation(punctuated)
            await self._repo.save(task)
            await self._emit_status(task)

            # 4. LLM 总结
            summary = await self._llm.summarize(punctuated)
            task.finish_summary(summary)
            await self._repo.save(task)
            await self._event_bus.publish(TaskCompletedEvent(task_id=task_id.value))

        except Exception as e:
            task.fail(str(e))
            await self._repo.save(task)
            await self._event_bus.publish(
                TaskFailedEvent(task_id=task_id.value, error=str(e))
            )

    async def _emit_status(self, task: ProcessingTask) -> None:
        await self._event_bus.publish(
            TaskStatusChangedEvent(
                task_id=task.task_id.value,
                new_status=task.status.value,
                progress_percent=task.progress_percent,
            )
        )


class GetTaskStatusUseCase:
    """用例：查询任务状态"""

    def __init__(self, repo: ProcessingTaskRepository):
        self._repo = repo

    async def execute(self, task_id: str) -> TaskStatusDTO:
        task = await self._repo.find_by_id(TaskId(task_id))
        if not task:
            from src.domain.exceptions import TaskNotFoundError
            raise TaskNotFoundError(f"任务不存在: {task_id}")
        return TaskStatusDTO(
            task_id=task.task_id.value,
            status=task.status.value,
            progress_percent=task.progress_percent,
            video_url=task.video_url.value,
            raw_transcript=task.raw_transcript,
            punctuated_text=task.punctuated_text,
            summary=task.summary,
            error_message=task.error_message,
            created_at=task.created_at.isoformat() if task.created_at else None,
            updated_at=task.updated_at.isoformat() if task.updated_at else None,
        )
