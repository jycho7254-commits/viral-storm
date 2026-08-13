# -*- coding: utf-8 -*-
"""
Viral Storm — 캠페인 매니저 + 스케줄러
"""
import os, sys, json, time, random, sqlite3
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'viral_storm.db')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')

sys.path.insert(0, BASE_DIR)


def init_db():
    """DB 초기화"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        username TEXT,
        status TEXT DEFAULT 'active',
        last_used TEXT,
        total_posts INTEGER DEFAULT 0
    )''')
    
    conn.commit()
    conn.close()
    print('✅ DB 초기화 완료')


def create_campaign(game_name, game_info, platforms, posts_per_day=3):
    """캠페인 생성"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO campaigns (game_name, game_info, platforms, posts_per_day)
                 VALUES (?, ?, ?, ?)''',
              (game_name, json.dumps(game_info, ensure_ascii=False), 
               json.dumps(platforms), posts_per_day))
    
    campaign_id = c.lastrowid
    conn.commit()
    conn.close()
    
    print(f'✅ 캠페인 생성: ID={campaign_id}, 게임={game_name}')
    return campaign_id


def generate_content_batch(campaign_id, count=5):
    """캠페인용 콘텐츠 일괄 생성"""
    from src.engine.content_generator import run_campaign, load_personas
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 캠페인 정보 조회
    c.execute('SELECT game_name, game_info, platforms FROM campaigns WHERE id=?', (campaign_id,))
    row = c.fetchone()
    if not row:
        print(f'캠페인 {campaign_id} 없음')
        return
    
    game_name, game_info_json, platforms_json = row
    game_info = json.loads(game_info_json)
    platforms_list = json.loads(platforms_json)
    
    print(f'\n캠페인 {campaign_id}: {game_name}')
    print(f'생성 수량: {count}개')
    print(f'플랫폼: {platforms_list}')
    
    # 글 생성
    results = run_campaign(game_info, platforms=platforms_list, posts_per_platform=count)
    
    # DB 저장
    saved = 0
    for r in results:
        if r.get('text'):
            q = r['quality']
            c.execute('''INSERT INTO content 
                        (campaign_id, text, persona, platform, char_count, keyword_count, quality_pass, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')''',
                     (campaign_id, r['text'], r['persona'], r['platform'],
                      q['char_count'], q['keyword_count'], 1 if q['pass'] else 0))
            saved += 1
    
    conn.commit()
    conn.close()
    
    print(f'\n✅ {saved}개 콘텐츠 저장 완료 (대기 상태)')
    return saved


def get_pending_content(campaign_id=None, platform=None, limit=1):
    """업로드 대기 중인 콘텐츠 조회"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = 'SELECT * FROM content WHERE status = "pending"'
    params = []
    
    if campaign_id:
        query += ' AND campaign_id = ?'
        params.append(campaign_id)
    if platform:
        query += ' AND platform = ?'
        params.append(platform)
    
    query += ' ORDER BY RANDOM() LIMIT ?'
    params.append(limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    return rows


def mark_posted(content_id, post_url=''):
    """발행 완료 표시"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''UPDATE content SET status='posted', posted_at=datetime('now','localtime'), post_url=? WHERE id=?''',
              (post_url, content_id))
    conn.commit()
    conn.close()


def list_campaigns():
    """캠페인 목록"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM campaigns ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    
    cols = ['id', 'game_name', 'game_info', 'platforms', 'posts_per_day', 'status', 'created_at', 'updated_at']
    return [dict(zip(cols, row)) for row in rows]


def campaign_stats(campaign_id):
    """캠페인 통계"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) FROM content WHERE campaign_id=?', (campaign_id,))
    total = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM content WHERE campaign_id=? AND status="pending"', (campaign_id,))
    pending = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM content WHERE campaign_id=? AND status="posted"', (campaign_id,))
    posted = c.fetchone()[0]
    
    c.execute('SELECT platform, COUNT(*) FROM content WHERE campaign_id=? GROUP BY platform', (campaign_id,))
    by_platform = c.fetchall()
    
    conn.close()
    
    return {
        'total': total,
        'pending': pending,
        'posted': posted,
        'by_platform': dict(by_platform)
    }


