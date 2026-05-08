import json
import os
from datetime import datetime
from pathlib import Path

from models import Document, get_resource_dir


def scan_documents() -> list[Document]:
    """扫描 resources/ 目录，返回所有可用文档。"""
    docs = []
    res_dir = get_resource_dir()
    if not res_dir.exists():
        return docs

    for bvid_dir in sorted(res_dir.iterdir()):
        if not bvid_dir.is_dir():
            continue

        bvid = bvid_dir.name
        info = load_info_json(bvid)
        title = info.get("title", bvid) if info else bvid
        created_at = None
        if info and "created_at" in info:
            try:
                created_at = datetime.fromisoformat(info["created_at"])
            except Exception:
                pass

        pages = []
        for raw_file in sorted(bvid_dir.glob("*_raw.txt")):
            try:
                page_num = int(raw_file.stem.replace("_raw", ""))
            except ValueError:
                continue

            part = info.get("pages", {}).get(str(page_num), f"P{page_num}") if info else f"P{page_num}"
            pages.append({
                "page": page_num,
                "part": part,
                "has_raw": True,
                "has_punctuated": (bvid_dir / f"{page_num}_punctuated.md").exists(),
                "has_summary": (bvid_dir / f"{page_num}_summary.md").exists(),
            })

        if pages:
            docs.append(Document(
                bvid=bvid,
                title=title,
                pages=pages,
                created_at=created_at,
            ))

    # 按创建时间倒序
    docs.sort(key=lambda d: d.created_at or datetime.min, reverse=True)
    return docs


def load_info_json(bvid: str) -> dict:
    path = get_resource_dir() / bvid / "info.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}
