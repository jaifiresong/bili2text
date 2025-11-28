import os
import subprocess

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
