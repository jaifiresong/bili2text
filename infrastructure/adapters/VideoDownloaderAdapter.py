import os
import asyncio

from domain import VideoInfo, VideoUrl
from domain.models import VideoInfoItem, Platform
from domain.ports import VideoDownloaderPort
from infrastructure.config import BASE_DIR
from infrastructure.external.downloaders.BiliDownloader import BiliDownloader
from infrastructure.external.downloaders.douyin_downloader import DouyinClient

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

        if 'douyin.com' in url.value:
            client = DouyinClient()
            info = await asyncio.to_thread(client.extr_video_info, url.value)
            if not info:
                raise Exception('获取抖音视频信息失败')

            aweme_id_str = str(info.get('aweme_id', ''))
            if not aweme_id_str:
                raise Exception('解析抖音 aweme_id 失败')

            aweme_id = int(aweme_id_str)
            title = info.get('title', '')

            return VideoInfo(
                platform=Platform.DOUYIN,
                bvid=aweme_id_str,
                title=title,
                aid=0,
                cid=aweme_id,
                pages=[VideoInfoItem(cid=aweme_id, page=1, part=title)],
                url=url
            )

        raise Exception('暂不支持该平台')

    async def download(self, item: VideoInfoItem, video: VideoInfo) -> str:
        audio_path = os.path.join(BASE_DIR, f"storage/audio/{item.cid}.mp3")
        if not os.path.exists(os.path.dirname(audio_path)):
            os.makedirs(os.path.dirname(audio_path))

        if video.platform == Platform.DOUYIN:
            client = DouyinClient()
            info = await asyncio.to_thread(client.extr_video_info, video.url.value)
            music_url = info.get('music_url', '')
            if not music_url:
                raise Exception('未找到抖音音频下载地址')
            await asyncio.to_thread(client.download, music_url, audio_path)
            return audio_path

        if video.platform == Platform.BILIBILI:
            d = BiliDownloader()
            stream_url = await d.get_play_url(item.cid, video.bvid)
            await d.download(stream_url, audio_path)
            return audio_path

        raise Exception('暂不支持该平台')


if __name__ == '__main__':
    ...
