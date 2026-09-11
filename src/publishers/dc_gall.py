# -*- coding: utf-8 -*-
"""DC인사이드 갤러리 발행기 — Webshare 프록시 경유

주의: DC는 비로그인 글쓰기 불가 — 고정닉/유동닉 쿠키 필요
쿠키 확보: config/dc_session.json {"cookies": {"...": "..."}}
"""
import json
import random
import re
import time
from pathlib import Path

import curl_cffi.requests as req

BASE = Path(__file__).resolve().parents[2]
POOL = BASE / 'config' / 'proxy_pool.json'


def get_proxy(idx: int = None) -> str:
    if not POOL.exists():
        return None
    pool = json.loads(POOL.read_text())
    return random.choice(pool) if idx is None else pool[idx % len(pool)]


def publish(text: str, title: str = None, gallery: str = 'viral', proxy: str = None) -> str:
    """DC 갤러리 글쓰기 — 성공 시 글 URL 반환"""
    proxy = proxy or get_proxy()
    if not proxy:
        raise RuntimeError('프록시 없음 — config/proxy_pool.json')

    sess_f = BASE / 'config' / 'dc_session.json'
    cookies = {}
    if sess_f.exists():
        cookies = json.loads(sess_f.read_text()).get('cookies', {})

    s = req.Session(impersonate='chrome120', proxies={'http': proxy, 'https': proxy})

    # 1) 글쓰기 페이지에서 폼 토큰 획득
    r = s.get(f'https://gall.dcinside.com/board/write/', params={'id': gallery},
              cookies=cookies, timeout=20,
              headers={'Referer': f'https://gall.dcinside.com/board/lists/?id={gallery}'})
    m = re.search(r'name="block_no"\s*value="([^"]*)"', r.text) or re.search(r'ci_t\s*=\s*[\'"]([^\'"]+)', r.text)
    if r.status_code != 200:
        raise RuntimeError(f'글쓰기 페이지 {r.status_code} — 프록시 차단 가능')

    # 2) 발행
    data = {
        'id': gallery,
        'subject': title or text[:40],
        'memo': text,
        'mode': 'write',
    }
    r2 = s.post('https://gall.dcinside.com/board/write/', params={'id': gallery},
                data=data, cookies=cookies, timeout=25,
                headers={'Referer': f'https://gall.dcinside.com/board/write/?id={gallery}',
                         'Origin': 'https://gall.dcinside.com'})
    # 성공: 리다이렉트/새글 확인
    if r2.status_code == 200:
        if 'window.location' in r2.text or 'no' in r2.url:
            m2 = re.search(r'gall\.dcinside\.com/board/view/\?id=[\w]+&no=(\d+)', r2.text)
            if m2:
                return f'https://gall.dcinside.com/board/view/?id={gallery}&no={m2.group(1)}'
            return f'https://gall.dcinside.com/board/lists/?id={gallery}'
    raise RuntimeError(f'발행 응답 {r2.status_code} — 캡챠/로그인 필요 가능')


if __name__ == '__main__':
    import sys
    gal = sys.argv[1] if len(sys.argv) > 1 else 'viral'
    txt = sys.argv[2] if len(sys.argv) > 2 else '테스트 글입니다'
    print(publish(txt, gallery=gal))
