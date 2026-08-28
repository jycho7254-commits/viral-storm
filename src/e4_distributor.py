# -*- coding: utf-8 -*-
"""E4 배포관 (08-28) — 발행 + 성과수집
현재: YT OAuth 대기중 → 성과수집 로직만 구현 (발행은 수동/대기)
- collect_metrics(): 발행 콘텐츠 조회수/좋아요 수집 (yt-dlp로 공개 통계)
- job 승인(approval→posted) 워크플로우 헬퍼
"""
import json
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DB = BASE / "data" / "viral_storm.db"


def approve_job(job_id: str, note: str = ""):
    """형 승인 → posted 전환 (E4 진입점)"""
    c = sqlite3.connect(DB)
    c.execute("UPDATE jobs SET status='posted', stage_detail=? WHERE job_id=?", (note or "승인완료", job_id))
    c.commit()
    c.close()
    print(f"[E4] {job_id} → posted")


def collect_metrics(video_url: str) -> dict:
    """yt-dlp로 공개 메트릭 수집 (조회수/좋아요/댓글)"""
    r = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-warnings", video_url],
        capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(r.stdout)
        return {
            "url": video_url,
            "views": d.get("view_count"),
            "likes": d.get("like_count"),
            "comments": d.get("comment_count"),
            "title": (d.get("title") or "")[:60],
            "collected_at": datetime.now().isoformat(timespec="seconds"),
        }
    except Exception:
        return {"url": video_url, "error": r.stderr[-100:] if r.stderr else "파싱실패"}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2 and sys.argv[1] == "approve":
        approve_job(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    elif len(sys.argv) > 2 and sys.argv[1] == "metrics":
        print(json.dumps(collect_metrics(sys.argv[2]), ensure_ascii=False, indent=1))
