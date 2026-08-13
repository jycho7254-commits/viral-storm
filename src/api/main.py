# -*- coding: utf-8 -*-
"""
Viral Storm — FastAPI 백엔드 메인
"""
import os, sys, json, sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'viral_storm.db')
sys.path.insert(0, BASE_DIR)

app = FastAPI(title='Viral Storm API', version='1.0')

# CORS (Next.js 프론트엔드)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


# === Models ===
class GameInfo(BaseModel):
    name: str
    genre: str = ''
    platform: str = '모바일'
    age_rating: str = '전체이용가'
    description: str = ''
    features: str = ''
    competitors: str = ''

class CampaignCreate(BaseModel):
    game_name: str
    game_info: GameInfo
    platforms: List[str] = ['blog', 'twitter', 'dc']
    posts_per_day: int = 3

class GenerateRequest(BaseModel):
    campaign_id: int
    count: int = 3

class PostContent(BaseModel):
    content_id: int
    platform: str


# === DB Helper ===
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_name TEXT NOT NULL,
        game_info TEXT NOT NULL,
        platforms TEXT NOT NULL,
        posts_per_day INTEGER DEFAULT 3,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        updated_at TEXT DEFAULT (datetime('now', 'localtime'))
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campaign_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        persona TEXT,
        platform TEXT,
        char_count INTEGER,
        keyword_count INTEGER,
        quality_pass INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        posted_at TEXT,
        post_url TEXT,
        FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
    )''')
    conn.commit()
    conn.close()


# === Routes ===

@app.on_event('startup')
async def startup():
    init_db()


@app.get('/api/health')
async def health():
    return {'status': 'ok', 'time': datetime.now().isoformat()}


@app.get('/api/campaigns')
async def list_campaigns():
    """캠페인 목록"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM campaigns ORDER BY created_at DESC')
    rows = c.fetchall()
    
    result = []
    for row in rows:
        d = dict(row)
        d['game_info'] = json.loads(d['game_info'])
        d['platforms'] = json.loads(d['platforms'])
        
        # 통계
        c.execute('SELECT COUNT(*) as total, SUM(CASE WHEN status="pending" THEN 1 ELSE 0 END) as pending, SUM(CASE WHEN status="posted" THEN 1 ELSE 0 END) as posted FROM content WHERE campaign_id=?', (d['id'],))
        stats = dict(c.fetchone())
        d['stats'] = stats
        result.append(d)
    
    conn.close()
    return {'campaigns': result}


@app.post('/api/campaigns')
async def create_campaign(req: CampaignCreate):
    """캠페인 생성"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO campaigns (game_name, game_info, platforms, posts_per_day)
                 VALUES (?, ?, ?, ?)''',
              (req.game_name, req.game_info.model_dump_json(),
               json.dumps(req.platforms), req.posts_per_day))
    campaign_id = c.lastrowid
    conn.commit()
    conn.close()
    return {'id': campaign_id, 'message': f'캠페인 생성: {req.game_name}'}


@app.get('/api/campaigns/{campaign_id}')
async def get_campaign(campaign_id: int):
    """캠페인 상세"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM campaigns WHERE id=?', (campaign_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(404, '캠페인 없음')
    
    d = dict(row)
    d['game_info'] = json.loads(d['game_info'])
    d['platforms'] = json.loads(d['platforms'])
    
    # 콘텐츠 목록
    c.execute('SELECT * FROM content WHERE campaign_id=? ORDER BY created_at DESC LIMIT 20', (campaign_id,))
    d['content'] = [dict(r) for r in c.fetchall()]
    
    conn.close()
    return d


@app.delete('/api/campaigns/{campaign_id}')
async def delete_campaign(campaign_id: int):
    """캠페인 삭제"""
    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM content WHERE campaign_id=?', (campaign_id,))
    c.execute('DELETE FROM campaigns WHERE id=?', (campaign_id,))
    conn.commit()
    conn.close()
    return {'message': f'캠페인 {campaign_id} 삭제'}


@app.post('/api/campaigns/{campaign_id}/pause')
async def pause_campaign(campaign_id: int):
    """캠페인 일시정지"""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE campaigns SET status="paused" WHERE id=?', (campaign_id,))
    conn.commit()
    conn.close()
    return {'message': '일시정지'}


@app.post('/api/campaigns/{campaign_id}/resume')
async def resume_campaign(campaign_id: int):
    """캠페인 재개"""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE campaigns SET status="active" WHERE id=?', (campaign_id,))
    conn.commit()
    conn.close()
    return {'message': '재개'}


@app.post('/api/content/generate')
async def generate_content_api(req: GenerateRequest):
    """콘텐츠 생성 (비동기 백그라운드)"""
    from src.engine.content_generator import run_campaign
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT game_name, game_info, platforms FROM campaigns WHERE id=?', (req.campaign_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(404, '캠페인 없음')
    
    game_info = json.loads(row['game_info'])
    platforms = json.loads(row['platforms'])
    
    # 플랫폼당 1개씩만 생성 (빠르게)
    results = run_campaign(game_info, platforms=platforms, posts_per_platform=1)
    
    saved = 0
    for r in results:
        if r.get('text'):
            q = r['quality']
            c.execute('''INSERT INTO content 
                        (campaign_id, text, persona, platform, char_count, keyword_count, quality_pass, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')''',
                     (req.campaign_id, r['text'], r['persona'], r['platform'],
                      q['char_count'], q['keyword_count'], 1 if q['pass'] else 0))
            saved += 1
    
    conn.commit()
    conn.close()
    return {'generated': saved, 'message': f'{saved}개 콘텐츠 생성'}


@app.get('/api/content/pending')
async def get_pending(campaign_id: Optional[int] = None, platform: Optional[str] = None, limit: int = 10):
    """대기 중인 콘텐츠"""
    conn = get_db()
    c = conn.cursor()
    
    query = 'SELECT * FROM content WHERE status="pending"'
    params = []
    
    if campaign_id:
        query += ' AND campaign_id=?'
        params.append(campaign_id)
    if platform:
        query += ' AND platform=?'
        params.append(platform)
    
    query += ' ORDER BY created_at DESC LIMIT ?'
    params.append(limit)
    
    c.execute(query, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {'content': rows}


@app.get('/api/content/{content_id}')
async def get_content(content_id: int):
    """콘텐츠 상세"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM content WHERE id=?', (content_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(404, '콘텐츠 없음')
    conn.close()
    return dict(row)


