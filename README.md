# bili2text — B站视频转录与智能总结系统

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/FastAPI-0.100+-green.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Whisper-OpenAI-orange.svg" alt="OpenAI Whisper">
  <img src="https://img.shields.io/badge/LLM-OpenAI%20Compatible-purple.svg" alt="OpenAI Compatible LLM">
  <img src="https://img.shields.io/badge/Architecture-DDD-red.svg" alt="DDD Architecture">
</p>

<p align="center">
  <b>一键将 B站视频转为高质量文字稿 + AI 智能总结</b><br>
  <i>基于 FastAPI + OpenAI Whisper + LLM，支持 SSE 实时进度推送</i>
</p>

<p align="center">
  <a href="#-功能特性">功能特性</a> •
  <a href="#-在线演示">在线演示</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-api-文档">API 文档</a> •
  <a href="#-架构设计">架构设计</a> •
  <a href="#-配置说明">配置说明</a>
</p>

---

## ✨ 功能特性

- 🎬 **B站视频解析** — 输入 BV 号或视频链接，自动获取视频信息（标题、分 P、CID 等）
- 🎵 **音频自动下载** — 自动提取视频音轨，支持多 P 批量下载
- 🎯 **Whisper 语音转录** — 基于 OpenAI Whisper 模型，支持中文普通话高精度识别，自动输出简体中文
- ✍️ **AI 智能标点** — 使用 LLM 为原始转录文本添加合适的中文标点、分段和 Markdown 小标题
- 📝 **AI 内容总结** — 针对教程类内容，自动提取核心概念、方法论、关键知识点和面试考点
- 🔄 **SSE 实时推送** — 处理进度实时推送到前端，支持创建 → 下载 → 转录 → 标点 → 总结全流程可视化
- 🏗️ **DDD 分层架构** — 领域层零外部依赖，端口与适配器模式，代码结构清晰可维护
- 🌐 **Web UI + REST API** — 同时提供浏览器界面和 API 接口，方便集成到自己的工作流

## 🖼️ 在线演示

<table>
  <tr>
    <td align="center">
      <img src="docs/img.png" width="400" alt="Web UI 首页"><br>
      <sub>Web UI 首页 — 输入视频链接即可开始</sub>
    </td>
    <td align="center">
      <img src="docs/img_1.png" width="400" alt="任务列表"><br>
      <sub>任务列表 — 实时查看所有处理任务</sub>
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="docs/img_2.png" width="400" alt="处理进度"><br>
      <sub>SSE 实时推送 — 进度一目了然</sub>
    </td>
    <td align="center">
      <img src="docs/img_3.png" width="400" alt="结果展示"><br>
      <sub>结果展示 — 原文、标点文本、总结三栏对比</sub>
    </td>
  </tr>
</table>

## 🚀 快速开始

### 环境要求

- Python 3.10+
- FFmpeg（Whisper 依赖）
- 至少 4GB 可用内存（Whisper 模型加载）
- OpenAI 兼容的 LLM API Key（Kimi、DeepSeek、OpenAI 等）

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/bili2text.git
cd bili2text
```

### 2. 安装依赖

本项目依赖来自父项目虚拟环境（`.venv`），请确保虚拟环境已激活：

```bash
# 创建并激活虚拟环境（如尚未创建）
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows

# 安装核心依赖
pip install fastapi uvicorn whisper openai pydantic jinja2 tinydb
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
# LLM API 配置（支持任意 OpenAI 兼容接口）
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4

# 可选：配置多个模型用于不同任务
# PUNCTUATION_MODEL=deepseek-v4-flash
# SUMMARY_MODEL=kimi-k2.6
```

### 4. 启动服务

```bash
uvicorn main:app --reload
```

服务将在 `http://127.0.0.1:8000` 启动。

- **Web UI**: 访问 `http://127.0.0.1:8000/`
- **API 文档**: 访问 `http://127.0.0.1:8000/docs`（Swagger UI）
- **健康检查**: `http://127.0.0.1:8000/health`

## 📡 API 文档

### 基础信息

- **Base URL**: `http://127.0.0.1:8000/api/v1/tasks`
- **Content-Type**: `application/json`

### 接口列表

| 方法 | 路径 | 描述 | 状态码 |
|------|------|------|--------|
| GET | `/api/v1/tasks/parse?video_url={url}` | 解析视频 URL，返回视频信息 | 202 |
| POST | `/api/v1/tasks/` | 提交视频处理任务 | 202 |
| GET | `/api/v1/tasks/test` | 测试接口 | 200 |
| GET | `/api/v1/tasks/{task_id}/stream` | SSE 实时进度推送 | 200 |

### 使用示例

#### 1. 解析视频

```bash
curl "http://127.0.0.1:8000/api/v1/tasks/parse?video_url=https://www.bilibili.com/video/BV1fMwvzDECY/"
```

**响应示例：**

```json
{
  "bvid": "BV1fMwvzDECY",
  "title": "Python 进阶教程",
  "aid": 123456789,
  "cid": 987654321,
  "pages": [
    {"cid": 987654321, "page": 1, "part": "P1 课程介绍"},
    {"cid": 987654322, "page": 2, "part": "P2 装饰器详解"}
  ]
}
```

#### 2. 提交处理任务

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tasks/" \
  -H "Content-Type: application/json" \
  -d '{"video_id": "abc123...", "pages": [1, 2]}'
