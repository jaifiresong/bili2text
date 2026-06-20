import json
import os

from typing import Callable, Generator, List, Optional
from openai import OpenAI, APIError


class ChatClient:
    """通用大模型对话客户端，支持自动上下文管理、流式/非流式调用。"""

    def __init__(
            self,
            model: str,
            api_key: str,
            base_url: str,
            system_role: Optional[str] = None,
            max_history: int = 100,
            on_chunk: Optional[Callable[[str], None]] = None,
    ):
        """
        Args:
            model: 模型名称。
            api_key: API Key。
            base_url: API Base URL。
            system_role: 系统角色设定，仅允许设置一次。
            max_history: 最大保留历史消息数（含 system/user/assistant），超出则自动丢弃最早的非 system 消息。
            on_chunk: 流式输出时，每个 chunk 的回调函数，例如 lambda s: print(s, end="")。
        """
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._messages: List[dict] = []
        self._max_history = max(max_history, 2)  # 至少保留 system + 一轮对话
        self._on_chunk = on_chunk

        if system_role:
            self.set_role(system_role)

    # ------------------------------------------------------------------
    # 角色与历史管理
    # ------------------------------------------------------------------
    def set_role(self, role: str = "You are a helpful assistant.") -> None:
        """设置系统角色。如果已存在则替换，确保只有一条 system 消息。"""
        if self._messages and self._messages[0]["role"] == "system":
            self._messages[0]["content"] = role
        else:
            self._messages.insert(0, {"role": "system", "content": role})

    def clear_history(self, keep_system: bool = True) -> None:
        """清空历史消息。"""
        if keep_system and self._messages and self._messages[0]["role"] == "system":
            self._messages = [self._messages[0]]
        else:
            self._messages = []

    def get_history(self) -> List[dict]:
        """获取当前完整上下文（浅拷贝）。"""
        return self._messages.copy()

    def _trim_history(self) -> None:
        """当消息数超出限制时，丢弃最早的非 system 消息对。"""
        # 保留 system 消息 + 最近 N 条
        system_msg = []
        rest = self._messages
        if self._messages and self._messages[0]["role"] == "system":
            system_msg = [self._messages[0]]
            rest = self._messages[1:]

        # 限制非 system 消息数量；由于对话是成对的，这里保留偶数条避免角色错位
        limit = self._max_history - len(system_msg)
        if len(rest) > limit:
            # 确保保留完整对话轮次（user-assistant 成对）
            drop = len(rest) - limit
            if drop % 2 != 0:
                drop += 1
            rest = rest[drop:]
        self._messages = system_msg + rest

    def _get_completion(self, stream):
        return self._client.chat.completions.create(model=self._model, messages=self._messages, stream=stream)

    # ------------------------------------------------------------------
    # 核心调用
    # ------------------------------------------------------------------
    def chat(self, message: str, stream: bool = False) -> str:
        """
        发送单条消息并获取回复。

        Args:
            message: 用户消息。
            stream: 是否流式输出。若为 True 且设置了 on_chunk，则会逐块回调。

        Returns:
            assistant 的完整回复文本。
        """
        self._messages.append({"role": "user", "content": message})
        self._trim_history()

        try:
            if stream:
                return self._chat_stream()
            return self._chat_sync()
        except APIError as e:
            # 请求失败时，回滚刚追加的 user 消息，避免脏上下文
            self._messages.pop()
            raise RuntimeError(f"LLM API 调用失败: {e}") from e
        except Exception as e:
            self._messages.pop()
            raise

    def chat_stream(self, message: str) -> Generator[str, None, None]:
        """
        流式对话，返回生成器，调用方自行消费每一段文本。
        同时会自动维护上下文（完整回复后追加到 history）。
        """
        self._messages.append({"role": "user", "content": message})
        self._trim_history()

        try:
            completion = self._get_completion(stream=True)
        except APIError as e:
            self._messages.pop()
            raise RuntimeError(f"LLM API 调用失败: {e}") from e
        except Exception:
            self._messages.pop()
            raise

        rsp_parts = []
        try:
            for chunk in completion:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content
                if content:
                    rsp_parts.append(content)
                    yield content
        except Exception as e:
            # 流式过程中出错，不保存不完整回复
            self._messages.pop()  # 回滚 user 消息
            raise RuntimeError(f"流式读取中断: {e}") from e

        rsp = "".join(rsp_parts)
        self._messages.append({"role": "assistant", "content": rsp})

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _chat_sync(self) -> str:
        """非流式调用。"""
        completion = self._get_completion(stream=False)
        rsp = completion.choices[0].message.content or ""
        self._messages.append({"role": "assistant", "content": rsp})
        return rsp

    def _chat_stream(self) -> str:
        """内部流式调用，聚合后返回完整字符串，支持 on_chunk 回调。"""
        completion = self._get_completion(stream=True)

        rsp_parts = []
        for chunk in completion:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                rsp_parts.append(content)
                if self._on_chunk:
                    self._on_chunk(content)

        rsp = "".join(rsp_parts)
        self._messages.append({"role": "assistant", "content": rsp})
        return rsp

    # ------------------------------------------------------------------
    # 表示
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"model={self._model!r}, "
            f"history_len={len(self._messages)})"
        )

    def __str__(self) -> str:
        lines = [f"Model: {self._model}", f"History ({len(self._messages)} messages):"]
        for i, msg in enumerate(self._messages):
            role = msg["role"]
            content = msg["content"]
            preview = content[:60].replace("\n", " ") + ("..." if len(content) > 60 else "")
            lines.append(f"  [{i}] {role}: {preview}")
        return "\n".join(lines)


# ===================================================================
# 使用示例
# ===================================================================
if __name__ == "__main__":
    from infrastructure.config import LLM_CFG

    cfg = LLM_CFG['mimo-v2.5']

    client = ChatClient(
        **cfg,
        system_role="You are a helpful assistant.",
        on_chunk=lambda s: print(s, end=""),
    )

    # 示例 1：非流式（适合脚本自动化）
    answer = client.chat("你是哪个模型？", stream=False)
    print("\n--- 完整回复 ---")
    print(answer)

    # 示例 2：流式（适合交互终端）
    print("\n--- 流式回复 ---")
    client.chat("用一句话解释 Python 的 GIL。", stream=True)
    print()

    # 示例 3：流式生成器（调用方完全掌控输出）
    print("\n--- 生成器模式 ---")
    for chunk in client.chat_stream("列举三种 Python 异步框架。"):
        print(chunk, end="")
    print()
