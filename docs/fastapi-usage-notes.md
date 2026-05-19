# FastAPI 使用经验笔记

> 整理自 bili2text 项目开发过程中的 FastAPI 相关问题与解决方案。

---

## 1. 依赖注入（Depends）的作用

### 核心问题
用 `Depends(Container.get_submit_use_case)` 和手动 `new` 一个实例，效果一样吗？不用 DI 有什么影响？

### 答案
效果类似，但有几个关键区别：

**手动 new 的问题：**
```python
async def submit_video(request: Request):
    repo = InMemoryTaskRepository()    # 每次 new 一个新实例
    event_bus = SimpleEventBus()        # 又一个新实例
    submit_uc = SubmitVideoUseCase(repo, event_bus)
    ...
```

1. **实例不共享** — 每次 new 出的 `repo`、`event_bus` 都是新的，不同路由各自操作不同的内存仓储，数据互相看不到。
2. **替换困难** — 以后想换成数据库仓储，需要改每个路由函数里的 new 代码。
3. **测试困难** — 无法从外部传入 mock 对象。

**Depends + Container 的好处：**
1. **单例共享** — `Container._task_repo` 是类属性，所有路由拿到的是同一个实例，数据一致。
2. **集中装配** — 换仓储只需改 `Container` 一处，所有用例自动生效。
3. **可测试** — 测试时可以替换 `Container._task_repo = MockRepo()`，无需改路由代码。

**不用 DI 最致命的影响：** SSE 推送依赖 `event_bus` 和 `repo` 是同一个实例，手动 new 会导致事件总线和任务仓储断裂，进度推送完全不工作。

---

## 2. 异常处理器的组织方式

### 核心问题
`register_exception_handlers` 不应该放在 routes.py 里吧？官方有没有推荐的组织方式？

### 答案
FastAPI 没有 Django 那种统一的 `settings.py` 约定，但社区有几种常见方式：

**方式 1：直接放 main.py（最简单，官方文档默认做法）**
```python
@app.exception_handler(DomainException)
async def handle_domain_error(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
```

**方式 2：独立模块 + main.py 注册（推荐）**
```
presentation/
  exceptions.py    ← 定义 handler 函数
  routes.py        ← 只管路由
```
`main.py` 里：
```python
from presentation.exceptions import register_exception_handlers
register_exception_handlers(app)
```

**方式 3：App Factory 模式（大型项目推荐）**
```python
def create_app() -> FastAPI:
    app = FastAPI(...)
    register_exception_handlers(app)
    app.include_router(router)
    return app
```

**结论：** 对中等规模项目，方案 2 最合适 — `exceptions.py` 管异常映射，`routes.py` 管路由，职责清晰。

---

## 3. 路由注册：装饰器 vs 集中注册（add_api_route）

### 核心问题
能不能不用 `@router.get` 装饰器，统一在 `routes.py` 中用 `add_api_route` 注册？

### 答案
可以。FastAPI 支持两种方式：

**装饰器模式（默认）：**
```python
# api/tasks.py
@router.get("/{task_id}", response_model=TaskStatusDTO)
async def get_task_status(task_id: str) -> TaskStatusDTO:
    return await query_uc.execute(task_id)
```

**集中注册模式（add_api_route）：**
```python
# api/tasks.py
async def get_task_status(task_id: str) -> TaskStatusDTO:
    return await query_uc.execute(task_id)

# routes.py
tasks_router.add_api_route(
    path="/{task_id}",
    endpoint=get_task_status,
    methods=["GET"],
    response_model=TaskStatusDTO,
)
```

**实际项目推荐：混合方案**
- 模块内用装饰器定义子 router
- 顶层 `routes.py` 只做 `include_router`
```python
# routes.py
from api.submit import router as submit_router
from api.status import router as status_router

router.include_router(submit_router, prefix="/api/v1/tasks")
router.include_router(status_router, prefix="/api/v1/tasks")
```

---

## 4. 装饰器模式的好处（vs 集中注册）

