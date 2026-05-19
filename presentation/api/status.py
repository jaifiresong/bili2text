"""查询任务状态接口（Get Task Status Handler）。

路由：GET /api/v1/tasks/  (任务列表)
路由：GET /api/v1/tasks/{task_id}  (任务详情)
"""

from fastapi import APIRouter, Depends, HTTPException

from domain.exceptions import TaskNotFoundError

from application.use_cases import ListTasksUseCase, GetTaskDetailUseCase
from presentation.dependencies import get_depend_object

router = APIRouter(tags=["tasks"])


@router.get("/test")
async def test_hello():
    """测试接口：验证路由可达。"""
    return "hello world"


@router.get("/")
async def list_tasks(
    list_uc: ListTasksUseCase = Depends(get_depend_object(ListTasksUseCase)),
):
    """列出所有处理任务。"""
    return await list_uc.execute()


@router.get("/{task_id}")
async def get_task_detail(
    task_id: str,
    detail_uc: GetTaskDetailUseCase = Depends(get_depend_object(GetTaskDetailUseCase)),
):
    """查询任务详情，含处理结果文本。"""
    try:
        return await detail_uc.execute(task_id)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
