# -*- coding: utf-8 -*-
"""
바이럴 패턴 지식베이스 통합 — 10,074건 학습 결과를 생성기에 주입하는 관문.
patterns_{youtube,community,blog}.json을 카테고리별 규칙으로 변환.

사용법 (content_generator / shorts_script 호출 전):
    from src.engine.viral_patterns import apply_patterns
    prompt_hint = apply_patterns('dc', category='product')
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
LEAR = BASE / "data" / "learning"


def _load(name):
    p = LEAR / name
    if p.exists():
        return json.load(open(p, encoding="utf-8"))
    return {}


YT = _load("patterns_youtube.json")
CM = _load("patterns_community.json")
BL = _load("patterns_blog.json")


def get_yt_formula(category: str = "game") -> str:
    """카테고리에 맞는 YT 제목 공식 템플릿 반환"""
    cat_map = {"fashion": "clothing", "game": "game", "platform": "site", "product": "product", "place": "etc_experience"}
    key = cat_map.get(category, "game")
    formulas = YT.get("by_category", {}).get(key, {})
    if isinstance(formulas, dict):
        tops = formulas.get("top_formulas") or formulas.get("formulas") or []
        if tops:
            return "\n".join(f"- {t if isinstance(t, str) else t.get('template', '')}" for t in tops[:4])
    all_f = YT.get("title_formulas", [])
    return "\n".join(f"- {f.get('template', '')}" for f in all_f[:4] if isinstance(f, dict))


def get_hook_words() -> list:
    return [w if isinstance(w, str) else w.get("word", "") for w in YT.get("hook_words", [])][:8]


def get_community_rules() -> str:
    rules = CM.get("title_rules", [])
    lines = []
    for r in rules:
        if isinstance(r, dict):
            lines.append(f"- {r.get('name', '')}: {r.get('detail', '')[:80]}")
        else:
            lines.append(f"- {r}")
    return "\n".join(lines[:8])


def get_blog_rules() -> str:
    formulas = BL.get("title_formulas", [])
    markers = [m.get("marker") if isinstance(m, dict) else m for m in BL.get("trust_markers", [])]
    lines = ["제목 공식:"]
    for f in formulas[:5]:
        lines.append(f"- {f.get('formula', '') if isinstance(f, dict) else f}")
    lines.append("신뢰 마커 (1~2개만): " + ", ".join([m for m in markers if m][:8]))
    return "\n".join(lines)


def get_anti_patterns() -> str:
    """안티 패턴 통합 (금지 목록)"""
    aps = []
    for src in (YT.get("anti_patterns", []), CM.get("anti_patterns", []), BL.get("anti_patterns", [])):
        for a in src:
            if isinstance(a, dict):
                aps.append(a.get("pattern") or a.get("name") or str(a)[:60])
            else:
                aps.append(str(a)[:60])
    return "\n".join(f"- {a}" for a in dict.fromkeys(aps) if a)[:1200]


def apply_patterns(platform: str, category: str = "game") -> str:
    """플랫폼별 프롬프트 힌트 조합"""
    parts = []
    if platform in ("youtube", "shorts"):
        parts.append("【유튜브 제목 공식 (실측 데이터 기반)】\n" + get_yt_formula(category))
        parts.append("【훅 워드】" + ", ".join(get_hook_words()))
    elif platform in ("dc", "arca", "community"):
        parts.append("【커뮤니티 규칙 (DC 9,428건 학습)】\n" + get_community_rules())
    elif platform in ("blog", "naver"):
        parts.append("【블로그 규칙 (네이버 상위노출 학습)】\n" + get_blog_rules())
    anti = get_anti_patterns()
    if anti:
        parts.append("【금지 패턴】\n" + anti)
    return "\n\n".join(parts)


if __name__ == "__main__":
    for pf in ["youtube", "dc", "blog"]:
        hint = apply_patterns(pf, "product")
        print(f"===== {pf} ({len(hint)}자) =====")
        print(hint[:400])
        print()
