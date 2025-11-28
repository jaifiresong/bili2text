pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

参考项目
- 下载视频，特别感谢，自由度高
    - https://github.com/abumpkin/bilibiliDownloader

- 下载视频
    - https://github.com/yutto-dev/bilili

- 项目实现方式和技术栈参考
    - https://github.com/lanbinshijie/bili2text

抖音视频下载
https://www.xiazaitool.com/dy



pip install fastapi "uvicorn[standard]"

# 格式：uvicorn <文件名>:<应用对象名> --reload
uvicorn main:app --reload
--reload 参数：让服务器在检测到代码文件变化时自动重新加载（仅用于开发环境）。


自动交互式文档（Swagger UI）：
访问：http://127.0.0.1:8000/docs