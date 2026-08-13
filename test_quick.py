# -*- coding: utf-8 -*-
"""빠른 글 생성 테스트 — 1회만"""
import os, sys
os.environ['GLM_API_KEY'] = '11a4e2078eda4b91a39ae7c28e2d28bd.LTmBqMWJEy99yVVK'
os.environ['GLM_BASE_URL'] = 'https://api.z.ai/api/coding/paas/v4'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.engine.content_generator import generate_content, load_personas
import json

personas = load_personas()
game = {
    'name': '트릭컬 리바이브',
    'genre': '서브컬처 RPG',
    'platform': '모바일 (iOS/Android)',
    'age_rating': '전체이용가',
    'description': '3등신 캐릭터가 등장하는 서브컬처 RPG',
    'features': '풀더빙, 한정캐 없음, 2주마다 업데이트',
    'competitors': '원신, 붕괴 스타레일'
}

# 1개만 빠르게
persona = personas[0]  # 직장인
print(f'페르소나: {persona["name"]}')
print(f'플랫폼: dc')
print('생성 중...')

result = generate_content(game, persona, platform='dc')

if result.get('text'):
    print(f'\n{"="*60}')
    print(result['text'])
    print(f'\n{"="*60}')
    q = result['quality']
    print(f'품질: {q["char_count"]}자, 키워드 {q["keyword_count"]}회, 통과={q["pass"]}')
else:
    print(f'에러: {result.get("error")}')
