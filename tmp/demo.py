"""
抖音视频下载 Demo
提取自 DY_video_downloader 项目的核心逻辑

功能:
  1. 解析抖音分享链接 (v.douyin.com 短链接 → 视频 ID)
  2. 获取视频详情 (标题、作者、视频地址、背景音乐)
  3. 下载无水印视频 + 背景音乐

用法:
  python demo.py <抖音分享链接>

  # 设置 Cookie (强烈推荐，否则 API 会返回空):
  # 方法1: 设置环境变量
  set DOUYIN_COOKIE=你的登录cookie
  python demo.py <链接>

  # 方法2: 创建 config.json 和 demo.py 同目录
  # {"cookie": "你的登录cookie"}

  # 方法3: 直接修改下方 COOKIE 变量

依赖:
  pip install requests
"""

import re
import os
import sys
import json
import time
import random
import string
import requests
import urllib.parse
import urllib3.util.retry
from requests.adapters import HTTPAdapter

# ===== 配置 =====
# 直接在这里填写 Cookie (优先级最低)
COOKIE = 'SEARCH_RESULT_LIST_TYPE=%22single%22; hevc_supported=true; n_mh=fj84ydEPltANKZOVdZpKQi4l4s0RGZyqpGeaRyKiLAc; enter_pc_once=1; UIFID=99405022e0708801aee7ff4c54400ac8e593ae85f3b433b0b452508931dcf94fec1eb277ac641cd102e3503ba10100ff05ea46529b38f9ef92427327c9c6db421b7b1c732a6afaacf8cd1e12e0262e0de95ea88b4f978ac0593bfb7ce21358e81ed52ed711b80746ad59027a5f0ad0046662fe4874ea4f4fe92d70c7c8af7ae7756f207524db431bb88a90e77bbe4e628c26c32842e43fb37af6f7c29a2336b07fd3d1e6a89bc6c7ab588ee5ebe3b647442fbdbba213a3025dc53d1595b92c5b; d_ticket=c16799a6b54cbb11b87e9c0197cf5b13d0ae3; my_rd=2; SEARCH_UN_LOGIN_PV_CURR_DAY=%7B%22date%22%3A1769436185633%2C%22count%22%3A3%7D; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.5%7D; SelfTabRedDotControl=%5B%7B%22id%22%3A%227587273689973688346%22%2C%22u%22%3A3%2C%22c%22%3A0%7D%5D; passport_csrf_token=f95e6dccf69c658beef1ed81a32ceffe; passport_csrf_token_default=f95e6dccf69c658beef1ed81a32ceffe; is_staff_user=false; __security_mc_1_s_sdk_crypt_sdk=a16d2ba7-4347-b3c0; __security_mc_1_s_sdk_cert_key=3cd103d7-47dc-b6bb; bd_ticket_guard_client_web_domain=2; passport_mfa_token=CjVd4HUnznh1cq4PjO17rSA75g9OWcg6k%2FKhyVfIJlJC2qIfh6fF1W0krNxK5mynrJgLhrBF4RpKCjwAAAAAAAAAAAAAUFL5TSqmPLYRcEOzV%2Fg2vP5BjputLEUJ4yndrwSAP520Ik7zJ9VTI2ApO9abB6kupEsQ3JuPDhj2sdFsIAIiAQMpivGW; passport_assist_user=CjwpKpaL5N7Znu9arh0uZyzF0yBvWeH49az8rScVvYKc2aGBjV25MGjEenhlfItvWr9ulPZUfVejSqg8OzcaSgo8AAAAAAAAAAAAAFBSCwOh5HZIKfxr7RFaBKdWdYEnTiUlMCiIX2Mm_Lj4RfRquztGB7eyBrqBqe-U7lnCEMmbjw4Yia_WVCABIgEDaED71g%3D%3D; uid_tt=9b39588eed0b01859c3899b29a6f9c48; uid_tt_ss=9b39588eed0b01859c3899b29a6f9c48; sid_tt=bb6e841218715e4d397b3d56a75670c2; sessionid=bb6e841218715e4d397b3d56a75670c2; sessionid_ss=bb6e841218715e4d397b3d56a75670c2; has_biz_token=false; __security_mc_1_s_sdk_sign_data_key_web_protect=95ef1e4b-4b5c-87e8; _bd_ticket_crypt_cookie=dcc1b8eb319a7e84aff08d52789b78a5; login_time=1776566858506; publish_badge_show_info=%220%2C0%2C0%2C1779504517340%22; is_dash_user=1; sid_guard=bb6e841218715e4d397b3d56a75670c2%7C1779504522%7C5184000%7CWed%2C+22-Jul-2026+02%3A48%3A42+GMT; session_tlb_tag=sttt%7C7%7Cu26EEhhxXk05ez1Wp1Zwwv_________SfhCG47PhJh8p8bB7SRfxkFqXyQQkz0dhrA-LKKnX2wU%3D; sid_ucp_v1=1.0.0-KDZlMTAzMjdjOGE1NWIxMTc0OWQ3YzkwMTZhZTlkMjc3MmI0ZDRlZWIKHwjRmLPN4wIQiqvE0AYY7zEgDDCaoarVBTgFQPsHSAQaAmxmIiBiYjZlODQxMjE4NzE1ZTRkMzk3YjNkNTZhNzU2NzBjMg; ssid_ucp_v1=1.0.0-KDZlMTAzMjdjOGE1NWIxMTc0OWQ3YzkwMTZhZTlkMjc3MmI0ZDRlZWIKHwjRmLPN4wIQiqvE0AYY7zEgDDCaoarVBTgFQPsHSAQaAmxmIiBiYjZlODQxMjE4NzE1ZTRkMzk3YjNkNTZhNzU2NzBjMg; is_support_rtm_web_ts=1; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A2560%2C%5C%22screen_height%5C%22%3A1440%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A12%2C%5C%22device_memory%5C%22%3A16%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A0%7D%22; strategyABtestKey=%221779783307.255%22; ttwid=1%7CUWa9OrB1r6xMqTMe_WfGSeF-Iig1RnRsViraxEgemgQ%7C1779783306%7Cc95775f98cff22d2fc4c7c1e30031151642ce5352180d634df8225860fc97af2; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e582729277672715a646971273f2763646976602729277f6b5a666475273f2763646976602729276d6a6e5a6b6a716c273f2763646976602729276c6b6f5a7f6367273f27636469766027292771273f273c31323d3536363d323c323234272927676c715a75776a716a666a69273f2763646976602778; bit_env=dZ4QapT-Qj5aPHgCFZNUoUPDByQH2yujd6F4BTyvxBNPASOP2Hk4XX4qCrB8Y4TiJbpQ5hhxGc2NYxuSzynHUVf_6dB3w1Zbqz7l8tPJDxmiSQk0Hl1dSsmOqhnrT2lGKBg9gXs0M7_umTZDiwHQwUMPf7yccDKUWgtwFcLwWF9yxQDTU9H57LPa8F_1u4w9QvisKu733P0o0a4bY_Jvk3VzzkszjuN-ZMgEqZoH5u3ynkUFfagNEml0-usffmrw1FwA25PkxGVsZlqydjK5hyrxksCewvl860xxrNSN2QF5bn0KuDl8GlkGXyAH-UavTFZAEA_x7gyXAB364l8lk9yVizz-lPZiUx50iGMvEvuaY7Xvm-agdnSIeNkmxBc-18nEU3Q4GMqEYaoTWfaP8Xm8455K9lcTtZDZvfjGM7NMX1FdbiEKBqDdXq3wQi_0LG3pcs6XTlXNHpkMQTyWejCWoiEM7JSFwgpjuCK755ebaNaTzjBpvLzKxQsPngsk; gulu_source_res=eyJwX2luIjoiYzI2YmJhYzE0ZTUwZDg3M2I0OGE2ZmEwMGJiODE4NzA5MzQ3N2ZhODY1MmFkYmNjODJkZDcyOWQxOTJhZjhlNCJ9; passport_auth_mix_state=8l4og9sb26rzh2hftp0qbsg9yk1qbcwr43pzbtiz7v15ro2x; playRecommendGuideTagCount=2; totalRecommendGuideTagCount=2; __druidClientInfo=JTdCJTIyY2xpZW50V2lkdGglMjIlM0E2NTYlMkMlMjJjbGllbnRIZWlnaHQlMjIlM0ExMTk5JTJDJTIyd2lkdGglMjIlM0E2NTYlMkMlMjJoZWlnaHQlMjIlM0ExMTk5JTJDJTIyZGV2aWNlUGl4ZWxSYXRpbyUyMiUzQTElMkMlMjJ1c2VyQWdlbnQlMjIlM0ElMjJNb3ppbGxhJTJGNS4wJTIwKFdpbmRvd3MlMjBOVCUyMDEwLjAlM0IlMjBXaW42NCUzQiUyMHg2NCklMjBBcHBsZVdlYktpdCUyRjUzNy4zNiUyMChLSFRNTCUyQyUyMGxpa2UlMjBHZWNrbyklMjBDaHJvbWUlMkYxNDguMC4wLjAlMjBTYWZhcmklMkY1MzcuMzYlMjIlN0Q=; download_guide=%223%2F20260526%2F0%22; FOLLOW_LIVE_POINT_INFO=%22MS4wLjABAAAAJ_bnrSrmp23mvHx_oUo-ZEJd93IvV9uokcDMZD27AcU%2F1779811200000%2F0%2F0%2F1779784016852%22; FOLLOW_NUMBER_YELLOW_POINT_INFO=%22MS4wLjABAAAAJ_bnrSrmp23mvHx_oUo-ZEJd93IvV9uokcDMZD27AcU%2F1779811200000%2F0%2F1779783416853%2F0%22; IsDouyinActive=true; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCSXExbjZuc2FkMVBOYUdQSVo0dHk1Vllpd3hNbE1ka3ZOYi8rNWduMUE0a0NsL3gxblZXUVd5SWFiNjJlY3ljYXg1RGtYTW80a2IyVjRmVk9Td1BBbjg9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; home_can_add_dy_2_desktop=%221%22; odin_tt=66809be22e202e954eda8d0b72f1ccb228a1e58d7352ecefcb24611848a7c2b860607cadfb4d98bc8e7cea16f49a7ee2d3333943ed8a358fc3eca4dee221bf8fcce115b27fc52fb909498033db3faa70; biz_trace_id=f2e98bb0; bd_ticket_guard_client_data_v2=eyJyZWVfcHVibGljX2tleSI6IkJJcTFuNm5zYWQxUE5hR1BJWjR0eTVWWWl3eE1sTWRrdk5iLys1Z24xQTRrQ2wveDFuVldRV3lJYWI2MmVjeWNheDVEa1hNbzRrYjJWNGZWT1N3UEFuOD0iLCJ0c19zaWduIjoidHMuMi5iMWY5YTdhZDgzOTNhYWM5NGMxM2M3ZWJhYzNkMGRlODM4YWIzMTU3Yjg0ODI1OGQwODBlZjljNzUyYTRhNDZlYzRmYmU4N2QyMzE5Y2YwNTMxODYyNGNlZGExNDkxMWNhNDA2ZGVkYmViZWRkYjJlMzBmY2U4ZDRmYTAyNTc1ZCIsInJlcV9jb250ZW50Ijoic2VjX3RzIiwicmVxX3NpZ24iOiJDZUhyR2RWa3hDQlJ6blRRbFhwd3pHa3U1STA1a25xZllNWUNzZng5Y2E0PSIsInNlY190cyI6IiMycGNmUmoxU1RwK3JEd2R4dzR3Z2lLczYrUG83dGxFeEI2c3YwU3RJY0hyM3FJZmNKWE5lbWtFa3pWd2UifQ%3D%3D'

