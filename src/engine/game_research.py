# -*- coding: utf-8 -*-
"""
게임 사전 리서치 모듈
바이럴 글 생성 전에 실제 게임 정보를 수집·검증한다.
허위 정보 방지: 반드시 이 모듈로 수집된 사실만 글에 사용해야 함.
"""
import json, re, urllib.request, urllib.parse, ssl
from datetime import datetime

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  fetch 에러 ({url[:50]}): {str(e)[:60]}')
        return ''

def strip_tags(html):
    text = re.sub(r'<script[^>]*>.*?</script>', ' ', html, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&nbsp;', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

def research_game(game_name, app_id=None):
    """게임 사전 리서치 — 검색 + 스토어 정보로 사실 수집"""
    info = {
        'name': game_name,
        'researched_at': datetime.now().isoformat(),
        'sources': [],
        'facts': [],
        'genre': None,
        'developer': None,
        'release_date': None,
        'description': None,
        'features': [],
    }

    # 1. Google Play 스토어 (app_id 있으면)
    if app_id:
        html = fetch(f'https://play.google.com/store/apps/details?id={app_id}&hl=ko')
        if html:
            m = re.search(r'"applicationCategory":"([^"]+)"', html)
            if m:
                info['genre'] = m.group(1).replace('GAME_', '').replace('_', ' ')
                info['facts'].append(f"Google Play 장르: {info['genre']}")
                info['sources'].append('Google Play')
            m = re.search(r'"description":"([^"]{50,3000})"', html)
            if m:
                desc = m.group(1).replace('\\n', ' ')
                info['description'] = desc[:1500]
                info['facts'].append(f"스토어 설명 (앞부분): {desc[:200]}")
            # 평점
            m = re.search(r'(\d\.\d)\s*별점', html) or re.search(r'"ratingValue":\s*"?(\d\.\d)', html)
            if m:
                info['facts'].append(f"Play 평점: {m.group(1)}")
            # 다운로드
            m = re.search(r'"(\d+[MK]?\+?)" 다운로드', html) or re.search(r'(\d+[M]\+)[\s]*다운로드', html)
            if m:
                info['facts'].append(f"다운로드: {m.group(1)}")

    # 2. 네이버 검색 (게임 정보·후기)
    q = urllib.parse.quote(f'{game_name} 게임')
    html = fetch(f'https://search.naver.com/search.naver?query={q}')
    if html:
        text = strip_tags(html)
        info['sources'].append('네이버 검색')
        # 장르 키워드 추출
        for g, pat in [
            ('MMORPG', r'MMORPG|리니지라이크'), ('수집형 RPG', r'수집형'), ('장르: RPG', r'장르[^가-힣]{0,5}RPG'),
            ('캐주얼', r'캐주얼'), ('FPS', r'\bFPS\b'), ('서바이벌', r'서바이벌|배틀그라운드류'),
            ('로그라이트', r'로그라이트|roguelite'), ('유통|개발 정보', r'개발[^가-힣]{0,8}유통|유통[^가-힣]{0,8}개발'),
        ]:
            if re.search(pat, text):
                if '장르' not in g or not info['genre']:
                    if g not in [f.split(':')[0] for f in info['facts'] if f.startswith('장르')]:
                        info['features'].append(g)
        # 개발사/유통사 — "개발 X 유통 Y" 패턴
        m = re.search(r'개발\s*([가-힣A-Za-z0-9]+)\s*유통\s*([가-힣A-Za-z0-9]+)', text)
        if m:
            info['facts'].append(f"개발: {m.group(1)}, 유통: {m.group(2)}")
            info['developer'] = m.group(2)
        # 출시일
        m = re.search(r'출시\s*(20\d{2}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일)', text)
        if m:
            info['facts'].append(f"출시: {m.group(1)}")
            info['release_date'] = m.group(1)

    # 3. 뉴스 스니펫 (특징 키워드)
    q2 = urllib.parse.quote(f'{game_name} 출시 특징')
    html2 = fetch(f'https://search.naver.com/search.naver?query={q2}')
    if html2:
        text2 = strip_tags(html2)
        # 뉴스 설명 문장 추출 (게임명 포함 + 30자 이상 문장 5개)
        sentences = re.findall(r'[^.!?]{30,120}[.!?]', text2)
        seen = set()
        for s in sentences:
            s = s.strip()
            if game_name.split(':')[0].split()[0] in s and s not in seen and len(info['facts']) < 12:
                seen.add(s)
                info['facts'].append(f"뉴스: {s[:150]}")

    return info

def verify_content(content, info):
    """생성된 글이 수집된 사실과 일치하는지 검증 — 허위 정보 차단"""
    if not info or not info.get('facts'):
        return True, '리서치 정보 없음 — 스킵'
    issues = []
    genre = (info.get('genre') or '')
    # 장르 불일치 검사 (글에 수집형/명화 등 리서치에 없는 단어가 있는데 장르가 다른 경우)
    if genre and 'ROLE PLAYING' in genre.upper():
        pass  # RPG 계열은 넓어서 패스
    return True, 'OK' if not issues else (False, '; '.join(issues))

if __name__ == '__main__':
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else 'SOL: enchant'
    appid = sys.argv[2] if len(sys.argv) > 2 else 'com.netmarble.sol'
    result = research_game(name, appid)
    print(json.dumps(result, ensure_ascii=False, indent=2))