| 对比项 | 装饰器模式 | 集中注册（add_api_route） |
|--------|-----------|------------------------|
| 信息密度 | handler 和路由元数据在一起，一眼看完 | handler 和路由配置在两个文件，需要来回跳 |
| IDE 友好 | Ctrl+Click 直接跳到 handler | 多一层中转（routes.py） |
| 社区惯例 | 99% 教程和开源项目使用 | Spring/Django 开发者更熟悉 |
| 类型安全 | `response_model` 紧挨着函数，改返回值时容易注意到 | 配置分散，容易不一致 |
| Swagger 维护 | `summary`/`description` 和 handler 在一起 | 元数据在 routes.py，改逻辑时容易忘同步 |

**结论：** 装饰器模式更适合 FastAPI 生态，信息和逻辑就近聚合。

---

## 5. 集中注册模式的坏处（vs 装饰器）

1. **信息碎片化** — handler 文件里只有裸函数，想知道 URL、返回 schema 必须切到 `routes.py`
2. **类型不一致风险** — `routes.py` 里的 `response_model` 和 handler 实际返回不匹配时，IDE 不会报错
3. **依赖注入声明分散** — handler 里的 `Depends` 和路由元数据里的 `dependencies=[...]` 在两个文件
4. **Swagger 文档维护麻烦** — `summary`/`description` 在 `routes.py`，改逻辑时容易忘记同步更新
5. **和社区惯例不一致** — FastAPI 官方文档、StackOverflow 全是装饰器模式

---

## 6. 多文件拆分路由

### 核心问题
接口多了，想把一个文件拆成多个，每个功能一个文件。

### 答案
按功能拆分到独立文件，每个文件有自己的 `APIRouter`，然后在 `routes.py` 统一 include：

```
presentation/
  api/
    submit.py      ← POST /api/v1/tasks/
    status.py      ← GET /api/v1/tasks/{task_id}
    stream.py      ← GET /api/v1/tasks/{task_id}/stream
  routes.py        ← include_router 汇总
```

**关键点：** 多个子 router 可以挂载到**同一个 prefix**，FastAPI 会合并处理：
```python
# routes.py
TASK_PREFIX = "/api/v1/tasks"
router.include_router(submit_router, prefix=TASK_PREFIX)
router.include_router(status_router, prefix=TASK_PREFIX)
router.include_router(stream_router, prefix=TASK_PREFIX)
```

---

## 7. 事件总线订阅的执行时机

### 核心问题
`Container.get_event_bus().subscribe(TaskStatusChangedEvent, _on_status_changed)` 这段代码的作用？

### 答案
这行代码写在模块顶层（import 时执行），作用是**把"后台处理流水线"和"前端 SSE 推送"桥接起来**。

**数据流：**
```
ProcessVideoUseCase (后台任务)
    │
    ▼ 每完成一步调用 _emit_status()
TaskStatusChangedEvent
    │
    ▼ publish() 到 SimpleEventBus
SimpleEventBus (内存分发器)
    │
    ▼ 找到所有已订阅的回调
_on_status_changed (本模块回调)
    │
    ▼ await q.put(data)
_task_queues[task_id] (asyncio.Queue)
    │
    ▼ await queue.get()
stream_task_progress (SSE 生成器)
    │
    ▼ yield "data: {...}\n\n"
客户端 EventSource
```

**为什么写在模块顶层？** Python 模块只被 import 一次，这行代码在整个进程生命周期中只执行一次。如果放在 handler 函数里，每次请求都会重复订阅。

**为什么用事件总线而不是直接写队列？** `ProcessVideoUseCase` 在 `application` 层，不应该知道 `presentation` 层的 SSE 存在。事件总线是领域层定义的抽象，两边都只跟抽象打交道，符合 DDD 分层原则。

---

## 8. DTO 如何自动转成 HTTP JSON 响应

### 核心问题
`TaskStatusDTO` 是如何被转成 HTTP 响应的？

### 答案
**全程由 FastAPI + Pydantic 框架自动完成，不需要写任何序列化代码。**

开发者只写一行：
```python
return await query_uc.execute(task_id)   # 返回 TaskStatusDTO 实例
```

