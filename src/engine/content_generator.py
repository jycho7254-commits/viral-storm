# -*- coding: utf-8 -*-
"""
Viral Storm — AI 글 생성 엔진 (Core)
5종 페르소나, AI 냄새 제거, 품질 검증 파이프라인
"""
import json, os, re, random, time, urllib.request, ssl

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

# === AI 모델 설정 ===
ZAI_API_KEY = os.environ.get('GLM_API_KEY', '11a4e2078eda4b91a39ae7c28e2d28bd.LTmBqMWJEy99yVVK')
ZAI_BASE_URL = os.environ.get('GLM_BASE_URL', 'https://api.z.ai/api/coding/paas/v4')

# === AI 냄새 제거용 후처리 ===
AI_PATTERNS = {
    # AI가 자주 쓰는 표현 → 자연스러운 표현
    r'첫째로': '우선',
    r'둘째로': '그리고',
    r'셋째로': '마지막으로',
    r'결론적으로': '결국',
    r'종합적으로': '전체적으로 보면',
    r'따라서': '그래서',
    r'또한': '그리고',
    r'더불어': '추가로',
    r'이러한': '이런',
    r'바탕으로': '기반으로',
    r'획기적인': '완전 새로운',
    r'혁신적인': '신박한',
    r'최적화된': '딱 맞는',
    r'고도화된': '좋은',
    r'다양한': '여러',
    r'다양하게': '여러 가지로',
    r'용이하게': '쉽게',
    r'용이하다': '쉽다',
    r'효율적': '효율적이',  # trailing 처리
    r'것입니다': '거예요',
    r'입니다\.': '이에요.',
    r'합니다\.': '해요.',
    r'습니다\.': '어요.',
    r'습니다,': '어요,',
    r'습니다': '어요',
}

# 감탄사 / 구어체 주입용
EXCLAMATIONS = ['와', '대박', '진짜', '헐', '미쳤다', '개꿀', '존맛', '씹찢', '개좋음']
COLLOQUIAL_ENDINGS = ['~더라고요', '~임', '~하는 거', '~했음', '~같음', '~것 같음', '~드래요']
INTENTIONAL_TYPOS = [('재밌다', '재미따'), ('좋다', '좋다ㅋ'), ('어려워', '어려워ㅠ'), ('힘들다', '힘듦')]

def remove_ai_smell(text):
    """AI 냄새 제거 — 패턴 치환"""
    for pattern, replacement in AI_PATTERNS.items():
        text = re.sub(pattern, replacement, text)
    
    # 너무 완벽한 문장 끊기 — 일부 문장 끝에 구어체 추가
    sentences = text.split('. ')
    result = []
    for i, sent in enumerate(sentences):
        # 3문장마다 감탄사나 구어체 추가
        if i > 0 and i % 4 == 0:
            sent = sent.rstrip('.') + random.choice([' ㅋㅋ', ' ㅎㅎ', ' (웃음)', '']).rstrip() + '.'
        result.append(sent)
    
    return '. '.join(result)

def add_human_imperfection(text):
    """인간적 불완전성 추가"""
    # 의도적 오타 0~1개
    if random.random() < 0.3:
        for original, typo in INTENTIONAL_TYPOS:
            if original in text:
                text = text.replace(original, typo, 1)
                break
    
    # 문장 길이 다양화 (Burstiness)
    # 너무 긴 문장(60자+)은 중간에 끊기
    sentences = text.split('\n')
    result = []
    for sent in sentences:
        if len(sent) > 80 and random.random() < 0.4:
            mid = len(sent) // 2
            # 자연스러운 끊기 지점 찾기
            for delim in [', ', ' 그리고 ', ' 근데 ', ' 데 ', '서 ']:
                idx = sent.find(delim, mid - 15)
                if idx > 0:
                    result.append(sent[:idx + len(delim)].strip())
                    result.append(sent[idx + len(delim):].strip())
                    break
            else:
                result.append(sent)
        else:
            result.append(sent)
    
    return '\n'.join(result)

def check_quality(text, game_name, min_chars=800, max_chars=3000):
    """품질 검증"""
    issues = []
    
    # 글자 수
    char_count = len(text.replace(' ', ''))
    if char_count < min_chars:
        issues.append(f'글자 수 부족: {char_count}자 (최소 {min_chars}자)')
    if char_count > max_chars:
        issues.append(f'글자 수 초과: {char_count}자 (최대 {max_chars}자)')
    
    # 키워드 밀도
    keyword_count = text.count(game_name)
    text_length = len(text.replace(' ', ''))
    density = keyword_count / max(text_length, 1) * 100
    
    if density > 5:
        issues.append(f'키워드 밀도 과다: {density:.1f}% (게임명 {keyword_count}회)')
    if density < 0.5 and keyword_count < 2:
        issues.append(f'키워드 부족: {keyword_count}회')
    
    # AI 냄새 패턴 확인
    ai_smell_count = 0
    for pattern in ['첫째로', '둘째로', '결론적으로', '종합적으로', '것입니다']:
        if pattern in text:
            ai_smell_count += 1
    
    if ai_smell_count > 0:
        issues.append(f'AI 냄새 패턴 {ai_smell_count}개 발견')
    
    return {
        'pass': len(issues) == 0,
        'issues': issues,
        'char_count': char_count,
        'keyword_count': keyword_count,
        'keyword_density': round(density, 2)
    }


