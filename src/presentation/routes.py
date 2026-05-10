import asyncio
import json
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sse_starlette.sse import EventSourceResponse

from src.domain.exceptions import DomainException, InvalidVideoUrlError, TaskNotFoundError
from src.domain.models import TaskId
from src.domain.events import TaskStatusChangedEvent, SimpleEventBus
from src.presentation.dependencies import Container
from src.application.use_cases import SubmitVideoUseCase, ProcessVideoUseCase, GetTaskStatusUseCase
from src.application.dto import TaskStatusDTO

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# ---- SSE 订阅管理：每个 task_id 对应一个 asyncio.Queue ----
_task_queues: Dict[str, asyncio.Queue] = {}


def _ensure_queue(task_id: str) -> asyncio.Queue:
    if task_id not in _task_queues:
        _task_queues[task_id] = asyncio.Queue()
    return _task_queues[task_id]


# 注册事件总线处理器，将事件转发到对应 task 的 Queue
async def _on_status_changed(event: TaskStatusChangedEvent) -> None:
    q = _task_queues.get(event.task_id)
    if q:
        await q.put({
            "task_id": event.task_id,
            "status": event.new_status,
            "progress_percent": event.progress_percent,
        })


# 初始化时订阅
Container.get_event_bus().subscribe(TaskStatusChangedEvent, _on_status_changed)


# ---- API Endpoints ----

@router.post("/", response_model=TaskStatusDTO, status_code=202)
async def submit_video(
    request: Request,
    background_tasks: BackgroundTasks,
    submit_uc: SubmitVideoUseCase = Depends(Container.get_submit_use_case),
    process_uc: ProcessVideoUseCase = Depends(Container.get_process_use_case),
):
    """提交视频URL，创建异步处理任务"""
    body = await request.json()
    url = body.get("video_url", "")
    if not url:
        raise HTTPException(status_code=400, detail="缺少 video_url 字段")

    try:
        task_id = await submit_uc.execute(url)
    except InvalidVideoUrlError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 后台异步执行处理流水线
    background_tasks.add_task(process_uc.execute, task_id)

    return TaskStatusDTO(
        task_id=task_id.value,
        status="created",
        progress_percent=5,
        video_url=url,
    )


@router.get("/{task_id}", response_model=TaskStatusDTO)
async def get_task_status(
    task_id: str,
    query_uc: GetTaskStatusUseCase = Depends(Container.get_query_use_case),
):
    """查询任务状态与结果"""
    try:
        return await query_uc.execute(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="任务不存在")


@router.get("/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE 流式推送处理进度"""
    queue = _ensure_queue(task_id)

    async def event_generator():
        while True:
            data = await queue.get()
            yield {"data": json.dumps(data)}
            # 终端状态后结束流
            if data.get("status") in ("completed", "failed"):
                break

    return EventSourceResponse(event_generator())


# ---- 全局异常处理（可挂载到 main.py 的 app 上） ----

def register_exception_handlers(app):
    @app.exception_handler(InvalidVideoUrlError)
    async def handle_invalid_url(request, exc):
        return HTTPException(status_code=400, detail=str(exc))

    @app.exception_handler(TaskNotFoundError)
    async def handle_not_found(request, exc):
        return HTTPException(status_code=404, detail="任务不存在")

    @app.exception_handler(DomainException)
    async def handle_domain_error(request, exc):
        return HTTPException(status_code=500, detail=str(exc))
