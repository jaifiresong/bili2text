# Bili2Text 项目架构文档

> 本文档面向开发者和维护者，帮助你理解系统的设计思路、各层职责，以及如何安全地修改和扩展代码。

---

## 1. 项目概述

**Bili2Text** 是一个基于 FastAPI 的 Web 服务，用户输入 B 站视频地址后，系统自动完成：

```
用户输入URL → 下载音频 → Whisper语音识别 → LLM加标点 → LLM总结 → 展示结果
```

系统采用**分层架构 + 端口-适配器模式**，将核心业务逻辑与外部技术实现解耦，确保代码的可维护性、可测试性和可扩展性。

---

## 2. 架构总览

### 2.1 分层架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         表示层 (Presentation)                        │
│   FastAPI Routes / Jinja2 Templates / SSE 实时推送                   │
├─────────────────────────────────────────────────────────────────────┤
│                         应用层 (Application)                         │
│   Use Cases（用例编排）/ DTO 转换 / 事务边界                           │
├─────────────────────────────────────────────────────────────────────┤
│                    领域层 (Domain)  ← 系统核心                        │
│   聚合根(ProcessingTask) / 值对象 / 领域事件 / 端口接口                 │
├─────────────────────────────────────────────────────────────────────┤
│                      基础设施层 (Infrastructure)                     │
│   适配器实现(Anti-Corruption Layer) / 仓储实现 / 外部服务调用           │
│   yt-dlp  |  Whisper  |  OpenAI API  |  内存/数据库仓储               │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

| 原则 | 说明 |
|------|------|
| **依赖倒置** | 领域层定义接口（Ports），基础设施层实现。领域层零外部依赖。 |
| **聚合根边界清晰** | `ProcessingTask` 不持有其他聚合实例，只存原始值（如 `audio_path`）。 |
| **编排在外，规则在内** | 流水线步骤编排放在**应用层**；状态转换与校验放在**领域层**。 |
| **防腐层（ACL）** | 所有外部工具（yt-dlp、Whisper、LLM）均通过适配器封装，隔离技术细节。 |
| **适度设计** | 采用轻量级内存 EventBus，避免引入重型消息队列，同时保留未来扩展空间。 |

---

## 3. 各层详解

### 3.1 领域层（Domain Layer）

**文件位置**：`src/domain/`

**职责**：包含系统的核心业务概念、规则与约束。它是系统的**心脏**，不依赖任何框架、库或外部服务。

#### 3.1.1 值对象（Value Objects）

值对象是**不可变**的，通过其属性值来判断相等性，没有唯一标识。

```python
# src/domain/models.py

@dataclass(frozen=True)
class VideoUrl:
    value: str

    def __post_init__(self):
        if not self._is_valid(self.value):
            raise InvalidVideoUrlError(f"无效的B站URL: {self.value}")

    @property
    def video_id(self) -> str:
        """从 URL 中提取 BV 号"""
        ...
```

**为什么用值对象？**
- **自校验**：创建时即验证 URL 格式，避免非法数据流入系统。
- **不可变**：`frozen=True` 确保一旦创建不会被意外修改，减少 Bug。
- **语义化**：`VideoUrl` 比裸字符串 `str` 更能表达业务含义。

#### 3.1.2 聚合根（Aggregate Root）

`ProcessingTask` 是整个系统的核心聚合根，它封装了从 URL 到最终摘要的完整生命周期。

```python
@dataclass
class ProcessingTask:
    task_id: TaskId
    video_url: VideoUrl
    status: TaskStatus = TaskStatus.CREATED
    audio_path: Optional[str] = None
    raw_transcript: Optional[str] = None
    transcript_segments: list[TranscriptSegment] = field(default_factory=list)
    punctuated_text: Optional[str] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
```

**关键设计决策**：

> `ProcessingTask` 内部**不持有** `VideoAudio` 实体或 `Transcription` 实体，只存储原始值（`audio_path`, `raw_transcript` 等）。

