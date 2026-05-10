from pathlib import Path
from typing import Optional, Tuple

import yt_dlp

from src.domain.models import VideoUrl, TranscriptSegment
from src.domain.ports import VideoDownloaderPort, SpeechRecognizerPort, LLMServicePort


class YtDlpVideoDownloaderAdapter(VideoDownloaderPort):
    """yt-dlp 音频下载适配器（防腐层）"""

    async def download_audio(self, url: VideoUrl) -> Tuple[bytes, dict]:
        output_path = f"/tmp/{url.video_id}"
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": output_path,
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url.value, download=True)
        audio_path = f"{output_path}.mp3"
        data = Path(audio_path).read_bytes()
        return data, {
            "title": info.get("title", ""),
            "duration": info.get("duration", 0),
        }


class WhisperSpeechRecognizerAdapter(SpeechRecognizerPort):
    """Whisper 语音识别适配器（防腐层）"""

    def __init__(self, model_size: str = "base"):
        import whisper
        self._model = whisper.load_model(model_size)

    async def transcribe(self, audio_path: str, language: str = "zh") -> Tuple[str, list[TranscriptSegment]]:
        result = self._model.transcribe(audio_path, language=language)
        segments = [
            TranscriptSegment(start=seg["start"], end=seg["end"], text=seg["text"])
            for seg in result.get("segments", [])
        ]
        raw_text = result.get("text", "")
        return raw_text, segments


class OpenAILLMAdapter(LLMServicePort):
    """OpenAI 兼容 LLM 适配器（防腐层）"""

    PUNCTUATION_PROMPT = """请为以下语音识别生成的无标点文本添加合适的标点符号和段落分隔。
要求：
1. 保持原文内容不变，仅添加标点
2. 根据语义适当分段
3. 不要添加任何解释或额外内容

原始文本：
{text}"""

    SUMMARY_PROMPT = """请对以下文本进行简洁的总结，提取关键信息。
要求：
1. 总结应涵盖主要观点
2. 使用清晰的结构（可使用序号或小标题）
3. 长度控制在原文的20%-30%

文本：
{text}"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: Optional[str] = None):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def add_punctuation(self, raw_text: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": self.PUNCTUATION_PROMPT.format(text=raw_text)
            }],
        )
        return response.choices[0].message.content

    async def summarize(self, text: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": self.SUMMARY_PROMPT.format(text=text)
            }],
        )
        return response.choices[0].message.content