def call_ai(prompt, system_prompt='', temperature=0.8, max_tokens=2000):
    """Z.AI GLM API 호출"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    messages = []
    if system_prompt:
        messages.append({'role': 'system', 'content': system_prompt})
    messages.append({'role': 'user', 'content': prompt})
    
    data = json.dumps({
        'model': 'glm-5.2',
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'top_p': 0.9
    }).encode()
    
    url = ZAI_BASE_URL.rstrip('/') + '/chat/completions'
    req = urllib.request.Request(url, data=data, headers={
        'Authorization': f'Bearer {ZAI_API_KEY}',
        'Content-Type': 'application/json'
    })
    
    resp = urllib.request.urlopen(req, timeout=60, context=ctx)
    result = json.loads(resp.read())
    
    return result['choices'][0]['message']['content']


def generate_content(game_info, persona, platform='blog'):
    """게임 정보 + 페르소나로 콘텐츠 생성"""
    
    # 플랫폼별 길이 설정
    platform_config = {
        'blog': {'min': 1500, 'max': 2500, 'format': '블로그 포스팅'},
        'twitter': {'min': 50, 'max': 280, 'format': '트위터 트윗'},
        'dc': {'min': 200, 'max': 1000, 'format': '커뮤니티 게시글'},
        'arca': {'min': 200, 'max': 1000, 'format': '커뮤니티 게시글'},
        'youtube': {'min': 100, 'max': 500, 'format': 'YouTube Shorts 대본'},
    }
    
    cfg = platform_config.get(platform, platform_config['blog'])
    
    # 시스템 프롬프트 — 페르소나 주입
    system = f"""너는 {persona['name']}이야. {persona['description']}

{persona['tone']}

절대 AI처럼 쓰지 마. 다음 규칙을 반드시 지켜:
1. "첫째로, 둘째로" 같은 나열 금지
2. "혁신적", "획기적", "최적화" 같은 마케팅 용어 금지
3. 완벽한 문장 구조 금지 (자연스러운 끊김 허용)
4. "~습니다/입니다" 남용 금지 ("~했어요", "~더라고요", "~임" 혼용)
5. 감정이 없는 객관적 서술 금지
6. 같은 단어 반복 금지
7. 개인적인 경험이나 느낌을 반드시 포함할 것"""

    # 사용자 프롬프트
    user = f"""다음 게임에 대한 {cfg['format']}을 작성해.

게임명: {game_info.get('name', '')}
장르: {game_info.get('genre', '')}
플랫폼: {game_info.get('platform', '')}
연령등급: {game_info.get('age_rating', '')}
소개: {game_info.get('description', '')}
핵심 특징: {game_info.get('features', '')}
경쟁작: {game_info.get('competitors', '')}

조건:
- 글자 수: {cfg['min']}~{cfg['max']}자
- 게임명 "{game_info.get('name', '')}" 자연스럽게 3~5회 언급
- {'제목 포함 (호기심 유발)' if platform != 'twitter' else '해시태그 2~3개'}
- {'장단점 솔직 평가 포함' if platform == 'blog' else ''}
- {'댓글 유도 마무리' if platform in ['blog', 'dc', 'arca'] else ''}

진짜 사람이 쓴 것처럼 자연스럽게 써. 게임을 실제로 해본 것처럼."""

    try:
        # 3회 생성 후 최고 품질 선택
        candidates = []
        max_attempts = 3 if platform == 'blog' else 1  # 블로그만 3회, 나머지 1회
        for attempt in range(max_attempts):
            raw = call_ai(user, system, temperature=0.8 + random.uniform(-0.1, 0.1))
            
            # AI 냄새 제거
            cleaned = remove_ai_smell(raw)
            cleaned = add_human_imperfection(cleaned)
            
            # 품질 검증
            quality = check_quality(cleaned, game_info.get('name', ''), 
                                   min_chars=max(100, cfg['min'] - 500),
                                   max_chars=cfg['max'] + 500)
            
            candidates.append({
                'text': cleaned,
                'quality': quality,
                'attempt': attempt + 1
            })
            
            print(f'  후보 {attempt+1}: {quality["char_count"]}자, 통과={quality["pass"]}, 이슈={len(quality["issues"])}')
        
        # 품질이 가장 좋은 것 선택
        best = max(candidates, key=lambda x: (x['quality']['pass'], x['quality']['char_count']))
        
        return {
            'text': best['text'],
            'quality': best['quality'],
            'persona': persona['id'],
            'platform': platform,
            'candidates_generated': len(candidates)
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'text': '',
            'persona': persona['id'],
            'platform': platform
        }


def load_personas():
    """페르소나 설정 로드"""
    import yaml
    path = os.path.join(CONFIG_DIR, 'personas.yaml')
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('personas', [])


def run_campaign(game_info, platforms=None, posts_per_platform=1):
    """캠페인 실행 — 전체 파이프라인"""
    if platforms is None:
        platforms = ['blog', 'twitter', 'dc']
    
    personas = load_personas()
    results = []
    
    for platform in platforms:
        print(f'\n{"="*40}')
        print(f'플랫폼: {platform}')
        print(f'{"="*40}')
        
        for i in range(posts_per_platform):
            # 랜덤 페르소나 선택
            persona = random.choice(personas)
            print(f'\n[{i+1}/{posts_per_platform}] 페르소나: {persona["name"]}')
            
            content = generate_content(game_info, persona, platform)
            results.append(content)
            
            if content.get('text'):
                q = content['quality']
                print(f'  결과: {q["char_count"]}자, 키워드 {q["keyword_count"]}회, 통과={q["pass"]}')
            else:
                print(f'  에러: {content.get("error", "unknown")}')
    
    return results


if __name__ == '__main__':
    # 테스트
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
            print(f'\n--- 생성 결과 ({r["persona"]}) ---')
            print(r['text'][:1000])
            print(f'\n--- 품질: {r["quality"]} ---')
