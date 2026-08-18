# -*- coding: utf-8 -*-
"""
viral_run.py — 채널별 바이럴 실행 러너
사용법:
  python src/scheduler/viral_run.py --channel naver    # 네이버 블로그 (연동된 계정)
  python src/scheduler/viral_run.py --channel dc --proxy http://ip:3128  # DC (프록시+신규세션)
  python src/scheduler/viral_run.py --channel shorts   # 유튜브 숏츠 (TTS+렌더+업로드)
  python src/scheduler/viral_run.py --channel all

채널 정책 (2026-08-18 명훈이형 결정):
  1. 네이버 블로그 = 연동된 기존 계정 (gamereviewlab, 세션 파일 사용)
  2. DC/커뮤니티 = 프록시 + 신규 글쓰기 (기존 세션 재사용 금지)
  3. 유튜브 숏츠 = AI느낌 없는 바이럴 스타일 영상 (edge-tts+실제 게임화면)
"""
import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

PY = r"C:\Users\user\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe"
DB = BASE / "data" / "viral_storm.db"


def db():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    return conn


def get_pending(platform=None, limit=1):
    conn = db()
    q = "SELECT c.*, cp.game_name FROM content c JOIN campaigns cp ON c.campaign_id=cp.id WHERE c.status='pending'"
    args = []
    if platform:
        q += " AND c.platform=?"
        args.append(platform)
    q += " ORDER BY c.id LIMIT ?"
    args.append(limit)
    rows = conn.execute(q, args).fetchall()
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        text = d.get("text") or ""
        d["body"] = text
        # 제목 추출 우선순위: '제목:' 라인 > 마크다운 제외 첫 문장 > 게임명
        import re as _re
        m = _re.search(r"제목:\s*(.+)", text)
        if m:
            d["title"] = m.group(1).strip().strip("*")[:50]
        else:
            clean = _re.sub(r"^[-*#\s]+", "", text.split("\n")[0]).strip()
            d["title"] = (clean or (d.get("game_name") or "게임") + " 후기")[:45]
        items.append(d)
    return items


def mark_posted(cid, url):
    conn = db()
    conn.execute(
        "UPDATE content SET status='posted', post_url=?, posted_at=? WHERE id=?",
        (url, datetime.now().isoformat(), cid),
    )
    conn.commit()
    conn.close()


def mark_failed(cid, err):
    conn = db()
    conn.execute(
        "UPDATE content SET status='failed', error=? WHERE id=?",
        (str(err)[:500], cid),
    )
    conn.commit()
    conn.close()


# ── 채널 1: 네이버 블로그 (연동 계정) ──────────────────────
def run_naver(items):
    from src.platforms.automation import NaverBlogAutomation

    auto = NaverBlogAutomation(session_file=str(BASE / "config" / "naver_viral_session.json"))
    auto.init_browser(headless=False)
    try:
        for it in items:
            print(f"[네이버] 발행: {it['title'][:40]}")
            r = auto.post(it["title"], it["body"], images=it.get("images"))
            if r.get("success"):
                mark_posted(it["id"], r.get("url", ""))
                print("  ✅ 완료:", r.get("url"))
            else:
                mark_failed(it["id"], r.get("error", "unknown"))
                print("  ❌ 실패:", r.get("error"))
    finally:
        auto.close()


# ── 채널 2: DC/커뮤니티 (프록시+신규세션) ──────────────────
def run_dc(items, proxy=None):
    from src.platforms.automation import DCAutomation

    if not proxy:
        print("[DC] 프록시 미지정 — 직접 IP로 실행 (차단 위험)")
    auto = DCAutomation(proxy=proxy)
    auto.init_browser(headless=False)
    try:
        for it in items:
            print(f"[DC] 발행: {it['title'][:40]} (proxy={proxy or 'direct'})")
            r = auto.post(it.get("gallery", "game"), it["title"], it["body"])
            if r.get("success"):
                mark_posted(it["id"], r.get("url", ""))
            else:
                mark_failed(it["id"], r.get("error", "unknown"))
    finally:
        auto.close()


# ── 채널 3: 유튜브 숏츠 ──────────────────────────────────
def run_shorts(items):
    from src.engine.shorts_maker import build_short, probe_duration
    from src.platforms.youtube_upload import upload

    for it in items:
        print(f"[숏츠] 제작: {it['title'][:40]}")
        # 스크립트: 본문을 문장 단위로
        script_lines = [s.strip() for s in it["body"].split(".") if s.strip()][:6]
        imgs = it.get("images") or []
        if not imgs:
            print("  ⚠️ 이미지 없음 — 기본 배경으로 렌더")
            import subprocess as sp
            tmp = BASE / "data" / "shorts_bg"
            tmp.mkdir(exist_ok=True)
            bg = tmp / "bg.png"
            FF = r"C:\Users\user\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0-full_build\bin\ffmpeg.exe"
            sp.run([FF, "-y", "-f", "lavfi", "-i", "color=c=0x16213e:s=1080x1920:d=1", str(bg)], capture_output=True)
            imgs = [str(bg)]
        out = BASE / "data" / "shorts_out" / f"short_{it['id']}_{datetime.now():%m%d_%H%M}.mp4"
        out.parent.mkdir(exist_ok=True)
        try:
            build_short(it["title"], script_lines, imgs, str(out))
            # 업로드 (토큰 있을 때만)
            try:
                r = upload(str(out), it["title"], description=it["body"][:200], tags=["게임", "shorts"])
                mark_posted(it["id"], r["url"])
                print("  ✅ 업로드:", r["url"])
            except SystemExit as e:
                print("  ⚠️ 업로드 건너뜀:", str(e)[:80])
                print("     영상만 제작 완료:", out)
        except Exception as e:
            mark_failed(it["id"], e)
            print("  ❌ 실패:", str(e)[:100])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", required=True, choices=["naver", "dc", "shorts", "all"])
    ap.add_argument("--proxy", default=None, help="DC용 프록시 (http://ip:port)")
    ap.add_argument("--limit", type=int, default=1)
    args = ap.parse_args()

    ch = args.channel
    if ch in ("naver", "all"):
        items = get_pending("naver", args.limit)
        if items:
            run_naver(items)
        else:
            print("[네이버] 대기 콘텐츠 없음")
    if ch in ("dc", "all"):
        items = get_pending("dc", args.limit)
        if items:
            run_dc(items, proxy=args.proxy)
        else:
            print("[DC] 대기 콘텐츠 없음")
    if ch in ("shorts", "all"):
        items = get_pending("youtube", args.limit)
        if items:
            run_shorts(items)
        else:
            print("[숏츠] 대기 콘텐츠 없음")


if __name__ == "__main__":
    main()
