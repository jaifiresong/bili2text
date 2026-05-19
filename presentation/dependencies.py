from fastapi import Request, Depends
from typing import TypeVar, Type, Generic

from domain import VideoDownloaderPort, SpeechRecognizerPort, LLMServicePort
from domain.repositories import VideoInfoRepository, ProcessingTaskRepository
from infrastructure.adapters import VideoDownloaderAdapter
from infrastructure.adapters.LLMServiceAdapter import LLMServiceAdapter
from infrastructure.adapters.SpeechAdapter import SpeechAdapter
from infrastructure.repositories import TinyDBVideoInfoRepository, InMemoryProcessingTaskRepository
from application.use_cases import ParseUrlUseCase, ProcessVideoUseCase, ListTasksUseCase, GetTaskDetailUseCase, ListDocumentsUseCase, GetDocumentDetailUseCase


class Container:
    def __init__(self):
        self.providers = {}  # 抽象 → 实现

    def register(self, abstract, concrete):
        if hasattr(concrete.__init__, '__annotations__'):
            deps = []
            annotations = concrete.__init__.__annotations__
            for name, tp in annotations.items():
                if tp in self.providers:
                    # 自动收集依赖
                    deps.append(self.providers[tp])

            self.providers[abstract] = concrete(*deps)
        else:
            self.providers[abstract] = concrete()

    def resolve(self, cls):
        return self.providers[cls]


container = Container()
container.register(VideoDownloaderPort, VideoDownloaderAdapter)
container.register(SpeechRecognizerPort, SpeechAdapter)
container.register(LLMServicePort, LLMServiceAdapter)
container.register(VideoInfoRepository, TinyDBVideoInfoRepository)
container.register(ProcessingTaskRepository, InMemoryProcessingTaskRepository)
container.register(ParseUrlUseCase, ParseUrlUseCase)
container.register(ProcessVideoUseCase, ProcessVideoUseCase)
container.register(ListTasksUseCase, ListTasksUseCase)
container.register(GetTaskDetailUseCase, GetTaskDetailUseCase)
container.register(ListDocumentsUseCase, ListDocumentsUseCase)
container.register(GetDocumentDetailUseCase, GetDocumentDetailUseCase)

T = TypeVar('T')


class BeanResolver(Generic[T]):
    def __init__(self, bean_type: Type[T]):
        self.bean_type = bean_type

    def __call__(self, request: Request) -> T:
        return container.resolve(self.bean_type)


# 创建便捷函数
def get_depend_object(bean_type: Type[T]) -> T:
    """通用依赖注入函数"""
    return BeanResolver(bean_type)