这样做的好处：
- 聚合边界清晰，不会出现"加载一个任务连带加载大量音频元数据"的性能问题。
- 减少循环引用和序列化复杂度。
- 符合 DDD "聚合根之间通过 ID 引用"的最佳实践。

#### 3.1.3 状态机

```
CREATED ──► DOWNLOADING ──► TRANSCRIBING ──► PUNCTUATING ──► SUMMARIZING ──► COMPLETED
    │                                                                              ▲
    └──────────────────────────────────────────────────────────────────────────────┘
                              FAILED (任意阶段可进入)
```

状态转换方法（领域逻辑）内聚在聚合根内：

```python
def start_download(self) -> None:
    self._transition_to(TaskStatus.DOWNLOADING)

def finish_download(self, audio_path: str) -> None:
    self.audio_path = audio_path
    self._transition_to(TaskStatus.TRANSCRIBING)

def fail(self, error: str) -> None:
    self.error_message = error
    self.status = TaskStatus.FAILED
```

#### 3.1.4 端口（Ports）

端口是领域层对外部世界提出的**能力要求**，由基础设施层实现。

```python
class VideoDownloaderPort(ABC):
    @abstractmethod
    async def download_audio(self, url: VideoUrl) -> Tuple[bytes, dict]:
        """返回音频字节与元信息"""
        ...

class SpeechRecognizerPort(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: str, language: str = "zh") -> Tuple[str, list[TranscriptSegment]]:
        ...

class LLMServicePort(ABC):
    @abstractmethod
    async def add_punctuation(self, raw_text: str) -> str:
        ...

    @abstractmethod
    async def summarize(self, text: str) -> str:
        ...

class ProcessingTaskRepository(ABC):
    @abstractmethod
    async def save(self, task: ProcessingTask) -> None:
        ...

    @abstractmethod
    async def find_by_id(self, task_id: TaskId) -> Optional[ProcessingTask]:
        ...
```

#### 3.1.5 领域事件

领域事件用于在**不破坏分层边界**的前提下，通知外部"发生了某件业务大事"。

```python
@dataclass(frozen=True)
class TaskStatusChangedEvent(DomainEvent):
    task_id: str
    new_status: str
    progress_percent: int
```

当前使用轻量级 `SimpleEventBus`（内存回调）：
- 足够支撑 SSE 实时进度推送。
- 如果未来需要持久化事件、跨进程通信，可平滑替换为 RabbitMQ / Redis PubSub，无需修改领域层。

---

### 3.2 应用层（Application Layer）

**文件位置**：`src/application/`

**职责**：编排领域对象完成用例，处理事务边界，转换 DTO。它**不包含业务规则**，只负责"指挥调度"。

#### 3.2.1 用例（Use Cases）

每个用例对应一个用户意图：

| 用例 | 职责 |
|------|------|
| `SubmitVideoUseCase` | 接收 URL，创建 `ProcessingTask`，发布 `TaskCreatedEvent` |
| `ProcessVideoUseCase` | 执行完整流水线：下载 → 转录 → 加标点 → 总结 |
| `GetTaskStatusUseCase` | 按 ID 查询任务状态，转换为 DTO 返回 |

**为什么把流水线编排放在应用层？**

因为 "先下载、再转录、再加标点、最后总结" 是一个**跨领域的协调流程**，不是单纯的业务规则。把它放在应用层，领域层只需关心"状态转换是否合法"。

```python
class ProcessVideoUseCase:
    async def execute(self, task_id: TaskId) -> None:
        task = await self._repo.find_by_id(task_id)

        # 1. 下载
        task.start_download()
        await self._repo.save(task)
        await self._emit_status(task)

        audio_bytes, meta = await self._downloader.download_audio(task.video_url)
        ...
        task.finish_download(audio_path)
        await self._repo.save(task)

        # 2. 转录
        task.start_transcribing()
        ...
```

