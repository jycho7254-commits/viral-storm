# -*- coding: utf-8 -*-
"""유튜브 보충 수집 — 7,538 → 10,000 (신규 쿼리 조합)"""
import sys
import random
import time
import json as _json
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
from src.learning.collect_corpus import save

# 조합 확장 — 이전과 겹치지 않는 변형
TOPICS_A = ["쿠키런 킹덤", "블루 아카이브", "명일방주", "젠레스 존 제로", "붕괴 3rd", "스타레일", "원신 캐릭터", "배틀그라운드 모바일", "스팀 인디", "로맨스 게임", "보드게임", "VR 게임", "닌텐도 스위치", "플스5 게임", "엑스박스", "FC 온라인", "리니지W", "아이온2", "검은사막", "로스트아크"]
TOPICS_B = ["자켓", "트렌치코트", "니트베스트", "와이드팬츠", "치노팬츠", "셔츠", "맨투맨", "후드집업", "양말", "벨트", "지갑", "선캡", "니트원피스", "스커트", "부츠", "로퍼", "샌들", " ankle"]
TOPICS_C = ["아이폰 17", "갤럭시 S26", "애플워치", "갤럭시워치", "에어팟 프로", "버즈", "아이맥", "맥북", "갤럭시탭", "킨들", "스위치", "PS5", "전기자전거", "전동킥보드", "캠핑텐트", "등산용품", "골프채", "헬스용품", "요가매트", "러닝화"]
TOPICS_D = ["chatgpt", "미드저니", "stable diffusion", "노션 템플릿", "구글 스프레드시트", "엑셀 꿀팁", "포토샵", "프리미어", "피그마", "깃허브", "리눅스", "홈서버", "nas", "iot", "스마트홈", "유튜브 알고리즘", "인스타 마케팅", "블로그 시작"]
MODS = ["리뷰", "후기", "추천", "비교", "꿀팁", "총정리", "브이로그", "언박싱", "장단점", "솔직", "실사용", "구매 가이드", "초보", "2026 최신", "직접 해봄"]

def gen():
    qs = []
    for t in TOPICS_A + TOPICS_B + TOPICS_C + TOPICS_D:
        for m in MODS:
            qs.append(f"{t} {m}")
    random.Random(777).shuffle(qs)
    return qs

def collect(queries):
    items = []
    for q in queries:
        try:
            r = subprocess.run(["yt-dlp", "--dump-json", "--flat-playlist", f"ytsearch12:{q}"],
                               capture_output=True, text=True, timeout=50)
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
                items.append({"id": f"yt_{d.get('id')}", "source": "youtube", "query": q,
                              "title": title[:150], "views": d.get("view_count"),
                              "duration": d.get("duration"),
                              "channel": d.get("channel") or "", 
                              "url": f"https://youtube.com/watch?v={d.get('id')}"})
        except Exception:
            pass
        time.sleep(random.uniform(0.4, 0.9))
    return items

if __name__ == "__main__":
    queries = gen()
    # 목표까지 부족분만
    cur = len(_json.load(open(BASE / "data/ / learning" / "corpus_youtube.json", encoding="utf-8"))) if False else len(_json.load(open(BASE / "data/learning/corpus_youtube.json", encoding="utf-8")))
    need = max(0, 10000 - cur)
    print(f"현재 {cur}건 → 보충 목표 {need}건 (쿼리 풀 {len(queries)})")
    est_per_q = 8  # 중복 감안
    use = queries[:int(need / est_per_q) + 50]
    print(f"사용 쿼리 {len(use)}개")
    B = 40
    total = cur
    for i in range(0, len(use), B):
        items = collect(use[i:i+B])
        e, n = save("corpus_youtube.json", items)
        total = e + n
        print(f"[보충] 배치 {i//B+1} → 누적 {total}")
        if total >= 10000:
            print("목표 달성!")
            break
    print(f"최종: {total}")
