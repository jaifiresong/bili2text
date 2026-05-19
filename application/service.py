import logging

from domain import ProcessingTask, VideoInfo, VideoDownloaderPort, SpeechRecognizerPort, LLMServicePort
from domain.models import VideoInfoItem
from domain.repositories import VideoInfoRepository


class TaskHandleService:
    def __init__(
            self,
            task: ProcessingTask,
            video: VideoInfo,
            downloader: VideoDownloaderPort,
            speech: SpeechRecognizerPort,
            llm: LLMServicePort,
            repo: VideoInfoRepository,
    ):
        self.task = task
        self.video = video
        self.downloader = downloader
        self.speech = speech
        self.llm = llm
        self.repo = repo

    async def start(self):
        _map = {i.page: i for i in self.video.pages}
        for page in self.task.pages:
            item: VideoInfoItem = _map[page]
            await self.handle_item(item)
        print("任务完成")

    async def handle_item(self, item: VideoInfoItem):
        if not item.audio_path:
            print(f"开始下载 {item}...")
            item.audio_path = await self.downloader.download(item, self.video)
            await self.repo.save(self.video)

        if not item.txt_raw_path:
            print(f"开始识别 {item}...")
            item.txt_raw_path = await self.speech.transcribe(item)
            await self.repo.save(self.video)

        if not item.txt_punctuation_path:
            print(f"开始加标点 {item}...")
            item.txt_punctuation_path = await self.llm.add_punctuation(item)
            await self.repo.save(self.video)

        if not item.txt_summarize_path:
            print(f"开始总结 {item}...")
            item.txt_summarize_path = await self.llm.summarize(item)
            await self.repo.save(self.video)

        print(f"处理完成 {item}")