# 从环境变量读取
COOKIE = os.environ.get('DOUYIN_COOKIE', COOKIE)

# 从 config.json 读取
_config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
if os.path.exists(_config_file):
    try:
        with open(_config_file, 'r', encoding='utf-8') as _f:
            _cfg = json.load(_f)
            _cookie_from_file = (_cfg.get('cookie') or '').replace('\n', '').replace('\r', '').strip()
            if _cookie_from_file:
                COOKIE = _cookie_from_file
    except Exception:
        pass

# ===== HTTP 会话 =====
_retry = urllib3.util.retry.Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
_session = requests.Session()
_session.mount('https://', HTTPAdapter(max_retries=_retry))


def _redact(s: str) -> str:
    if not s:
        return ''
    if len(s) > 20:
        return s[:8] + '...' + s[-4:]
    return s


# ===== a_bogus 签名 (纯 Python, 移植自 Rust) =====
_U32_MASK = 0xFFFFFFFF
_IV = (0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
       0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E)
_TJ = tuple([0x79CC4519] * 16 + [0x7A879D8A] * 48)
_S4 = b"Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe="
_S3 = b"ckdp1h4ZKsUB80/Mfvw36XIgR25+WQAlEi7NLboqYTOPuzmFjJnryx9HVGDaStCe"
_WINDOW_ENV_STR = "1536|747|1536|834|0|30|0|0|1536|834|1536|864|1525|747|24|24|Win32"


