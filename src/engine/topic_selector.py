# -*- coding: utf-8 -*-
"""
GMI → 바이럴 피드백: 게임 마켓 인사이트 데이터에서
'지금 쓸 만한 게임'을 자동 선정하는 토픽 셀렉터.

점수 구성 (0~100):
  - 랭킹 상위 (rank <= 20): 최대 30점 (1위=30, 20위=15 선형)
  - 뉴스 볼륨 (최근 7일): 최대 30점 (개당 5점, 6개 이상 상한)
  - 이슈성(평점 갭): 최대 25점 — 랭킹 높은데 평점 낮으면 화제성(논쟁) 후보
  - 신규/이벤트: 최대 15점 — 최근 30일 내 뉴스에 '출시/업데이트/이벤트' 키워드

이미 발행한 게임(최근 14일)은 페널티 -40점 → 같은 게임 연속 방지.
"""
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta

GMI_DATA = r'C:\Users\user\Desktop\game_dashboard_v2\data'
VIRAL_DB = r'C:\Users\user\Desktop\viral-storm\data\viral_storm.db'
OUTPUT = r'C:\Users\user\Desktop\viral-storm\data\topic_suggestion.json'

HOT_KEYWORDS = ['출시', '업데이트', '이벤트', '사전등록', '오픈', '신규', '협업', '콜라보']


def load_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def recent_published_games(days=14):
    """최근 N일 내 발행한 게임 목록 (캠페인에서 추출)"""
    if not os.path.exists(VIRAL_DB):
        return set()
    conn = sqlite3.connect(VIRAL_DB)
    c = conn.cursor()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    try:
        c.execute("SELECT game_name FROM campaigns WHERE created_at >= ?", (cutoff,))
        return {r[0] for r in c.fetchall()}
    except Exception:
        return set()
    finally:
        conn.close()


def news_volume():
    """최근 7일 뉴스를 게임명별로 집계 + 핫키워드 히트수"""
    news = load_json(os.path.join(GMI_DATA, 'kr_news.json')) or []
    cutoff = datetime.now() - timedelta(days=7)
    vol = {}
    for n in news:
        try:
            d = datetime.strptime(n.get('date', ''), '%Y-%m-%d')
        except ValueError:
            continue
        if d < cutoff:
            continue
        title = n.get('title', '')
        vol.setdefault('__all__', []).append(title)
    return vol


def score_games():
    rk = load_json(os.path.join(GMI_DATA, 'kr_rankings.json')) or []
    news = load_json(os.path.join(GMI_DATA, 'kr_news.json')) or []
    cutoff7 = datetime.now() - timedelta(days=7)
    done = recent_published_games()

    # 뉴스 타이틀 매칭용
    news_recent = []
    for n in news:
        try:
            if datetime.strptime(n.get('date', ''), '%Y-%m-%d') >= cutoff7:
                news_recent.append(n.get('title', ''))
        except ValueError:
            pass

    results = []
    for g in rk[:30]:  # 상위 30개만 평가
        name = g.get('title', '')
        local = g.get('local_name', '') or name
        rank = g.get('rank', 99)
        rating = g.get('rating', None)

        # 랭킹 점수 (30~15)
        s_rank = max(0, 30 - (rank - 1) * 0.75) if rank <= 20 else 0

        # 뉴스 매칭 (30점)
        matched = [t for t in news_recent if name in t or local in t]
        s_news = min(30, len(matched) * 5)

        # 이슈성: 랭킹 상위 + 평점 낮음 (25점)
        s_issue = 0
        hooks = []
        if rating is not None and isinstance(rating, (int, float)) and 0 < rating < 5:
            if rank <= 10:
                gap = (5 - rating) / 5  # 0~1
                s_issue = round(25 * min(1, gap * 1.6))
                if rating < 3 and rank <= 10:
                    hooks.append(f'매출 {rank}위인데 평점 {rating}')
        # 신규/이벤트 (15점)
        s_hot = 0
        for t in matched:
            if any(k in t for k in HOT_KEYWORDS):
                s_hot = 15
                hooks.append('최근 출시/이벤트 뉴스')
                break

        total = s_rank + s_news + s_issue + s_hot
        if name in done:
            total -= 40
            hooks.append('최근 발행 이력 페널티')

        if total <= 0:
            continue
        results.append({
            'name': name,
            'local_name': local,
            'developer': g.get('developer', ''),
            'app_id': g.get('app_id', ''),
            'rank': rank,
            'rating': rating,
            'news_7d': len(matched),
            'score': round(total, 1),
            'hooks': hooks[:3],
            'suggested_angle': build_angle(name, rank, rating, hooks),
        })

    results.sort(key=lambda x: -x['score'])
    return results[:5]


def build_angle(name, rank, rating, hooks):
    if rating and rating < 3 and rank <= 10:
        return f"'{name}' 매출 {rank}위 vs 평점 {rating} — 왜 갈리는지 직접 해본 후기"
    if '최근 출시/이벤트 뉴스' in (hooks or []):
        return f"'{name}' 요즘 이슈 — 출시/업데이트 직접 체험 후기"
    return f"'{name}' {rank}위 인기 게임 솔직 후기"


def export_feedback():
    """바이럴 → GMI 피드백: 발행 이력을 GMI data에 내보내기"""
    if not os.path.exists(VIRAL_DB):
        return None
    conn = sqlite3.connect(VIRAL_DB)
    c = conn.cursor()
    c.execute('''SELECT c2.game_name, c1.text, c1.status, c1.post_url, c1.posted_at, c1.char_count
                 FROM content c1 JOIN campaigns c2 ON c1.campaign_id = c2.id
                 WHERE c1.status = 'posted' ORDER BY c1.posted_at DESC''')
    posts = [{'game': r[0], 'text_preview': (r[1] or '')[:80], 'status': r[2],
              'url': r[3], 'posted_at': r[4], 'chars': r[5]} for r in c.fetchall()]
    conn.close()
    out = {'updated': datetime.now().isoformat(), 'posts': posts}
    with open(os.path.join(GMI_DATA, 'viral_activity.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return len(posts)


if __name__ == '__main__':
    sugg = score_games()
    print(f'=== 오늘의 추천 토픽 ({datetime.now():%m-%d %H:%M}) ===')
    for i, s in enumerate(sugg, 1):
        print(f"{i}. [{s['score']}점] {s['name']} ({s['local_name']}) — 랭킹 {s['rank']}위, 평점 {s['rating']}, 뉴스 {s['news_7d']}건")
        print(f"   앵글: {s['suggested_angle']}")
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({'generated': datetime.now().isoformat(), 'suggestions': sugg}, f, ensure_ascii=False, indent=2)
    n = export_feedback()
    print(f'GMI 피드백 내보냄: 발행 {n}건')
