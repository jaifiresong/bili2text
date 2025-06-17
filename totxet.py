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


def to_text(bv):
    """
    指定 Whisper 输出为简体中文
    使用 --initial_prompt 参数，用简体中文输入 "以下是普通话的句子。" 就能生成简体中文字幕。（补充：whisper.cpp 用户可以尝试使用--prompt参数）
    以此类推，用繁体中文输入 "以下是普通話的句子。" 就能得到繁体字幕。
    有关 --initial_prompt 参数，可在 openai的文档查看更多:https://platform.openai.com/docs/guides/speech-to-text/prompting
    """
    print('start transcribe ...')
    st = time.time()
    model = whisper.load_model('tiny')
    r = model.transcribe(f'./runtime/tmp-{bv}.mp3', fp16=False, language='Chinese', initial_prompt='以下是普通话的句子')
    with open(f'./runtime/{bv}.txt', 'w', encoding='utf-8') as fp:
        fp.write(r['text'])
    en = time.time()
    print('完成，用时：', en - st)


if '__main__' == __name__:
    # obj = D('https://www.bilibili.com/video/BV1XM411K7JR/?spm_id_from=333.788&vd_source=544102bc44b42747fd532b892c2f591e')
    obj = D('https://www.bilibili.com/video/BV1oa411b7c9/?spm_id_from=333.1007.top_right_bar_window_history.content.click&vd_source=544102bc44b42747fd532b892c2f591e')
    print('')
    excuteCommand(f'ffmpeg -i ./runtime/{obj.audio} -q:a 0 -map a ./runtime/tmp-{obj.bv}.mp3 -y')
    to_text(obj.bv)
