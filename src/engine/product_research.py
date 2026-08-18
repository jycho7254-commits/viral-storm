# -*- coding: utf-8 -*-
"""
제품 일반화 아키텍처 — 게임뿐 아니라 옷/플랫폼/사이트/서비스 전부 홍보 가능하게.

기존: game_research.py가 Google Play + 게임 뉴스만 리서치
확장: product_research.py가 제품 카테고리별 소스로 리서치
  - game: Google Play + 게임 뉴스 (기존 로직 유지)
  - fashion(옷/브랜드): 무신사/지그재그 상품 정보 + 블로그 후기
  - platform/site(사이트/앱/서비스): 공식 사이트 메타 + 커뮤니티 언급
  - product(일반 제품): 쿠팡/네이버쇼핑 상품명 + 리뷰 키워드
  - place(매장/카페/숙소): 지역 + 업종 리뷰

모든 카테고리가 동일한 인터페이스(facts 리스트)를 반환 → 
content_generator/shorts_script는 게임/제품 구분 없이 동작.
"""
import re
import urllib.parse
import urllib.request
import ssl
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=timeout, context=ctx).read().decode("utf-8", "replace")
    except Exception:
        return ""


def research_game(name: str) -> dict:
    """기존 게임 리서치 — game_research 위임"""
    import sys
    sys.path.insert(0, str(BASE))
    try:
        from src.engine.game_research import research as _r
        return _r(name)
    except Exception:
        return {"facts": [f"{name} 게임", "모바일/PC 게임"], "source": "fallback"}


def research_fashion(name: str) -> dict:
    """옷/패션 브랜드 — 네이버 검색으로 브랜드 정보 + 후기 키워드"""
    facts = [f"{name} 브랜드/제품"]
    html = _fetch("https://search.naver.com/search.naver?query=" + urllib.parse.quote(f"{name} 후기"))
    if html:
        # 후기 관련 키워드 추출
        for kw in ["사이즈", "핏", "재질", "세탁", "가격", "가성비", "정사이즈", "오버사이즈", "면", "무신사", "지그재그"]:
            if kw in html:
                facts.append(f"언급되는 키워드: {kw}")
    return {"facts": facts[:8], "source": "naver_search"}


def research_platform(name: str) -> dict:
    """사이트/앱/플랫폼 — 공식 사이트 접속 + 메타 정보"""
    facts = [f"{name} 서비스/플랫폼"]
    # URL 추출 시도
    m = re.search(r"(https?://[^\s]+)", name)
    if m:
        url = m.group(1)
        facts.append(f"공식 주소: {url}")
        html = _fetch(url)
        if html:
            t = re.search(r"<title>([^<]+)</title>", html)
            if t:
                facts.append(f"사이트 제목: {t.group(1).strip()}")
            d = re.search(r'name="description" content="([^"]+)"', html)
            if d:
                facts.append(f"사이트 설명: {d.group(1)[:100]}")
        name_clean = re.sub(r"https?://[^\s]+", "", name).strip()
    else:
        name_clean = name
        # 앱이면 GP 검색
        html = _fetch("https://play.google.com/store/search?q=" + urllib.parse.quote(name_clean) + "&c=apps&hl=ko")
        if html and "details?id=" in html:
            facts.append("Google Play 등록 앱")
    return {"facts": facts[:8], "source": "site_meta"}


def research_product(name: str) -> dict:
    """일반 제품 — 네이버쇼핑 지식+커뮤니티 언급"""
    facts = [f"{name} 제품"]
    html = _fetch("https://search.naver.com/search.naver?query=" + urllib.parse.quote(f"{name} 리뷰"))
    if html:
        found = set()
        for kw in ["가격", "성능", "품질", "AS", "리뷰", "평점", "추천", "비교", "장점", "단점", "재구매"]:
            if kw in html and kw not in found:
                found.add(kw)
                facts.append(f"쇼핑 키워드: {kw}")
    return {"facts": facts[:8], "source": "shopping_search"}


def research_place(name: str) -> dict:
    """매장/카페/숙소/맛집"""
    facts = [f"{name} 매장/장소"]
    html = _fetch("https://search.naver.com/search.naver?query=" + urllib.parse.quote(name))
    if html:
        for kw in ["위치", "영업시간", "주차", "예약", "메뉴", "대기", "후기", "분위기"]:
            if kw in html:
                facts.append(f"정보: {kw}")
    return {"facts": facts[:8], "source": "place_search"}


# 카테고리 라우팅
RESEARCHERS = {
    "game": research_game,
    "fashion": research_fashion,
    "platform": research_platform,
    "product": research_product,
    "place": research_place,
}


def detect_category(name: str, hint: str = None) -> str:
    """제품명+힌트로 카테고리 자동 감지"""
    if hint and hint in RESEARCHERS:
        return hint
    n = name.lower()
    if re.search(r"http|www\.|\.com|\.kr|\.io|사이트|앱|플랫폼|서비스", n):
        return "platform"
    if re.search(r"옷|의류|티셔츠|후드|바지|신발|스니커|브랜드|패션|코디|룩북|아우터|에어포스|나이키|아디다스|무신사", n):
        return "fashion"
    if re.search(r"카페|맛집|식당|숙소|호텔|리조트|여행|블루보틀", n):
        return "place"
    if re.search(r"게임|모바일|rpg|mmorpg|쿠키런|리니지|서브컬처", n):
        return "game"
    # 기본: 일반 제품 (게임 아님 — 트릭컬 사건처럼 오판 방지)
    return "product"


def research(name: str, category: str = None) -> dict:
    """통합 리서치 진입점 — 모든 제품 유형 지원"""
    cat = detect_category(name, category)
    r = RESEARCHERS[cat](name)
    r["category"] = cat
    r["name"] = name
    return r


if __name__ == "__main__":
    # 카테고리별 테스트
    tests = [
        ("트릭컬 리바이브", "game"),
        ("나이키 에어포스", "fashion"),
        ("https://notion.so", "platform"),
        ("다이슨 에어랩", None),
        ("강남 블루보틀 카페", None),
    ]
    for name, hint in tests:
        r = research(name, hint)
        print(f"[{r['category']:8s}] {name} → {len(r['facts'])}개 팩트")
        for f in r["facts"][:3]:
            print(f"    - {f[:60]}")
