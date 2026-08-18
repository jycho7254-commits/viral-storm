# -*- coding: utf-8 -*-
"""
대량 코퍼스 확장 — 네이버 1만건 / 유튜브 1만건 목표
쿼리를 조합 생성해서 collect_corpus의 수집기 재사용 (idempotent 저장)
"""
import sys
import random
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

from src.learning.collect_corpus import collect_naver_blog, collect_youtube, save

# ── 쿼리 생성기 ──────────────────────────────
GAME_TOPICS = ["리니지M", "트릭컬 리바이브", "원신", "붕괴 스타레일", "니케", "로블록스", "로얄매치", "킹샷", "라스트워", "마비노기", "메이플스토리", "쿠키런", "블루아카이브", "명일방주", "젠레스", "우마무스메", "브롤스타즈", "클래시로얄", "서든어택", "발로란트", "리그오브레전드", "배틀그라운드", "스팀게임", "인디게임", "모바일게임", "캐주얼게임", "RPG게임"]
FASHION_TOPICS = ["나이키 에어포스", "아디다스 삼선", "무신사 후드", "코듀로이 자켓", "슬랙스", "청바지 코디", "오버사이즈 티", "겨울 패딩", "여름 원피스", "구두 추천", "스니커즈", "백팩", "가방 추천", "시계 추천", "선글라스", "모자 코디", "레더자켓", "니트"]
BEAUTY_TOPICS = ["다이슨 에어랩", "선크림 추천", "토너 추천", "클렌징폼", "세럼 추천", "마스크팩", "쿠션 추천", "립틴트", "향수 추천", "샴푸 추천", "드라이기"]
PRODUCT_TOPICS = ["아이패드", "갤럭시 폰", "아이폰 케이스", "무선이어폰", "블루투스 스피커", "노트북 거치대", "게이밍마우스", "기계식키보드", "모니터암", "캠핑의자", "캐리어", "무선청소기", "공기청정기", "커피머신", "전기밥솥", "안마의자", "레저매트", "운동화"]
SITE_TOPICS = ["무료 사이트", "유용한 사이트", "작업 사이트", "디자인 툴", "AI 사이트", "번역 사이트", "PDF 변환", "이미지 편집", "동영상 편집", "노션 사용법", "ChatGPT 사용법", "클라우드 저장"]
PLACE_TOPICS = ["강남 카페", "홍대 맛집", "부산 여행", "제주 숙소", "경주 여행", "스키장", "워터파크", "골프장", "찜질방", "박물관", "전시회", "놀이공원"]
FOOD_TOPICS = ["맛집 후기", "레시피", "다이어트 식단", "간식 추천", "커피 원두", "와인 추천", "위스키", "맥주 추천", "반찬", "도시락"]

MODIFIERS = ["후기", "추천", "리뷰", "진짜", "솔직 후기", "찐후기", "내돈내산", "가성비", "비교", "순위", "best", "2026", "최신"]

def gen_queries(topics, mods, limit):
    qs = []
    for t in topics:
        for m in mods:
            qs.append(f"{t} {m}")
    random.Random(42).shuffle(qs)
    return qs[:limit]


def run_naver(target=10000):
    """네이버 1만건 — 쿼리당 ~15-25건 → 550개 쿼리"""
    all_topics = GAME_TOPICS + FASHION_TOPICS + BEAUTY_TOPICS + PRODUCT_TOPICS + SITE_TOPICS + PLACE_TOPICS + FOOD_TOPICS
    queries = gen_queries(all_topics, MODIFIERS, 600)
    print(f"네이버 쿼리 {len(queries)}개 → 목표 {target}")
    total = 0
    batch = 40
    for i in range(0, len(queries), batch):
        chunk = queries[i:i+batch]
        items = collect_naver_blog(chunk, per_query=25)
        e, n = save("corpus_naver.json", items)
        total = e + n
        print(f"[네이버] 배치 {i//batch+1}/{(len(queries)+batch-1)//batch} → 누적 {total}")
        if total >= target:
            print("목표 달성 조기 종료")
            break
    print(f"네이버 최종: {total}")


def run_youtube(target=10000):
    """유튜브 1만건 — 쿼리당 ~10-20건 → 600개 쿼리"""
    all_topics = GAME_TOPICS + FASHION_TOPICS + BEAUTY_TOPICS + PRODUCT_TOPICS + SITE_TOPICS + PLACE_TOPICS + FOOD_TOPICS
    queries = gen_queries(all_topics, MODIFIERS + ["브이로그", "언박싱", "꿀팁", "총정리", "실패", "구매"], 600)
    print(f"유튜브 쿼리 {len(queries)}개 → 목표 {target}")
    total = 0
    batch = 30
    for i in range(0, len(queries), batch):
        chunk = queries[i:i+batch]
        items = collect_youtube_with_queries(chunk)
        e, n = save("corpus_youtube.json", items)
        total = e + n
        print(f"[유튜브] 배치 {i//batch+1}/{(len(queries)+batch-1)//batch} → 누적 {total}")
        if total >= target:
            print("목표 달성 조기 종료")
            break
    print(f"유튜브 최종: {total}")


def collect_youtube_with_queries(queries):
    """collect_corpus.collect_youtube를 쿼리 주입형으로 (per_query=15)"""
    import json as _json
    import subprocess
    all_items = []
    for q in queries:
        try:
            r = subprocess.run(
                ["yt-dlp", "--dump-json", "--flat-playlist", f"ytsearch15:{q}"],
                capture_output=True, text=True, timeout=60,
            )
            for line in r.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    d = _json.loads(line)
                except Exception:
                    continue
                title = (d.get("title") or "").strip()
                if not title:
                    continue
                all_items.append({
                    "id": f"yt_{d.get('id')}",
                    "source": "youtube",
                    "query": q,
                    "title": title[:150],
                    "views": d.get("view_count"),
                    "duration": d.get("duration"),
                    "channel": d.get("channel") or d.get("uploader") or "",
                    "url": f"https://youtube.com/watch?v={d.get('id')}",
                })
        except Exception:
            pass
        time.sleep(random.uniform(0.5, 1.2))
    return all_items


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    if mode in ("naver", "both"):
        run_naver()
    if mode in ("yt", "both"):
        run_youtube()
