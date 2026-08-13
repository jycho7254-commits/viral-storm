# -*- coding: utf-8 -*-
"""테스트 실행 스크립트"""
import os, sys
os.environ['GLM_API_KEY'] = '11a4e2078eda4b91a39ae7c28e2d28bd.LTmBqMWJEy99yVVK'
os.environ['GLM_BASE_URL'] = 'https://api.z.ai/api/coding/paas/v4'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.engine.content_generator import run_campaign

test_game = {
    'name': '트릭컬 리바이브',
    'genre': '서브컬처 RPG',
    'platform': '모바일 (iOS/Android)',
    'age_rating': '전체이용가',
    'description': '3등신 캐릭터가 등장하는 서브컬처 RPG로, 풀더빙과 깊이 있는 스토리가 특징',
    'features': '풀더빙, 3등신 볼따구 아트, 한정캐 없음, 2주마다 업데이트',
    'competitors': '원신, 붕괴 스타레일, 승리의 여신 니케'
}

print('=== Viral Storm 글 생성 엔진 테스트 ===\n')
results = run_campaign(test_game, platforms=['dc'], posts_per_platform=1)

for r in results:
    if r.get('text'):
        print(f'\n{"="*60}')
        print(f'생성 결과 (페르소나: {r["persona"]}, 플랫폼: {r["platform"]})')
        print(f'{"="*60}')
        print(r['text'])
        print(f'\n--- 품질: 글자수={r["quality"]["char_count"]}, 키워드={r["quality"]["keyword_count"]}회, 통과={r["quality"]["pass"]} ---')
        if r['quality']['issues']:
            print(f'이슈: {r["quality"]["issues"]}')
    else:
        print(f'에러: {r.get("error")}')
