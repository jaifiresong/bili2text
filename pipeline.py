import asyncio
import os
import uuid
from datetime import datetime

import whisper

from ChatClient import ChatClient
from downloaders.BiliDownloader import BiliDownloader
from models import (
    TaskInfo,
    TaskStatus,
    save_doc_content,
    save_info_json,
)
from process_doc import PROMPT_PUNCTUATION, PROMPT_SUMMARY

# 全局任务状态
tasks: dict[str, TaskInfo] = {}
task_queues: dict[str, asyncio.Queue] = {}

# Whisper 模型（懒加载）
_whisper_model = None


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        print("[Whisper] 正在加载模型 small ...")
        _whisper_model = whisper.load_model("small")
        print("[Whisper] 模型加载完成")
    return _whisper_model


def create_task(bvid: str, title: str, selected_pages: list[int]) -> str:
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = TaskInfo(
        task_id=task_id,
        bvid=bvid,
        title=title,
        selected_pages=selected_pages,
        total_pages=len(selected_pages),
    )
    task_queues[task_id] = asyncio.Queue()
    return task_id


def get_task(task_id: str) -> TaskInfo | None:
    return tasks.get(task_id)


async def _notify(task_id: str, event: str, data: dict):
    q = task_queues.get(task_id)
    if q:
        await q.put({"event": event, "data": data})


async def _run_whisper(audio_path: str) -> str:
    model = get_whisper_model()
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: model.transcribe(
            audio_path,
            fp16=False,
            language="Chinese",
            initial_prompt="以下是普通话的句子",
        ),
    )
    return result["text"]


async def _run_llm(prompt: str, system_role: str) -> str:
    cfg = {
        "model": os.getenv("LLM_MODEL"),
        "api_key": os.getenv("LLM_API_KEY"),
        "base_url": os.getenv("LLM_BASE_URL"),
    }
    client = ChatClient(**cfg, system_role=system_role)
    return client.chat(prompt, stream=False)


async def run_pipeline(task_id: str, url: str, selected_pages: list[int]):
    """执行完整处理管道。"""
    task = tasks[task_id]
    task.status = TaskStatus.DOWNLOADING
    await _notify(task_id, "status", {"status": task.status.value, "message": "开始解析视频信息..."})

    try:
        downloader = BiliDownloader(url)
        pages_map = await downloader.get_video_info()

        # 提取标题：通常第1P的 part 就是主标题
        first_page = pages_map.get(1, {})
        video_title = first_page.get("part", task.bvid or downloader.bvid)
        task.title = video_title
        task.bvid = downloader.bvid

        # 保存 info.json
        pages_meta = {}
        for k, v in pages_map.items():
            pages_meta[str(k)] = v.get("part", f"P{k}")
        save_info_json(
            downloader.bvid,
            {
                "bvid": downloader.bvid,
                "title": video_title,
                "pages": pages_meta,
                "created_at": datetime.now().isoformat(),
            },
        )

        total = len(selected_pages)

        for idx, page_num in enumerate(selected_pages):
            task.current_page = page_num
            task.progress = int((idx / total) * 100)
            page_info = pages_map.get(page_num)
            if not page_info:
                continue

            page_name = page_info.get("part", f"P{page_num}")

            # 1. 下载
            task.status = TaskStatus.DOWNLOADING
            task.message = f"下载 P{page_num} {page_name}"
            await _notify(task_id, "progress", {
                "status": task.status.value,
                "message": task.message,
                "progress": task.progress,
                "current_page": page_num,
            })
            await downloader.download(page_info, page_num)

            # 2. 转录
            task.status = TaskStatus.TRANSCRIBING
            task.message = f"转录 P{page_num} {page_name}"
            await _notify(task_id, "progress", {
                "status": task.status.value,
                "message": task.message,
                "progress": task.progress,
                "current_page": page_num,
            })
            audio_path = f"./resources/{downloader.bvid}/{page_num}.mp3"
            raw_text = await _run_whisper(audio_path)
            save_doc_content(downloader.bvid, page_num, "raw", raw_text)

            # 3. 加标点
            task.status = TaskStatus.PUNCTUATING
            task.message = f"加标点 P{page_num} {page_name}"
            await _notify(task_id, "progress", {
                "status": task.status.value,
                "message": task.message,
                "progress": task.progress,
                "current_page": page_num,
            })
            punctuated = await _run_llm(raw_text, PROMPT_PUNCTUATION)
            save_doc_content(downloader.bvid, page_num, "punctuated", punctuated)

            # 4. 总结
            task.status = TaskStatus.SUMMARIZING
            task.message = f"总结 P{page_num} {page_name}"
            await _notify(task_id, "progress", {
                "status": task.status.value,
                "message": task.message,
                "progress": task.progress,
                "current_page": page_num,
            })
            summary = await _run_llm(raw_text, PROMPT_SUMMARY)
            save_doc_content(downloader.bvid, page_num, "summary", summary)

        # 全部完成
        task.status = TaskStatus.COMPLETED
        task.progress = 100
        task.message = "全部完成"
        task.completed_at = datetime.now()
        await _notify(task_id, "completed", {
            "message": "全部完成",
            "bvid": task.bvid,
            "title": task.title,
        })

    except Exception as e:
        task.status = TaskStatus.FAILED
        task.message = f"失败: {e}"
        await _notify(task_id, "failed", {"message": str(e)})
