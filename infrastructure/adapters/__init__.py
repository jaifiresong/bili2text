"""基础设施适配器（Infrastructure Adapters）—— 防腐层实现。

本模块实现了 ``domain.ports`` 中定义的所有抽象端口，
将外部技术细节（yt-dlp、OpenAI Whisper、OpenAI API）封装为领域层可理解的接口。

设计原则：
- 适配器只负责"翻译"数据格式与调用协议，不包含业务逻辑。
- 若未来需要更换底层库（例如用 Azure Speech 替代 Whisper），
  只需新增适配器并在 Container 中替换即可。
"""
from .VideoDownloaderAdapter import VideoDownloaderAdapter

__all__ = [
    'VideoDownloaderAdapter'
]
