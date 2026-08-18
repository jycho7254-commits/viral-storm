# -*- coding: utf-8 -*-
"""
Viral Storm 사이트 — FastAPI 백엔드
- 캠페인 생성 (제품명/설명/타겟연령/플랫폼/기간)
- 캠페인 실행 (글/숏츠 생성)
- 바이럴 지표 대시보드 (조회/반응/노출)
- 숏츠 생성 API (이미지+TTS+렌더)
"""
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

PY = r"C:\Users\user\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe"
DB = BASE / "data" / "viral_site.db"

app = FastAPI(title="Viral Storm Site")

# 생성된 숏츠 영상 서빙 (/videos/xxx.mp4)
VIDEOS_DIR = BASE / "data" / "shorts_out"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")


def db():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        product_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        category TEXT DEFAULT 'game',
        target_age TEXT DEFAULT '20-30',
        platforms TEXT DEFAULT '["naver","youtube","dc"]',
        start_date TEXT,
        end_date TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    );
    CREATE TABLE IF NOT EXISTS contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        platform TEXT NOT NULL,
        kind TEXT DEFAULT 'post',
        title TEXT DEFAULT '',
        body TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        post_url TEXT,
        metrics_json TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now','localtime')),
        posted_at TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
    );
    CREATE TABLE IF NOT EXISTS metrics_daily (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        views INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        comments INTEGER DEFAULT 0,
        clicks INTEGER DEFAULT 0,
        FOREIGN KEY (campaign_id) REFERENCES campaigns(id),
        UNIQUE (campaign_id, date)
    );
    """)
    conn.commit()
    conn.close()


init_db()


# ── 모델 ──────────────────────────────────────

class CampaignIn(BaseModel):
    product_name: str
    name: Optional[str] = None
    description: str = ""
    category: str = "game"  # game/fashion/platform/product/place
    target_age: str = "20-30"
    platforms: list = ["naver", "youtube", "dc"]
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ── 캠페인 CRUD ──────────────────────────────

@app.get("/api/campaigns")
def list_campaigns():
    conn = db()
    rows = conn.execute("""
        SELECT c.*, 
               (SELECT COUNT(*) FROM contents WHERE campaign_id=c.id) as content_count,
               (SELECT COUNT(*) FROM contents WHERE campaign_id=c.id AND status='posted') as posted_count,
               (SELECT COALESCE(SUM(views),0) FROM metrics_daily WHERE campaign_id=c.id) as total_views
        FROM campaigns c ORDER BY c.id DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/campaigns")