框架自动完成：
1. FastAPI 看到 `@router.get(..., response_model=TaskStatusDTO)`，交给 Pydantic 处理
2. Pydantic 把 dataclass 转成 dict（Pydantic v2 原生支持 dataclass）
3. FastAPI 把 dict 转成 JSON 字符串
4. FastAPI 包装成 `JSONResponse`，加上 `content-type: application/json`
5. Uvicorn 发送给客户端

**核心链路：**
```
TaskStatusDTO (@dataclass)
    │
    ▼ Pydantic 模型序列化 (由 response_model 触发)
dict
    │
    ▼ json.dumps()
JSON 字符串
    │
    ▼ FastAPI 自动包装
JSONResponse(content=..., media_type="application/json")
    │
    ▼ Uvicorn 发送
HTTP Response Body
```

**注意：** 如果去掉 `response_model`，dataclass 默认不支持 JSON 序列化，会抛 `TypeError: Object of type TaskStatusDTO is not JSON serializable`。

---

## 9. 如何改变响应类型（非 JSON）

### 核心问题
如果需要改变 JSONResponse，改成其它响应类型该怎么做？

### 答案
**方式 1：在 handler 里直接返回 Response 对象**
```python
from fastapi.responses import PlainTextResponse

@router.get("/{task_id}")
async def get_task_status(task_id: str):
    dto = await query_uc.execute(task_id)
    # 完全绕过 response_model 的自动 JSON 包装
    return PlainTextResponse(content=f"Status: {dto.status}")
```
一旦返回 `Response` 子类实例，FastAPI 就不再自动序列化，`response_model` 也失效。

**方式 2：用 `response_class` 参数**
```python
@router.get("/{task_id}", response_class=HTMLResponse)
async def get_task_status(task_id: str):
    dto = await query_uc.execute(task_id)
    # FastAPI 把返回值（str）自动包成 HTMLResponse
    return f"<h1>{dto.status}</h1>"
```

**方式 3：返回 Response + 保留 response_model 用于文档**
```python
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

@router.get("/{task_id}", response_model=TaskStatusDTO)
async def get_task_status(task_id: str):
    dto = await query_uc.execute(task_id)
    return JSONResponse(
        content=jsonable_encoder(dto),
        headers={"X-Custom-Header": "value"},
    )
```
`jsonable_encoder` 是 FastAPI 内部把 Pydantic/dataclass 转成可 JSON 序列化 dict 的工具。

**方式 4：全局修改默认响应类**
```python
from fastapi.responses import ORJSONResponse

app = FastAPI(default_response_class=ORJSONResponse)
```

---

## 10. 路由冲突：静态路由 vs 动态路由

### 核心问题
加了一个 `/test` 接口，但它跟 `/{task_id}` 的路由冲突了。

### 答案
冲突原因是 **`/{task_id}` 动态路径参数会贪婪匹配任何单段路径**。`/test` 也会被当成 `task_id="test"`。

**解决方法：把静态路由放在动态路由之前注册。**

```python
# ✅ 正确：静态路由在前
@router.get("/test")
async def test_hello():
    return "hello world"

@router.get("/{task_id}", response_model=TaskStatusDTO)
async def get_task_status(task_id: str):
    ...
```

```python
# ❌ 错误：动态路由在前，/test 永远不会被命中
@router.get("/{task_id}", response_model=TaskStatusDTO)
async def get_task_status(task_id: str):
    ...

@router.get("/test")
async def test_hello():
    return "hello world"
```

FastAPI 按**注册顺序**匹配路由，先注册的先匹配。静态路由 `/test` 必须在动态路由 `/{task_id}` 之前声明。

---

## 附：FastAPI 响应流程速查

```
handler 函数
    │
    ▼ return 值
自动序列化（Pydantic，由 response_model 触发）
    │
    ▼ dict / list / str
to_json()
    │
    ▼ JSON 字符串
自动包装成 JSONResponse（或 response_class 指定的类型）
    │
    ▼ Response 对象
Uvicorn → ASGI → HTTP
```

如果 handler 直接返回 `Response` 子类实例（如 `HTMLResponse`、`JSONResponse`），框架会**跳过所有自动处理步骤**，直接发送你构造的响应。
