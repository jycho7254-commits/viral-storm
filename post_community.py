# -*- coding: utf-8 -*-
"""커뮤니티 자유 발행기 — 원하는 커뮤니티에 직접 글 올리기

지원 채널:
  - naver_blog  : 네이버 블로그 (세션 기반 — 이미 검증됨)
  - dc          : DC인사이드 갤러리 (프록시 필요)
  - naver_cafe  : 네이버 카페 (세션 기반)
  - fmkorea     : FM코리아 (세션 필요)

사용:
  python post_community.py --channel naver_blog --title "제목" --text "내용"
  python post_community.py --channel dc --gallery basketball --title "제목" --text "내용"
  python post_community.py --list   # 발행 가능 채널 상태
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE / 'data' / 'viral_storm.db'
sys.path.insert(0, str(BASE))


def load_session(name: str):
    p = BASE / 'config' / f'{name}.json'
    if p.exists():
        return json.loads(p.read_text(encoding='utf-8'))
    return None


# ════════════════════════════════════════
# 채널별 발행기
# ════════════════════════════════════════
def post_naver_blog(title: str, text: str) -> dict:
    """네이버 블로그 — 세션 발행 (기존 검증 파이프라인 재사용)"""
    try:
        from src.publishers.naver_blog import publish
        url = publish(text, title=title)
        return {'ok': True, 'url': url}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:120]}


def post_dc(gallery: str, title: str, text: str, proxy: str = None) -> dict:
    """DC인사이드 — 글쓰기 API (프록시 필수)
    proxy 예: http://user:pass@host:port
    """
    if not proxy:
        proxy = (BASE / 'config' / 'proxy.txt').read_text(encoding='utf-8').strip() \
            if (BASE / 'config' / 'proxy.txt').exists() else None
    if not proxy:
        return {'ok': False, 'error': '프록시 미설정 — config/proxy.txt 또는 --proxy'}
    try:
        import curl_cffi.requests as req
        s = req.Session(impersonate='chrome120', proxies={'https': proxy, 'http': proxy})
        sess = load_session('dc_session')
        if not sess:
            return {'ok': False, 'error': 'config/dc_session.json 없음 — 로그인 쿠키 필요'}
        # DC 글쓰기 ( 갤러리 API )
        r = s.post(
            f'https://gall.dcinside.com/board/write/',
            params={'id': gallery},
            data={'subject': title, 'memo': text, 'mode': 'write'},
            cookies=sess.get('cookies', {}),
            timeout=20,
        )
        if r.status_code == 200 and 'window.location' in r.text:
            return {'ok': True, 'url': f'https://gall.dcinside.com/board/list/?id={gallery}'}
        return {'ok': False, 'error': f'응답 {r.status_code} — 캡챠/차단 가능'}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:120]}


def post_naver_cafe(cafe_id: str, menu_id: str, title: str, text: str) -> dict:
    """네이버 카페 글쓰기 — 세션 필요"""
    sess = load_session('naver_session')
    if not sess:
        return {'ok': False, 'error': 'config/naver_session.json 없음'}
    try:
        import curl_cffi.requests as req
        s = req.Session(impersonate='chrome120')
        r = s.post(
            f'https://cafe.naver.com/ArticleWrite.nhn',
            params={'clubid': cafe_id, 'menuid': menu_id},
            data={'subject': title, 'content': text},
            cookies=sess if isinstance(sess, dict) else {},
            timeout=20,
        )
        return {'ok': r.status_code == 200, 'status': r.status_code}
    except Exception as e:
        return {'ok': False, 'error': str(e)[:120]}


# ════════════════════════════════════════
# DB 기록
# ════════════════════════════════════════
def record(channel: str, title: str, result: dict):
    con = sqlite3.connect(DB)
    con.execute(
        "INSERT INTO content(platform, kind, text, status, post_url, created_at) "
        "VALUES(?,?,?,?,?,datetime('now','localtime'))",
        (channel, 'manual', title[:100],
         'posted' if result.get('ok') else 'failed',
         result.get('url', result.get('error', ''))[:200]),
    )
    con.commit()
    con.close()


CHANNELS = {
    'naver_blog': {'fn': lambda a: post_naver_blog(a.title, a.text), 'ready': True},
    'dc': {'fn': lambda a: post_dc(a.gallery, a.title, a.text, a.proxy), 'ready': '프록시+세션 필요'},
    'naver_cafe': {'fn': lambda a: post_naver_cafe(a.cafe, a.menu, a.title, a.text), 'ready': '카페ID+세션 필요'},
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--channel', choices=CHANNELS.keys())
    ap.add_argument('--title', default='')
    ap.add_argument('--text', required=False)
    ap.add_argument('--gallery', default='basketball', help='DC 갤러리 id')
    ap.add_argument('--cafe', default='', help='네이버 카페 clubid')
    ap.add_argument('--menu', default='', help='카페 menuid')
    ap.add_argument('--proxy', default=None)
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()

    if a.list:
        print('발행 채널:')
        for k, v in CHANNELS.items():
            print(f'  {k:12s} — {"✅ 즉시 가능" if v["ready"] is True else "⏳ " + v["ready"]}')
        return

    if not a.channel or not a.text:
        print('--channel, --text 필수 (자세히: post_community.py -h)')
        return

    ch = CHANNELS[a.channel]
    result = ch['fn'](a)
    record(a.channel, a.title or '(제목없음)', result)
    status = '✅ 발행 성공' if result.get('ok') else f"❌ {result.get('error')}"
    print(f"[{datetime.now():%H:%M:%S}] {a.channel} → {status}")
    if result.get('url'):
        print('  URL:', result['url'])


if __name__ == '__main__':
    main()
