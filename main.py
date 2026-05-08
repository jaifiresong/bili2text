import json
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models import TaskStatus, read_doc_content, load_info_json as _load_info_json
from pipeline import create_task, get_task, run_pipeline, task_queues
from services import scan_documents
from downloaders.BiliDownloader import BiliDownloader

load_dotenv()

app = FastAPI(title="Bili2Text")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ===================================================================
# API Routes
# ===================================================================

@app.post("/api/resolve")
async def api_resolve(request: Request):
    """解析B站URL，返回视频信息和分P列表。"""
    body = await request.json()
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL 不能为空")

    try:
        downloader = BiliDownloader(url)
        pages_map = await downloader.get_video_info()
        pages = []
        for page_num in sorted(pages_map.keys()):
            p = pages_map[page_num]
            pages.append({
                "page": page_num,
                "part": p.get("part", f"P{page_num}"),
                "duration": p.get("duration", 0),
                "cid": p.get("cid", 0),
            })
        return {
            "bvid": downloader.bvid,
            "title": pages[0]["part"] if pages else downloader.bvid,
            "pages": pages,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析失败: {e}")


@app.post("/api/tasks")
async def api_create_task(request: Request):
    """创建处理任务。"""
    body = await request.json()
    url = body.get("url", "").strip()
    selected_pages = body.get("pages", [])
    bvid = body.get("bvid", "")
    title = body.get("title", bvid)

    if not url or not selected_pages:
        raise HTTPException(status_code=400, detail="URL 或分P列表不能为空")

    task_id = create_task(bvid, title, selected_pages)

    # 启动后台任务
    import asyncio
    asyncio.create_task(run_pipeline(task_id, url, selected_pages))

    return {"task_id": task_id, "status": TaskStatus.PENDING.value}


@app.get("/api/tasks/{task_id}")
async def api_get_task(task_id: str):
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task.model_dump()


@app.get("/api/tasks/{task_id}/sse")
async def api_task_sse(task_id: str):
    """SSE 实时推送任务进度。"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_stream():
        q = task_queues.get(task_id)
        if not q:
            return
        while True:
            msg = await q.get()
            yield f"data: {json.dumps(msg)}\n\n"
            if msg["event"] in ("completed", "failed"):
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/documents")
async def api_documents():
    """获取所有文档列表。"""
    return [doc.model_dump() for doc in scan_documents()]


@app.get("/api/documents/{bvid}/{page}")
async def api_document_content(bvid: str, page: int, doc_type: str = "raw"):
    """获取指定文档内容。"""
    content = read_doc_content(bvid, page, doc_type)
    info = _load_info_json(bvid)
    part = ""
    if info and "pages" in info:
        part = info["pages"].get(str(page), "")
    return {"bvid": bvid, "page": page, "part": part, "type": doc_type, "content": content}


# ===================================================================
# Page Routes
# ===================================================================

@app.get("/", response_class=HTMLResponse)
async def page_index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/documents", response_class=HTMLResponse)
async def page_documents(request: Request):
    docs = scan_documents()
    return templates.TemplateResponse(request, "documents.html", {"docs": docs})


@app.get("/documents/{bvid}/{page}", response_class=HTMLResponse)
async def page_detail(request: Request, bvid: str, page: int):
    info = _load_info_json(bvid)
    title = info.get("title", bvid) if info else bvid
    part = ""
    if info and "pages" in info:
        part = info["pages"].get(str(page), "")
    return templates.TemplateResponse(request, "detail.html", {
        "bvid": bvid,
        "page": page,
        "title": title,
        "part": part,
    })


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
