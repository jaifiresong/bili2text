import json
import os
import httpx
import asyncio
from urllib.parse import quote, unquote, urlparse

from efficient.util_dict import get_nested_value

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}


class BiliDownloader:
    def __init__(self, sessdata: str | None = None):
        cookies = httpx.Cookies()
        if sessdata:
            cookies.set("SESSDATA", quote(unquote(sessdata)))

        self.client: httpx.AsyncClient = httpx.AsyncClient(
            headers=HEADERS,
            cookies=cookies,
            follow_redirects=True,
            timeout=httpx.Timeout(10.0, connect=10.0, read=300.0, write=30.0),
            verify=False,
        )

    async def _resolve_url(self, url):
        """跟随重定向，获取最终的B站规范URL。"""
        resp = await self.client.get(url)
        print(str(resp.url))
        parsed = urlparse(str(resp.url))
        bvid = parsed.path.strip('/').split('/')[-1]
        return bvid

    async def get_video_info(self, url) -> dict:
        """获取视频基本信息，返回含cid、title等的字典。"""
        api = "https://api.bilibili.com/x/web-interface/view"
        bvid = await self._resolve_url(url)
        params = {'bvid': bvid}
        resp = await self.client.get(api, params=params)
        data = resp.json()
        if data["code"] != 0:
            raise RuntimeError(f"获取视频信息失败: {data.get('message', '未知错误')}")
        return get_nested_value(data, 'data')

    async def get_play_url(self, cid, bvid) -> str:
        """获取DASH格式播放地址。"""
        api = "https://api.bilibili.com/x/player/playurl"
        params = {
            "qn": 127,
            "fnval": 4048,
            "fourk": 1,
            "otype": "json",
            "cid": cid,
            "bvid": bvid,
        }

        resp = await self.client.get(api, params=params)
        data = resp.json()
        # print(resp.text)
        # print(json.dumps(get_nested_value(data, 'data.dash.audio[0]')))
        return get_nested_value(data, 'data.dash.audio[0].base_url')

    async def download(self, stream_url, full_name):
        async with self.client.stream("GET", stream_url, follow_redirects=True) as resp:
            downloaded = 0
            total = int(resp.headers.get("content-length", 0))
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


if '__main__' == __name__:
    async def test():
        d = BiliDownloader()
        info = await d.get_video_info('https://www.bilibili.com/video/BV1oQwYzCEmc/')
        print(json.dumps(info))
        print(info['bvid'])
        print(info['pages'][0]['cid'])
        stream_url = await d.get_play_url(info['pages'][0]['cid'], info['bvid'])

        await d.download(stream_url, 'test.mp3')


    asyncio.run(test())
