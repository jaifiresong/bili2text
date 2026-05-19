import asyncio
import os

from domain import VideoDownloaderPort, LLMServicePort
from domain.models import VideoInfoItem
from infrastructure.config import LLM_CFG, BASE_DIR
from infrastructure.external.ChatClient import ChatClient

PROMPT_PUNCTUATION = """你是一位专业的中文文本编辑。请对以下转录文本进行处理：

要求：
1. 严格保留原始文字内容，不要增删改任何字词。
2. 文本中的标点符号大多是错误的，为文本添加合适的中文标点符号（逗号、句号、顿号、冒号、引号、破折号等）。
3. 文本中可能出现错别字，你要根据自己的专业经验修正。
3. 根据语义进行合理分段，每段不要太长，提升阅读体验。
4. 根据内容主题适当添加 Markdown 小标题（## 或 ###），划分内容模块。
5. 直接输出处理后的文本，不要添加额外说明（如"以下是处理后的文本"）。

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


def handle_txt(video: VideoInfoItem, stage='punctuation'):
    if stage == 'punctuation':
        cfg = LLM_CFG['deepseek-v4-flash']
        llm = ChatClient(**cfg, system_role=PROMPT_PUNCTUATION, on_chunk=lambda s: print(s, end=""))
        a_path = video.txt_raw_path
        b_path = os.path.join(BASE_DIR, f"storage/punctuation/{video.cid}.txt")
    else:
        cfg = LLM_CFG['kimi-k2.6']
        llm = ChatClient(**cfg, system_role=PROMPT_SUMMARY, on_chunk=lambda s: print(s, end=""))
        a_path = video.txt_punctuation_path
        b_path = os.path.join(BASE_DIR, f"storage/summary/{video.cid}.txt")

    if not os.path.exists(os.path.dirname(b_path)):
        os.makedirs(os.path.dirname(b_path))

    with open(a_path, 'r', encoding='utf-8') as fp:
        txt = llm.chat(fp.read(), True)
    with open(b_path, 'w', encoding='utf-8') as fp:
        fp.write(txt)
    return b_path


class LLMServiceAdapter(LLMServicePort):
    async def add_punctuation(self, video: VideoInfoItem) -> str:
        return await asyncio.to_thread(handle_txt, video, 'punctuation')

    async def summarize(self, video: VideoInfoItem) -> str:
        return await asyncio.to_thread(handle_txt, video, 'summary')
