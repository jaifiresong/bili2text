import whisper
import time
import os
from downloader import D

st = time.time()
model = whisper.load_model('tiny')

r = model.transcribe(f'./runtime/tmp-BV1224y1u7hF.mp3.mp3', fp16=False, language='Chinese', initial_prompt='以下是普通话的句子')
print(r['text'])
en = time.time()
print(en - st)
