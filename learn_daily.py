# -*- coding: utf-8 -*-
"""한국 바이럴 글/영상 매일 학습 파이프라인 (새벽 1시 크론)
① 커뮤니티 글 학습 (네이버 카페/블로그 — 판매/마케팅 글) 100개+
② 유튜브 한국 바이럴 영상 100개 (yt-dlp 메타)
③ 패턴 추출 → patterns_daily_YYYYMMDD.json
④ 보고서 생성 (요약)

실행: python learn_daily.py
"""
import json
import re
import subprocess
import sys
import time
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / 'data' / 'learning' / 'daily'
OUT.mkdir(parents=True, exist_ok=True)
TODAY = datetime.now().strftime('%Y%m%d')

# ════════════════════════════════════════
# ① 네이버 블로그 바이럴 글 수집 (검색 API 아님 — 시리얼 파싱, 이미 검증된 방식)
# ════════════════════════════════════════
def collect_blog_posts(target=110):
    """네이버 뷰 검색 — 바이럴 키워드 회전, 스마트블록 파싱"""
    sys.path.insert(0, str(BASE))
    import curl_cffi.requests as req
    s = req.Session(impersonate='chrome120')

    queries = [
        '쿠팡 꿀템 후기', '다이소 신상 추천', '무신사 코디 추천',
        '올리브영 리뷰', '인기 가전제품 추천', '여행지 추천 국내',
        '맛집 추천', '운동 루틴 공유', '생활꿀팁 정리', '직장인 꿀템',
        '주방 아이템 추천', '청소 꿀팁', '뷰티 신제품 리뷰', '아기용품 추천',
    ]
    posts = []
    seen = set()
    for q in queries:
        if len(posts) >= target:
            break
        try:
            r = s.get(
                'https://search.naver.com/search.naver',
                params={'where': 'view', 'query': q, 'pd': '4'},  # pd=4: 최근 1주
                timeout=15,
            )
            # 뷰 검색 HTML 내장 JSON 파싱: "title":..., "url": https://blog.naver.com/...
            items = []
            pat = re.compile(r'"title":"([^"]{6,120})","name":"[^"]*","datetime":(\d+)[^}]*?"url":"(https://blog\.naver\.com/[^"]+)"')
            pat2 = re.compile(r'"title":"([^"]{6,120})"[^}]*?"url":"(https://blog\.naver\.com/[^"]+)"')
            seen_titles = set()
            items = []
            for m in pat.finditer(r.text):
                title, ts, url = m.group(1), int(m.group(2)), m.group(3)
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                from datetime import datetime as _dt
                try:
                    d = _dt.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
                except Exception:
                    d = ''
                items.append({'title': title.replace('<b>', '').replace('</b>', ''),
                              'contents': '', 'date': d, 'url': url})
            for m in pat2.finditer(r.text):
                title, url = m.group(1), m.group(2)
                if title in seen_titles or url in [it['url'] for it in items]:
                    continue
                seen_titles.add(title)
                items.append({'title': title, 'contents': '', 'date': '', 'url': url})
                title, ts, url = m.group(1), int(m.group(2)), m.group(3)
                from datetime import datetime as _dt
                try:
                    d = _dt.fromtimestamp(ts / 1000).strftime('%Y-%m-%d')
                except Exception:
                    d = ''
                items.append({'title': title.replace('<b>', '').replace('</b>', ''),
                              'contents': '', 'date': d, 'url': url})
            for it in items:
                title = re.sub(r'<[^>]+>', '', it.get('title', '') or '')
                desc = re.sub(r'<[^>]+>', '', it.get('contents', '') or '')
                date = (it.get('date') or '')[:10].replace('.', '-')
                url = it.get('url') or ''
                if not title or url in seen:
                    continue
                seen.add(url)
                posts.append({'title': title, 'desc': desc[:200], 'date': date,
                              'url': url, 'query': q, 'source': 'blog'})
            time.sleep(random.uniform(1.2, 2.5))
        except Exception:
            continue
    return posts


# ════════════════════════════════════════
# ② 유튜브 한국 바이럴 영상 100개 (yt-dlp flat)
# ════════════════════════════════════════
YT_QUERIES = [
    '쿠팡 꿀템', '다이소 꿀템', '올리브영 추천', '무신사 추천',
    '인기 숏츠 제품', '꿀템 추천 쇼츠', '생활꿀팁 쇼츠', '여행지 추천 쇼츠',
    '맛집 탐방', '직장인 브이로그', '홈트 루틴', '청소 꿀팁 쇼츠',
    'kitchen gadget korea', 'korean product review',
]

