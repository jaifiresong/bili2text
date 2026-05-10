# B站视频音频转录与智能总结系统 — 融合架构设计

以 2.md 的简洁骨架为基础，吸收 1.md 的 SSE 实时推送、轻量领域事件、值对象自校验等优点，
避免过度工程，同时保留必要的 DDD 严谨性。

## 启动

```bash
uvicorn src.main:app --reload
```

## 架构要点

- **领域层零外部依赖**：所有外部交互通过端口抽象。
- **聚合根之间只存原始值**：`ProcessingTask` 不持有 `VideoAudio`/`Transcription` 实例，只存 `audio_path`/`raw_transcript` 等原始值。
- **流水线编排置于应用层**：`ProcessVideoUseCase` 负责 download → transcribe → punctuate → summarize 的编排。
- **轻量领域事件**：`SimpleEventBus` 采用内存回调模式，足够支撑 SSE 推送，后续可平滑替换为消息队列。
- **适度分包**：避免 1.md 的过度细分，保持 Python 项目可维护性。