def _u32(v): return v & _U32_MASK
def _rotl(v, b): b %= 32; return _u32((v << b) | (v >> (32 - b)))
def _p0(v): return _u32(v ^ _rotl(v, 9) ^ _rotl(v, 17))
def _p1(v): return _u32(v ^ _rotl(v, 15) ^ _rotl(v, 23))
def _ff(x, y, z, i): return x ^ y ^ z if i < 16 else (x & y) | (x & z) | (y & z)
def _gg(x, y, z, i): return x ^ y ^ z if i < 16 else (x & y) | ((~x & _U32_MASK) & z)


def sm3_hash(data: bytes) -> bytes:
    state = list(_IV)
    buf = bytearray(data)
    bit_len = len(data) * 8
    buf.append(0x80)
    while len(buf) % 64 != 56:
        buf.append(0)
    buf.extend(bit_len.to_bytes(8, 'big'))
    for offset in range(0, len(buf), 64):
        block = buf[offset:offset + 64]
        w = [0] * 68
        wp = [0] * 64
        for i in range(16):
            w[i] = int.from_bytes(block[i * 4:i * 4 + 4], 'big')
        for i in range(16, 68):
            w[i] = _u32(_p1(w[i - 16] ^ w[i - 9] ^ _rotl(w[i - 3], 15)) ^ _rotl(w[i - 13], 7) ^ w[i - 6])
        for i in range(64):
            wp[i] = w[i] ^ w[i + 4]
        a = list(state)
        for i in range(64):
            ss1 = _rotl(_u32(_rotl(a[0], 12) + a[4] + _rotl(_TJ[i], i)), 7)
            ss2 = ss1 ^ _rotl(a[0], 12)
            tt1 = _u32(_ff(a[0], a[1], a[2], i) + a[3] + ss2 + wp[i])
            tt2 = _u32(_gg(a[4], a[5], a[6], i) + a[7] + ss1 + w[i])
            a[3], a[2], a[1], a[0] = a[2], _rotl(a[1], 9), a[0], tt1
            a[7], a[6], a[5], a[4] = a[6], _rotl(a[5], 19), a[4], _p0(tt2)
        state = [_u32(s + v) for s, v in zip(state, a)]
    return b''.join(w.to_bytes(4, 'big') for w in state)


