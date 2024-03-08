import subprocess
import whisper
import time
from downloader import D


def excuteCommand(com):
    ex = subprocess.Popen(com, stdout=subprocess.PIPE, shell=True)
    out, err = ex.communicate()
    status = ex.wait()
    print(out.decode())
    return out.decode()


obj = D('https://www.bilibili.com/video/BV1224y1u7hF/?spm_id_from=333.788&vd_source=544102bc44b42747fd532b892c2f591e')
excuteCommand(f'ffmpeg -i ./runtime/{obj.audio} -q:a 0 -map a ./runtime/tmp-{obj.bv}.mp3 -y')

print('start transcribe ...')
st = time.time()
model = whisper.load_model('tiny')
"""
指定 Whisper 输出为简体中文
使用 --initial_prompt 参数，用简体中文输入 "以下是普通话的句子。" 就能生成简体中文字幕。（补充：whisper.cpp 用户可以尝试使用--prompt参数）
以此类推，用繁体中文输入 "以下是普通話的句子。" 就能得到繁体字幕。
有关 --initial_prompt 参数，可在 openai的文档查看更多:https://platform.openai.com/docs/guides/speech-to-text/prompting
"""
r = model.transcribe(f'./runtime/tmp-{obj.bv}.mp3', fp16=False, language='Chinese', initial_prompt='以下是普通话的句子')
with open(f'{obj.bv}.txt', 'w', encoding='utf-8') as fp:
    fp.write(r['text'])

en = time.time()
print('完成，用时：', en - st)
