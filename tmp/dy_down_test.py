import json

from infrastructure.external.downloaders.douyin_downloader import DouyinClient

client = DouyinClient()
# info = client.resolve_share_url("https://www.douyin.com/jingxuan?modal_id=7649618569144585635")
# info = client.extr_video_info("https://www.douyin.com/jingxuan?modal_id=7649618569144585635")
# info = client.extr_video_info("https://www.douyin.com/jingxuan?modal_id=7650808310732313507")
# info = client.extr_video_info("https://www.douyin.com/jingxuan?modal_id=7649422251011345706") # 没有 music_url
info = client.extr_video_info("https://www.douyin.com/jingxuan?modal_id=7650808310732313507") # 音频不对应

print(json.dumps(info))

print(info['music_url'])

# client.download(info['music_url'], 'music.mp3')