def rc4_encrypt(plain: bytes, key: bytes) -> bytes:
    s = list(range(256))
    j = 0
    for i in range(256):
        j = (j + s[i] + key[i % len(key)]) & 0xFF
        s[i], s[j] = s[j], s[i]
    i = j = 0
    out = bytearray()
    for b in plain:
        i = (i + 1) & 0xFF
        j = (j + s[i]) & 0xFF
        s[i], s[j] = s[j], s[i]
        out.append(s[(s[i] + s[j]) & 0xFF] ^ b)
    return bytes(out)


def _b64(data: bytes, table: bytes = _S4, pad: bool = True) -> str:
    r, dlen = [], len(data) - (len(data) % 3)
    for off in range(0, dlen, 3):
        n = (data[off] << 16) | (data[off + 1] << 8) | data[off + 2]
        r.append(chr(table[(n >> 18) & 0x3F]))
        r.append(chr(table[(n >> 12) & 0x3F]))
        r.append(chr(table[(n >> 6) & 0x3F]))
        r.append(chr(table[n & 0x3F]))
    rem = len(data) - dlen
    if rem == 1:
        n = data[dlen] << 16
        r.append(chr(table[(n >> 18) & 0x3F]))
        r.append(chr(table[(n >> 12) & 0x3F]))
        if pad:
            r.extend(['=', '='])
    elif rem == 2:
        n = (data[dlen] << 16) | (data[dlen + 1] << 8)
        r.append(chr(table[(n >> 18) & 0x3F]))
        r.append(chr(table[(n >> 12) & 0x3F]))
        r.append(chr(table[(n >> 6) & 0x3F]))
        if pad:
            r.append('=')
    return ''.join(r)


