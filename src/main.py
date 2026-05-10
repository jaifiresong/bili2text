"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.requests import Request

from src.presentation.routes import router, register_exception_handlers

app = FastAPI(
    title="B站视频转录与智能总结系统",
    description="基于 DDD 分层架构的 B 站视频音频提取与智能文本处理服务",
    version="1.0.0",
)

# 注册全局异常处理器
register_exception_handlers(app)

# 挂载 API 路由
app.include_router(router)

# 模板
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "presentation" / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok"}
