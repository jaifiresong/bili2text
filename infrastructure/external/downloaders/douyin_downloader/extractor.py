"""
视频信息提取

从抖音 API 响应中提取视频下载地址、封面、背景音乐等信息。
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import DouyinClient


def get_video_info(client: "DouyinClient", aweme_id: str) -> dict:
    for use_abogus in [True, False]:
        params = {
            'aweme_id': aweme_id,
            'os': 'windows',
        }
        data, ok = client.request(
            '/aweme/v1/web/aweme/detail/',
            params,
            skip_sign=not use_abogus,
        )
        if ok and data.get('aweme_detail'):
            break

    if not ok or not data.get('aweme_detail'):
        print(f'[错误] 获取视频详情失败')
        return {}

    post = data['aweme_detail']
    author = post.get('author') or {}
    video_data = post.get('video') or {}
    music = post.get('music') or {}

    info = {
        'aweme_id': post.get('aweme_id', ''),
        'title': post.get('item_title', ''),
        'desc': post.get('desc', ''),
        'author_nickname': author.get('nickname', ''),
        'author_uid': author.get('uid', ''),
        'cover_url': '',
        'video_urls': [],
        'music_url': '',
    }

    cover = video_data.get('cover') or {}
    if cover.get('url_list'):
        info['cover_url'] = cover['url_list'][0]

    candidates = []
    for br in video_data.get('bit_rate') or []:
        if not isinstance(br, dict):
            continue
        for key in ('play_addr', 'play_addr_h264'):
            addr = br.get(key) or {}
            for u in (addr.get('url_list') or []):
                if u:
                    candidates.append(u)
    play_addr = video_data.get('play_addr') or {}
    for u in (play_addr.get('url_list') or []):
        if u:
            candidates.append(u)
    download_addr = video_data.get('download_addr') or {}
    for u in (download_addr.get('url_list') or []):
        if u:
            candidates.append(u)

    seen = set()
    clean = []
    for u in candidates:
        u = u.replace('playwm', 'play').replace('watermark=1', 'watermark=0')
        if u and u not in seen:
            seen.add(u)
            clean.append(u)

    info['video_urls'] = clean
    if clean:
        print(f'[视频] {len(clean)} 个可用地址')
        for i, u in enumerate(clean[:2]):
            print(f'  [{i}] {u[:80]}...')
    else:
        print('[警告] 未找到视频下载地址')

    if isinstance(music.get('play_url'), dict):
        mu_list = music['play_url'].get('url_list', [])
        if mu_list:
            info['music_url'] = mu_list[0]
            print(f'[音乐] {mu_list[0][:80]}...')
    if not info['music_url'] and music.get('h5_url'):
        info['music_url'] = music['h5_url']

    print(f'[标题] {info["desc"][:60] or "无标题"}')
    print(f'[作者] {info["author_nickname"]}')

    return info