def _gen_random_bytes() -> bytes:
    now = time.time_ns()
    r1 = ((now & _U32_MASK) * 10000) % 10000
    r2 = (((now >> 32) & _U32_MASK) * 10000) % 10000
    r3 = (((now >> 16) & _U32_MASK) * 10000) % 10000

    def mix(v, vm, s, sm): return ((v & vm) | (s & sm)) & 0xFF
    return bytes([
        mix(r1, 0xAA, 3, 0x55), mix(r1, 0x55, 3, 0xAA),
        mix(r1 >> 8, 0xAA, 45, 0x55), mix(r1 >> 8, 0x55, 45, 0xAA),
        mix(r2, 0xAA, 1, 0x55), mix(r2, 0x55, 1, 0xAA),
        mix(r2 >> 8, 0xAA, 0, 0x55), mix(r2 >> 8, 0x55, 0, 0xAA),
        mix(r3, 0xAA, 1, 0x55), mix(r3, 0x55, 1, 0xAA),
        mix(r3 >> 8, 0xAA, 5, 0x55), mix(r3 >> 8, 0x55, 5, 0xAA),
    ])


def _gen_rc4_bb(params: str, ua: str, args: tuple) -> bytes:
    st = int(time.time() * 1000)
    ph2 = sm3_hash(sm3_hash(params.encode()))
    ch2 = sm3_hash(sm3_hash(b'cus'))
    ua_key = bytes([0, 1, args[2] & 0xFF])
    ua_enc = rc4_encrypt(ua.encode(), ua_key)
    ua_enc_str = _b64(ua_enc, _S3, pad=False)
    ua_hash = sm3_hash(ua_enc_str.encode())
    et = int(time.time() * 1000)
    b = bytearray(73)
    b[8] = 3
    b[44:48] = (et & _U32_MASK).to_bytes(4, 'big')
    b[20:24] = (st & _U32_MASK).to_bytes(4, 'big')
    b[26:30] = (args[0] & _U32_MASK).to_bytes(4, 'big')
    b[34:38] = (args[2] & _U32_MASK).to_bytes(4, 'big')
    b[38], b[39] = ph2[21], ph2[22]
    b[40], b[41] = ch2[21], ch2[22]
    b[42], b[43] = ua_hash[23], ua_hash[24]
    b[18] = 44
    b[51] = 6241 >> 8
    b[56], b[57], b[58] = 6383 & 0xFF, 6383 & 0xFF, (6383 >> 8) & 0xFF
    w_env = _WINDOW_ENV_STR.encode()
    b[64], b[65] = len(w_env), len(w_env) & 0xFF
    idxs = (18, 20, 26, 30, 38, 40, 42, 21, 27, 31, 35, 39, 41, 43,
            22, 28, 32, 36, 23, 29, 33, 37, 44, 45, 46, 47, 48, 49,
            50, 24, 25, 52, 53, 54, 55, 57, 58, 59, 60, 65, 66, 70, 71)
    ck = 0
    for i in idxs:
        ck ^= b[i]
    b[72] = ck
    bb = bytearray()
    bb.extend(b[18:19])
    bb.extend(b[20:21])
    bb.extend(b[52:55])
    bb.extend(b[26:59])
    bb.extend(b[38:44])
    bb.extend(b[21:23])
    bb.extend(b[27:38])
    bb.extend(b[44:61])
    bb.extend(b[24:26])
    bb.extend(b[65:67])
    bb.extend(b[70:72])
    bb.extend(w_env)
    bb.append(b[72])
    return rc4_encrypt(bytes(bb), b'y')


