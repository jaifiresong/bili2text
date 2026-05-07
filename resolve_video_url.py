"""解析B站视频地址，获取视频/音频流下载链接。

用法:
    python scripts/resolve_video_url.py <视频地址> [SESSDATA]

示例:
    python scripts/resolve_video_url.py https://www.bilibili.com/video/BV1xx411c7mD
    python scripts/resolve_video_url.py https://b23.tv/xxxxx
    python scripts/resolve_video_url.py https://www.bilibili.com/video/BV1xx411c7mD "你的SESSDATA"




参考项目
https://github.com/KKKZOZ/bilibili2text
https://github.com/yutto-dev/yutto

"""
from __future__ import annotations
import asyncio

import re
import sys
from urllib.parse import quote, unquote

import httpx

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}

VIDEO_CODEC_MAP = {7: "avc", 12: "hevc", 13: "av1"}

VIDEO_QUALITY_MAP = {
    127: "8K 超高清",
    126: "杜比视界",
    125: "HDR 真彩",
    120: "4K 超清",
    116: "1080P 高帧率",
    112: "1080P 高码率",
    80: "1080P",
    74: "720P 高帧率",
    64: "720P",
    48: "720P 高码率",
    32: "480P",
    16: "360P",
}

AUDIO_QUALITY_MAP = {
    30251: "Hi-Res 无损",
    30250: "杜比全景声",
    30232: "192K",
    30280: "132K",
    30216: "64K",
}


def create_client(sessdata: str | None = None) -> httpx.AsyncClient:
    cookies = httpx.Cookies()
    if sessdata:
        cookies.set("SESSDATA", quote(unquote(sessdata)))
    return httpx.AsyncClient(
        headers=HEADERS,
        cookies=cookies,
        follow_redirects=True,
        timeout=10,
        verify=False,
    )


def parse_url(url: str) -> tuple[str, str]:
    """从URL中解析出bvid或aid。返回 (aid, bvid)，其中未找到的为空字符串。"""
    patterns = [
        (r"bilibili\.com/video/(BV[\w]+)", "bvid"),
        (r"bilibili\.com/video/av(\d+)", "aid"),
    ]
    for pattern, id_type in patterns:
        m = re.search(pattern, url)
        if m:
            if id_type == "bvid":
                return ("", m.group(1))
            else:
                return (m.group(1), "")
    return ("", "")


async def resolve_url(client: httpx.AsyncClient, url: str) -> str:
    """跟随重定向，获取最终的B站规范URL。"""
    resp = await client.get(url)
    return str(resp.url)


def av2bv(aid: int) -> str:
    """av转bv。"""
    XOR_CODE = 23442827791579
    MAX_AID = 1 << 51
    ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
    ENCODE_MAP = 8, 7, 0, 5, 1, 3, 2, 4, 6
    BASE = len(ALPHABET)
    PREFIX = "BV1"
    bvid = [""] * 9
    tmp = (MAX_AID | aid) ^ XOR_CODE
    for i in range(len(ENCODE_MAP)):
        bvid[ENCODE_MAP[i]] = ALPHABET[tmp % BASE]
        tmp //= BASE
    return PREFIX + "".join(bvid)


async def get_video_info(client: httpx.AsyncClient, aid: str, bvid: str) -> dict:
    """获取视频基本信息，返回含cid、title等的字典。"""
    api = "https://api.bilibili.com/x/web-interface/view"
    params = {}
    if bvid:
        params["bvid"] = bvid
    else:
        params["aid"] = aid
    resp = await client.get(api, params=params)
    data = resp.json()
    if data["code"] != 0:
        raise RuntimeError(f"获取视频信息失败: {data.get('message', '未知错误')}")
    return data["data"]


