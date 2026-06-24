"""
抖音 API 客户端

封装 API 请求、WebID 获取、参数注入、签名逻辑与链接解析。
"""
import os
import re
import time
import random
import string
import requests
import urllib.parse
import urllib3.util.retry
from requests.adapters import HTTPAdapter

from infrastructure.config import DOUYIN_COOKIE
from . import config
from .logger import _logger
from .sign import a_bogus_sign
from .extractor import get_video_info


def extract_aweme_id(url: str) -> str:
    m = re.search(r'/video/(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'aweme_id=(\d+)', url)
    if m:
        return m.group(1)
    m = re.search(r'modal_id=(\d+)', url)
    if m:
        return m.group(1)
    return ''


class DouyinClient:
    """抖音 API 客户端 (同步版)"""

    def __init__(self, cookie: str = ''):
        self.cookie = cookie or DOUYIN_COOKIE
        self._webid = None
        self._webid_time = 0
        retry = urllib3.util.retry.Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
        self.session = requests.Session()
        self.session.mount('https://', HTTPAdapter(max_retries=retry))

    def _fetch_webid(self) -> str:
        if self._webid and (time.time() - self._webid_time) < 600:
            return self._webid
        try:
            h = config.COMMON_HEADERS.copy()
            h.update({
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'accept': 'text/html,application/xhtml+xml',
            })
            r = self.session.get(f'{config.DOUYIN_HOST}/?recommend=1', headers=h, timeout=10)
            for pat in [r'\\"user_unique_id\\":\\"(\d+)\\"',
                        r'"user_unique_id":"(\d+)"',
                        r'"webid":"(\d+)"',
                        r'webid=(\d+)']:
                m = re.search(pat, r.text)
                if m:
                    self._webid = m.group(1)
                    self._webid_time = time.time()
                    return self._webid
        except Exception:
            pass
        return ''

    def _get_ms_token(self) -> str:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=107))

    def _get_verify_fp(self) -> str:
        return 'verify_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

    def _resolve_share_url(self, text: str) -> str:
        m = re.search(r'https?://[^\s<>"\']+', text)
        if m:
            text = m.group()
        text = re.split(r'[，。！？；、,!;]', text, maxsplit=1)[0].strip().rstrip('，。！？；、,.!;')
        if text.startswith('www.'):
            text = 'https://' + text
        if 'v.douyin.com' in text:
            _logger.info(f'[解析] 短链接: {text}')
            try:
                r = self.session.get(text, allow_redirects=False, timeout=10, verify=False)
                if r.status_code in (301, 302):
                    location = r.headers.get('Location', '')
                    if location:
                        _logger.info(f'[解析] 重定向 → {location}')
                        return location
            except Exception as e:
                _logger.info(f'[解析] 重定向失败: {e}')
        return text

    def get_temp_cookie(self) -> str:
        s = requests.Session()
        s.headers.update({
            'User-Agent': config.UA,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        try:
            s.get(config.DOUYIN_HOST, timeout=10)
            cookies = [f'{c.name}={c.value}' for c in s.cookies]
            return '; '.join(cookies)
        except Exception:
            return ''

    def extr_video_info(self, url: str):
        url = self._resolve_share_url(url)
        aweme_id = extract_aweme_id(url)
        info = self.get_video_info(aweme_id)
        return info

    def download(self, url: str, filepath: str) -> bool:
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        h = {
            'User-Agent': config.UA,
            'Accept': '*/*',
            'Referer': 'https://www.douyin.com/',
            'Range': 'bytes=0-',
        }
        resp = self.session.get(url, headers=h, stream=True, timeout=(10, 120))
        resp.raise_for_status()
        total = int(resp.headers.get('Content-Length', 0)) or None
        downloaded = 0
        start_t = time.time()

        with open(filepath, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded / total * 100
                    speed = downloaded / (time.time() - start_t + 0.001)
                    eta = (total - downloaded) / speed if speed > 0 else 0
                    bar = '█' * int(pct / 5) + '░' * (20 - int(pct / 5))
                    print(f'\r  {bar} {pct:5.1f}% '
                          f'{downloaded / 1024 / 1024:.1f}/{total / 1024 / 1024:.1f} MB '
                          f'{speed / 1024 / 1024:.1f} MB/s ETA {eta:.0f}s',
                          end='', flush=True)
                else:
                    print(f'\r  已下载 {downloaded / 1024 / 1024:.1f} MB', end='', flush=True)
        print()
        print(f'[完成] {filepath}')

    def request(self, uri: str, user_params: dict, extra_headers: dict = None, method: str = 'GET', skip_sign: bool = True) -> tuple:
        params = dict(user_params)
        params.update(config.COMMON_PARAMS)
        headers = dict(config.COMMON_HEADERS)
        if extra_headers:
            headers.update(extra_headers)
        if self.cookie:
            headers['Cookie'] = self.cookie
        params['msToken'] = self._get_ms_token()
        verify_fp = self._get_verify_fp()
        params['verifyFp'] = verify_fp
        params['fp'] = verify_fp
        if self.cookie:
            for item in self.cookie.split(';'):
                if '=' in item:
                    k, v = item.strip().split('=', 1)
                    if k == 'dy_swidth':
                        params['screen_width'] = v
                    elif k == 'dy_sheight':
                        params['screen_height'] = v
        webid = self._fetch_webid()
        if webid:
            params['webid'] = webid
        if not skip_sign:
            qs = '&'.join(f'{k}={urllib.parse.quote(str(v))}' for k, v in params.items())
            params['a_bogus'] = a_bogus_sign(qs, headers['User-Agent'])
        url = f'{config.DOUYIN_HOST}{uri}'
        _logger.info(f'[请求] {method} {uri}')
        _logger.info(f'[参数] aid={params.get("aid")} '
                     f'version={params.get("version_name")} '
                     f'webid={webid or "无"} '
                     f'abogus={"是" if not skip_sign else "否"}')
        try:
            if method.upper() == 'POST':
                resp = self.session.post(url, data=params, headers=headers, timeout=(10, 30))
            else:
                resp = self.session.get(url, params=params, headers=headers, timeout=(10, 30))
        except requests.RequestException as e:
            _logger.info(f'[错误] 网络请求失败: {e}')
            return {'message': f'网络请求失败: {e}'}, False
        if resp.status_code != 200 or len(resp.content) == 0:
            _logger.info(f'[警告] HTTP {resp.status_code}, 内容为空 (被限流)')
            return {'message': '请求被拦截，请稍后再试或更换 Cookie'}, False
        try:
            data = resp.json()
        except Exception:
            _logger.info('[错误] JSON 解析失败')
            return {}, False
        if data.get('status_code', 0) != 0:
            _logger.info(f'[错误] API: status_code={data["status_code"]} ' f'msg={data.get("status_msg", "")}')
            return data, False
        return data, True

    get_video_info = get_video_info