```

**响应示例：**

```json
{
  "video_id": "abc123...",
  "pages": [1, 2],
  "task_id": "f47ac10b58cc4372a5670e02b2c3d479",
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

#### 3. 实时进度推送（SSE）

```javascript
const eventSource = new EventSource('http://127.0.0.1:8000/api/v1/tasks/{task_id}/stream');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('当前状态:', data.status, '进度:', data.progress);
};
```

## 🏗️ 架构设计

### DDD 分层架构

```
presentation/     ← HTTP 路由、Web UI、异常处理
    ├── api/           API 端点（submit, status, stream）
    ├── templates/     Jinja2 模板
    └── dependencies.py  依赖注入容器（手工 DI，非 FastAPI 内置）

application/      ← 应用服务、用例编排
    ├── use_cases.py   业务用例（解析、处理、查询）
    └── dto.py         数据传输对象

domain/           ← 核心业务逻辑（零外部依赖！）
    ├── models.py      领域模型、值对象、枚举
    ├── events.py      领域事件总线（SimpleEventBus）
    ├── ports.py       端口定义（抽象接口）
    └── repositories.py 仓储接口

infrastructure/   ← 技术实现
    ├── adapters/      端口适配器（下载、语音识别、LLM）
    ├── external/      外部服务客户端
    ├── repositories.py 仓储实现（TinyDB、内存）
    └── config.py      配置管理
```

### 处理流水线

```
用户提交视频链接
      │
      ▼
[解析URL] ──→ 获取视频信息（标题、分P）
      │
      ▼
[创建任务] ──→ ProcessingTask（内存存储）
      │
      ▼
[下载音频] ──→ 按 CID 存储为 MP3
      │
      ▼
[Whisper转录] ──→ 原始文本（简体中文）
      │
      ▼
[LLM标点] ──→ 加标点、分段、Markdown标题
      │
      ▼
[LLM总结] ──→ 核心概念、方法论、面试提示
      │
      ▼
[完成] ──→ 所有产物存储到 ./storage/
```

**数据流：**

```
ProcessVideoUseCase
       │
       ▼ _emit_status()
SimpleEventBus.publish()
       │
       ▼ 回调 _on_status_changed()
asyncio.Queue
       │
       ▼ await queue.get()
SSE 生成器
       │
       ▼ yield "data: {...}\n\n"
   客户端 EventSource
```

### 设计亮点

- **领域层零外部依赖** — `domain/` 目录下不出现任何 `import fastapi`、`import whisper`、`import openai`，确保核心业务逻辑纯粹
- **端口与适配器模式** — 所有外部服务（下载、语音识别、LLM）通过 `domain/ports.py` 抽象，实现细节在 `infrastructure/adapters/` 中隔离
- **自定义 DI 容器** — `presentation/dependencies.py` 集中管理所有依赖注册，支持单例共享和测试替换
- **SSE 实时推送** — 基于内存事件总线，零外部消息队列依赖，轻量且足够支撑当前场景

## ⚙️ 配置说明

### LLM 模型配置

在 `infrastructure/config.py` 中配置 LLM 模型：

```python
LLM_CFG = {
    'kimi-k2.6': {
        'api_key': os.getenv('LLM_API_KEY'),
        'base_url': os.getenv('LLM_BASE_URL'),
        'model': 'kimi-k2.6',
    },
    'deepseek-v4-flash': {
        'api_key': os.getenv('LLM_API_KEY'),
        'base_url': os.getenv('LLM_BASE_URL'),
        'model': 'deepseek-v4-flash',
    },
}
```

当前策略：
- **标点任务**：使用轻量级模型（如 DeepSeek-V4-Flash），成本低、响应快
- **总结任务**：使用强模型（如 Kimi-K2.6），确保总结质量

### 存储结构

```
./
├── storage/
│   ├── video_info.json          # TinyDB 持久化（视频元数据）
│   ├── audio/{cid}.mp3          # 下载的音频文件
│   ├── {cid}.txt                # Whisper 原始转录文本
│   ├── punctuation/{cid}.txt    # LLM 标点后的文本
│   └── summary/{cid}.txt        # LLM 总结文本
└── {bvid}/
    └── {page}.mp3               # 视频音频（备用）
```

### Whisper 模型选择

在 `infrastructure/adapters/SpeechAdapter.py` 中配置：

```python
# 可选模型：tiny, base, small, medium, large
# 精度与速度权衡：tiny（最快）→ large（最准）
speech_model = {
    'tiny': None,   # ~1GB 内存，适合快速测试
    'small': None,  # ~2GB 内存，平衡选择
}
```

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| [FastAPI](https://fastapi.tiangolo.com/) | 高性能 Web 框架 |
| [OpenAI Whisper](https://github.com/openai/whisper) | 语音识别与转录 |
| [Pydantic](https://docs.pydantic.dev/) | 数据验证与序列化 |
| [Jinja2](https://jinja.palletsprojects.com/) | 模板引擎（Web UI） |
| [TinyDB](https://tinydb.readthedocs.io/) | 轻量级 JSON 数据库 |
| [uvicorn](https://www.uvicorn.org/) | ASGI 服务器 |

## 📝 应用场景

- 📚 **学习笔记** — 将 B站教程视频转为文字稿，方便做笔记和复习
- 🔍 **内容检索** — 为视频内容建立全文索引，快速定位知识点
- 📝 **文章创作** — 基于视频内容生成结构化文章或博客
- 🎓 **知识管理** — 构建个人视频知识库，配合 Obsidian/Notion 使用
- 🤖 **二次开发** — 基于本项目的 API 和架构，构建更复杂的视频处理工作流

## 🤝 贡献指南

欢迎 Issue 和 PR！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 📄 许可证

[MIT](LICENSE) © yourname

---

<p align="center">
  如果这个项目对你有帮助，请给个 ⭐ Star！<br>
  <sub>Keywords: B站视频转文字, Bilibili transcription, Whisper 语音识别, AI 视频总结, FastAPI, DDD 架构, SSE 实时推送, OpenAI 兼容, 视频转录, 语音转文本, Python 视频处理</sub>
</p>
