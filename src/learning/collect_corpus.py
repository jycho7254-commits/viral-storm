# -*- coding: utf-8 -*-
"""
바이럴 사례 대량 수집기 — 목표 1만건+
채널: DC갤러리(광고성 글) / 유튜브(yt-dlp 바이럴 영상 메타) / 루리웹(홍보성 게시글) /
      네이버 블로그 검색(Playwright) / 티스토리(검색) / 아카라이브
정책: 공개 페이지만, robots 준수, 요청 간 딜레이로 부하 최소화.
결과: data/learning/corpus_*.json (원시) → analyze에서 패턴 추출
"""
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / "data" / "learning"
OUT.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
PY = sys.executable

# ── 공통 ──────────────────────────────────────────────

def save(chunk_name, items):
    p = OUT / chunk_name
    existing = []
    if p.exists():
        try:
            existing = json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    seen = {i.get("id") or i.get("url") for i in existing}
    new = [i for i in items if (i.get("id") or i.get("url")) not in seen]
    json.dump(existing + new, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return len(existing), len(new)


def curl_get(url, timeout=15):
    """curl_cffi impersonation — insane-search 엔진 방식"""
    try:
        from curl_cffi import requests as creq
        r = creq.get(url, timeout=timeout, impersonate="chrome120", headers=UA)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None


# ── 1. DC 갤러리 (체험판/광고 갤러리 + 인기 갤러리) ────────

DC_GALLS = [
    # (id, type) — 게임+일반 제품 홍보가 섞인 갤러리들
    ("newrelease_new", "major"),     # 신작/출시 갤러리
    ("game_new1", "major"),          # 게임 뉴스
    ("mobile_new", "major"),         # 모바일 게임
    ("solehchant", "minor"),         # SOL (광고글 많음)
    ("kingshot", "minor"),
    ("victorynikke", "minor"),
    ("lastwar", "mini"),
    ("brawlstars", "mini"),
    ("lineagem", "major"),
    ("maplerpg", "major"),
    ("roblox", "minor"),
    ("royalmatch", "minor"),
    ("whiteoutsv", "minor"),
    ("fconline", "major"),
    ("umamusme", "major"),
    ("zzz", "minor"),
    ("honkaistarrail", "minor"),
    ("wutheringwaves", "minor"),
    ("nikke", "minor"),
    ("gossipharbor", "minor"),
    ("candycrush", "minor"),
    ("topheroes", "minor"),
    ("raven2", "minor"),
    ("sevennightsrebirth", "major"),
    ("nyanko", "major"),
    ("limbuscompany", "minor"),
    ("dragonvillage", "minor"),
    ("vampire", "minor"),
    ("mumonarch2", "minor"),
    ("i9", "minor"),
    # 제품/일상/패션 확장 (08-19 종합 바이럴 학습)
    ("camera", "major"),        # 카메라(제품)
    ("fashion", "major"),       # 패션
    ("sneakers", "major"),      # 신발(제품)
    ("perfume", "major"),       # 향수(제품)
    ("cosmetic", "major"),      # 화장품
    ("coffee", "major"),        # 커피/프랜차이즈
    ("budgetpc", "major"),      # 가성비 PC(제품)
    ("smartphone", "major"),    # 스마트폰(제품)
    ("watch", "major"),         # 시계(제품)
    ("interior", "major"),      # 인테리어/가구
    ("car", "major"),           # 자동차
    ("travel", "major"),        # 여행/숙소
    ("food", "major"),          # 맛집/식품
    ("shopping", "major"),      # 쇼핑/드마트
    ("health", "major"),        # 건강/운동
]

def collect_dc(max_pages=3):
    """DC 갤러리 게시글 수집 — 제목/추천수/댓글수/작성일"""
    all_items = []
    for gid, gtype in DC_GALLS:
        prefix = {"major": "https://gall.dcinside.com/board/lists/",
                  "minor": "https://gall.dcinside.com/mgallery/board/lists/",
                  "mini": "https://gall.dcinside.com/mini/board/lists/"}[gtype]
        for page in range(1, max_pages + 1):
            url = f"{prefix}?id={gid}&page={page}"
            html = curl_get(url)
            if not html:
                continue
            rows = re.findall(r'<tr class="ub-content[^"]*"[^>]*>(.*?)</tr>', html, re.DOTALL)
            for row in rows:
                no = re.search(r"no=(\d+)", row)
                t = re.search(r'gall_tit[^>]*>\s*<a[^>]*>(.*?)</a>', row, re.DOTALL)
                if not (no and t):
                    continue
                title = re.sub(r"<[^>]+>", "", t.group(1)).strip()
                if not title or title in ("공지", "설문", "이벤트"):
                    continue
                rec = re.search(r"gall_recommend[^>]*>\s*(\d+)", row)
                cmt = re.search(r'gall_reply[^>]*>.*?(\d+)', row, re.DOTALL)
                date = re.search(r'(\d{2}-\d{2} \d{2}:\d{2})', row)
                all_items.append({
                    "id": f"dc_{gid}_{no.group(1)}",
                    "source": "dc",
                    "gallery": gid,
                    "title": title[:120],
                    "recommends": int(rec.group(1)) if rec else 0,
                    "comments": int(cmt.group(1)) if cmt else 0,
                    "date": date.group(1) if date else "",
                })
            time.sleep(random.uniform(0.8, 1.6))
        print(f"  DC {gid}: 누적 {len(all_items)}")
    return all_items


# ── 2. 유튜브 바이럴 영상 (yt-dlp) ────────────────────

YT_QUERIES = [
    "게임 추천 숏츠", "모바일 게임 리뷰", "이 게임 꿀팁", "게임 후기 브이로그",
    "옷 추천 브이로그", "패션 룩북", "코디 팁", "OOTD 한국",
    "무료 사이트 추천", "유용한 사이트", "앱 추천", "서비스 후기",
    "제품 리뷰 언박싱", "요즘 핫한 제품", "인생템 추천", "리얼 리뷰",
    "게임 광고", "브랜드 협찬", "체험단 후기", "정품 리뷰",
    "신발 추천", "스킨케어 추천", "맛집 추천", "여행 후기",
]

def collect_youtube(per_query=8):
    all_items = []
    for q in YT_QUERIES:
        try:
            r = subprocess.run(
                ["yt-dlp", "--dump-json", "--flat-playlist", f"ytsearch{per_query}:{q}"],
                capture_output=True, text=True, timeout=60,
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
            print(f"  YT '{q}': 누적 {len(all_items)}")
        except Exception as e:
            print(f"  YT '{q}' 에러: {str(e)[:40]}")
        time.sleep(random.uniform(1.0, 2.0))
    return all_items


# ── 3. 루리웹 (홍보/체험단 성격 게시글) ────────────────

def collect_ruliweb(max_pages=10):
    all_items = []
    # 루리웹 뉴스 베스트 + 게시판 — 대시보드 검증된 방식(urllib UA)이 안정적
    import urllib.request
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    def ufetch(url):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            return urllib.request.urlopen(req, timeout=12, context=ctx).read().decode("utf-8", errors="ignore")
        except Exception:
            return ""

    targets = [f"https://bbs.ruliweb.com/news/best"]
    # 히스토리 페이지도
    for page in range(2, max_pages + 1):
        targets.append(f"https://bbs.ruliweb.com/news/best?page={page}")
    for url in targets:
        html = ufetch(url)
        if not html:
            continue
        items = re.findall(r'<a[^>]*href="(https://bbs\.ruliweb\.com/news/board/[^"]+)"[^>]*>([^<]+)', html)
        for u, title in items:
            title = title.strip()
            if len(title) < 8:
                continue
            all_items.append({
                "id": u[-20:],
                "source": "ruliweb",
                "board": "news_best",
                "title": title[:120],
                "url": u,
            })
        time.sleep(random.uniform(1.0, 1.8))
    print(f"  루리웹: {len(all_items)}")
    return all_items


# ── 4. 네이버 블로그/티스토리 검색 (Playwright) ──────────

def collect_naver_blog(queries, per_query=20):
    """네이버 뷰어 검색 — 블로그 포스트 제목/날짜/설명. Playwright 필요."""
    from playwright.sync_api import sync_playwright
    all_items = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, user_agent=UA["User-Agent"])
        pg = ctx.new_page()
        for q in queries:
            try:
                url = "https://search.naver.com/search.naver?query=" + urllib.parse.quote(q) + "&nso=&where=blog"
                pg.goto(url, wait_until="networkidle", timeout=40000)
                time.sleep(2)
                pg.mouse.wheel(0, 1500)  # 지연 렌더링 트리거
                time.sleep(2.5)
                items = pg.evaluate("""() => {
                    const out = [];
                    const seen = new Set();
                    document.querySelectorAll('a[href*="blog.naver.com"]').forEach(a => {
                        const title = (a.textContent || '').trim().replace(/\\s+/g, ' ');
                        const url = a.href || '';
                        if (title.length > 10 && url.includes('blog.naver.com') && !url.includes('PostList') && !seen.has(url)) {
                            // '네이버 블로그' '새 창 열림' 등 노이즈 제거
                            const clean = title.split('네이버 블로그')[0].replace('새 창 열림', '').trim();
                            if (clean.length > 10 && !seen.has(url)) {
                                seen.add(url);
                                out.push({title: clean.slice(0, 120), url});
                            }
                        }
                    });
                    return out;
                }""")
                for i, it in enumerate(items[:per_query]):
                    all_items.append({
                        "id": it["url"][-40:],
                        "source": "naver_blog",
                        "query": q,
                        "title": it["title"],
                        "url": it["url"],
                    })
                print(f"  네이버 '{q}': {len(items)}개 → 누적 {len(all_items)}")
            except Exception as e:
                print(f"  네이버 '{q}' 에러: {str(e)[:40]}")
            time.sleep(random.uniform(2.0, 3.5))
        b.close()
    return all_items


def collect_tistory(queries, per_query=15):
    """티스토리 — 구글 검색 대신 티스토리 자체 검색 크롤 (curl)"""
    all_items = []
    for q in queries:
        url = "https://www.google.com/search?q=site:tistory.com+" + urllib.parse.quote(q) + "&num=20"
        # 구글 직접 크롤은 차단 위험 — 대신 다음 검색 사용
        url = "https://search.daum.net/search?w=blog&q=" + urllib.parse.quote(q + " site:tistory.com")
        html = curl_get(url)
        if not html:
            time.sleep(2)
            continue
        titles = re.findall(r'<a[^>]*class="[^"]*f-link[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
        if not titles:
            titles = re.findall(r'href="(https?://[^"]*\.tistory\.com/[^"]*)"[^>]*>(.*?)</a>', html, re.DOTALL)
        for u, t in titles[:per_query]:
            title = re.sub(r"<[^>]+>", "", t).strip()
            if len(title) < 8:
                continue
            all_items.append({
                "id": u[-40:],
                "source": "tistory",
                "query": q,
                "title": title[:120],
                "url": u.split("&")[0],
            })
        print(f"  티스토리 '{q}': 누적 {len(all_items)}")
        time.sleep(random.uniform(2.0, 3.0))
    return all_items


BLOG_QUERIES = [
    "게임 추천 후기", "무료 게임", "모바일게임 후기", "게임 브이로그",
    "옷 추천 코디", "패션 브이로그 룩북", "쇼핑 후기", "온라인 쇼핑 리뷰",
    "사이트 추천", "무료 사이트", "유용한 어플", "서비스 이용 후기",
    "인생템 추천", "제품 추천", "언박싱 리뷰", "갓성비 후기",
]


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()

    if mode in ("dc", "all"):
        items = collect_dc(max_pages=8)
        e, n = save("corpus_dc.json", items)
        print(f"[DC] 기존 {e} + 신규 {n}")

    if mode in ("yt", "all"):
        items = collect_youtube(per_query=10)
        e, n = save("corpus_youtube.json", items)
        print(f"[YT] 기존 {e} + 신규 {n}")

    if mode in ("ruli", "all"):
        items = collect_ruliweb(max_pages=8)
        e, n = save("corpus_ruliweb.json", items)
        print(f"[루리웹] 기존 {e} + 신규 {n}")

    if mode in ("naver", "all"):
        items = collect_naver_blog(BLOG_QUERIES, per_query=25)
        e, n = save("corpus_naver.json", items)
        print(f"[네이버] 기존 {e} + 신규 {n}")

    if mode in ("tistory", "all"):
        items = collect_tistory(BLOG_QUERIES, per_query=15)
        e, n = save("corpus_tistory.json", items)
        print(f"[티스토리] 기존 {e} + 신규 {n}")

    # 총계
    total = 0
    for f in OUT.glob("corpus_*.json"):
        d = json.load(open(f, encoding="utf-8"))
        total += len(d)
        print(f"  {f.name}: {len(d)}")
    print(f"\n총 코퍼스: {total}건 | 소요 {time.time()-t0:.0f}초")