注意每一步都会 `save(task)`，确保任务状态持久化，即使服务崩溃也能从最近状态恢复（配合数据库仓储）。

#### 3.2.2 DTO（Data Transfer Object）

DTO 用于隔离领域实体与外部接口，防止接口直接暴露领域内部结构。

```python
@dataclass
class TaskStatusDTO:
    task_id: str
    status: str
    progress_percent: int
    video_url: str
    raw_transcript: Optional[str] = None
    punctuated_text: Optional[str] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
```

---

### 3.3 基础设施层（Infrastructure Layer）

**文件位置**：`src/infrastructure/`

**职责**：实现领域层定义的端口，封装具体技术细节。

#### 3.3.1 适配器（Adapters）

每个适配器对应一个外部工具：

| 适配器 | 实现端口 | 技术实现 |
|--------|----------|----------|
| `YtDlpVideoDownloaderAdapter` | `VideoDownloaderPort` | yt-dlp |
| `WhisperSpeechRecognizerAdapter` | `SpeechRecognizerPort` | openai-whisper |
| `OpenAILLMAdapter` | `LLMServicePort` | OpenAI API / 兼容 API |

**以 `OpenAILLMAdapter` 为例**：

```python
class OpenAILLMAdapter(LLMServicePort):
    async def add_punctuation(self, raw_text: str) -> str:
        prompt = "请为以下无标点文本添加合适的标点符号..."
        response = await self._client.chat.completions.create(...)
        return response.choices[0].message.content
```

如果以后要换成本地 Ollama：
1. 新建 `OllamaLlmAdapter(LLMServicePort)`。
2. 在 `Container` 中把 `OpenAILLMAdapter` 替换为 `OllamaLlmAdapter`。
3. **领域层和应用层代码完全不需要改动**。

#### 3.3.2 仓储实现

当前使用 `InMemoryTaskRepository`（内存字典），适合开发和演示。生产环境只需：
1. 新建 `SQLAlchemyTaskRepository(ProcessingTaskRepository)`。
2. 在 `Container` 中替换即可。

---

### 3.4 表示层（Presentation Layer）

**文件位置**：`src/presentation/`

**职责**：处理 HTTP 请求/响应、渲染页面、管理依赖注入。

#### 3.4.1 依赖注入容器（Container）

`Container` 是一个手动实现的 IoC 容器，集中管理所有层的依赖关系。

```python
class Container:
    _event_bus = SimpleEventBus()
    _task_repo = InMemoryTaskRepository()
    _downloader = YtDlpVideoDownloaderAdapter()
    _llm = OpenAILLMAdapter(api_key=..., model=...)

    @classmethod
    def get_process_use_case(cls) -> ProcessVideoUseCase:
        return ProcessVideoUseCase(
            task_repo=cls._task_repo,
            downloader=cls._downloader,
            recognizer=cls._recognizer,
            llm=cls._llm,
            event_bus=cls._event_bus,
        )
```

这样做的好处：
- 依赖关系一目了然。
- 单元测试时可以用 Mock 替换任何组件。
- 避免在路由函数里硬编码 `new SomeClass()`。

#### 3.4.2 SSE 实时推送

前端通过 `EventSource` 连接到 `/api/v1/tasks/{id}/stream`，服务端利用 `asyncio.Queue` 将事件总线中的状态变更实时推送给客户端。

相比轮询：
- 更实时（状态变更瞬间送达）。
- 更省资源（无需反复建立 HTTP 连接）。


---

## 4. 请求生命周期（时序图）

以"提交视频并处理"为例：

