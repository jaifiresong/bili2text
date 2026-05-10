"""轻量级 IoC 容器 / 依赖注入"""
import os
from typing import AsyncGenerator

from src.domain.events import SimpleEventBus
from src.domain.ports import (
    ProcessingTaskRepository,
    VideoDownloaderPort,
    SpeechRecognizerPort,
    LLMServicePort,
)
from src.infrastructure.repositories import InMemoryTaskRepository
from src.infrastructure.adapters import (
    YtDlpVideoDownloaderAdapter,
    WhisperSpeechRecognizerAdapter,
    OpenAILLMAdapter,
)
from src.application.use_cases import SubmitVideoUseCase, ProcessVideoUseCase, GetTaskStatusUseCase


class Container:
    """手动依赖注入容器，集中管理所有层之间的依赖关系"""

    # ---- 配置 ----
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-xxx")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", None)
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # ---- 基础设施层 ----
    _event_bus: SimpleEventBus = SimpleEventBus()
    _task_repo: ProcessingTaskRepository = InMemoryTaskRepository()
    _downloader: VideoDownloaderPort = YtDlpVideoDownloaderAdapter()
    _recognizer: SpeechRecognizerPort = WhisperSpeechRecognizerAdapter(model_size=WHISPER_MODEL)
    _llm: LLMServicePort = OpenAILLMAdapter(
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
    )

    # ---- 应用层 ----
    @classmethod
    def get_event_bus(cls) -> SimpleEventBus:
        return cls._event_bus

    @classmethod
    def get_task_repo(cls) -> ProcessingTaskRepository:
        return cls._task_repo

    @classmethod
    def get_submit_use_case(cls) -> SubmitVideoUseCase:
        return SubmitVideoUseCase(cls._task_repo, cls._event_bus)

    @classmethod
    def get_process_use_case(cls) -> ProcessVideoUseCase:
        return ProcessVideoUseCase(
            task_repo=cls._task_repo,
            downloader=cls._downloader,
            recognizer=cls._recognizer,
            llm=cls._llm,
            event_bus=cls._event_bus,
        )

    @classmethod
    def get_query_use_case(cls) -> GetTaskStatusUseCase:
        return GetTaskStatusUseCase(cls._task_repo)
