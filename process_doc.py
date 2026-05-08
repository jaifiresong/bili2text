import argparse
import os
import sys
from pathlib import Path

from llm import ChatClient


def get_client(system_role: str) -> ChatClient:
    """根据环境变量创建 ChatClient 实例。"""
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    if not api_key:
        print("错误：未设置 OPENAI_API_KEY 环境变量。")
        print("示例（PowerShell）: $env:OPENAI_API_KEY='sk-xxx'")
        print("示例（Cmd）       : set OPENAI_API_KEY=sk-xxx")
        print("示例（Bash）      : export OPENAI_API_KEY=sk-xxx")
        sys.exit(1)

    return ChatClient(
        model=model,
        api_key=api_key,
        base_url=base_url,
        system_role=system_role,
        # 两个任务都是单轮长文本，history 不需要很大
        max_history=4,
    )


PROMPT_PUNCTUATION = """你是一位专业的中文文本编辑。请对以下视频教程转录文本进行处理：

要求：
1. 严格保留原始文字内容，不要增删改任何字词。
2. 为文本添加合适的中文标点符号（逗号、句号、顿号、冒号、引号、破折号等）。
3. 根据语义进行合理分段，每段不要太长，提升阅读体验。
4. 根据内容主题适当添加 Markdown 小标题（## 或 ###），划分内容模块。
5. 保持教程讲解的口语化风格，不要过度书面化。
6. 直接输出处理后的文本，不要添加额外说明（如"以下是处理后的文本"）。

待处理文本：
"""

PROMPT_SUMMARY = """你是一位资深的软件架构学习教练。请对以下教程内容进行深度总结，目标是让读者用最少的时间掌握核心知识：

要求：
1. 提取核心概念与关键术语。
2. 梳理讲解中的方法论、设计原则或思维框架（如有步骤，用编号列出）。
3. 用 bullet points 列出读者必须记住的关键点。
4. 如有面试考点或易错点，单独标注为 "面试提示"。
5. 输出格式使用 Markdown，结构清晰，层次分明。
6. 直接输出总结内容，不要添加额外说明。

待总结文本：
"""


def main():
    parser = argparse.ArgumentParser(
        description="为无标点的视频教程转录文本添加标点，并生成知识点总结。"
    )
    parser.add_argument("input_file", help="输入文件路径（例如 ddd/0.mp3.txt）")
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"错误：文件不存在: {input_path}")
        sys.exit(1)

    try:
        text = input_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"读取文件失败: {e}")
        sys.exit(1)

    if not text.strip():
        print("错误：输入文件为空。")
        sys.exit(1)

    print(f"已读取文件: {input_path} ({len(text)} 字符)")

    # 任务1：加标点（独立 client，隔离上下文）
    print("\n[任务 1/2] 加标点与分段")
    client1 = get_client("你是一个专业的中文文本编辑。")
    try:
        punctuated = client1.chat(PROMPT_PUNCTUATION + text, stream=False)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    out_punctuated = input_path.parent / (input_path.stem + "_punctuated.md")
    out_punctuated.write_text(punctuated, encoding="utf-8")
    print(f"已保存: {out_punctuated}")

    # 任务2：总结（独立 client，隔离上下文）
    print("\n[任务 2/2] 提取关键点")
    client2 = get_client("你是一个资深的软件架构学习教练。")
    try:
        summary = client2.chat(PROMPT_SUMMARY + text, stream=False)
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    out_summary = input_path.parent / (input_path.stem + "_summary.md")
    out_summary.write_text(summary, encoding="utf-8")
    print(f"已保存: {out_summary}")

    print("\n全部完成！")


if __name__ == "__main__":
    main()
