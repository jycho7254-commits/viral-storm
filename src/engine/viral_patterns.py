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


def _load_kr_patterns():
    """종합 패턴 (2026-09-06 마스터 v2 — 40,261건 재분석) + 한국 바이럴 101영상"""
    import json, os
    base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'learning')
    NL = chr(10)
    parts = []
    try:
        mp = json.load(open(os.path.join(base, 'master_patterns_v2.json'), encoding='utf-8'))
        sc = mp.get('숏츠_공식', {})
        parts.append("【마스터 패턴 v2 — 40,261건 종합 재분석 (2026-09-06)】" + NL
                     + "- 길이: " + str(sc.get('길이', {}).get('최적', '')) + NL
                     + "- 제목: 평균 39자, 괄호 태그 사용(상위 56% vs 하위 25%)" + NL
                     + "- 훅 순위: " + ', '.join(str(x) for x in sc.get('제목', {}).get('훅_순위', [])[:4]) + NL
                     + "- 상위 유형: " + ', '.join(str(x) for x in mp.get('숏츠_공식', {}).get('상위_쇼츠_유형', [])[:3]) + NL
                     + "- 금지: " + ', '.join(mp.get('anti_patterns', [])[:3]))
    except Exception:
        pass
    try:
        kp = json.load(open(os.path.join(base, 'kr_viral_patterns.json'), encoding='utf-8'))['핵심패턴']
        parts.append("【한국 바이럴 실측 (101영상)】" + NL
                     + "- 훅 3종: " + " / ".join(kp['한국_훅_3종']) + NL
                     + "- 제품류 공식: " + " / ".join(kp['제품류_공식']))
    except Exception:
        pass
    return NL.join(parts) if parts else None


def apply_patterns(platform: str, category: str = "game") -> str:
    """플랫폼별 프롬프트 힌트 조합"""
    parts = []
    if platform in ("youtube", "shorts"):
        parts.append("【유튜브 제목 공식 (실측 데이터 기반)】\n" + get_yt_formula(category))
        parts.append("【훅 워드】" + ", ".join(get_hook_words()))
        _kr = _load_kr_patterns()
        if _kr:
            parts.append(_kr)
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
