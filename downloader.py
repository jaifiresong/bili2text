import urllib.request
from urllib.request import Request
from urllib.parse import urlparse
from bs4 import BeautifulSoup as Soup
import time
import sys, os
import gzip
import re
import json
import subprocess
import http.cookiejar

cookie = http.cookiejar.CookieJar()
cookieHandler = urllib.request.HTTPCookieProcessor(cookie)
Downloader = urllib.request.build_opener(cookieHandler)
headers = {
    'Accept': '*/*',
    'Cache-Control': 'no-cache',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'accept-encoding': 'gzip',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66',
}


def progressBar(progress: float) -> str:
    num = 25
    progress *= 100
    fix = int(progress * num / 10) % 10
    strReturn = '<'
    outputCharCount = int(progress * num / 100)
    for i in range(outputCharCount):
        strReturn += '='
    strReturn += str(fix)
    for i in range(num - 1 - outputCharCount):
        strReturn += ' '
    strReturn += '> '
    strReturn += "%.2f%%" % progress
    return strReturn
    # <========================>


def download(path, filename: str, HttpResponse, /):
    dataLen = HttpResponse.headers['Content-Length']
    with open(os.path.join(path, filename), "wb+") as f:
        size = 0
        previousSize = 0
        refreshInSec = 0.2
        start_time = time.time()
        totalTime = start_time
        while chunk := HttpResponse.read(512):
            f.write(chunk)
            size += 512
            if time.time() - start_time > refreshInSec:
                start_time = time.time()
                outputStr = "\r" + progressBar(size / int(dataLen))
                outputStr += " 已下载：" + "%.2f" % (size / 1024 / 1024) + ' MB'
                outputStr += " 下载速度：" + "%.3f" % ((size - previousSize) / 1024 / 1024 / refreshInSec) + ' MB/s  '
                sys.stdout.write(outputStr)
                previousSize = size
        totalTime = time.time() - totalTime
        sys.stdout.write("\r" + ' ' * 80)
        sys.stdout.write("\r文件大小：" + "%.3f" % (size / 1024 / 1024) + ' MB'
                                                                     " 平均下载速度：" + "%.3f" % (int(dataLen) / totalTime / 1024 / 1024) + ' MB/s')
        f.flush()
        f.close()


def epid2json(ep_id: str) -> str:
    apiUrl = 'https://api.bilibili.com/pgc/player/web/playurl?'
    urlArgs = [
        "fnval=80",
        "otype=json",
        "ep_id=" + ep_id
    ]
    apiUrl = apiUrl + "&".join(urlArgs)
    response = Downloader.open(Request(apiUrl, headers=headers))
    if response.headers['content-encoding'] == 'gzip':
        jsond = gzip.decompress(response.read()).decode("utf-8")
    else:
        jsond = response.read().decode("utf-8")
    return jsond


class D:
    url = None
    bv = None
    audio = None

    def __init__(self, url):
        arr = urlparse(url).path.split('/')
        self.bv = arr[-1] if arr[-1] else arr[-2]
        self.audio = f'{self.bv}.mp3'
        if os.path.exists('./runtime/' + self.audio):
            print('文件已存在：' + self.audio)
            return
        self.url = url
        _html = self.open_html()
        doc, fileName, playinfo = self.extract_media_info(_html)
        if playinfo == None:
            # ep
            objs = self.ep(url, doc, fileName)
        else:
            # 普通视频
            objs = self.ordinary(playinfo)
        self.download(objs)

    def open_html(self):
        R = Request(self.url, headers=headers)
        print("正在请求网络连接...")
        try:
            rsp = Downloader.open(R)
        except Exception as info:
            print("连接发生错误", info)
            input()
        if rsp.headers['content-encoding'] == 'gzip':
            _html = gzip.decompress(rsp.read()).decode("utf-8")
        else:
            _html = rsp.read().decode("utf-8")
        return _html

    def extract_media_info(self, _html):
        print("正在解析网页...")
        outputPath = os.path.split(os.path.realpath(sys.argv[0]))[0]
        doc = Soup(_html, features="html.parser")
        # print(doc)
        fileName =  '1212.mp4'
        for rchar in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'):
            fileName = fileName.replace(rchar, "-")
        if os.path.exists(os.path.join(outputPath, fileName)):
            while True:
                choice = input(os.path.join(outputPath, fileName) + "\n文件已存在，是否替换？[y/n]")
                if choice.lower() == "y":
                    os.remove(os.path.join(outputPath, fileName))
                    break
                if choice.lower() == "n":
                    sys.exit()
        jsonData = doc.find(text=re.compile('window.__playinfo__'))
        print(jsonData)
        return [doc, fileName, jsonData]

    # ep
    def ep(self, url, doc, fileName):
        check = url[url.rfind('/') + 1:]
        if check.find("ep") != -1:
            epid = check[check.find("ep") + 2:]
            if epid.find("?") != -1:
                epid = epid[:epid.find("?")]
        else:
            jsonData = doc.find(text=re.compile('window.__INITIAL_STATE__'))
            if jsonData == None:
                print("解析失败!")
                input("按回车结束")
                sys.exit()
            jsonData: str = jsonData[jsonData.find("{"):jsonData.rfind("};") + 1]
            try:
                eplist = json.loads(jsonData)["epList"]
            except:
                print("解析失败!")
                input("按回车结束")
                sys.exit()
            epid = str(eplist[0]['id'])
            fileName = eplist[0]['titleFormat'] + fileName
        print("epid:", epid)
        jsonData: str = epid2json(epid)
        try:
            objs = json.loads(jsonData)['result']['dash']
            return objs
        except:
            print("解析失败!", json.loads(jsonData)["message"])
            input("按回车结束")
            sys.exit()

    # 普通视频
    def ordinary(self, jsonData):
        jsonData: str = jsonData[jsonData.find("{"):]
        try:
            objs = json.loads(jsonData)['data']['dash']
            return objs
        except:
            try:
                objs = json.loads(jsonData)['data']['durl']
                objs[0]['url']
                return objs
            except:
                print("解析失败!", json.loads(jsonData)["message"])
                input("按回车结束")
                sys.exit()

    def download(self, info):
        d_headers = {
            'range': ' bytes=0-',
            'referer': ' https://www.bilibili.com/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36 Edg/87.0.664.66',
        }
        vurl = info['video'][0]["baseUrl"]
        aurl = info['audio'][0]["baseUrl"]

        a = 0
        if a:
            # 下载视频
            R = Request(vurl, headers=d_headers)
            response = Downloader.open(R)
            download('./runtime', 'tmp.mp4', response)
            response.close()

        # 下载音频
        R = Request(aurl, headers=d_headers)
        loop = True
        while loop:
            try:
                response = Downloader.open(R)
                loop = False
            except:
                pass
        download('./runtime', self.audio, response)
        response.close()


if '__main__' == __name__:
    # v = D('https://www.bilibili.com/video/BV1AN411K7SC/?spm_id_from=333.999.0.0&vd_source=544102bc44b42747fd532b892c2f591e')
    v = D('https://www.bilibili.com/video/BV1oa411b7c9/?spm_id_from=333.1007.top_right_bar_window_history.content.click&vd_source=544102bc44b42747fd532b892c2f591e')
