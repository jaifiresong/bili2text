from transformers import pipeline
import time

# 1. 加载模型 (第一次运行会自动下载)
print('加载 GLM-ASR-Nano 模型...')
asr_pipe = pipeline(
    "automatic-speech-recognition",
    model="zai-org/GLM-ASR-Nano-2512",
    device=-1,  # 使用 GPU，若用 CPU 可改为 -1
)

# 2. 转录音频
st = time.time()
result = asr_pipe(f'./resources/BV178w1z7EHQ/1.mp3')
en = time.time()

print('识别文本:', result["text"])
print('完成，用时：', en - st)