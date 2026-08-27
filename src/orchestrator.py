# -*- coding: utf-8 -*-
"""orchestrator.py — 바이럴 스톰 v3 멀티엔진 오케스트레이터 (08-27)

E1 브레인(서칭+라이팅) / E2 스튜디오(영상) / E3 검수관 / E4 배포관
jobs 테이블 상태머신으로 단계 추적 (MoneyPrinterTurbo stop_at 방식 채택)

사용:
  python -m src.orchestrator add "나이키 에어포스" fashion --resources data/client_assets/나이키
  python -m src.orchestrator run                  # 다음 잡 1개 처리 (pending → 다음 단계로)
  python -m src.orchestrator run --stop-at script # 대본까지만
  python -m src.orchestrator status               # 잡 현황
"""
import json
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DB = BASE / "data" / "viral_storm.db"

STATES = ["pending", "writing", "rendering", "review", "approval", "posted", "failed"]


# ── 공통 ──────────────────────────────────────────
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def set_status(job_id: str, status: str, detail: str = "", **fields):
    c = conn()
    sets = ["status=?", "stage_detail=?", "updated_at=?"]
    vals = [status, detail, datetime.now().isoformat(timespec="seconds")]
    for k, v in fields.items():
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(job_id)
    c.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE job_id=?", vals)
    c.commit()
    c.close()


# ── E1 브레인: 서칭 + 라이팅 ─────────────────────
def e1_write(job) -> dict:
    """코퍼스 패턴 기반 대본 생성 — How-to/숫자형 공식 (에어포스 100개 학습 반영)"""
    category = job["category"] or "product"
    product = job["product"]

    # 카테고리별 훅 공식 (100개 학습 결과)
    formulas = {
        "fashion": [
            ("{p} 신는 사람 5가지 실수, 알고 계셨나요?", "hook", "+12%", "+15Hz"),
            ("{p}는 진짜, 뭐든 잘 어울려요", "body", "+4%", "-4Hz"),
            ("청바지? 수트? 전부 정답이에요", "pop", "+8%", "+10Hz"),
            ("하나로 코디 완성!", "pop", "+10%", "+12Hz"),
            ("디테일까지 살아있는 마감", "body", "+2%", "-6Hz"),
            ("10년을 써도 질리지 않는 클래식", "body", "+3%", "-3Hz"),
            ("지금이, 제일 싼 시즌이에요", "cta", "+15%", "+22Hz"),
        ],
        "game": [
            ("{p} 초보가 100% 저지르는 실수 5가지", "hook", "+12%", "+15Hz"),
            ("이거 모르면 완전 손해입니다", "body", "+4%", "-4Hz"),
            ("꿀팁 3가지 알려드릴게요", "pop", "+8%", "+10Hz"),
            ("출퇴근길에 딱이에요", "pop", "+10%", "+12Hz"),
            ("이 타이밍에 시작하면 개이득", "body", "+3%", "-3Hz"),
            ("지금 시작이 골든타임입니다", "cta", "+15%", "+22Hz"),
        ],
        "product": [
            ("이 {p}, AI가 아니면 못 담는 화면이에요!", "hook", "+12%", "+15Hz"),
            ("{p}는 진짜, 뭐든 잘 어울려요", "body", "+4%", "-4Hz"),
            ("이 가격에 이 퀄리티", "pop", "+10%", "+12Hz"),
            ("디테일 하나하나 미쳤습니다", "body", "+2%", "-6Hz"),
            ("지금 놓치면 다시 없을 가격", "cta", "+15%", "+22Hz"),
        ],
    }
    lines = formulas.get(category, formulas["product"])
    script = [
        {"text": t.format(p=product), "emotion": emo, "rate": rate, "pitch": pitch}
        for t, emo, rate, pitch in lines
    ]
    return {"script": script, "category": category, "formula": "howto-list-v1"}


