# -*- coding: utf-8 -*-
"""실제 바이럴 마케팅 영상 1000개 수집 — 쿠팡 꿀템/파트너스/숏츠 마케팅
yt-dlp flat-playlist로 메타데이터 (제목/조회수/길이/채널)
"""
import json
import random
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "data" / "learning" / "viral_videos.json"

QUERIES = [
    # 쿠팡 계열
    "쿠팡 꿀템", "쿠팡 파트너스", "쿠팡 숏츠", "쿠팡 리뷰", "쿠팡 찐템",
    "쿠팡 저렴한 꿀템", "쿠팡 갓성비", "쿠팡 인생템", "쿠팡 5000원 템", "쿠팡 만원 템",
    "쿠팡 실사용 후기", "쿠팡 살만한템", "쿠팡 추천 숏츠", "쿠팡 브이로그", "쿠팡 하울",
    # 꿀템/갓성비 계열
    "꿀템 추천", "꿀템 숏츠", "갓성비 후기", "인생템 추천", "이거 사지마",
    "돈내 아깝지 않은", "가성비 템", "리뷰 숏츠", "언박싱 숏츠", "신박한 템",
    "1만원 꿀템", "5000원 이하", "최강 가성비", "숏츠 리뷰", "짧은 리뷰",
    "살까말까", "직접 써봄", "실사용 후기 숏츠", "검증된 꿀템", "광고 아니고 진짜",
    # 마케팅/바이럴 스타일
    "제품 홍보 숏츠", "마케팅 숏츠", "제품 소개 영상", "아이템 추천", "템추",
    "인스타 꿀템", "믿고 사는", "재구매 템", "스마트스토어 제품", "제품 리뷰 영상",
    "쇼핑 숏츠", "구매 후기", "개봉기", "제품 비교", "이거 몰랐지",
    "숏츠 마케팅", "제품 광고", "브랜드 홍보", "신제품 소개", "인기 템",
    # 게임/앱 마케팅 숏츠 (비교용)
    "게임 광고 숏츠", "게임 추천 숏츠", "앱 추천 숏츠", "꿀앱 추천", "게임 실사용",
]


def collect(q, n=15):
    items = []
    try:
        r = subprocess.run(
            ["yt-dlp", "--dump-json", "--flat-playlist", f"ytsearch{n}:{q}"],
            capture_output=True, text=True, timeout=90,
        )
        for line in r.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            title = (d.get("title") or "").strip()
            if not title:
                continue
            items.append({
                "id": f"yt_{d.get('id')}",
                "query": q,
                "title": title[:120],
                "views": d.get("view_count"),
                "duration": d.get("duration"),
                "channel": d.get("channel") or d.get("uploader") or "",
                "url": f"https://youtube.com/watch?v={d.get('id')}",
            })
    except Exception:
        pass
    return items


def main():
    existing = []
    if OUT.exists():
        try:
            existing = json.load(open(OUT, encoding="utf-8"))
        except Exception:
            pass
    seen = {x.get("id") for x in existing}

    print(f"쿼리 {len(QUERIES)}개 × 15개 → 목표 1000+ (기존 {len(existing)})")
    B = 10
    for i in range(0, len(QUERIES), B):
        batch_new = []
        for q in QUERIES[i:i + B]:
            items = collect(q)
            for it in items:
                if it["id"] not in seen:
                    seen.add(it["id"])
                    batch_new.append(it)
            time.sleep(random.uniform(0.4, 1.0))
        existing.extend(batch_new)
        json.dump(existing, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"배치 {i//B+1}/{(len(QUERIES)+B-1)//B} → 누적 {len(existing)}")
        if len(existing) >= 1100:
            print("목표 초과 달성!")
            break
    print(f"최종: {len(existing)}")


if __name__ == "__main__":
    main()
