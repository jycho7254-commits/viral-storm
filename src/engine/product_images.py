# -*- coding: utf-8 -*-
"""
제품별 숏츠 이미지 수집기 — 카테고리별 소스
  game: Google Play 스크린샷 (기존)
  fashion/product: 네이버/구글 이미지 검색 상품 사진
  platform: 사이트 스크린샷 (Playwright 캡처)
  place: 네이버 지도/이미지
"""
import re
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
ASSETS = BASE / "data" / "shorts_assets"
ASSETS.mkdir(parents=True, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _download(url, path):
    try:
        req = urllib.request.Request(url, headers=UA)
        data = urllib.request.urlopen(req, timeout=15, context=ctx).read()
        if len(data) > 20000:
            open(path, "wb").write(data)
            return True
    except Exception:
        pass
    return False


def _slug(name: str) -> str:
    """파일명용 슬러그 — 한글은 해시로"""
    import hashlib
    s = re.sub(r"[^a-zA-Z0-9]", "", name)[:12].lower()
    if len(s) < 3:
        s = hashlib.md5(name.encode()).hexdigest()[:10]
    return s


def collect_game_images(name: str, count: int = 3) -> list:
    """Google Play 스크린샷 (기존 방식)"""
    import time
    q = urllib.parse.quote(name)
    url = f"https://play.google.com/store/search?q={q}&c=apps&hl=ko"
    req = urllib.request.Request(url, headers=UA)
    html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", "replace")
    ids = re.findall(r"/store/apps/details\?id=([a-zA-Z0-9._]+)", html)
    if not ids:
        return []
    app_id = ids[0]
    url2 = f"https://play.google.com/store/apps/details?id={app_id}&hl=ko"
    req = urllib.request.Request(url2, headers=UA)
    html2 = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", "replace")
    imgs = re.findall(r"(https://play-lh\.googleusercontent\.com/[A-Za-z0-9_-]+)=w526-h296", html2)
    paths = []
    ok = 0
    slug = _slug(name)
    for i, u in enumerate(dict.fromkeys(imgs)):
        if ok >= count:
            break
        for sz in ["=w1067-h1920", ""]:
            p = ASSETS / f"{slug}_{ok}.png"
            if _download(u + sz, p):
                paths.append(str(p))
                ok += 1
                break
    return paths


def collect_web_images(name: str, count: int = 3) -> list:
    """패션/제품/매장 — 네이버 이미지 검색 (구글은 차단됨)"""
    from playwright.sync_api import sync_playwright
    import time as _t
    import urllib.parse as _up
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx2 = b.new_context(viewport={"width": 1280, "height": 900}, user_agent=UA["User-Agent"])
        pg = ctx2.new_page()
        q = _up.quote(name)
        try:
            pg.goto(f"https://search.naver.com/search.naver?query={q}&where=image", wait_until="networkidle", timeout=30000)
            _t.sleep(3)
            imgs = pg.evaluate("""() => {
                const out = [];
                document.querySelectorAll('img').forEach(i => {
                    const src = i.src || '';
                    if (src.includes('pstatic.net') && src.includes('shopping-phinf') === false && i.naturalWidth > 250) out.push(src);
                    else if (src.includes('search.pstatic.net') && i.naturalWidth > 250) out.push(src);
                });
                return [...new Set(out)].slice(0, 12);
            }""")
        except Exception:
            imgs = []
        slug = _slug(name)
        ok = 0
        for src in imgs:
            if ok >= count:
                break
            pth = ASSETS / f"{slug}_w{ok}.png"
            if _download(src, pth):
                paths.append(str(pth))
                ok += 1
        b.close()
    return paths


def collect_site_screenshots(url: str, count: int = 3) -> list:
    """플랫폼/사이트 — 직접 스크린샷 (스크롤 위치별)"""
    from playwright.sync_api import sync_playwright
    import time as _t
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx2 = b.new_context(viewport={"width": 1080, "height": 1920}, user_agent=UA["User-Agent"])
        pg = ctx2.new_page()
        try:
            pg.goto(url, wait_until="networkidle", timeout=30000)
            _t.sleep(2)
            slug = _slug(url)
            for i in range(count):
                pth = ASSETS / f"{slug}_shot{i}.png"
                pg.screenshot(path=str(pth))
                paths.append(str(pth))
                pg.mouse.wheel(0, 1600)
                _t.sleep(1.2)
        except Exception:
            pass
        b.close()
    return paths


def collect_images(name: str, category: str = None, count: int = 3) -> list:
    """통합 진입점"""
    if category is None:
        from src.engine.product_research import detect_category
        category = detect_category(name)
    if category == "game":
        return collect_game_images(name, count)
    if category == "platform":
        m = re.search(r"https?://[^\s]+", name)
        if m:
            return collect_site_screenshots(m.group(0), count)
        return collect_web_images(name, count)
    # fashion/product/place → 웹 이미지
    return collect_web_images(name, count)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(BASE))
    for name, cat in [("트릭컬 리바이브", "game"), ("나이키 에어포스", "fashion")]:
        r = collect_images(name, cat, 2)
        print(f"[{cat}] {name}: {len(r)}장")
        for p in r:
            print("   ", p)
