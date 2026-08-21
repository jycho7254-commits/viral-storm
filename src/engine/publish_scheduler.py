# -*- coding: utf-8 -*-
"""바이럴 발행 스케줄러 — APScheduler 기반 시간대 분산 자동 발행

전략 (학습 코퍼스 기반):
- 네이버 블로그: 10:00, 20:00 (출퇴근 후 트래픽 피크)
- DC인사이드: 12:30, 18:30, 23:00 (점심/저녁/심야 3회 — 커뮤니티 활동 시간)
- X(트위터): 9:00, 13:00, 17:00, 21:00 (하루 4회 — 노출 빈도 최적화)
- 유튜브 숏츠: 18:00, 21:30 (퇴근 후 시청 피크)

실행: python -m src.engine.publish_scheduler [--dry-run]
"""
import argparse
import random
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
DB = BASE / "data" / "viral_storm.db"

# 플랫폼별 발행 시간 (시, 분)
SCHEDULE = {
    "blog": [(10, 0), (20, 0)],
    "dc": [(12, 30), (18, 30), (23, 0)],
    "twitter": [(9, 0), (13, 0), (17, 0), (21, 0)],
}


def get_pending(con: sqlite3.Connection, platform: str, limit: int = 1):
    rows = con.execute(
        "SELECT id, text FROM content WHERE platform=? AND status='pending' "
        "ORDER BY created_at LIMIT ?", (platform, limit)
    ).fetchall()
    return rows


def publish_blog(content_id: int, text: str) -> tuple:
    """네이버 블로그 발행 — 세션 기반"""
    try:
        sys.path.insert(0, str(BASE))
        from src.publishers.naver_blog import publish as blog_publish
        url = blog_publish(text)
        return ("posted", url)
    except Exception as e:
        return ("failed", str(e)[:80])


def publish_dc(content_id: int, text: str) -> tuple:
    """DC 발행 — 프록시 필요 (준비 전이면 스킵으로 표시)"""
    return ("skipped", "DC 프록시 미설정 — Oracle Cloud 준비 후 활성화")


def publish_twitter(content_id: int, text: str) -> tuple:
    """X 발행 — 잠금 해제 대기"""
    return ("skipped", "X 계정 잠금해제 대기중")


def mark(con, cid: int, status: str, url: str = ""):
    con.execute(
        "UPDATE content SET status=?, posted_at=datetime('now','localtime'), post_url=? WHERE id=?",
        (status, url, cid),
    )
    con.commit()


def run_tick(dry_run: bool = False, now=None) -> list:
    """현재 시간에 해당하는 플랫폼 발행 처리 (now 주입 가능 — 테스트용)"""
    now = now or datetime.now()
    hhmm = (now.hour, now.minute)
    results = []

    con = sqlite3.connect(DB)
    for platform, times in SCHEDULE.items():
        # 현재 시간이 발행 시간 ±25분 창에 있는지
        hit = any(abs((h * 60 + m) - (hhmm[0] * 60 + hhmm[1])) <= 25 for h, m in times)
        if not hit:
            continue

        pending = get_pending(con, platform)
        if not pending:
            results.append((platform, None, "발행 대기 콘텐츠 없음"))
            continue

        cid, text = pending[0]
        # 사람처럼 — 랜덤 딜레이 정보만 로그 (실제 sleep은 스케줄러가 분산)
        delay = random.randint(60, 600)

        if dry_run:
            results.append((platform, cid, f"[DRY] 발행 예정 ({delay}초 후) {len(text)}자"))
            continue

        publisher = {"blog": publish_blog, "dc": publish_dc, "twitter": publish_twitter}[platform]
        try:
            status, url = publisher(cid, text)
            mark(con, cid, status, url)
            results.append((platform, cid, f"{status}: {url}"))
        except Exception as e:
            mark(con, cid, "failed", str(e)[:80])
            results.append((platform, cid, f"failed: {str(e)[:60]}"))
    con.close()
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--serve", action="store_true", help="APScheduler 상시 구동")
    args = ap.parse_args()

    if args.serve:
        from apscheduler.schedulers.blocking import BlockingScheduler

        sched = BlockingScheduler()
        # 30분마다 체크 — 시간대 창 매칭 방식이라 유연
        sched.add_job(lambda: [print(f"[{p}] #{c}: {m}", flush=True) for p, c, m in run_tick()],
                      "interval", minutes=30, id="publish_tick")
        print("발행 스케줄러 구동 — 30분 간격 체크. Ctrl+C 종료")
        sched.start()
    else:
        for platform, cid, msg in run_tick(dry_run=args.dry_run):
            print(f"[{platform}] #{cid}: {msg}")


if __name__ == "__main__":
    main()
