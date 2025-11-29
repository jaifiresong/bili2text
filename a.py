import os
import subprocess

import whisper


def f1():
    i = 0
    for root, dirs, files in os.walk('./DDD'):
        for file in files:
            if file.endswith('.mp4'):
                print(file)
                # ffmpeg -i 6.mp4 -q:a 0 -map a 6.mp3 -y
                cmd = [
                    'ffmpeg',
                    '-i', f'"{os.path.join(root, file)}"',
                    '-q:a 0',
                    '-map a', f"./{i}.mp3",
                    '-y'
                ]

                print(' '.join(cmd))
                os.system(' '.join(cmd))
                # subprocess.call(cmd)
                i += 1


def f2():
    model = whisper.load_model('small')
    for root, dirs, files in os.walk('./DDD'):
        for file in files:
            if file.endswith('.mp3'):
                print(file)
                r = model.transcribe(os.path.join(root, file), fp16=False, language='Chinese', initial_prompt='以下是普通话的句子')
                with open(f'./DDD/{file}.txt', 'w', encoding='utf-8') as fp:
                    fp.write(r['text'])


if '__main__' == __name__:
    f2()