def scheduler_tick():
    """스케줄러 틱 — 실행 주기마다 호출
    
    1. 대기 중인 콘텐츠 확인
    2. 하루 분량 남았으면 새로 생성
    3. 시간대에 맞으면 업로드
    """
    from src.engine.content_generator import run_campaign
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 활성 캠페인 조회
    c.execute('SELECT id, game_name, game_info, platforms, posts_per_day FROM campaigns WHERE status="active"')
    campaigns = c.fetchall()
    
    now = datetime.now()
    hour = now.hour
    
    # 업로드 시간대 (9~11시, 19~21시)
    upload_hours = [9, 10, 11, 19, 20, 21]
    
    for camp_id, game_name, game_info_json, platforms_json, posts_per_day in campaigns:
        # 오늘 업로드 수 확인
        today = now.strftime('%Y-%m-%d')
        c.execute('''SELECT COUNT(*) FROM content 
                     WHERE campaign_id=? AND status='posted' 
                     AND date(posted_at)=?''', (camp_id, today))
        posted_today = c.fetchone()[0]
        
        # 오늘 더 업로드 가능?
        if posted_today >= posts_per_day:
            continue
        
        # 대기 중인 콘텐츠 확인
        c.execute('''SELECT COUNT(*) FROM content 
                     WHERE campaign_id=? AND status='pending' ''', (camp_id,))
        pending = c.fetchone()[0]
        
        # 대기 중인 콘텐츠가 부족하면 생성
        if pending < 2:
            print(f'캠페인 {camp_id} ({game_name}): 콘텐츠 생성 필요 (대기 {pending}개)')
            # 비동기 생성은 메인 루프에서 처리
        
        # 업로드 시간이면 실행
        if hour in upload_hours and pending > 0:
            c.execute('''SELECT id, text, platform FROM content 
                         WHERE campaign_id=? AND status='pending' 
                         ORDER BY RANDOM() LIMIT 1''', (camp_id,))
            row = c.fetchone()
            if row:
                content_id, text, platform = row
                print(f'업로드 대기: 콘텐츠 {content_id} → {platform}')
                # 실제 업로드는 플랫폼 모듈에서
    
    conn.close()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Viral Storm 캠페인 매니저')
    parser.add_argument('command', choices=['init', 'create', 'generate', 'list', 'stats', 'tick'])
    parser.add_argument('--name', help='게임명')
    parser.add_argument('--genre', default='', help='장르')
    parser.add_argument('--desc', default='', help='게임 소개')
    parser.add_argument('--features', default='', help='핵심 특징')
    parser.add_argument('--competitors', default='', help='경쟁작')
    parser.add_argument('--platform', default='모바일', help='게임 플랫폼')
    parser.add_argument('--age', default='전체이용가', help='연령등급')
    parser.add_argument('--targets', nargs='*', default=['blog', 'twitter', 'dc'], help='대상 플랫폼')
    parser.add_argument('--count', type=int, default=5, help='생성 수량')
    parser.add_argument('--id', type=int, help='캠페인 ID')
    parser.add_argument('--per-day', type=int, default=3, help='하루 포스팅 수')
    
    args = parser.parse_args()
    
    if args.command == 'init':
        init_db()
    
    elif args.command == 'create':
        init_db()
        game_info = {
            'name': args.name,
            'genre': args.genre,
            'platform': args.platform,
            'age_rating': args.age,
            'description': args.desc,
            'features': args.features,
            'competitors': args.competitors
        }
        cid = create_campaign(args.name, game_info, args.targets, args.per_day)
        print(f'\n캠페인 ID: {cid}')
        print(f'콘텐츠 생성: python {sys.argv[0]} generate --id {cid} --count {args.count}')
    
    elif args.command == 'generate':
        init_db()
        generate_content_batch(args.id, args.count)
    
    elif args.command == 'list':
        init_db()
        campaigns = list_campaigns()
        for c in campaigns:
            print(f'  ID={c["id"]} | {c["game_name"]} | {c["status"]} | {c["platforms"]} | {c["created_at"]}')
    
    elif args.command == 'stats':
        init_db()
        s = campaign_stats(args.id)
        print(f'캠페인 {args.id} 통계:')
        print(f'  전체: {s["total"]}개')
        print(f'  대기: {s["pending"]}개')
        print(f'  발행: {s["posted"]}개')
        print(f'  플랫폼별: {s["by_platform"]}')
    
    elif args.command == 'tick':
        scheduler_tick()
