# -*- coding: utf-8 -*-
"""
숏츠 대본 전용 생성기 — content_generator와 shorts_maker를 연결
일반 글이 아니라 문장 단위 나레이션 스크립트를 생성:
  후킹(1~2문장) → 경험/디테일(2~3문장) → CTA(1문장)
한 문장 = 자막 1장면 = 이미지 1컷 대응
"""
import random
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

from src.engine.content_generator import call_ai, strip_markdown


def parse_script(raw: str, max_lines: int = 6) -> list:
    """AI 응답을 문장 단위로 파싱 — 번호/불릿 제거, 자연스러운 문장만"""
    text = strip_markdown(raw)
    # 번호 목록/불릿 제거
    text = re.sub(r"^\s*\d+[.)]\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*]\s*", "", text, flags=re.M)
    # 줄 단위 분리
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # 제목 같은 라인 제외 (10자 미만이거나 물음표로 끝나지 않는 첫 줄은 후킹일 수 있으니 유지)
    sentences = []
    for l in lines:
        # 문장 내부에 마침표 여러 개면 분리
        parts = re.split(r"(?<=[.!?])\s+", l)
        for p in parts:
            p = p.strip()
            if p and 5 <= len(p) <= 60:  # 자막으로 쓸 수 있는 길이
                sentences.append(p)
    return sentences[:max_lines]


def generate_shorts_script(game_info: dict, persona: dict, angle: str = None) -> dict:
    """숏츠 나레이션 스크립트 생성 — 문장 리스트 반환"""
    facts = (game_info.get("research") or {}).get("facts") or []
    facts_block = "\n".join(f"- {f}" for f in facts[:8]) if facts else "- (일반 게임 경험만 사용)"

    system = f"""너는 {persona['name']}이야. {persona['description']}
유튜브 숏츠 나레이션 스크립트를 써. 실제 게이머가 말하는 톤.

절대 규칙:
1. 한 줄이 한 자막 — 문장 하나씩 줄바꿈으로 구분
2. 첫 문장은 3초 안에 시선을 붙잡는 후킹 (질문, 충격 고백, 반박)
3. 마크다운/이모지/특수기호 금지 — 순수 텍스트만
4. 문장 길이 15~40자 (짧게 숨 쉬듯이)
5. AI 느낌 나는 단어 금지 (혁신적, 최적화, ~습니다)
6. 마지막 문장은 CTA (해보라, 댓글 유도)
"""

    user = f"""게임: {game_info.get('name', '')}
장르: {game_info.get('genre', '')}

검증된 사실:
{facts_block}

{f'앵글: {angle}' if angle else ''}

6개 문장으로 숏츠 대본을 써줘. 구조:
1번: 후킹 (질문이나 충격 고백)
2~3번: 실제 경험 디테일
4~5번: 이 게임의 진짜 매력
6번: CTA

각 문장을 한 줄씩, 번호 없이."""

    raw = call_ai(user, system, temperature=0.85, max_tokens=3000)
    lines = parse_script(raw, max_lines=6)

    return {
        "lines": lines,
        "game": game_info.get("name", ""),
        "persona": persona.get("id", ""),
        "raw_len": len(raw),
    }


if __name__ == "__main__":
    # 테스트: 트릭컬
    from src.engine.content_generator import load_personas

    personas = load_personas()
    p = random.choice(personas)
    game = {
        "name": "트릭컬 리바이브",
        "genre": "서브컬처 RPG",
        "research": {
            "facts": [
                "3등신 볼따구 캐릭터 디자인",
                "모바일 서브컬처 RPG",
                "경쟁작: 원신, 붕괴 스타레일, 니케",
                "국내 개발사 게임",
            ]
        },
    }
    r = generate_shorts_script(game, p)
    print(f"페르소나: {p['name']}")
    print(f"문장 {len(r['lines'])}개:")
    for i, l in enumerate(r["lines"], 1):
        print(f"  {i}. {l}")
