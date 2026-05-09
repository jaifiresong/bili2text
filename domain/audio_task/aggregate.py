from dataclasses import dataclass, field


@dataclass
class AudioTask:
    """聚合根：音频处理任务（领域层核心）"""
    task_id: str