# ── E2 스튜디오: 영상 생성 (하위 스크립트 호출) ───
def e2_render(job, script_data: dict) -> str:
    """실제 렌더는 scripts/make_short_v3 계열 재사용 — 여기선 잡 파이프라인만.
    WAN이 오래 걸리므로 이 단계가 GPU 독점 구간."""
    from src.e2_render import render as _render
    return _render(
        job_id=job["job_id"],
        product=job["product"],
        category=job["category"] or "product",
        script=script_data["script"],
        resource_dir=job["resource_dir"] or "",
    )


# ── E3 검수관 ─────────────────────────────────────
def e3_review(job, video_path: str) -> dict:
    """프레임/오디오/길이 자동검수 — 트릭컬 사고 방지 게이트"""
    from src.e3_review import review as _review
    return _review(video_path, job["category"] or "fashion")


# ── 실행기 ────────────────────────────────────────
def next_stage(job):
    s = job["status"]
    if s == "pending":
        return "writing"
    if s == "writing":
        return "rendering"
    if s == "rendering":
        return "review"
    if s == "review":
        return "approval"
    return None


def run_one(stop_at: str = None):
    c = conn()
    job = c.execute(
        "SELECT * FROM jobs WHERE status IN ('pending','writing','rendering','review') "
        "ORDER BY created_at LIMIT 1"
    ).fetchone()
    c.close()
    if not job:
        print("처리할 잡 없음")
        return

    job = dict(job)
    jid = job["job_id"]
    stage = next_stage(job)
    print(f"[{jid[:8]}] {job['product']} — {job['status']} → {stage}")

    if stage == "writing":
        data = e1_write(job)
        set_status(jid, "writing" if stop_at != "script" else "writing",
                   "E1 완료", script_json=json.dumps(data, ensure_ascii=False))
        print(f"  E1 대본 {len(data['script'])}문장 생성 ({data['formula']})")
        # stop_at=script면 여기서 대기
        if stop_at == "script":
            set_status(jid, "writing", "stop_at=script 도달 — 대기")
            return
        stage = "rendering"

    if stage == "rendering":
        script_data = json.loads(job.get("script_json") or "{}") or e1_write(job)
        set_status(jid, "rendering", "E2 시작")
        vpath = e2_render(job, script_data)
        set_status(jid, "rendering", "E2 완료", video_path=vpath)
        if stop_at == "video":
            return
        stage = "review"

    if stage == "review":
        vpath = job.get("video_path") or ""
        result = e3_review(job, vpath)
        set_status(jid, "review", f"E3: {result.get('reason', '')}",
                   review_json=json.dumps(result, ensure_ascii=False))
        if result.get("passed"):
            set_status(jid, "approval", "자동검수 통과 — 형 승인 대기")
        else:
            set_status(jid, "approval", "수동 승인 대기 (E3 자동검수 미탑재)")
        print(f"  E3: {result.get('reason', '통과')}")


def add_job(product: str, category: str, resources: str = ""):
    c = conn()
    jid = uuid.uuid4().hex[:12]
    c.execute(
        "INSERT INTO jobs (job_id, product, category, resource_dir) VALUES (?,?,?,?)",
        (jid, product, category, resources),
    )
    c.commit()
    c.close()
    print(f"잡 추가: {jid} — {product} ({category})")


def status():
    c = conn()
    rows = c.execute(
        "SELECT job_id, product, category, status, stage_detail, updated_at FROM jobs ORDER BY created_at DESC LIMIT 15"
    ).fetchall()
    c.close()
    if not rows:
        print("잡 없음")
        return
    print(f"{'ID':<10} {'제품':<18} {'상태':<10} 상세/갱신")
    for r in rows:
        print(f"{r['job_id'][:8]:<10} {r['product'][:16]:<18} {r['status']:<10} {(r['stage_detail'] or '')[:30]} ({(r['updated_at'] or '')[5:16]})")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        status()
    elif args[0] == "add":
        add_job(args[1], args[2] if len(args) > 2 else "product",
                args[3] if len(args) > 3 else "")
    elif args[0] == "run":
        stop = None
        if "--stop-at" in args:
            stop = args[args.index("--stop-at") + 1]
        run_one(stop)
    elif args[0] == "status":
        status()
