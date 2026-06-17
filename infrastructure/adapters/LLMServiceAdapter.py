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

# 第1版
PROMPT_SUMMARY_v1 = """你是一位资深的软件架构学习教练。请对以下教程内容进行深度总结，目标是让读者用最少的时间掌握核心知识：

要求：
- 提取文档中的核心主题，尽量精简，去掉口水话的内容。
- 根据文档的的核心主题判断是否可以梳理出讲解中的方法论、思维框架，可以的话列出来。
- 如果有读者必须记住的关键点，用 bullet points 列出来。
- 输出格式使用 Markdown，结构清晰，层次分明。
- 直接输出总结内容，不要添加额外说明。

待总结文本：
"""

PROMPT_SUMMARY = """
你是一个专业的知识提炼助手。我刚刚通读了一篇长文章，对内容有了大致了解，现在需要一份“复习用”的精简总结，避免重新阅读全文。

请根据我提供的文章，生成以下结构化总结，要求只保留核心信息，语言高度凝练，方便我快速扫读和回忆：

1. **核心主题与目的**：用简短的话概括文章到底在讲什么，想解决什么问题或传达什么观点。
2. **重要概念与术语**：列出文中出现的关键概念、术语及其简要定义（如果有）。
3. **关键论点/章节要点**：
    - 提炼文中最重要的分论点或逻辑板块，每个用简短的话说明。
    - 如果有支撑案例或数据，提取文中特别有说服力的例子、实验或数据，简要注明其说明了什么，放在论点或逻辑板块后面。
    - 此处结构要清析，要让读者分清：是分论点或逻辑板块，还是支撑案例或数据。
4. **思维框架**：根据文中核心主题判断是否可以梳理出讲解中的方法论、思维框架，可以的话列出来。
5. **结论或行动启示**：概括文章的最终结论、建议或对读者有什么用。

请严格遵循以上结构，避免长篇大段复述原文，每部分都用要点形式呈现。如果文章信息不足以支撑某一项，可注明“无”。

直接输出总结内容，不要添加额外说明。文章内容如下：
"""


def handle_txt(video: VideoInfoItem, stage='punctuation'):
    if stage == 'punctuation':
        cfg = LLM_CFG['deepseek-v4-flash']
        llm = ChatClient(**cfg, system_role=PROMPT_PUNCTUATION, on_chunk=lambda s: print(s, end=""))
        a_path = video.txt_raw_path
        b_path = os.path.join(BASE_DIR, f"storage/punctuation/{video.cid}.txt")
    else:
        cfg = LLM_CFG['deepseek-v4-pro']
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