def create_campaign(c: CampaignIn):
    conn = db()
    cur = conn.execute(
        """INSERT INTO campaigns (name, product_name, description, category, target_age, platforms, start_date, end_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (c.name or c.product_name, c.product_name, c.description, c.category,
         c.target_age, json.dumps(c.platforms), c.start_date or datetime.now().strftime("%Y-%m-%d"),
         c.end_date or (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")),
    )
    cid = cur.lastrowid
    conn.commit()
    conn.close()
    return {"id": cid, "ok": True}


@app.get("/api/campaigns/{cid}")
def get_campaign(cid: int):
    conn = db()
    r = conn.execute("SELECT * FROM campaigns WHERE id=?", (cid,)).fetchone()
    if not r:
        raise HTTPException(404)
    contents = conn.execute("SELECT * FROM contents WHERE campaign_id=? ORDER BY id DESC", (cid,)).fetchall()
    metrics = conn.execute(
        "SELECT * FROM metrics_daily WHERE campaign_id=? ORDER BY date", (cid,)
    ).fetchall()
    conn.close()
    d = dict(r)
    d["platforms"] = json.loads(d["platforms"] or "[]")
    d["contents"] = [dict(x) for x in contents]
    d["metrics"] = [dict(x) for x in metrics]
    return d


@app.delete("/api/campaigns/{cid}")
def delete_campaign(cid: int):
    conn = db()
    conn.execute("DELETE FROM contents WHERE campaign_id=?", (cid,))
    conn.execute("DELETE FROM metrics_daily WHERE campaign_id=?", (cid,))
    conn.execute("DELETE FROM campaigns WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ── 콘텐츠 생성 (제품 일반화 + 학습 패턴) ─────────

@app.post("/api/campaigns/{cid}/generate")
def generate_content_api(cid: int, platform: str = "blog", count: int = 1):
    """글/대본 생성 — product_research + content_generator + viral_patterns"""
    conn = db()
    camp = conn.execute("SELECT * FROM campaigns WHERE id=?", (cid,)).fetchone()
    if not camp:
        raise HTTPException(404)
    conn.close()
    camp = dict(camp)

    try:
        from src.engine.product_research import research
        from src.engine.content_generator import generate_content, load_personas
        from src.engine.shorts_script import generate_shorts_script
        import random

        r = research(camp["product_name"], camp["category"])
        personas = load_personas()
        persona = random.choice(personas)
        game_info = {
            "name": camp["product_name"],
            "genre": camp["category"],
            "description": camp["description"],
            "research": r,
        }
        results = []
        for _ in range(max(1, min(count, 5))):
            if platform in ("youtube", "shorts"):
                script = generate_shorts_script(game_info, persona)
                title = script["lines"][0] if script["lines"] else camp["product_name"]
                body = "\n".join(script["lines"])
            else:
                out = generate_content(game_info, persona, platform="blog" if platform == "naver" else platform)
                body = out.get("text", "")
                title = body.split("\n")[0][:50] if body else camp["product_name"]
            conn = db()
            cur = conn.execute(
                "INSERT INTO contents (campaign_id, platform, kind, title, body, status) VALUES (?,?,?,?,?, 'pending')",
                (cid, platform, "shorts" if platform in ("youtube", "shorts") else "post", title, body),
            )
            conn.commit()
            conn.close()
            results.append({"id": cur.lastrowid, "title": title[:60]})
        return {"ok": True, "generated": results, "research_facts": r["facts"][:5]}
    except Exception as e:
        raise HTTPException(500, str(e)[:300])


# ── 숏츠 영상 생성 (이미지+TTS+렌더) ─────────────

@app.post("/api/contents/{content_id}/make_video")
def make_video(content_id: int):
    """숏츠 영상 렌더 — product_images + shorts_maker"""
    conn = db()
    c = conn.execute("SELECT * FROM contents WHERE id=?", (content_id,)).fetchone()
    if not c:
        raise HTTPException(404)
    camp = conn.execute("SELECT * FROM campaigns WHERE id=?", (c["campaign_id"],)).fetchone()
    conn.close()
    c, camp = dict(c), dict(camp)

    try:
        from src.engine.product_images import collect_images
        from src.engine.shorts_maker import build_short, probe_duration

        # 서버 cwd 무관하게 절대경로 통일 (Errno 22 방지)
        import os
        os.chdir(str(BASE))
        lines = [l for l in c["body"].split("\n") if l.strip()][:6]
        imgs = collect_images(camp["product_name"], camp["category"], count=min(3, len(lines)))
        if not imgs:
            raise HTTPException(400, "이미지 수집 실패 — 제품명 확인 필요")
        out_dir = BASE / "data" / "shorts_out"
        out_dir.mkdir(exist_ok=True)
        out = str(out_dir / f"camp{camp['id']}_c{c['id']}_{datetime.now():%m%d_%H%M%S}.mp4")
        build_short(camp["product_name"], lines, imgs, out, voice="female")
        dur = probe_duration(out)
        conn = db()
        conn.execute("UPDATE contents SET status='rendered', post_url=?, metrics_json=? WHERE id=?",
                     (out, json.dumps({"duration": dur}), content_id))
        conn.commit()
        conn.close()
        return {"ok": True, "video": out, "duration": dur}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print("=== make_video 에러 ===")
        print(tb[-1500:])
        raise HTTPException(500, str(e)[:300])


# ── 지표 ─────────────────────────────────────

@app.post("/api/campaigns/{cid}/metrics")
def add_metrics(cid: int, date: str, views: int = 0, likes: int = 0, comments: int = 0, clicks: int = 0):
    conn = db()
    conn.execute("""INSERT INTO metrics_daily (campaign_id, date, views, likes, comments, clicks)
                    VALUES (?,?,?,?,?,?)
                    ON CONFLICT (campaign_id, date)
                    DO UPDATE SET views=views+excluded.views, likes=likes+excluded.likes,
                                  comments=comments+excluded.comments, clicks=clicks+excluded.clicks""",
                 (cid, date, views, likes, comments, clicks))
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/stats/overview")
def stats_overview():
    conn = db()
    r = conn.execute("""
        SELECT
          (SELECT COUNT(*) FROM campaigns) as campaigns,
          (SELECT COUNT(*) FROM contents) as contents,
          (SELECT COUNT(*) FROM contents WHERE status='posted') as posted,
          (SELECT COUNT(*) FROM contents WHERE status='pending') as pending,
          (SELECT COALESCE(SUM(views),0) FROM metrics_daily) as views,
          (SELECT COALESCE(SUM(likes),0) FROM metrics_daily) as likes,
          (SELECT COALESCE(SUM(comments),0) FROM metrics_daily) as comments
    """).fetchone()
    conn.close()
    return dict(r)


# ── 프론트 ─────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index():
    html = (BASE / "src" / "web" / "viral_site.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)