def a_bogus_sign(params: str, ua: str, args: tuple = (0, 1, 14)) -> str:
    combined = _gen_random_bytes() + _gen_rc4_bb(params, ua, args)
    return _b64(combined) + '='


# ===== 抖音 API 客户端 =====

class DouyinClient:
    """抖音 API 客户端 (同步版)"""

    HOST = 'https://www.douyin.com'
    UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
          'AppleWebKit/537.36 (KHTML, like Gecko) '
          'Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0')

    # 通用参数 — 与原始项目保持一致
    COMMON_PARAMS = {
        'device_platform': 'webapp',
        'aid': '6383',
        'channel': 'channel_pc_web',
        'update_version_code': '0',
        'pc_client_type': '1',
        'version_code': '190600',
        'version_name': '19.6.0',
        'cookie_enabled': 'true',
        'screen_width': '1680',
        'screen_height': '1050',
        'browser_language': 'zh-CN',
        'browser_platform': 'MacIntel',
        'browser_name': 'Edge',
        'browser_version': '145.0.0.0',
        'browser_online': 'true',
        'engine_name': 'Blink',
        'engine_version': '145.0.0.0',
        'os_name': 'Mac OS',
        'os_version': '10.15.7',
        'cpu_core_num': '8',
        'device_memory': '8',
        'platform': 'PC',
        'downlink': '10',
        'effective_type': '4g',
        'round_trip_time': '50',
        'pc_libra_divert': 'Mac',
        'support_h265': '1',
        'support_dash': '1',
        'disable_rs': '0',
        'need_filter_settings': '1',
        'list_type': 'single',
    }

    COMMON_HEADERS = {
        'User-Agent': UA,
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'sec-ch-ua-platform': '"macOS"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua': '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
        'referer': 'https://www.douyin.com/',
        'priority': 'u=1, i',
        'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'accept': 'application/json, text/plain, */*',
    }

    def __init__(self, cookie: str = ''):
        self.cookie = cookie or ''
        self._webid = None
        self._webid_time = 0

    # ---- WebID 获取 ----

    def _fetch_webid(self) -> str:
        if self._webid and (time.time() - self._webid_time) < 600:
            return self._webid
        try:
            h = self.COMMON_HEADERS.copy()
            h.update({
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'accept': 'text/html,application/xhtml+xml',
            })
            r = _session.get('https://www.douyin.com/?recommend=1', headers=h, timeout=10)
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

    # ---- 核心请求 ----

    def request(self, uri: str, user_params: dict,
                extra_headers: dict = None, method: str = 'GET',
                skip_sign: bool = True) -> tuple:
        """
        发送 API 请求
        返回: (data_dict, success_bool)
        与原始项目的 common_request 行为一致
        """
        # 1. 合并参数: 先用户参数，再通用参数覆盖 (原始: params.update(self.common_params))
        params = dict(user_params)
        params.update(self.COMMON_PARAMS)  # 通用参数优先级更高!

        # 2. 合并请求头
        headers = dict(self.COMMON_HEADERS)
        if extra_headers:
            headers.update(extra_headers)

        # 3. Cookie
        if self.cookie:
            headers['Cookie'] = self.cookie

        # 4. 注入 params: msToken, verifyFp, fp, webid (对应 _deal_params)
        params['msToken'] = self._get_ms_token()
        verify_fp = self._get_verify_fp()
        params['verifyFp'] = verify_fp
        params['fp'] = verify_fp
        # 从 cookie 中读取 screen_width/height
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

        # 5. a_bogus 签名
        if not skip_sign:
            qs = '&'.join(f'{k}={urllib.parse.quote(str(v))}' for k, v in params.items())
            params['a_bogus'] = a_bogus_sign(qs, headers['User-Agent'])

        url = f'{self.HOST}{uri}'
        print(f'[请求] {method} {uri}')
        print(f'[参数] aid={params.get("aid")} '
              f'version={params.get("version_name")} '
              f'webid={webid or "无"} '
              f'abogus={"是" if not skip_sign else "否"}')

        try:
            if method.upper() == 'POST':
                resp = _session.post(url, data=params, headers=headers, timeout=(10, 30))
            else:
                resp = _session.get(url, params=params, headers=headers, timeout=(10, 30))
        except requests.RequestException as e:
            print(f'[错误] 网络请求失败: {e}')
            return {'message': f'网络请求失败: {e}'}, False

        if resp.status_code != 200 or len(resp.content) == 0:
            print(f'[警告] HTTP {resp.status_code}, 内容为空 (可能被风控拦截)')
            return {'message': '请求被拦截，请检查 Cookie 是否有效'}, False

        try:
            data = resp.json()
        except Exception:
            print('[错误] JSON 解析失败')
            return {}, False

        if data.get('status_code', 0) != 0:
            print(f'[错误] API: status_code={data["status_code"]} '
                  f'msg={data.get("status_msg","")}')
            return data, False

        return data, True

    # ---- 获取临时 Cookie ----

    def get_temp_cookie(self) -> str:
        s = requests.Session()
        s.headers.update({
            'User-Agent': self.UA,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'zh-CN,zh;q=0.9',
        })
        try:
            s.get('https://www.douyin.com/', timeout=10)
            cookies = [f'{c.name}={c.value}' for c in s.cookies]
            return '; '.join(cookies)
        except Exception:
            return ''


# ===== 链接解析和视频信息提取 =====

def resolve_share_url(text: str) -> str:
    """从文本提取 URL，并解析 v.douyin.com 短链接"""
    m = re.search(r'https?://[^\s<>"\']+', text)
    if m:
        text = m.group()
    text = re.split(r'[，。！？；、,!;]', text, maxsplit=1)[0].strip().rstrip('，。！？；、,.!;')
    if text.startswith('www.'):
        text = 'https://' + text
    if 'v.douyin.com' in text:
        print(f'[解析] 短链接: {text}')
        try:
            r = _session.get(text, allow_redirects=False, timeout=10, verify=False)
            if r.status_code in (301, 302):
                location = r.headers.get('Location', '')
                if location:
                    print(f'[解析] 重定向 → {location}')
                    return location
        except Exception as e:
            print(f'[解析] 重定向失败: {e}')
    return text


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


def get_video_info(client: DouyinClient, aweme_id: str) -> dict:
    """获取视频详情，提取下载地址"""

    # 第一次: 无 a_bogus (skip_sign=True)
    # 如果失败，再试带 a_bogus
    for use_abogus in [True, False]:
        params = {
            'aweme_id': aweme_id,
            'os': 'windows',
        }
        data, ok = client.request(
            '/aweme/v1/web/aweme/detail/',
            params,
            skip_sign=not use_abogus,
        )
        if ok and data.get('aweme_detail'):
            break
        if use_abogus:
            # already tried both
            pass

    if not ok or not data.get('aweme_detail'):
        print(f'[错误] 获取视频详情失败 (已尝试 {"和".join(["无签名","有签名"][:2])})')
        return {}

    post = data['aweme_detail']
    author = post.get('author') or {}
    video_data = post.get('video') or {}
    music = post.get('music') or {}

    info = {
        'aweme_id': post.get('aweme_id', ''),
        'desc': post.get('desc', ''),
        'author_nickname': author.get('nickname', ''),
        'author_uid': author.get('uid', ''),
        'cover_url': '',
        'video_urls': [],
        'music_url': '',
    }

    # 封面
    cover = video_data.get('cover') or {}
    if cover.get('url_list'):
        info['cover_url'] = cover['url_list'][0]

    # === 无水印视频地址 ===
    candidates = []
    # 从 bit_rate 提取
    for br in video_data.get('bit_rate') or []:
        if not isinstance(br, dict):
            continue
        for key in ('play_addr', 'play_addr_h264'):
            addr = br.get(key) or {}
            for u in (addr.get('url_list') or []):
                if u:
                    candidates.append(u)
    # 从 play_addr 直接提取
    play_addr = video_data.get('play_addr') or {}
    for u in (play_addr.get('url_list') or []):
        if u:
            candidates.append(u)
    # 从 download_addr 提取
    download_addr = video_data.get('download_addr') or {}
    for u in (download_addr.get('url_list') or []):
        if u:
            candidates.append(u)

    # 去水印 + 去重
    seen = set()
    clean = []
    for u in candidates:
        u = u.replace('playwm', 'play').replace('watermark=1', 'watermark=0')
        if u and u not in seen:
            seen.add(u)
            clean.append(u)

    info['video_urls'] = clean
    if clean:
        print(f'[视频] {len(clean)} 个可用地址')
        for i, u in enumerate(clean[:2]):
            print(f'  [{i}] {u[:80]}...')
    else:
        print('[警告] 未找到视频下载地址')

    # === 背景音乐 ===
    if isinstance(music.get('play_url'), dict):
        mu_list = music['play_url'].get('url_list', [])
        if mu_list:
            info['music_url'] = mu_list[0]
            print(f'[音乐] {mu_list[0][:80]}...')
    if not info['music_url'] and music.get('h5_url'):
        info['music_url'] = music['h5_url']

    print(f'[标题] {info["desc"][:60] or "无标题"}')
    print(f'[作者] {info["author_nickname"]}')

    return info


# ===== 文件下载 =====

def download_file(url: str, filepath: str, label: str = '文件') -> bool:
    try:
        os.makedirs(os.path.dirname(filepath) or '.', exist_ok=True)
        print(f'[下载] {label}')
        h = {
            'User-Agent': DouyinClient.UA,
            'Accept': '*/*',
            'Referer': 'https://www.douyin.com/',
            'Range': 'bytes=0-',
        }
        resp = _session.get(url, headers=h, stream=True, timeout=(10, 120))
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
        return True
    except Exception as e:
        print(f'\n[错误] 下载失败: {e}')
        return False


