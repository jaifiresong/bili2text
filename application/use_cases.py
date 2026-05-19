"""应用层用例（Application Use Cases）。

应用层职责：
- 编排领域对象完成完整业务流程（提交视频、执行处理流水线、查询状态）。
- 协调基础设施端口（下载、识别、LLM）与领域事件总线。
- 不包含任何业务规则；所有状态转换委托给 ``ProcessingTask`` 聚合根。

设计原则：
- 一个用例类对应一个完整用户故事（如"提交视频并启动处理"）。
- 用例之间不直接调用，避免隐式依赖链。
"""

from pathlib import Path
from typing import Any, Dict, List

from domain.models import ProcessingTask, VideoInfo, VideoUrl

from domain.exceptions import TaskNotFoundError
from domain.ports import VideoDownloaderPort, SpeechRecognizerPort, LLMServicePort
from domain.repositories import VideoInfoRepository, ProcessingTaskRepository
from application.service import TaskHandleService


# 解析视频 URL
class ParseUrlUseCase:
    def __init__(self, downloader: VideoDownloaderPort, video_info_repo: VideoInfoRepository):
        self._downloader = downloader
        self._video_info_repo = video_info_repo

    async def execute(self, url_str: str) -> VideoInfo:
        video_url = VideoUrl(value=url_str)
        cached = await self._video_info_repo.find(url_id=video_url.id)
        if cached:
            return cached

        video_info: VideoInfo = await self._downloader.video_info(video_url)
        await self._video_info_repo.save(video_info)
        return video_info


class ProcessVideoUseCase:
    """用例：执行完整的视频处理流水线。

    编排逻辑（下载 -> 转录 -> 加标点 -> 总结）放在应用层，
    而每个步骤的具体状态推进由 ``ProcessingTask`` 聚合根负责。

    若任意步骤抛出异常，任务会被置为 ``FAILED`` 状态，并发布 ``TaskFailedEvent``。
    """

    def __init__(
            self,
            video_repo: VideoInfoRepository,
            task_repo: ProcessingTaskRepository,
            downloader: VideoDownloaderPort,
            speech: SpeechRecognizerPort,
            llm: LLMServicePort,
    ):
        self.video_repo = video_repo
        self.task_repo = task_repo
        self.downloader = downloader
        self.speech = speech
        self.llm = llm

    async def execute(self, video_id: str, pages: list) -> ProcessingTask:
        video_info = await self.video_repo.find(id=video_id)

        if not video_info:
            raise TaskNotFoundError(f"视频信息不存在: {video_id}")

        task = ProcessingTask(video_id=video_info.id, pages=pages)

        await self.task_repo.save(task)

        return task

    async def start_pipeline(self, task_id: str, video_id: str):
        """后台启动处理流水线：下载 → 转录 → 加标点 → 总结。"""
        video_info = await self.video_repo.find(id=video_id)
        task = await self.task_repo.find(task_id=task_id)

        if not video_info:
            raise TaskNotFoundError(f"视频信息不存在: {video_id}")
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        handler = TaskHandleService(task, video_info, self.downloader, self.speech, self.llm, self.video_repo)
        await handler.start()


class ListTasksUseCase:
    """列出所有处理任务。"""

    def __init__(self, task_repo: ProcessingTaskRepository, video_repo: VideoInfoRepository):
        self._task_repo = task_repo
        self._video_repo = video_repo

    async def execute(self) -> List[Dict[str, Any]]:
        tasks = await self._task_repo.find_all()
        result = []
        for task in tasks:
            video = await self._video_repo.find(id=task.video_id)
            result.append({
                "task_id": task.task_id,
                "video_id": task.video_id,
                "video_title": video.title if video else "未知视频",
                "pages": task.pages,
                "created_at": task.created_at.isoformat(),
            })
        return result


class GetTaskDetailUseCase:
    """查询任务详情，包含处理结果文本。"""

    def __init__(self, task_repo: ProcessingTaskRepository, video_repo: VideoInfoRepository):
        self._task_repo = task_repo
        self._video_repo = video_repo

    async def execute(self, task_id: str) -> Dict[str, Any]:
        task = await self._task_repo.find(task_id=task_id)
        if not task:
            raise TaskNotFoundError(f"任务不存在: {task_id}")

        video = await self._video_repo.find(id=task.video_id)
        page_map = {p.page: p for p in video.pages} if video else {}

        pages_result = []
        all_complete = True
        for page_num in task.pages:
            item = page_map.get(page_num)
            raw_text = _read_file(item.txt_raw_path)
            punctuated_text = _read_file(item.txt_punctuation_path)
            summary = _read_file(item.txt_summarize_path)
            if not all([raw_text, punctuated_text, summary]):
                all_complete = False
            pages_result.append({
                "page": page_num,
                "part": item.part if item else "",
                "cid": item.cid if item else 0,
                "raw_text": raw_text,
                "punctuated_text": punctuated_text,
                "summary": summary,
            })

        return {
            "task_id": task.task_id,
            "video_id": task.video_id,
            "video_title": video.title if video else "未知视频",
            "status": "completed" if all_complete else "processing",
            "pages": pages_result,
            "created_at": task.created_at.isoformat(),
        }


class ListDocumentsUseCase:
    """列出所有已处理的视频文档。"""

    def __init__(self, video_repo: VideoInfoRepository):
        self._video_repo = video_repo

    async def execute(self) -> List[Dict[str, Any]]:
        videos = await self._video_repo.find_all()
        result = []
        for v in videos:
            has_content = any(
                p.txt_raw_path or p.txt_punctuation_path or p.txt_summarize_path
                for p in v.pages
            )
            result.append({
                "id": v.id,
                "bvid": v.bvid,
                "title": v.title,
                "url_value": v.url.value,
                "page_count": len(v.pages),
                "has_content": has_content,
            })
        return result


class GetDocumentDetailUseCase:
    """查询某视频的所有分P文档内容。"""

    def __init__(self, video_repo: VideoInfoRepository):
        self._video_repo = video_repo

    async def execute(self, video_id: str) -> Dict[str, Any]:
        video = await self._video_repo.find(id=video_id)
        if not video:
            raise TaskNotFoundError(f"视频信息不存在: {video_id}")

        pages_result = []
        for p in video.pages:
            pages_result.append({
                "page": p.page,
                "part": p.part,
                "cid": p.cid,
                "raw_text": _read_file(p.txt_raw_path),
                "punctuated_text": _read_file(p.txt_punctuation_path),
                "summary": _read_file(p.txt_summarize_path),
            })

        return {
            "id": video.id,
            "bvid": video.bvid,
            "title": video.title,
            "url_value": video.url.value,
            "pages": pages_result,
        }


def _read_file(path: str | None) -> str | None:
    if not path:
        return None
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, FileNotFoundError):
        return None
