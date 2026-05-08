import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RESOLVING = "resolving"        # 解析视频信息
    DOWNLOADING = "downloading"    # 下载音频
    TRANSCRIBING = "transcribing"  # Whisper 转录
    PUNCTUATING = "punctuating"    # LLM 加标点
    SUMMARIZING = "summarizing"    # LLM 总结
    COMPLETED = "completed"
    FAILED = "failed"


class PageInfo(BaseModel):
    page: int
    part: str
    cid: int
    duration: int = 0


class TaskInfo(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    bvid: str = ""
    title: str = ""
    message: str = ""           # 当前步骤描述或错误信息
    progress: int = 0           # 0-100 整体进度
    current_page: int = 0       # 当前处理的分P
    total_pages: int = 0
    selected_pages: list[int] = []
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class Document(BaseModel):
    bvid: str
    title: str = ""
    pages: list[dict] = []      # [{"page": 1, "part": "标题", "has_raw": true, ...}]
    created_at: Optional[datetime] = None


def get_resource_dir() -> Path:
    return Path("./resources").resolve()


def read_doc_content(bvid: str, page: int, doc_type: str) -> str:
    """读取指定文档内容。doc_type: raw, punctuated, summary"""
    base = get_resource_dir() / bvid
    mapping = {
        "raw": base / f"{page}_raw.txt",
        "punctuated": base / f"{page}_punctuated.md",
        "summary": base / f"{page}_summary.md",
    }
    path = mapping.get(doc_type)
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def save_doc_content(bvid: str, page: int, doc_type: str, content: str) -> None:
    """保存文档内容。"""
    base = get_resource_dir() / bvid
    base.mkdir(parents=True, exist_ok=True)
    mapping = {
        "raw": base / f"{page}_raw.txt",
        "punctuated": base / f"{page}_punctuated.md",
        "summary": base / f"{page}_summary.md",
    }
    path = mapping.get(doc_type)
    if path:
        path.write_text(content, encoding="utf-8")


def save_info_json(bvid: str, info: dict) -> None:
    base = get_resource_dir() / bvid
    base.mkdir(parents=True, exist_ok=True)
    (base / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")


def load_info_json(bvid: str) -> Optional[dict]:
    path = get_resource_dir() / bvid / "info.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None