# ===== 主流程 =====

def main():
    # 链接
    raw = sys.argv[1] if len(sys.argv) > 1 else input('请输入抖音分享链接: ').strip()
    if not raw:
        print('请提供链接')
        return

    print('=' * 60)
    print('  抖音视频下载工具 v2')
    print('=' * 60)

    # 1. 解析链接
    url = resolve_share_url(raw)
    aweme_id = extract_aweme_id(url)
    if not aweme_id:
        print(f'[错误] 无法提取视频 ID: {url}')
        return
    print(f'[ID]   {aweme_id}')

    # 2. 初始化客户端
    client = DouyinClient(cookie=COOKIE)
    if not client.cookie:
        c = client.get_temp_cookie()
        if c:
            client.cookie = c
            print(f'[Cookie] 临时 Cookie ({len(c)} 字符)')
        else:
            print('[Cookie] 无 Cookie，API 可能被拦截')
    else:
        print(f'[Cookie] 用户 Cookie ({len(COOKIE)} 字符)')

    # 3. 获取视频信息
    print('-' * 60)
    info = get_video_info(client, aweme_id)
    if not info:
        print('[错误] 获取视频信息失败')
        print('\n提示: 抖音 API 需要有效的登录 Cookie')
        print('请通过以下方式提供 Cookie:')
        print('  1. set DOUYIN_COOKIE=你的cookie（cmd）')
        print('  2. 创建 config.json: {"cookie": "你的cookie"}')
        print('  3. 直接修改 demo.py 中的 COOKIE 变量')
        return

    # 4. 下载视频
    if info.get('video_urls'):
        print('-' * 60)
        safe = re.sub(r'[\\/:*?"<>|]', '_', info['desc'] or f'douyin_{aweme_id}')[:80] or f'douyin_{aweme_id}'
        video_path = f'downloads/{safe}.mp4'
        download_file(info['video_urls'][0], video_path, '视频')
    else:
        print('[跳过] 无视频')

    # 5. 下载音乐
    if info.get('music_url'):
        print('-' * 60)
        safe = re.sub(r'[\\/:*?"<>|]', '_', info['desc'] or f'douyin_{aweme_id}')[:80] or f'douyin_{aweme_id}'
        music_path = f'downloads/{safe}_music.mp3'
        download_file(info['music_url'], music_path, '背景音乐')
    else:
        print('[跳过] 无背景音乐')

    print('=' * 60)
    print('  完成!')
    print('=' * 60)


if __name__ == '__main__':
    main()
