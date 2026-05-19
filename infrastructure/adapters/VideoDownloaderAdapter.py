import os

from domain import VideoInfo, VideoUrl
from domain.models import VideoInfoItem
from domain.ports import VideoDownloaderPort
from infrastructure.config import BASE_DIR

from infrastructure.external.downloaders.BiliDownloader import BiliDownloader

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


class VideoDownloaderAdapter(VideoDownloaderPort):
    async def video_info(self, url: VideoUrl) -> VideoInfo:
        if 'bilibili.com' in url.value:
            data = await BiliDownloader().get_video_info(url.value)
            pages = []
            for i in data['pages']:
                pages.append(VideoInfoItem(cid=i['cid'], page=i['page'], part=i['part']))

            return VideoInfo(
                bvid=data['bvid'],
                title=data['title'],
                aid=data['aid'],
                cid=data['cid'],
                pages=pages,
                url=url
            )

        raise Exception('暂不支持该平台')

    async def download(self, item: VideoInfoItem, video: VideoInfo) -> str:
        d = BiliDownloader()
        stream_url = await d.get_play_url(item.cid, video.bvid)
        audio_path = os.path.join(BASE_DIR, f"storage/audio/{item.cid}.mp3")
        if not os.path.exists(os.path.dirname(audio_path)):
            os.makedirs(os.path.dirname(audio_path))

        await d.download(stream_url, audio_path)
        return audio_path


if __name__ == '__main__':
    ...
