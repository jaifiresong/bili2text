"""提交视频任务接口（Submit Task Handler）。

路由：POST /api/v1/tasks/
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from domain import ProcessingTask
from application.use_cases import ProcessVideoUseCase, ParseUrlUseCase
from presentation.dependencies import get_depend_object

router = APIRouter(tags=["tasks"])


@router.get("/parse", status_code=202)
async def parse_video_url(
        request: Request,
        parse_uc: ParseUrlUseCase = Depends(get_depend_object(ParseUrlUseCase)),
):
    """
    - ParseUrlUseCase.execute() 返回 VideoInfo（领域对象）
    - FastAPI 自动把 VideoInfo dataclass 序列化成 JSON
    合理。 在你当前的场景下完全没问题。
    原因很简单：
        你的 VideoInfo 字段全是基础类型（str, int, List[VideoInfoItem]），和 API 契约一一对应，不需要隐藏字段、不需要类型转换、不需要解耦。
        这时候硬定义一个跟 VideoInfo 一模一样的 DTO，纯粹是形式主义。
    但要注意一个隐性风险：
        Presentation 层直接返回领域对象，意味着领域模型的字段结构就是 API 契约。
        以后如果 VideoInfo 改了字段名或加了内部字段，API 会直接跟着变。
        对于内部项目或早期阶段，这完全可以接受；如果 API 需要版本化或对前端有稳定性承诺，到时候再加 DTO 也不迟。
    > 一句话：现阶段合理，不必为了形式主义定义空壳 DTO。等 API 契约和领域模型真正出现分歧时，再引入 DTO 解耦。
    """
    url = request.query_params.get("video_url", "https://www.bilibili.com/video/BV1fMwvzDECY/")
    if not url:
        raise HTTPException(status_code=400, detail="缺少 video_url 字段")
    return await parse_uc.execute(url)


@router.post("/", status_code=202)
async def submit_video(
        request: Request,
        background_tasks: BackgroundTasks,
        process_uc: ProcessVideoUseCase = Depends(get_depend_object(ProcessVideoUseCase))
):
    """提交选中的分P，创建异步处理任务。

    请求体: { "video_id": "...", "pages": [1, 2, ...] }
    创建任务后立即返回，流水线在后台执行。
    """
    body = await request.json()
    video_id = body.get("video_id", "")
    pages: list = body.get("pages", [])
    task: ProcessingTask = await process_uc.execute(video_id, pages)
    background_tasks.add_task(process_uc.start_pipeline, task.task_id, task.video_id)
    return task
