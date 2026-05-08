import json
import os

from openai import OpenAI


class ChatGPT:
    def __init__(self, model, api_key, base_url):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = model
        self._messages = []

    def set_role(self, role='You are a helpful assistant.'):
        self._messages.append({"role": "system", "content": role})

    def _chat(self):
        completion = self._client.chat.completions.create(
            model=self._model,
            messages=self._messages,
            stream=True,
            # max_tokens=8192,  # 输入 tokens + max_tokens 必须小于模型的上下文窗口大小
            # temperature=1.5  # 数默 1.0;建议：代码生成/数学解题 0.0;数据抽取/分析 1.0;通用对话 1.3;翻译 1.3;创意类写作/诗歌创作 1.5
        )

        rsp = ''
        for chunk in completion:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if content:
                print(content, end="")
                rsp += content
        print()
        self._messages.append(
            {"role": "assistant", "content": rsp}
        )
        return rsp

    def chat(self, message):
        self._messages.append(
            {"role": "user", "content": message}
        )
        return self._chat()

    def __repr__(self):
        return json.dumps(self._messages)


if __name__ == '__main__':
    from dotenv import load_dotenv

    load_dotenv()

    cfg = dict(
        base_url=os.getenv('LLM_BASE_URL'),
        model=os.getenv('LLM_MODEL'),
        api_key=os.getenv('LLM_API_KEY')
    )

    gpt = ChatGPT(**cfg)
    gpt.chat('你是哪个模型')
    print(gpt)
