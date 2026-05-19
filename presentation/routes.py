"""路由注册中心（Router Registration Hub）。

本模块是项目唯一的路由注册入口，职责：
- 从 ``presentation/api/`` 子模块导入各子路由（含装饰器定义）。
- 使用 ``include_router`` 统一挂载到主路由。

后续新增功能时：
1. 在 ``presentation/api/`` 下新建 handler 模块（用装饰器定义子 router）。
2. 在此文件 import 子 router 并 ``include_router``。
3. ``main.py`` 无需任何改动。
"""

from fastapi import APIRouter

from presentation.api.submit import router as submit_router
from presentation.api.status import router as status_router
from presentation.api.stream import router as stream_router
from presentation.api.documents import router as documents_router

# 主 API 路由聚合器（被 main.py 直接 include）
router = APIRouter()

# ============================================================================
# 任务路由（/api/v1/tasks）
# ============================================================================
TASK_PREFIX = "/api/v1/tasks"

router.include_router(submit_router, prefix=TASK_PREFIX)
router.include_router(status_router, prefix=TASK_PREFIX)
router.include_router(stream_router, prefix=TASK_PREFIX)

# ============================================================================
# 文档路由（/api/v1/documents）
# ============================================================================
router.include_router(documents_router, prefix="/api/v1/documents")
