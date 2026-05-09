# bili2text DDD 重构分析文档

> 版本：v1.0  
> 日期：2026-05-09  
> 范围：将现有过程式脚本重构为严格 DDD 四层架构，保持文件系统存储不变。

---

## 目录

1. [重构背景与目标](#1-重构背景与目标)
2. [通用语言 Ubiquitous Language](#2-通用语言-ubiquitous-language)
3. [限界上下文 Bounded Contexts](#3-限界上下文-bounded-contexts)
4. [四层架构与包结构](#4-四层架构与包结构)
5. [核心领域模型](#5-核心领域模型)
6. [防腐层设计](#6-防腐层设计)
7. [仓储设计](#7-仓储设计)
8. [应用服务编排](#8-应用服务编排)
9. [重构路线图](#9-重构路线图)
10. [目标目录树与关键伪代码](#10-目标目录树与关键伪代码)
11. [风险与注意事项](#11-风险与注意事项)

---

## 1. 重构背景与目标

### 1.1 现状痛点

当前 `bili2text` 是一个基于 FastAPI 的 B站视频转文字服务，核心流程为：**解析 BVid → 下载音频 → Whisper 转录 → LLM 加标点 → LLM 总结 → 生成文档**。虽然功能跑通，但代码结构存在明显的过程式痕迹，难以持续演进。

| 痛点 | 现状表现 | 影响 |
|------|---------|------|
| **全局状态污染** | `pipeline.py` 顶部定义全局字典 `tasks: dict` 和 `task_queues: dict` | 无法单元测试、无法水平扩展、并发下状态竞争风险 |
| **基础设施侵入业务** | `pipeline.py` 直接 `import whisper`、`from ChatClient import ChatClient` | 外部框架/库变更时改动面大，无法做技术降级 |
| **单一过程式脚本** | `pipeline.py` 186 行，一个 `run_pipeline` 函数包揽全部 5 个阶段 | 单点膨胀、职责混乱、无法对单个阶段做隔离测试 |
| **无明确的领域边界** | 任务状态管理、文档生成、通知推送全部杂糅在同一模块 | 新增功能时不知道代码该放哪，易引入循环依赖 |
| **存储与业务耦合** | `models.py` 同时定义 Pydantic DTO 和文件 I/O 函数 (`save_doc_content` 等) | 切换存储媒介（如未来切到数据库）时需要改业务代码 |
| **通知机制与表现层耦合** | `asyncio.Queue` 直接暴露在 `pipeline.py`，`main.py` 通过 `task_queues` 读取 | 领域层依赖了表现层的传输细节，违反依赖方向 |

### 1.2 重构目标

1. **建立清晰的领域边界**：划分“视频处理”与“文档管理”两个限界上下文，消除上帝类和过程式脚本。
2. **四层架构隔离**：严格区分 `presentation → application → domain → infrastructure`，上层依赖下层接口，下层绝不依赖上层。
3. **外部服务可替换**：Whisper、LLM、B站下载器、SSE 通知全部通过防腐层（Anti-Corruption Layer, ACL）接口抽象，实现手动依赖注入。
4. **领域驱动状态管理**：将 `ProcessingTask` 提升为真正的聚合根，封装状态转换行为，消灭全局 `tasks` 字典。
5. **异步事件驱动通信**：使用 `asyncio.Queue` 实现领域事件总线，应用层订阅事件并调用 `ITaskNotifier`，表现层实现 SSE 推送，彻底解耦核心流程与通知机制。
6. **仓储接口隔离持久化**：定义 `TaskRepository`、`DocumentRepository`，由基础设施层提供文件系统实现，保证领域层对存储媒介无感知。
7. **务实演进**：不过度引入消息中间件、ORM 或微服务拆分，保持单进程 FastAPI 架构，最小化运行时复杂度。

---

## 2. 通用语言 Ubiquitous Language

以下术语表在团队协作与代码命名中统一使用，避免“同一个概念多个名字”。

| 术语（中文） | 术语（英文） | 定义 | 出现上下文 |
|-------------|-------------|------|-----------|
| 视频标识 | BVid | B站视频的唯一标识符，如 `BV1xx411c7mD`。不可为空，值对象。 | 共享内核 |
| 分P序号 | PageNumber | 视频分P的正整数序号（从 1 开始）。值对象。 | 共享内核 |
| 处理任务 | ProcessingTask | 用户提交的一次完整视频处理请求，聚合根。包含所选分P、当前进度、状态机。 | 视频处理上下文 |
| 流水线阶段 | PipelineStage | 任务内部的一个执行阶段，如 DOWNLOADING、TRANSCRIBING。枚举值对象。 | 视频处理上下文 |
| 页结果 | PageResult | 某个分P的处理产物集合（原始文本、加标点文本、摘要）。值对象/实体。 | 视频处理上下文 |
| 完成百分比 | Percentage | 0-100 的整数，表示整体进度。值对象，带校验。 | 共享内核 |
| 内容文本 | ContentText | 非空的文本内容，及其内容类型（raw / punctuated / summary）。值对象。 | 共享内核 |
| 文档 | Document | 一个 BVid 下所有分P处理完成后的可读产物聚合，聚合根。 | 文档管理上下文 |
| 页文档 | PageDocument | 某一特定分P的文档视图，包含多种内容类型。 | 文档管理上下文 |
| 解析 | Resolve | 从 B站 URL 中提取视频元数据（标题、分P列表）。 | 防腐层 |
| 转录 | Transcribe | 将音频文件识别为原始文本（通过 Whisper 或等价服务）。 | 防腐层 |
| 加标点 | Punctuate | 通过 LLM 对原始文本进行标点符号补全与段落化。 | 防腐层 |
| 总结 | Summarize | 通过 LLM 对原始文本生成简短摘要。 | 防腐层 |
| 通知 | Notify | 将任务状态/进度变化推送给前端（当前实现为 SSE）。 | 防腐层 |
| 仓储 | Repository | 负责聚合根的持久化与查询，对调用方屏蔽存储细节。 | 基础设施 |
| 领域事件 | Domain Event | 领域内发生的具有业务意义的离散事件，如 `TaskCreated`、`StageCompleted`。 | 领域层 |

---

## 3. 限界上下文 Bounded Contexts

### 3.1 上下文划分

基于现有业务与代码职责，划分为 **两个核心上下文** 与 **一个共享内核**。

```
┌─────────────────────────────────────────────────────────────────────┐
│                         bili2text 系统                               │
│  ┌─────────────────────┐         ┌─────────────────────────────┐    │
│  │  视频处理上下文      │         │     文档管理上下文           │    │
│  │  Video Processing   │◄───────►│    Document Management       │    │
│  │  Context            │  订阅   │       Context                 │    │
│  │                     │  事件   │                               │    │
│  │  - 任务生命周期      │         │  - 扫描已生成文档             │    │
│  │  - 流水线编排        │         │  - 读取文档内容               │    │
│  │  - 状态机转换        │         │  - 文档目录展示               │    │
│  │  - 领域事件发布      │         │                               │    │
│  └─────────────────────┘         └─────────────────────────────┘    │
│           ▲                              ▲                          │
│           │         共享内核              │                          │
│           └──────── Shared Kernel ───────┘                          │
│                    (BVid, PageNumber, Percentage, ContentText)      │
└─────────────────────────────────────────────────────────────────────┘
```

- **视频处理上下文（Video Processing Context）**：核心上下文，承载 `ProcessingTask` 聚合根及完整流水线状态机。它是系统的“写模型”主战场。
- **文档管理上下文（Document Management Context）**：相对稳定的“读模型”上下文，负责消费处理结果，提供文档列表与内容读取。它通过订阅视频处理上下文发出的领域事件来感知新文档诞生。
- **共享内核（Shared Kernel）**：两上下文共同依赖的无行为值对象与通用工具，确保跨边界的概念一致性。

### 3.2 上下文映射关系

| 关系类型 | 上游上下文 | 下游上下文 | 说明 |
|---------|-----------|-----------|------|
| **发布-订阅（Pub/Sub）** | 视频处理上下文 | 文档管理上下文 | 视频处理上下文发布 `TaskCompleted` / `DocumentProduced` 事件；文档管理上下文的事件处理器消费并构建文档索引。两上下文通过领域事件松散耦合，无直接 API 调用。 |
| **共享内核（Shared Kernel）** | — | — | `BVid`、`PageNumber`、`Percentage`、`ContentText` 等值对象位于 `shared_kernel`，被两上下文共同 import。修改需双方协商，保持极小且稳定。 |

> **设计决策**：当前不引入“客户-供应商”式的 REST/RPC 调用，因为两上下文运行在同一进程内，领域事件总线即可满足解耦需求，避免分布式复杂度。

---

## 4. 四层架构与包结构

### 4.1 架构图与依赖规则

本重构采用 Eric Evans 提出的 **DDD 四层架构**，并针对 Python/FastAPI 场景做务实调整。

```
┌──────────────────────────────────────────────┐
│           表现层 Presentation                   │  FastAPI Routers / Jinja2 Templates
│  (routes.py, sse_notifier.py, schemas.py)    │  职责：HTTP 协议转换、参数校验、序列化
├──────────────────────────────────────────────┤
│           应用层 Application                    │  App Services / Event Handlers
│  (task_app_service.py, doc_app_service.py)   │  职责：编排用例、事务边界、事件发布/订阅
├──────────────────────────────────────────────┤
│           领域层 Domain                         │  Aggregates / Entities / Value Objects
│  (processing_task.py, document.py, events.py)│  职责：业务规则、状态机、领域事件定义
├──────────────────────────────────────────────┤
│         基础设施层 Infrastructure               │  Repositories / ACL Adapters / Config
│  (file_task_repo.py, whisper_adapter.py, ..) │  职责：持久化、外部服务调用、框架配置
└──────────────────────────────────────────────┘
```

**依赖规则（The Dependency Rule）**：

- 箭头只能 **向下**（外层依赖内层）。
- **领域层** 不依赖任何其他层，无外部 import（除 Python 标准库）。
- **应用层** 只依赖领域层接口，不依赖基础设施具体实现。
- **表现层** 只依赖应用层接口与基础设施层的具体装配代码（`main.py` 中的依赖注入）。
- 层与层之间通过 **接口（抽象基类 / Protocol）** 交互，运行时由 `main.py` 手动注入具体实现。

### 4.2 完整目录树（目标态）

```
D:\scj\bili2text
├── main.py                          # 应用入口：依赖注入组装、FastAPI 实例启动
├── requirements.txt
├── .env
├── README.md
├── AGENTS.md
│
├── presentation/                    # 表现层（原 main.py 中的路由与 SSE）
│   ├── __init__.py
│   ├── routes.py                    # FastAPI APIRoutes / Page Routes
│   ├── schemas.py                   # Pydantic Request/Response DTO（原 models.py 中的 DTO 部分）
│   └── sse_task_notifier.py         # ITaskNotifier 的 SSE 适配器实现
│
├── application/                     # 应用层（新增目录）
│   ├── __init__.py
│   ├── task_app_service.py          # TaskAppService：create_task, start_pipeline, get_task
│   ├── doc_app_service.py           # DocAppService：scan_documents, read_document
│   └── event_handlers.py            # 领域事件处理器：订阅事件 -> 调用 notifier / 更新读模型
│
├── domain/                          # 领域层（已有空目录，填充核心模型）
│   ├── __init__.py
│   ├── shared_kernel/               # 共享内核（值对象、通用工具）
│   │   ├── __init__.py
│   │   ├── value_objects.py         # BVid, PageNumber, Percentage, ContentText, ContentType
│   │   └── exceptions.py            # 领域异常基类 DomainError, ValidationError
│   │
│   ├── video_processing/            # 视频处理限界上下文
│   │   ├── __init__.py
│   │   ├── processing_task.py       # ProcessingTask 聚合根 + TaskStatus 枚举 + 状态机行为
│   │   ├── pipeline_stage.py        # PipelineStage 枚举
│   │   ├── page_result.py           # PageResult 值对象/实体
│   │   └── events.py                # 本上下文专用领域事件（TaskCreated, StageCompleted...）
│   │
│   ├── document_management/         # 文档管理限界上下文
│   │   ├── __init__.py
│   │   ├── document.py              # Document 聚合根
│   │   ├── page_document.py         # PageDocument 实体
│   │   └── events.py                # 本上下文专用领域事件（可选）
│   │
│   └── events.py                    # 通用领域事件基类、EventBus 抽象接口
│
├── infrastructure/                  # 基础设施层（已有目录，整理外部依赖）
│   ├── __init__.py
│   ├── config.py                    # 环境变量与配置读取（保持现有功能）
│   ├── persistence/                 # 仓储实现（文件系统）
│   │   ├── __init__.py
│   │   ├── file_task_repository.py  # TaskRepository 文件系统实现
│   │   └── file_document_repository.py  # DocumentRepository 文件系统实现
│   │
│   └── external/                    # 防腐层适配器
│       ├── __init__.py
│       ├── bili_gateway.py          # IBiliGateway 实现：基于 BiliDownloader
│       ├── audio_transcriber.py     # IAudioTranscriber 实现：基于 whisper
│       ├── text_processor.py        # ITextProcessor 实现：基于 ChatClient
│       └── task_notifier.py         # ITaskNotifier 实现：基于 asyncio.Queue（供 SSE 消费）
│
└── resources/                       # 文件系统数据目录（保持不变）
    └── <bvid>/
        ├── info.json
        ├── <page>_raw.txt
        ├── <page>_punctuated.md
        └── <page>_summary.md
```

### 4.3 原文件迁移映射

| 原文件 | 目标位置 | 说明 |
|--------|---------|------|
| `main.py` | `main.py` + `presentation/routes.py` | 路由提取到表现层，`main.py` 只做组装 |
| `pipeline.py` | 拆分到 `domain/video_processing/`, `application/` | 状态机进聚合根，编排进 AppService |
| `models.py` | `presentation/schemas.py` + `domain/shared_kernel/` + `domain/video_processing/` | DTO 上移，值对象下沉 |
| `services.py` | `application/doc_app_service.py` + `infrastructure/persistence/` | 扫描逻辑由应用层通过仓储接口调用 |
| `ChatClient.py` | `infrastructure/external/text_processor.py`（内部使用） | 作为 LLM 防腐层适配器的内部依赖 |
| `resolve_video_url.py` / `downloaders/BiliDownloader.py` | `infrastructure/external/bili_gateway.py`（内部使用） | 作为 B站防腐层适配器的内部依赖 |
| `process_doc.py` | 逻辑拆分至 `ITextProcessor` 接口及实现 | Prompt 定义保留在适配器或配置中 |

---

