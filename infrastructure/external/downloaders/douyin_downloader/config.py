"""
全局配置常量
"""

COOKIE = ''

DOUYIN_HOST = 'https://www.douyin.com'

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
      'AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0')

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
