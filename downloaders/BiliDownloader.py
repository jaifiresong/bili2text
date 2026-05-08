import json
import os.path
from os import mkdir

import httpx
import asyncio
from urllib.parse import quote, unquote, urlparse

from efficient.util_dict import get_nested_value

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


class BiliDownloader:
    def __init__(self, url: str, sessdata: str | None = None):
        cookies = httpx.Cookies()
        if sessdata:
            cookies.set("SESSDATA", quote(unquote(sessdata)))

        self.client: httpx.AsyncClient = httpx.AsyncClient(
            headers=HEADERS,
            cookies=cookies,
            follow_redirects=True,
            timeout=10,
            verify=False,
        )

        self.url = url
        self.bvid = None
        self.page = 2

    async def _resolve_url(self):
        """跟随重定向，获取最终的B站规范URL。"""
        resp = await self.client.get(self.url)
        print(str(resp.url))
        parsed = urlparse(str(resp.url))
        self.bvid = parsed.path.strip('/').split('/')[-1]
        self.path = f"./resources/{self.bvid}"
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    async def get_video_info(self) -> dict:
        """获取视频基本信息，返回含cid、title等的字典。"""
        await self._resolve_url()
        api = "https://api.bilibili.com/x/web-interface/view"
        params = {'bvid': self.bvid}
        resp = await self.client.get(api, params=params)
        data = resp.json()
        if data["code"] != 0:
            raise RuntimeError(f"获取视频信息失败: {data.get('message', '未知错误')}")

        _map = {i['page']: i for i in get_nested_value(data, 'data.pages')}
        return _map

    async def get_play_url(self, video) -> str:
        """获取DASH格式播放地址。"""
        api = "https://api.bilibili.com/x/player/playurl"
        params = {
            "qn": 127,
            "fnval": 4048,
            "fourk": 1,
            "otype": "json",
            "cid": video['cid'],
            "bvid": self.bvid,
        }

        resp = await self.client.get(api, params=params)
        data = resp.json()
        # print(resp.text)
        # print(json.dumps(get_nested_value(data, 'data.dash.audio[0]')))
        return get_nested_value(data, 'data.dash.audio[0].base_url')

    async def download(self, video: dict, name):
        stream_url = await self.get_play_url(video)
        async with self.client.stream("GET", stream_url, follow_redirects=True) as resp:
            downloaded = 0
            total = int(resp.headers.get("content-length", 0))

            full_name = os.path.join(self.path, f"{name}.mp3")
            if os.path.exists(full_name):
                stat = os.stat(full_name)
                if stat.st_size >= total:
                    print('已存在', full_name)
                    return

            print(f"{full_name} 视频大小：{total / 1024 / 1024:.2f} MB")

            with open(full_name, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        # 进度条
                        if total:
                            progress = downloaded / total * 100
                            print(f"\r下载进度：{progress:.1f}%", end="")

    async def x(self):
        pages = await self.get_video_info()
        for k, v in pages.items():
            await self.download(v, k)


if '__main__' == __name__:
    r = BiliDownloader('https://www.bilibili.com/video/BV1fMwvzDECY/?spm_id_from=333.788.videopod.episodes')
    # asyncio.run(r.download())
    asyncio.run(r.x())
