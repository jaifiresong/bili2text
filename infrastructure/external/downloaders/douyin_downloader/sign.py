"""
a_bogus 签名算法模块

包含 SM3 哈希、RC4 加密、自定义 Base64 编码以及 a_bogus 参数生成。
所有算法均为纯 Python 实现，移植自 Rust。
"""

import time

_U32_MASK = 0xFFFFFFFF
_IV = (0x7380166F, 0x4914B2B9, 0x172442D7, 0xDA8A0600,
       0xA96F30BC, 0x163138AA, 0xE38DEE4D, 0xB0FB0E4E)
_TJ = tuple([0x79CC4519] * 16 + [0x7A879D8A] * 48)
_S4 = b"Dkdpgh2ZmsQB80/MfvV36XI1R45-WUAlEixNLwoqYTOPuzKFjJnry79HbGcaStCe="
_S3 = b"ckdp1h4ZKsUB80/Mfvw36XIgR25+WQAlEi7NLboqYTOPuzmFjJnryx9HVGDaStCe"
_WINDOW_ENV_STR = "1536|747|1536|834|0|30|0|0|1536|834|1536|864|1525|747|24|24|Win32"


def _u32(v):
    return v & _U32_MASK


def _rotl(v, b):
    b %= 32
    return _u32((v << b) | (v >> (32 - b)))


def _p0(v):
    return _u32(v ^ _rotl(v, 9) ^ _rotl(v, 17))


def _p1(v):
    return _u32(v ^ _rotl(v, 15) ^ _rotl(v, 23))


def _ff(x, y, z, i):
    return x ^ y ^ z if i < 16 else (x & y) | (x & z) | (y & z)


def _gg(x, y, z, i):
    return x ^ y ^ z if i < 16 else (x & y) | ((~x & _U32_MASK) & z)


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

    def mix(v, vm, s, sm):
        return ((v & vm) | (s & sm)) & 0xFF

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
