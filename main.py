"""FastAPI 应用入口。

启动方式：
    uvicorn main:app --reload

环境变量要求：
    LLM_API_KEY 必须设置为有效的 OpenAI 兼容 API 密钥，否则 LLM 步骤会失败。
"""
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles

from presentation.exceptions import register_exception_handlers
from presentation.routes import router

app = FastAPI(
    title="B站视频转录与智能总结系统",
    description="基于 DDD 分层架构的 B 站视频音频提取与智能文本处理服务",
    version="1.0.0",
)

# 注册全局异常处理器（将领域异常映射为标准 HTTP JSON 响应）
register_exception_handlers(app)

# 挂载 API 路由
app.include_router(router)

# 挂载静态文件目录（用于独立 JS、CSS 等）
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Jinja2 模板配置
templates = Jinja2Templates(directory=str(BASE_DIR / "presentation" / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Web UI 首页。"""
    return templates.TemplateResponse(request, "index.html")


@app.get("/health")
async def health():
    """健康检查端点，供部署探针使用。"""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info",
    )
