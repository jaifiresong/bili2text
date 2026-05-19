"""SSE 进度流接口（Stream Task Progress Handler）。

路由：GET /api/v1/tasks/{task_id}/stream
"""

import asyncio
import json
from typing import Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from domain.events import TaskStatusChangedEvent

router = APIRouter(tags=["tasks"])

# ============================================================================
# 业务背景：为什么需要 SSE + 事件总线？
# ============================================================================
# 视频处理流水线（下载 -> 转录 -> 加标点 -> 总结）在 FastAPI BackgroundTasks
# 中异步执行，耗时可能数分钟。HTTP 轮询方案效率低，因此采用 SSE（Server-Sent
# Events）向客户端实时推送进度。
#
# 架构问题：BackgroundTasks 运行在用例层（application），而 SSE 流在表现层
#（presentation）返回给客户端。两者不能直接通信，因此引入"事件总线"作为桥梁：
#
#     BackgroundTasks (ProcessVideoUseCase)
#          │
#          ▼ 发布 TaskStatusChangedEvent
#     SimpleEventBus (domain/events.py)
#          │
#          ▼ 订阅回调 _on_status_changed
#     _task_queues[task_id] (asyncio.Queue)
#          │
#          ▼ 消费
#     stream_task_progress (本模块) → SSE Response
#
# 这样处理流水线完全不知道 HTTP/SSE 的存在，符合 DDD 分层原则。
# ============================================================================


# ---- 内存队列池：每个 task_id 对应一个 asyncio.Queue ----
# 当客户端打开 SSE 连接时，为该 task_id 创建一个队列；
# 当任务到达终态（completed/failed）或客户端断开时，队列被清理。
# 注意：单进程内存实现，重启进程后队列丢失。
_task_queues: Dict[str, asyncio.Queue] = {}


def _ensure_queue(task_id: str) -> asyncio.Queue:
    """获取或创建指定 task_id 的异步队列。

    若该 task 的 SSE 连接已被打开过，复用已有队列（支持客户端重连场景）。
    """
    if task_id not in _task_queues:
        _task_queues[task_id] = asyncio.Queue()
    return _task_queues[task_id]


async def _on_status_changed(event: TaskStatusChangedEvent) -> None:
    """事件总线回调：将进度事件投递到对应 task 的 SSE 队列中。

    只要事件总线发布了一个 ``TaskStatusChangedEvent``，此回调就会自动被触发，
    无论当时是否有客户端在连接 SSE（没有连接时，消息会堆积在队列中，
    等客户端连接后一次性拉取）。
    """
    q = _task_queues.get(event.task_id)
    if q:
        await q.put({
            "task_id": event.task_id,
            "status": event.new_status,
            "progress_percent": event.progress_percent,
        })


# ============================================================================
# 模块导入时执行（import-time side effect）：向全局事件总线注册订阅器。
# ============================================================================
# 1. Container 中的 SimpleEventBus 是单例（class 变量），所有用例共用同一个实例。
# 2. subscribe() 将 _on_status_changed 函数注册为 TaskStatusChangedEvent 的处理器。
# 3. 由于 Python 模块只会被导入一次，这行代码在整个进程生命周期中只执行一次。
# 4. 当 ProcessVideoUseCase._emit_status() 调用 event_bus.publish() 时，
#    事件会被分发到所有已订阅的处理器，_on_status_changed 就会将数据压入队列。
# ============================================================================

@router.get("/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE 流式推送处理进度。

    客户端通过 EventSource 连接此端点，实时接收 ``TaskStatusChangedEvent`` 转换的
    JSON 消息。当任务到达 ``completed`` 或 ``failed`` 终态后，流自动关闭。
    """
    # 确保该 task 有对应的队列（若后台任务已开始推送但客户端尚未连接，消息会暂存在队列中）
    queue = _ensure_queue(task_id)

    async def event_generator():
        """SSE 事件生成器。

        按 Server-Sent Events 协议格式输出：
        每行以 ``data: `` 开头，事件块之间以空行 ``\n\n`` 分隔。
        """
        try:
            while True:
                # 阻塞等待队列中的新消息（由 _on_status_changed 回调 put 进来）
                data = await queue.get()
                # 手动格式化为 SSE 协议要求的 text/event-stream 格式
                yield f"data: {json.dumps(data)}\n\n"
                # 终端状态后结束流，触发 finally 块清理队列
                if data.get("status") in ("completed", "failed"):
                    break
        finally:
            # 流结束后清理队列，防止长时间运行导致内存泄漏。
            # 注意：若后台任务尚未完成但客户端断开，队列会被清理，
            # 后续消息因找不到队列而被静默丢弃（符合预期：没人听了就不推）。
            _task_queues.pop(task_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