async def get_playurl(
    client: httpx.AsyncClient, aid: str, bvid: str, cid: str
) -> dict:
    """获取DASH格式播放地址。"""
    api = "https://api.bilibili.com/x/player/playurl"
    params = {
        "qn": 127,
        "fnval": 4048,
        "fourk": 1,
        "cid": cid,
        "otype": "json",
    }
    if bvid:
        params["bvid"] = bvid
    else:
        params["avid"] = aid
    resp = await client.get(api, params=params)
    data = resp.json()
    if data["code"] != 0:
        raise RuntimeError(f"获取播放地址失败: {data.get('message', '未知错误')}")
    if data["data"].get("dash") is None:
        raise RuntimeError("该视频不支持DASH格式")
    return data["data"]["dash"]


def extract_streams(dash: dict) -> tuple[list[dict], list[dict]]:
    """从dash数据中提取视频流和音频流信息。"""
    videos = []
    for v in dash.get("video", []):
        videos.append({
            "url": v["base_url"],
            "mirrors": v.get("backup_url") or [],
            "codec": VIDEO_CODEC_MAP.get(v["codecid"], f"unknown({v['codecid']})"),
            "width": v["width"],
            "height": v["height"],
            "quality_id": v["id"],
            "quality": VIDEO_QUALITY_MAP.get(v["id"], f"未知({v['id']})"),
        })

    audios = []
    for a in dash.get("audio", []):
        audios.append({
            "url": a["base_url"],
            "mirrors": a.get("backup_url") or [],
            "codec": "mp4a",
            "quality_id": a["id"],
            "quality": AUDIO_QUALITY_MAP.get(a["id"], f"未知({a['id']})"),
        })

    if dash.get("dolby") and dash["dolby"].get("audio"):
        for a in dash["dolby"]["audio"]:
            audios.append({
                "url": a["base_url"],
                "mirrors": a.get("backup_url") or [],
                "codec": "eac3",
                "quality_id": a["id"],
                "quality": f"杜比全景声 {AUDIO_QUALITY_MAP.get(a['id'], '')}",
            })

    if dash.get("flac") and dash["flac"].get("audio"):
        a = dash["flac"]["audio"]
        audios.append({
            "url": a["base_url"],
            "mirrors": a.get("backup_url") or [],
            "codec": "flac",
            "quality_id": a["id"],
            "quality": "Hi-Res 无损",
        })

    return videos, audios


async def resolve(url: str, sessdata: str | None = None):
    async with create_client(sessdata) as client:
        final_url = await resolve_url(client, url)
        aid, bvid = parse_url(final_url)
        if not aid and not bvid:
            raise ValueError(f"无法从URL解析出视频ID: {final_url}")

        info = await get_video_info(client, aid, bvid)
        title = info["title"]
        bvid = info["bvid"]
        aid = str(info["aid"])

        print(f"标题: {title}")
        print(f"avid: av{aid}  bvid: {bvid}")
        print()

        pages = info.get("pages", [])
        for page in pages:
            cid = str(page["cid"])
            part_name = page["part"]
            print(f"--- 分P: {part_name} (cid: {cid}) ---")

            dash = await get_playurl(client, aid, bvid, cid)
            videos, audios = extract_streams(dash)

            if videos:
                print(f"\n  视频流 ({len(videos)}条):")
                for i, v in enumerate(videos):
                    print(f"    [{i}] {v['quality']} | {v['codec']} | {v['width']}x{v['height']}")
                    print(f"        URL: {v['url']}")
                    if v["mirrors"]:
                        print(f"        镜像: {len(v['mirrors'])}个")

            if audios:
                print(f"\n  音频流 ({len(audios)}条):")
                for i, a in enumerate(audios):
                    print(f"    [{i}] {a['quality']} | {a['codec']}")
                    print(f"        URL: {a['url']}")
                    if a["mirrors"]:
                        print(f"        镜像: {len(a['mirrors'])}个")

            print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    sessdata = sys.argv[2] if len(sys.argv) > 2 else None


    asyncio.run(resolve(url, sessdata))


if __name__ == "__main__":
    # main()
    asyncio.run(resolve("https://www.bilibili.com/video/BV1sTAwzTEJL?spm_id_from=333.788.videopod.episodes&vd_source=544102bc44b42747fd532b892c2f591e&p=2"))
