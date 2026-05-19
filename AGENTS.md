# AGENTS.md — bili2text_v3

## Setup & Run

- **Python 解释器**: `D:\jaifiresong\bili2text\.venv\Scripts\python.exe` (父项目虚拟环境)
- **启动命令**: `uvicorn main:app --reload`（注意 README 中写的 `src.main:app` 是错的）
- 无 `pyproject.toml` / `requirements.txt`，依赖全部来自父项目的 venv
- `.env` 含真实 API key，**严禁提交或修改**

## DDD 分层约束（严格！）

```
presentation/ → application/ → domain/ ← infrastructure/
```

- **`domain/` 零外部依赖**：不得出现 `import whisper`、`import openai`、`import fastapi`、`import httpx` 等。只允许 Python 标准库 + 少量自包含工具库（如 `efficient.util_hash`）
- **端口定义在 `domain/ports.py`**，适配器实现在 `infrastructure/adapters/`，注册在 `presentation/dependencies.py`
- **`domain/__init__.py` 未导出 repositories**（`__all__` 里写了但没实际 import），需要从 `domain.repositories` 直接导入

## 自定义 DI 容器

- `presentation/dependencies.py` 有手工 `Container` 类（非 FastAPI 内置 DI）
- 所有端口→适配器的注册在此文件集中完成
- 路由通过 `Depends(get_depend_object(ParseUrlUseCase))` 获取依赖
- **SSE 推送依赖 Container 单例**：多个 handler 必须共享同一个 event_bus/repo 实例，不能每次手动 new

## 路由结构

所有 API 路由前缀 `/api/v1/tasks`，在 `presentation/routes.py` 统一 `include_router`：

| 方法 | 路径 | 文件 |
|------|------|------|
| GET | `/api/v1/tasks/parse` | `presentation/api/submit.py` |
| POST | `/api/v1/tasks/` | `presentation/api/submit.py` |
| GET | `/api/v1/tasks/test` | `presentation/api/status.py` |
| GET | `/api/v1/tasks/{task_id}/stream` | `presentation/api/stream.py` |

- **静态路由必须放在动态路由之前**（如 `/test` 在 `/{task_id}` 之前），否则被动态路由吞掉

## SSE & 事件总线

- `domain/events.py` — `SimpleEventBus` 内存实现
- **订阅必须在模块顶层**（import 时执行），不能放在 handler 函数里，否则每次请求会重复订阅
- 数据流：`ProcessVideoUseCase._emit_status()` → `SimpleEventBus.publish()` → `_on_status_changed` 回调 → `asyncio.Queue` → SSE 生成器 → 客户端

## 存储

- **视频信息**: TinyDB 持久化 `storage/video_info.json`
- **处理任务**: 内存字典 `InMemoryProcessingTaskRepository`（进程重启丢失）
- **音频/文本产物**: `./storage/{cid}.txt`、`./storage/punctuation/{cid}.txt`、`./storage/summary/{cid}.txt`
- **音频下载**: `./{bvid}/{page}.mp3`

## LLM 配置

- `infrastructure/config.py` 中 `LLM_CFG` 的 key 硬编码为 `'kimi-k2.6'`
- API key/base_url/model 从 `.env` 读取
- Prompt 模板硬编码在 `LLMServiceAdapter.py`，不属于领域层概念

## 当前代码状态

- DDD 分层骨架已就位，但 **流水线尚未完整跑通**
- `domain/service.py` 的 `TaskHandleService.start()` 在 `ProcessVideoUseCase.execute()` 中**未被调用**
- `TaskHandleService.handle_item()` 为同步方法但调用了 async 端口方法（返回 coroutine 未 await）

## 代码风格约定

- **不要删除代码中的任何注释**
- 使用 `dataclass` + `Pydantic BaseModel` 混合建模
- `mypy.ini` 已配置 `tinydb.mypy_plugin`
