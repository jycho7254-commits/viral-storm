# -*- coding: utf-8 -*-
"""한국 제품+게임 바이럴 유튜브 100개 학습 (09-04)
쿼리: 한국 게임(트릭컬 등) + 한국 제품(쿠팡 꿀템 등) × 수식어
yt-dlp flat-playlist로 메타만 → 100개 확보 → 분석
"""
import subprocess, json, os, time, random, re

OUT = 'data/learning/kr_viral_100.json'

QUERIES = [
    # 게임 바이럴 (한국)
    "트릭컬 미니게임천국 쇼츠",
    "트릭컬 광고",
    "에픽세븐 쇼츠",
    "닉네임 쇼츠 광고",
    "블루 아카이브 쇼츠",
    "원신 한국 쇼츠",
    "게임 광고 못참지",
    "모바일게임 광고 속보",
    # 제품 바이럴 (한국)
    "쿠팡 꿀템 쇼츠",
    "쿠팡 숏츠 추천",
    "꿀템 추천 쇼츠",
    "다이소 꿀템 쇼츠",
    "무신사 코디 쇼츠",
    "나이키 에어포스 한국",
    "신발 브이로그 한국",
    "광고 못참는 상품",
    "이거 사고 후회 안함",
    "리뷰 쇼츠 제품",
]

def search(query, limit=8):
    cmd = ['yt-dlp', '--dump-json', '--flat-playlist', '--no-warnings',
           f'ytsearch{limit}:{query}']
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    items = []
    for line in r.stdout.strip().split('\n'):
        if not line:
            continue
        try:
            d = json.loads(line)
            if d.get('id') and d.get('duration') and (d.get('duration') or 0) <= 65:  # 쇼츠/짧은 영상만
                items.append({
                    'id': d['id'], 'title': d.get('title', ''),
                    'dur': d.get('duration'), 'views': d.get('view_count'),
                    'q': query,
                })
        except Exception:
            pass
    return items

existing = {}
if os.path.exists(OUT):
    existing = {v['id']: v for v in json.load(open(OUT, encoding='utf-8'))}

collected = dict(existing)
for q in QUERIES:
    try:
        got = search(q, 8)
        new = 0
        for v in got:
            if v['id'] not in collected:
                v['views'] = v['views'] or 0
                collected[v['id']] = v
                new += 1
        print(f"[{q}] +{new} (총 {len(collected)})")
    except Exception as e:
        print(f"[{q}] 실패: {str(e)[:50]}")
    time.sleep(random.uniform(0.6, 1.2))
    if len(collected) >= 100:
        break

rows = list(collected.values())[:110]
json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"\n최종 저장: {len(rows)}개 → {OUT}")
