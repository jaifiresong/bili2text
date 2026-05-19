from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from domain.exceptions import DomainException, InvalidVideoUrlError, TaskNotFoundError


# ---- 全局异常处理（需要挂载到 main.py 的 app 上） ----

def register_exception_handlers(app):
    """注册领域异常到 FastAPI 全局异常处理器。

    这样所有未被路由层显式捕获的 ``DomainException`` 子类
    都会自动映射为对应的 HTTP JSON 响应。
    """

    @app.exception_handler(InvalidVideoUrlError)
    async def handle_invalid_url(request, exc):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(TaskNotFoundError)
    async def handle_not_found(request, exc):
        return JSONResponse(status_code=404, content={"detail": "任务不存在"})

    @app.exception_handler(DomainException)
    async def handle_domain_error(request, exc):
        return JSONResponse(status_code=500, content={"detail": str(exc)})