```
用户          浏览器           FastAPI              应用层                领域层              基础设施层
 │              │               │                     │                     │                    │
 │ 输入URL提交  │               │                     │                     │                    │
 │─────────────▶│               │                     │                     │                    │
 │              │ POST /tasks   │                     │                     │                    │
 │              │──────────────▶│                     │                     │                    │
 │              │               │ SubmitVideoUseCase  │                     │                    │
 │              │               │────────────────────▶│                     │                    │
 │              │               │                     │ 创建 ProcessingTask │                    │
 │              │               │                     │────────────────────▶│                    │
 │              │               │                     │ 保存 + 发布事件     │                    │
 │              │               │                     │─────────────────────────────────────────▶│
 │              │ 返回 task_id  │                     │                     │                    │
 │              │◀──────────────│                     │                     │                    │
 │              │               │                     │                     │                    │
 │              │   [后台启动 ProcessVideoUseCase]    │                     │                    │
 │              │               │                     │                     │                    │
 │              │               │                     │ 1. download_audio   │                    │
 │              │               │                     │─────────────────────────────────────────▶│ yt-dlp
 │              │               │                     │◀────────────────────────────────────────│
 │              │               │                     │                     │                    │
 │              │               │                     │ 2. transcribe       │                    │
 │              │               │                     │─────────────────────────────────────────▶│ Whisper
 │              │               │                     │◀────────────────────────────────────────│
 │              │               │                     │                     │                    │
 │              │               │                     │ 3. add_punctuation  │                    │
 │              │               │                     │─────────────────────────────────────────▶│ LLM API
 │              │               │                     │◀────────────────────────────────────────│
 │              │               │                     │                     │                    │
 │              │               │                     │ 4. summarize        │                    │
 │              │               │                     │─────────────────────────────────────────▶│ LLM API
 │              │               │                     │◀────────────────────────────────────────│
 │              │               │                     │                     │                    │
 │              │  SSE Event   │  状态变更事件        │                     │                    │
 │              │◀─────────────│◀────────────────────│                     │                    │
 │  实时进度条更新 │               │                     │                     │                    │
 │              │               │                     │                     │                    │
 │              │ GET /tasks/id │                     │                     │                    │
 │              │──────────────▶│ GetTaskStatusUseCase│                     │                    │
 │              │◀──────────────│ 返回完整结果         │                     │                    │
 │  展示最终结果  │               │                     │                     │                    │
```

---

## 5. 扩展指南

### 5.1 替换外部服务（零领域层改动）

**场景**：把 Whisper 换成阿里云语音识别。

```python
# 1. 新建适配器
class AliyunSpeechRecognizerAdapter(SpeechRecognizerPort):
    async def transcribe(self, audio_path: str, language: str = "zh") -> Tuple[str, list[TranscriptSegment]]:
        ...  # 调用阿里云 SDK

# 2. 在 Container 中替换
class Container:
    _recognizer = AliyunSpeechRecognizerAdapter(app_key=..., access_key=...)
```

完成。`domain/`, `application/` 下的代码**完全不需要改动**。

### 5.2 增加新的处理步骤

**场景**：在"加标点"和"总结"之间增加"翻译"步骤。

1. **领域层**：在 `TaskStatus` 枚举中增加 `TRANSLATING`，在 `ProcessingTask` 中增加 `translated_text` 字段和对应的状态转换方法。
2. **端口层**：在 `LLMServicePort` 中增加 `translate(self, text: str, target_lang: str) -> str` 方法。
3. **应用层**：在 `ProcessVideoUseCase.execute()` 的"加标点"和"总结"之间插入翻译步骤。
4. **基础设施层**：在 `OpenAILLMAdapter` 中实现 `translate` 方法。

注意：如果只是加一个简单的子步骤，也可以复用现有的 `LLMServicePort`，在应用层直接调用 `summarize` 类似的通用方法，无需修改端口。

### 5.3 持久化到数据库

1. 安装依赖：`pip install sqlalchemy aiosqlite`
2. 新建 `src/infrastructure/sqlalchemy_repository.py`：

