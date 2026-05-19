import asyncio
import os.path

import whisper
import time

from whisper import Whisper

from domain.models import VideoInfoItem
from infrastructure.config import BASE_DIR
from domain import SpeechRecognizerPort

speech_model = {
    'tiny': None,
    'small': None,
}


def to_text(audio_path, txt_path, m='tiny'):
    """
    指定 Whisper 输出为简体中文
    使用 --initial_prompt 参数，用简体中文输入 "以下是普通话的句子。" 就能生成简体中文字幕。（补充：whisper.cpp 用户可以尝试使用--prompt参数）
    以此类推，用繁体中文输入 "以下是普通話的句子。" 就能得到繁体字幕。
    有关 --initial_prompt 参数，可在 openai的文档查看更多:https://platform.openai.com/docs/guides/speech-to-text/prompting
    """
    if speech_model[m] is None:
        speech_model[m] = whisper.load_model(m)

    model: Whisper = speech_model[m]

    print('start transcribe ...')
    st = time.time()
    r = model.transcribe(audio_path, fp16=False, language='zh', initial_prompt='以下是普通话简体中文识别结果：')
    with open(txt_path, 'w', encoding='utf-8') as fp:
        fp.write(r['text'])
    en = time.time()
    print('完成，用时：', en - st)


class SpeechAdapter(SpeechRecognizerPort):
    async def transcribe(self, video: VideoInfoItem, language: str = "zh") -> str:
        txt_raw_path = os.path.join(BASE_DIR, f"storage/{video.cid}.txt")
        await asyncio.to_thread(to_text, video.audio_path, txt_raw_path)
        return txt_raw_path


if __name__ == '__main__':
    to_text(r'D:\jaifiresong\bili2text\storage\audio\36784898621.mp3', '1.txt')
