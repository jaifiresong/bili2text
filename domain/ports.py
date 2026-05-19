"""领域端口（Ports）—— 抽象接口定义。

端口是 DDD 六边形架构 / 整洁架构中的核心概念：
- 领域层定义“需要什么能力”（即这些抽象基类）。
- 基础设施层通过“适配器（Adapter）”提供具体实现。
- 这种依赖倒置确保了领域层永远不需要知道外部技术细节（yt-dlp、Whisper、OpenAI SDK）。

新增外部依赖时（例如换用 Azure Speech Service 替代 Whisper）：
1. 实现 ``SpeechRecognizerPort`` 的新适配器。
2. 在 ``Container`` 中替换实例即可，无需修改领域层或应用层代码。
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, List

from . import VideoUrl
from .models import VideoInfo, ProcessingTask, TranscriptSegment, VideoInfoItem


class VideoDownloaderPort(ABC):
    @abstractmethod
    async def video_info(self, url: VideoUrl) -> VideoInfo:
        """获取音频基信息
        """
        ...

    @abstractmethod
    async def download(self, item: VideoInfoItem, video: VideoInfo) -> str:
        """返回文件路径
        """
        ...


class SpeechRecognizerPort(ABC):
    """语音识别端口。

    职责：将音频文件（本地路径）转换为文本及时间轴片段。
    """

    @abstractmethod
    async def transcribe(self, video: VideoInfoItem, language: str = "zh") -> str:
        """返回文件路径
        """
        ...


class LLMServicePort(ABC):
    """大语言模型服务端口。

    职责：提供文本后处理能力（加标点、总结）。
    当前设计为两个独立方法，方便后续分别替换为专用模型或 Prompt 策略。
    """

    @abstractmethod
    async def add_punctuation(self, video: VideoInfoItem) -> str:
        """为无标点的原始识别文本添加标点符号与分段。
        返回文件路径
        """
        ...

    @abstractmethod
    async def summarize(self, video: VideoInfoItem) -> str:
        """对文本进行摘要总结。
        返回文件路径
        """
        ...
