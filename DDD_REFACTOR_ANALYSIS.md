# bili2text DDD 重构分析文档

> 版本：v2.0（基于老师评审修正）
> 日期：2026-05-09
> 范围：将现有过程式脚本重构为务实 DDD 四层架构，保持文件系统存储不变。

---

## 目录

1. [重构背景与目标](#1-重构背景与目标)
2. [通用语言 Ubiquitous Language](#2-通用语言-ubiquitous-language)
3. [限界上下文 Bounded Context](#3-限界上下文-bounded-context)
4. [四层架构与包结构](#4-四层架构与包结构)
5. [核心领域模型](#5-核心领域模型)
6. [领域端口（防腐层）](#6-领域端口防腐层)
7. [仓储设计](#7-仓储设计)
8. [应用服务编排](#8-应用服务编排)
9. [重构路线图](#9-重构路线图)
10. [目标目录树与关键伪代码](#10-目标目录树与关键伪代码)
11. [风险与注意事项](#11-风险与注意事项)


---

## 1. 重构背景与目标

### 1.1 现状痛点

当前 `bili2text` 是一个基于 FastAPI 的媒体内容转文字服务，核心流程为：**解析 URL -> 下载音频 -> Whisper 转录 -> LLM 加标点 -> LLM 总结 -> 生成文档**。虽然功能跑通，但代码结构存在明显的过程式痕迹，难以持续演进。

| 痛点 | 现状表现 | 影响 |
|------|---------|------|
| **全局状态污染** | `pipeline.py` 顶部定义全局字典 `tasks: dict` 和 `task_queues: dict` | 无法单元测试、无法水平扩展、并发下状态竞争风险 |
| **基础设施侵入业务** | `pipeline.py` 直接 `import whisper`、`from ChatClient import ChatClient` | 外部框架/库变更时改动面大，无法做技术降级 |
| **单一过程式脚本** | `pipeline.py` 186 行，一个 `run_pipeline` 函数包揽全部 5 个阶段 | 单点膨胀、职责混乱、无法对单个阶段做隔离测试 |
| **无明确的领域边界** | 任务状态管理、文档生成、通知推送全部杂糅在同一模块 | 新增功能时不知道代码该放哪，易引入循环依赖 |
| **存储与业务耦合** | `models.py` 同时定义 Pydantic DTO 和文件 I/O 函数 (`save_doc_content` 等) | 切换存储媒介（如未来切到数据库）时需要改业务代码 |
| **通知机制与表现层耦合** | `asyncio.Queue` 直接暴露在 `pipeline.py`，`main.py` 通过 `task_queues` 读取 | 领域层依赖了表现层的传输细节，违反依赖方向 |

### 1.2 重构目标

1. **建立清晰的领域边界**：识别单一限界上下文，消除上帝类和过程式脚本。
2. **四层架构隔离**：严格区分 `presentation -> application -> domain -> infrastructure`，上层依赖下层接口，下层绝不依赖上层。
3. **外部服务可替换**：Whisper、LLM 通过防腐层（Anti-Corruption Layer, ACL）接口抽象，实现手动依赖注入。下载器作为应用层依赖的基础设施适配器。
4. **领域驱动状态管理**：将 `ProcessingTask` 提升为真正的聚合根，封装状态转换行为，消灭全局 `tasks` 字典。
5. **仓储接口隔离持久化**：定义 `TaskRepository`，由基础设施层提供文件系统实现，保证领域层对存储媒介无感知。
6. **务实演进**：不过度引入消息中间件、ORM、事件总线或微服务拆分，保持单进程 FastAPI 架构，最小化运行时复杂度。


---

## 2. 通用语言 Ubiquitous Language

以下术语表在团队协作与代码命名中统一使用，避免同一个概念多个名字。

| 术语（中文） | 术语（英文） | 定义 | 说明 |
|-------------|-------------|------|------|
| **来源标识** | SourceIdentifier | 跨平台内容来源的唯一标识，由平台类型和外部 ID 组成 | 值对象，平台无关 |
| **分段索引** | SegmentIndex | 内容分段的正整数序号（从 1 开始） | 值对象，对应 B 站分 P、YouTube 章节等 |
| **分段信息** | SegmentInfo | 某个分段的元数据（索引、标题、时长） | 值对象 |
| **处理任务** | ProcessingTask | 用户提交的一次完整处理请求，聚合根 | 包含所选分段、当前进度、状态机 |
| **任务状态** | TaskStatus | 任务生命周期中的状态枚举 | 值对象：PENDING / RESOLVED / DOWNLOADING / TRANSCRIBING / PUNCTUATING / SUMMARIZING / COMPLETED / FAILED |
| **分段结果** | SegmentResult | 某个分段的处理产物集合（原始文本、加标点文本、摘要） | 聚合根内的实体 |
| **内容文本** | ContentText | 非空的文本内容，及其内容类型（raw / punctuated / summary） | 值对象 |
| **内容类型** | ContentType | 文本产物的类型标签 | 值对象枚举 |
| **解析** | Resolve | 从 URL 中提取内容元数据（标题、分段列表） | 基础设施层行为 |
| **转录** | Transcribe | 将音频文件识别为原始文本 | 领域端口 |
| **文本处理** | TextProcess | 对文本进行结构化处理（加标点、总结等） | 领域端口 |
| **通知** | Notify | 将任务状态/进度变化推送给前端（当前实现为 SSE） | 应用层行为 |
| **仓储** | Repository | 负责聚合根的持久化与查询，对调用方屏蔽存储细节 | 基础设施层实现 |

> **重要约定**：`BVid`、`URL`、`CID` 等 B 站平台特有术语**不属于**通用语言，它们只出现在基础设施层的 B 站网关适配器中。


---

## 3. 限界上下文 Bounded Context

### 3.1 上下文划分

基于现有业务规模与团队规模，本系统只划分**一个限界上下文**：

~~~
+---------------------------------------------+
|           Media Processing Context            |
|              媒体处理限界上下文                |
|                                               |
|  +-------------------------------------+     |
|  |         ProcessingTask              |     |
|  |         （聚合根）                   |     |
|  |  - 任务生命周期与状态机              |     |
|  |  - 分段结果集合                      |     |
|  |  - 业务规则与不变式                  |     |
|  +-------------------------------------+     |
|                                               |
|  共享值对象：SourceIdentifier, SegmentIndex,   |
|             ContentText, ContentType          |
|                                               |
|  防腐层端口：IAudioTranscriber, ITextProcessor |
+---------------------------------------------+
~~~

**设计决策**：当前业务逻辑紧密耦合（处理完立即生成文档），且由同一团队在同一进程中维护，**没有必要拆分为多个限界上下文**。过度拆分（如将文档管理拆为独立上下文）会引入不必要的跨边界通信复杂度。

未来如果出现以下信号，再考虑拆分：
- 文档查询逻辑变得极其复杂，需要独立演进
- 需要独立部署文档服务（如全文检索服务）
- 不同子系统由不同团队维护


---

## 4. 四层架构与包结构

### 4.1 架构图与依赖规则

采用 Eric Evans 提出的 **DDD 四层架构**，针对 Python/FastAPI 单进程场景做务实调整。

~~~
+----------------------------------------------+
|           表现层 Presentation                   |  FastAPI Routers / Jinja2 Templates
|  (routes.py, sse_notifier.py, schemas.py)    |  职责：HTTP 协议转换、参数校验、序列化、SSE 推送
+----------------------------------------------+
|           应用层 Application                    |  App Services
|  (task_app_service.py, doc_app_service.py)   |  职责：编排用例、事务边界、协调领域对象与端口
+----------------------------------------------+
|           领域层 Domain                         |  Aggregates / Entities / Value Objects / Ports
|  (processing_task.py, segment_result.py,      |  职责：业务规则、状态机、不变式、端口契约定义
|   ports.py)                                  |
+----------------------------------------------+
|         基础设施层 Infrastructure               |  Repositories / Adapters / Config
|  (file_task_repository.py, whisper_adapter.py,|  职责：持久化、外部服务调用、框架配置、URL 解析
|   bili_downloader.py, openai_client.py)      |
+----------------------------------------------+
~~~

**依赖规则（The Dependency Rule）**：

- 箭头只能 **向下**（外层依赖内层）。
- **领域层** 不依赖任何其他层，无外部 import（除 Python 标准库）。
- **应用层** 只依赖领域层，不依赖基础设施具体实现。
- **表现层** 只依赖应用层接口与基础设施层的具体装配代码（`main.py` 中的依赖注入）。
- 领域层通过 **端口（抽象基类 / Protocol）** 声明对外部能力的依赖，基础设施层提供适配器实现。


### 4.2 完整目录树（目标态）

~~~
D:\jaifiresong\bili2text
|-- main.py                          # 应用入口：依赖注入组装、FastAPI 实例启动
|-- requirements.txt
|-- .env
|-- README.md
|-- AGENTS.md
|
|-- presentation/                    # 表现层
|   |-- __init__.py
|   |-- routes.py                    # FastAPI APIRoutes / Page Routes
|   |-- schemas.py                   # Pydantic Request/Response DTO
|   |-- sse_notifier.py              # ITaskNotifier 的 SSE 实现
|
|-- application/                     # 应用层
|   |-- __init__.py
|   |-- task_app_service.py          # TaskAppService：create_task, start_pipeline, get_task
|   |-- doc_app_service.py           # DocAppService：scan_documents, read_document
|
|-- domain/                          # 领域层
|   |-- __init__.py
|   |-- shared_kernel/               # 共享值对象
|   |   |-- __init__.py
|   |   |-- value_objects.py         # SourceIdentifier, SegmentIndex, ContentText, ContentType
|   |   |-- exceptions.py            # 领域异常基类 DomainError, ValidationError
|   |
|   |-- processing/                  # 媒体处理聚合与实体
|   |   |-- __init__.py
|   |   |-- processing_task.py       # ProcessingTask 聚合根 + TaskStatus 枚举 + 状态机行为
|   |   |-- segment_result.py        # SegmentResult 实体
|   |   |-- ports.py                 # 领域端口：IAudioTranscriber, ITextProcessor, ITaskNotifier
|   |
|   |-- exceptions.py                # 通用领域异常
|
|-- infrastructure/                  # 基础设施层
|   |-- __init__.py
|   |-- config.py                    # 环境变量与配置读取
|   |-- persistence/                 # 仓储实现
|   |   |-- __init__.py
|   |   |-- file_task_repository.py  # TaskRepository 文件系统实现
|   |
|   |-- adapters/                    # 防腐层适配器
|       |-- __init__.py
|       |-- bili_downloader.py       # 基于 BiliDownloader 的下载适配器
|       |-- whisper_transcriber.py   # IAudioTranscriber 实现：基于 whisper
|       |-- llm_text_processor.py    # ITextProcessor 实现：基于 ChatClient
|
|-- resources/                       # 文件系统数据目录（保持不变）
    |-- <platform>/<external_id>/
        |-- info.json
        |-- <segment>_raw.txt
        |-- <segment>_punctuated.md
        |-- <segment>_summary.md
~~~


### 4.3 原文件迁移映射

| 原文件 | 目标位置 | 说明 |
|--------|---------|------|
| `main.py` | `main.py` + `presentation/routes.py` | 路由提取到表现层，`main.py` 只做组装 |
| `pipeline.py` | 拆分到 `domain/processing/`, `application/` | 状态机进聚合根，编排进 AppService |
| `models.py` | `presentation/schemas.py` + `domain/shared_kernel/` + `domain/processing/` | DTO 上移，值对象下沉 |
| `services.py` | `application/doc_app_service.py` + `infrastructure/persistence/` | 扫描逻辑由应用层通过仓储接口调用 |
| `ChatClient.py` | `infrastructure/adapters/llm_text_processor.py`（内部使用） | 作为 LLM 适配器的内部依赖 |
| `downloaders/BiliDownloader.py` | `infrastructure/adapters/bili_downloader.py`（内部使用） | 作为下载适配器的内部依赖 |
| `process_doc.py` | 逻辑拆分至 `ITextProcessor` 接口及实现 | Prompt 定义保留在适配器或配置中 |


---

## 5. 核心领域模型

### 5.1 聚合根：ProcessingTask

`ProcessingTask` 是媒体处理上下文的唯一聚合根，封装任务生命周期中的所有状态变更与业务规则。

**属性**：
- `task_id: str` -- 全局唯一标识
- `source: SourceIdentifier` -- 内容来源标识（平台无关）
- `title: str` -- 内容标题
- `selected_segments: list[int]` -- 用户选择处理的分段索引列表
- `status: TaskStatus` -- 当前状态
- `message: str` -- 当前步骤描述（供展示，不承载业务规则）
- `progress: int` -- 整体进度 0-100
- `current_segment: int` -- 当前正在处理的分段索引
- `results: dict[int, SegmentResult]` -- 各分段的处理结果（实体集合）
- `created_at: datetime`
- `completed_at: datetime | None`

**领域方法**：
- `start_resolution()` -- 开始解析元信息
- `resolve_completed(source, title, segments)` -- 解析完成，状态变为 RESOLVED
- `mark_downloading(segment_index)` / `skip_download()`
- `mark_transcribing(segment_index)` / `skip_transcription()`
- `mark_punctuating(segment_index)` / `skip_punctuation()`
- `mark_summarizing(segment_index)` / `skip_summarization()`
- `update_progress(current_idx, total)` -- 更新整体进度，校验 0-100
- `complete()` -- 标记全部完成（不可从 FAILED 转入）
- `fail(reason)` -- 标记失败

**不变式**：
- `progress` 必须在 `0-100` 之间
- `FAILED` 状态不可转为 `COMPLETED`
- `complete()` 时 `selected_segments` 必须非空


### 5.2 实体：SegmentResult

`SegmentResult` 是 `ProcessingTask` 聚合根内部的实体，代表某个分段的处理产物。

**属性**：
- `segment_index: int` -- 分段索引（局部标识）
- `raw_text: ContentText | None`
- `punctuated_text: ContentText | None`
- `summary: ContentText | None`

> 为何是实体而非值对象？因为它属于特定聚合根（`ProcessingTask`），需要通过 `task_id + segment_index` 联合定位。但生命周期完全由聚合根控制，外部不可直接访问。

### 5.3 值对象

| 值对象 | 字段 | 校验规则 |
|--------|------|---------|
| `SourceIdentifier` | `platform: str`, `external_id: str` | 两者均非空 |
| `SegmentIndex` | `value: int` | >= 1 |
| `ContentType` | 枚举：`RAW`, `PUNCTUATED`, `SUMMARY` | -- |
| `ContentText` | `text: str`, `type: ContentType` | text 非空 |
| `Percentage` | `value: int` | 0 <= value <= 100 |


---

## 6. 领域端口（防腐层）

领域层只定义契约，不依赖任何外部框架。

### 6.1 端口划分决策

| 能力 | 是否定义端口 | 归属 | 理由 |
|------|-------------|------|------|
| **下载** | 否 | 基础设施适配器 | 下载音频是实现细节，领域层只关心获取音频源。应用层直接调用下载适配器 |
| **转录** | 是 | `IAudioTranscriber` | 音频 -> 文本是业务核心步骤，Whisper 只是其中一种实现。未来可能换本地模型、云 API、甚至人工 |
| **文本处理** | 是 | `ITextProcessor` | 原始文本 -> 结构化文本和文本 -> 摘要是领域行为，LLM 只是实现手段。统一为一个端口 + instruction 策略，更灵活 |
| **通知** | 是 | `ITaskNotifier` | 放在领域层，因为任务状态变化后需要通知可以视为业务规则的一部分。SSE 实现放在表现层 |

### 6.2 端口契约（伪代码）

~~~python
# domain/processing/ports.py
from typing import Protocol

class IAudioTranscriber(Protocol):
    async def transcribe(self, audio_path: str) -> str:
        ...

class ITextProcessor(Protocol):
    async def process(self, text: str, instruction: str) -> str:
        ...

class ITaskNotifier(Protocol):
    async def notify(self, task_id: str, event: str, data: dict) -> None:
        ...
~~~

### 6.3 关键设计决策

- **下载器不进端口**：下载是技术实现，不是领域概念。应用层直接调用 `BiliDownloader` 适配器，获取音频路径后交给领域层。
- **文本处理统一端口**：加标点和总结本质上是“文本 -> 文本”的变换，区别仅在于 instruction（提示词）。统一为 `ITextProcessor` 更灵活，未来新增处理（如翻译、提取关键词）无需改接口。
- **通知放在领域层**：任务状态变化后“需要通知观察者”是业务规则的一部分。表现层负责实现 `ITaskNotifier`（如 SSE），但契约定义在领域层。


---

## 7. 仓储设计

### 7.1 仓储接口

仓储负责聚合根的持久化与查询，对调用方屏蔽存储细节。

~~~python
# domain/processing/ports.py (与端口同文件或单独文件)
from typing import Protocol, Optional

class TaskRepository(Protocol):
    def save(self, task: ProcessingTask) -> None:
        ...

    def get_by_id(self, task_id: str) -> Optional[ProcessingTask]:
        ...

    def get_all(self) -> list[ProcessingTask]:
        ...
~~~

### 7.2 文件系统实现

~~~python
# infrastructure/persistence/file_task_repository.py
class FileTaskRepository:
    def __init__(self, base_dir: str = "./resources"):
        self._base = Path(base_dir)

    def save(self, task: ProcessingTask) -> None:
        # 序列化 ProcessingTask 为 JSON，写入文件系统
        ...

    def get_by_id(self, task_id: str) -> Optional[ProcessingTask]:
        # 从文件系统读取并反序列化
        ...
~~~

### 7.3 设计决策

- **不引入 ORM**：当前文件系统存储足够简单，ORM 会增加不必要的复杂度。
- **聚合根整存整取**：仓储只操作完整的 `ProcessingTask` 聚合根，不暴露内部实体（如 `SegmentResult`）的单独存储接口。
- **文档扫描归仓储**：现有的 `services.py` 扫描逻辑，由 `FileTaskRepository.get_all()` 提供，应用层只调用仓储接口。


---

## 8. 应用服务编排

### 8.1 TaskAppService

应用层负责编排用例、协调领域对象与端口，不承载业务规则。

~~~python
# application/task_app_service.py
class TaskAppService:
    def __init__(
        self,
        task_repo: TaskRepository,
        transcriber: IAudioTranscriber,
        text_processor: ITextProcessor,
        notifier: ITaskNotifier,
        downloader: BiliDownloaderAdapter,  # 基础设施适配器
    ):
        ...

    async def create_task(self, url: str, selected_segments: list[int]) -> str:
        # 1. 调用 downloader 解析 URL，获取元信息
        # 2. 构造 ProcessingTask 聚合根
        # 3. 调用 task_repo.save()
        # 4. 异步启动 pipeline
        ...

    async def start_pipeline(self, task_id: str) -> None:
        # 1. 从 repo 加载 task
        # 2. 逐个分段执行：下载 -> 转录 -> 加标点 -> 总结
        # 3. 每步调用 task.mark_xxx() 驱动状态机
        # 4. 每步调用 notifier.notify() 推送进度
        # 5. 完成后 task_repo.save()
        ...
~~~

### 8.2 DocAppService

~~~python
# application/doc_app_service.py
class DocAppService:
    def __init__(self, task_repo: TaskRepository):
        self._repo = task_repo

    def scan_documents(self) -> list[DocumentDTO]:
        # 通过仓储扫描所有已完成的 ProcessingTask
        ...

    def read_document(self, task_id: str, segment_index: int, content_type: str) -> str:
        # 读取指定分段的内容文本
        ...
~~~

### 8.3 与原有 pipeline.py 的区别

| 职责 | 原 `pipeline.py` | 新架构 |
|------|-----------------|--------|
| 状态机 | 直接修改 `task.status = ...` | `task.mark_xxx()` 领域方法 |
| 文件存在检查 | 内联 `os.path.exists(...)` | 应用层调用仓储或下载器适配器 |
| 异常清理 | 内联 `try/except` + `os.remove(...)` | 应用层捕获异常，调用适配器清理 |
| 通知推送 | 直接操作 `asyncio.Queue` | 通过 `ITaskNotifier` 端口 |
| 全局状态 | 全局 `tasks: dict` | 仓储持久化 + 内存缓存（可选） |


---

## 9. 重构路线图

### 阶段一：领域层核心（优先级最高）

1. **抽取值对象**：创建 `domain/shared_kernel/value_objects.py`，定义 `SourceIdentifier`、`SegmentIndex`、`ContentText`、`ContentType`、`Percentage`。
2. **抽取聚合根**：创建 `domain/processing/processing_task.py`，实现 `ProcessingTask` 聚合根与 `TaskStatus` 枚举。
3. **抽取实体**：创建 `domain/processing/segment_result.py`，实现 `SegmentResult`。
4. **定义领域端口**：创建 `domain/processing/ports.py`，定义 `IAudioTranscriber`、`ITextProcessor`、`ITaskNotifier`、`TaskRepository`。
5. **单元测试**：为聚合根的状态机编写纯 Python 单元测试（无需启动 FastAPI）。

### 阶段二：基础设施适配器

1. **迁移 Whisper 适配器**：创建 `infrastructure/adapters/whisper_transcriber.py`，实现 `IAudioTranscriber`。
2. **迁移 LLM 适配器**：创建 `infrastructure/adapters/llm_text_processor.py`，实现 `ITextProcessor`，复用 `ChatClient`。
3. **迁移下载适配器**：创建 `infrastructure/adapters/bili_downloader.py`，复用 `BiliDownloader`。
4. **实现文件仓储**：创建 `infrastructure/persistence/file_task_repository.py`，实现 `TaskRepository`。
5. **配置读取**：创建 `infrastructure/config.py`，集中读取 `.env`，应用层启动时注入。

### 阶段三：应用服务

1. **实现 TaskAppService**：编排 `create_task` 和 `start_pipeline` 用例。
2. **实现 DocAppService**：提供文档扫描与读取。
3. **断点续跑**：在应用服务中实现文件存在性检查与失败清理逻辑。

### 阶段四：表现层与组装

1. **迁移路由**：创建 `presentation/routes.py`，调用 AppService。
2. **SSE 通知器**：创建 `presentation/sse_notifier.py`，实现 `ITaskNotifier`。
3. **组装入口**：更新 `main.py`，手动注入所有依赖。
4. **端到端测试**：验证完整流程与原有功能等价。


---

## 10. 目标目录树与关键伪代码

### 10.1 核心伪代码：TaskAppService.start_pipeline

~~~python
# application/task_app_service.py
class TaskAppService:
    async def start_pipeline(self, task_id: str) -> None:
        task = self._repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.start_resolution()
        await self._notifier.notify(task_id, "status", {"message": task.message})

        try:
            # 1. 解析（基础设施层）
            source, title, segments = await self._downloader.resolve(task.source)
            task.resolve_completed(source, title, [s.index for s in segments])

            total = len(task.selected_segments)

            for idx, seg_idx in enumerate(task.selected_segments):
                task.update_progress(idx, total)
                segment = segments[seg_idx - 1]

                # 2. 下载（基础设施层，存在则跳过）
                audio_path = await self._downloader.download(source, segment)

                # 3. 转录（通过端口）
                task.mark_transcribing(seg_idx)
                await self._notifier.notify(task_id, "progress", {...})
                raw_text = await self._transcriber.transcribe(audio_path)

                # 4. 加标点（通过端口）
                task.mark_punctuating(seg_idx)
                punctuated = await self._text_processor.process(raw_text, "PUNCTUATE")

                # 5. 总结（通过端口）
                task.mark_summarizing(seg_idx)
                summary = await self._text_processor.process(raw_text, "SUMMARIZE")

                # 保存结果到聚合根
                task.results[seg_idx] = SegmentResult(
                    segment_index=seg_idx,
                    raw_text=ContentText(text=raw_text, type=ContentType.RAW),
                    punctuated_text=ContentText(text=punctuated, type=ContentType.PUNCTUATED),
                    summary=ContentText(text=summary, type=ContentType.SUMMARY),
                )

                # 持久化
                self._repo.save(task)

            task.complete()
            await self._notifier.notify(task_id, "completed", {"task_id": task_id})

        except Exception as e:
            task.fail(str(e))
            self._repo.save(task)
            await self._notifier.notify(task_id, "failed", {"message": str(e)})
            raise
~~~


---

## 11. 风险与注意事项

### 11.1 重构风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| **过度设计** | 引入过多抽象，增加理解成本 | 坚持务实原则：不引入 ORM、事件总线、消息队列。每个抽象必须有明确的替换需求 |
| **回归缺陷** | 重构过程中破坏现有功能 | 阶段四保留端到端测试，确保重构前后行为等价；阶段一优先写聚合根单元测试 |
| **性能下降** | 分层增加调用开销 | 文件 I/O 和网络请求仍是瓶颈，方法调用开销可忽略。如有需要，可引入内存缓存 |
| **团队学习成本** | DDD 概念对新手不友好 | 文档中标注每个设计的理由（Why），而非只写规则（What）。代码审查时重点讲解 |

### 11.2 注意事项

1. **不要急于拆分限界上下文**：当前系统规模下，一个上下文足够。过早拆分（如独立文档服务）会引入分布式复杂度，得不偿失。
2. **领域层保持纯粹**：领域层代码中不得出现 `import requests`、`import whisper`、`import openai` 等基础设施依赖。如果看到，说明分层失败。
3. **配置读取在基础设施层**：`.env` 读取、环境变量解析全部放在 `infrastructure/config.py`，通过纯数据类（如 `AppConfig`）注入到应用层。
4. **Prompt 不是领域概念**：加标点和总结的 Prompt 属于技术实现细节，放在 LLM 适配器或配置中，不要进入领域层。
5. **断点续跑是应用层策略**：文件存在性检查、失败清理属于应用层编排逻辑，不要放进聚合根。聚合根只负责状态变更和业务规则校验。