@app.post('/api/content/{content_id}/post')
async def post_content(content_id: int, platform: Optional[str] = Body(None)):
    """콘텐츠 발행 (플랫폼별)"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM content WHERE id=?', (content_id,))
    row = c.fetchone()
    if not row:
        raise HTTPException(404, '콘텐츠 없음')
    
    content = dict(row)
    target_platform = platform or content['platform']
    text = content['text']
    
    result = {'success': False, 'message': '', 'platform': target_platform}
    
    # 플랫폼별 발행
    try:
        if target_platform == 'twitter':
            # X API (잠금 해제 후 활성화)
            result['message'] = 'X 발행: 계정 잠금 해제 대기 중'
            
        elif target_platform == 'blog':
            # 네이버 블로그
            from src.platforms.automation import NaverBlogAutomation
            naver = NaverBlogAutomation()
            naver.init_browser(headless=False)
            
            # 세션 확인
            if naver.check_login_status():
                # 제목 추출 (첫 줄)
                lines = text.split('\n')
                title = lines[0].replace('#', '').strip()[:50] if lines else '게임 추천'
                body = '\n'.join(lines[1:]) if len(lines) > 1 else text
                
                tags = [content.get('persona', '게임추천'), '게임후기']
                res = naver.post(title, body, tags=tags)
                result.update(res)
            else:
                result['message'] = '네이버 로그인 필요'
            
            naver.close()
            
        elif target_platform in ['dc', 'arca']:
            result['message'] = f'{target_platform} 발행: 세션 설정 필요'
            
        else:
            result['message'] = f'알 수 없는 플랫폼: {target_platform}'
            
    except Exception as e:
        result['message'] = f'발행 에러: {str(e)[:100]}'
    
    # 발행 성공 시 DB 업데이트
    if result.get('success'):
        c.execute('''UPDATE content SET status='posted', posted_at=datetime('now','localtime'), post_url=? WHERE id=?''',
                  (result.get('url', ''), content_id))
        conn.commit()
    
    conn.close()
    return result


@app.get('/api/analytics/{campaign_id}')
async def analytics(campaign_id: int):
    """캠페인 분석"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) as total FROM content WHERE campaign_id=?', (campaign_id,))
    total = c.fetchone()['total']
    
    c.execute('SELECT COUNT(*) as cnt FROM content WHERE campaign_id=? AND status="pending"', (campaign_id,))
    pending = c.fetchone()['cnt']
    
    c.execute('SELECT COUNT(*) as cnt FROM content WHERE campaign_id=? AND status="posted"', (campaign_id,))
    posted = c.fetchone()['cnt']
    
    c.execute('SELECT platform, COUNT(*) as cnt FROM content WHERE campaign_id=? GROUP BY platform', (campaign_id,))
    by_platform = {r['platform']: r['cnt'] for r in c.fetchall()}
    
    c.execute('SELECT persona, COUNT(*) as cnt FROM content WHERE campaign_id=? GROUP BY persona', (campaign_id,))
    by_persona = {r['persona']: r['cnt'] for r in c.fetchall()}
    
    conn.close()
    
    return {
        'total': total,
        'pending': pending,
        'posted': posted,
        'by_platform': by_platform,
        'by_persona': by_persona
    }


@app.get('/api/platforms/status')
async def platform_status():
    """플랫폼 연결 상태"""
    return {
        'twitter': {
            'connected': os.path.exists(os.path.join(BASE_DIR, 'config', 'x_session.json')),
            'status': '잠금 해제 대기' if not os.path.exists(os.path.join(BASE_DIR, 'config', 'x_session.json')) else '연결됨'
        },
        'naver_blog': {
            'connected': os.path.exists(os.path.join(BASE_DIR, 'config', 'naver_session.json')),
            'status': '세션 필요' if not os.path.exists(os.path.join(BASE_DIR, 'config', 'naver_session.json')) else '연결됨'
        },
        'dc_inside': {
            'connected': os.path.exists(os.path.join(BASE_DIR, 'config', 'dc_session.json')),
            'status': '세션 필요' if not os.path.exists(os.path.join(BASE_DIR, 'config', 'dc_session.json')) else '연결됨'
        },
        'arca_live': {
            'connected': os.path.exists(os.path.join(BASE_DIR, 'config', 'arca_session.json')),
            'status': '세션 필요' if not os.path.exists(os.path.join(BASE_DIR, 'config', 'arca_session.json')) else '연결됨'
        }
    }


if __name__ == '__main__':
    import uvicorn
    init_db()
    uvicorn.run(app, host='0.0.0.0', port=8000)
