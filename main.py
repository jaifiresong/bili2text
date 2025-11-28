import loguru
import uvicorn
import whisper
from fastapi import FastAPI

app = FastAPI()
model = whisper.load_model('small')


@app.get("/")
def index():
    return {"message": "Hello FastAPI! 欢迎使用 Gemini"}


@app.get("/transcribe")
def transcribe():
    r = model.transcribe(audio=f'./runtime/1.m4a', fp16=False, language='Chinese', initial_prompt='以下是普通话的句子')
    loguru.logger.info(f"{r}")
    return {"text": r['text']}


if __name__ == "__main__":
    uvicorn.run(
        # 目标应用：指定模块名和应用实例名
        # 注意：这里需要传入 "文件名:应用对象" 的字符串形式，以便 reload 机制能正确监控文件变化
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # 开发服务最关键的参数：启用热重载
        log_level="info"
    )