```python
class SQLAlchemyTaskRepository(ProcessingTaskRepository):
    async def save(self, task: ProcessingTask) -> None:
        ...  # ORM 操作

    async def find_by_id(self, task_id: TaskId) -> Optional[ProcessingTask]:
        ...  # ORM 查询
```

3. 在 `Container` 中替换 `_task_repo` 即可。

### 5.4 接入 Celery（异步队列）

当前使用 FastAPI `BackgroundTasks` 执行后台处理。如果任务量大、需要分布式处理：

1. 将 `ProcessVideoUseCase.execute` 包装为 Celery Task。
2. 在 `SubmitVideoUseCase` 中调用 `celery_app.send_task("process_video", args=[task_id])`。
3. 在 Celery Worker 中导入 `Container` 并执行用例。

**无需改动领域层代码**，只需调整应用层的启动方式。

---

## 6. 目录结构速查

```
src/
├── main.py                          # FastAPI 入口
│
├── domain/                          # 【领域层】零外部依赖
│   ├── models.py                    # 聚合根 ProcessingTask + 值对象
│   ├── events.py                    # 轻量内存 EventBus + 领域事件
│   ├── ports.py                     # 端口接口（Downloader/Transcriber/LLM/Repository）
│   └── exceptions.py                # 领域异常体系
│
├── application/                     # 【应用层】编排 + DTO
│   ├── use_cases.py                 # Submit / Process / Query 三个用例
│   └── dto.py                       # TaskStatusDTO
│
├── infrastructure/                  # 【基础设施层】适配器 + 仓储
│   ├── adapters.py                  # yt-dlp / Whisper / OpenAI 适配器
│   └── repositories.py              # InMemory 仓储
│
└── presentation/                    # 【表示层】FastAPI 路由 + 页面
    ├── dependencies.py              # 手动 IoC 容器
    ├── routes.py                    # REST API + SSE 流式推送
    └── templates/
        └── index.html               # 前端页面（SSE 实时进度）
```

---

## 7. 常见问题（FAQ）

### Q1: 为什么不用 SQLAlchemy 做默认仓储？

为了降低上手门槛和本地演示成本。`InMemoryTaskRepository` 足够支撑单机演示，且替换成本极低（只需改 `Container` 中的一行）。

### Q2: 为什么用手动 IoC 容器而不是依赖注入框架（如 dependency-injector）？

手动容器在 Python 中足够清晰，且避免了引入额外依赖。项目复杂度上升后，可以随时替换为专业框架。

### Q3: `ProcessVideoUseCase` 中的异常处理为什么直接 `except Exception`？

因为不同外部工具抛出的异常类型各异（yt-dlp 的网络异常、Whisper 的文件异常、OpenAI 的 API 异常），在适配器层统一转换异常成本较高。当前采用"兜底捕获 + 记录错误信息"的策略，生产环境可以在适配器层逐步细化异常转换。

### Q4: SSE 连接断开怎么办？

前端在 `evtSource.onerror` 中处理了连接错误。如果任务已完成，前端会自动关闭连接；如果任务仍在处理中，用户可以刷新页面重新查询状态。

### Q5: 如何测试？

- **单元测试**：Mock `ProcessingTaskRepository` 和各个 Port，测试用例编排逻辑。
- **集成测试**：使用真实的 `InMemoryTaskRepository` + Mock 适配器，测试端到端流程。
- **领域模型测试**：直接实例化 `ProcessingTask`，测试状态机转换是否合法。

---

## 8. 配置说明

通过环境变量配置：

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `WHISPER_MODEL` | `base` | Whisper 模型大小（tiny/base/small/medium/large） |
| `LLM_API_KEY` | `sk-xxx` | OpenAI 或兼容 API 的密钥 |
| `LLM_BASE_URL` | `None` | 自定义 API 地址（如 Ollama: `http://localhost:11434/v1`） |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名称 |

---

*本文档与代码同步维护。如有架构调整，请同步更新本文档。*