def collect_videos(target=100):
    videos = []
    seen = set()
    for q in YT_QUERIES:
        if len(videos) >= target:
            break
        try:
            r = subprocess.run(
                ['yt-dlp', f'ytsearch10:{q}', '--skip-download', '--print',
                 '%(title)s\t%(view_count)s\t%(duration)s\t%(id)s\t%(channel)s',
                 '--no-warnings', '--quiet'],
                capture_output=True, text=True, timeout=90,
                encoding='utf-8', errors='replace')
            for line in (r.stdout or '').strip().split('\n'):
                if not line or len(videos) >= target:
                    break
                parts = line.split('\t')
                if len(parts) < 5:
                    continue
                title, views, dur, vid, ch = parts
                if vid in seen:
                    continue
                seen.add(vid)
                videos.append({
                    'title': title, 'views': int(views) if views and views != 'NA' else 0,
                    'duration': int(dur) if dur and dur != 'NA' else 0,
                    'id': vid, 'channel': ch, 'query': q,
                    'url': f'https://youtube.com/watch?v={vid}',
                })
            time.sleep(random.uniform(1.5, 3.0))
        except Exception:
            continue
    return videos


# ════════════════════════════════════════
# ③ 패턴 추출
# ════════════════════════════════════════
HOOK_PATTERNS = ['추천', '리뷰', '후기', '정리', '최고', '실화', '반전', '필수',
                 '꿀템', '솔직', '직접', '비교', '떡밥', '실사용', '장단점', '브이로그']

def extract_patterns(posts, videos):
    # 제목 훅 분석
    def hooks(items):
        c = Counter()
        for it in items:
            t = it.get('title', '')
            for h in HOOK_PATTERNS:
                if h in t:
                    c[h] += 1
        return c.most_common(8)

    # 숫자 사용률
    def num_rate(items):
        n = sum(1 for it in items if re.search(r'\d', it.get('title', '')))
        return round(n / max(len(items), 1) * 100, 1)

    # 느낌표/물음표
    def punct(items):
        ex = sum(1 for it in items if '!' in it.get('title', ''))
        q = sum(1 for it in items if '?' in it.get('title', ''))
        return {'excl': ex, 'question': q}

    # 영상 길이 분포
    def dur_dist(vs):
        buckets = {'~15s': 0, '16-30s': 0, '31-60s': 0, '60s+': 0}
        for v in vs:
            d = v.get('duration', 0)
            if d <= 15: buckets['~15s'] += 1
            elif d <= 30: buckets['16-30s'] += 1
            elif d <= 60: buckets['31-60s'] += 1
            else: buckets['60s+'] += 1
        return buckets

    top_videos = sorted(videos, key=lambda v: -v.get('views', 0))[:10]
    return {
        'date': TODAY,
        'posts_n': len(posts), 'videos_n': len(videos),
        'blog_hooks': hooks(posts), 'video_hooks': hooks(videos),
        'num_rate': {'blog': num_rate(posts), 'video': num_rate(videos)},
        'punct_blog': punct(posts),
        'video_duration': dur_dist(videos),
        'top_videos': [{'title': v['title'][:40], 'views': v['views']} for v in top_videos],
        'top_queries': Counter([p.get('query', '') for p in posts]).most_common(5),
    }


# ════════════════════════════════════════
# ④ 보고서
# ════════════════════════════════════════
def make_report(p):
    lines = [
        f"📊 바이럴 데일리 학습 보고 ({p['date']})",
        f"수집: 블로그 글 {p['posts_n']}개 / 영상 {p['videos_n']}개",
        "",
        f"[글 훅 TOP] " + ', '.join(f"{k}({v})" for k, v in p['blog_hooks'][:5]),
        f"[영상 훅 TOP] " + ', '.join(f"{k}({v})" for k, v in p['video_hooks'][:5]),
        f"[숫자 제목 비율] 블로그 {p['num_rate']['blog']}% / 영상 {p['num_rate']['video']}%",
        f"[영상 길이 분포] {p['video_duration']}",
        "",
        "[조회수 TOP 영상]",
    ]
    for v in p['top_videos'][:5]:
        lines.append(f"  · {v['title']} — {v['views']:,}회")
    return '\n'.join(lines)


if __name__ == '__main__':
    print(f"[{datetime.now():%H:%M:%S}] ① 블로그 글 수집 시작")
    posts = collect_blog_posts(110)
    print(f"  → {len(posts)}개")
    print(f"[{datetime.now():%H:%M:%S}] ② 유튜브 영상 수집 시작")
    videos = collect_videos(100)
    print(f"  → {len(videos)}개")
    pats = extract_patterns(posts, videos)
    (OUT / f'patterns_{TODAY}.json').write_text(
        json.dumps({'patterns': pats, 'posts': posts, 'videos': videos},
                   ensure_ascii=False, indent=1), encoding='utf-8')
    report = make_report(pats)
    (OUT / f'report_{TODAY}.txt').write_text(report, encoding='utf-8')
    print(report)
    # 종료 코드: 목표 미달 시에도 정상종료 (보고에 반영)
    print(f"\n완료: {OUT / f'patterns_{TODAY}.json'}")
