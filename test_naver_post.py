# -*- coding: utf-8 -*-
"""네이버 블로그 자동 포스팅 — 안정화 버전"""
import os, sys, time, sqlite3, json
from playwright.sync_api import sync_playwright

BASE = r'C:\Users\user\Desktop\viral-storm'
DB = os.path.join(BASE, 'data', 'viral_storm.db')
SESSION = os.path.join(BASE, 'config', 'naver_session.json')
WRITE_URL = 'https://blog.naver.com/PostWriteForm.naver?blogId=jycho7253'
PUB_BTN = '.publish_btn__m9KHH'
HELP_CLOSE = '.se-help-panel-close-button'

def close_all_popups(page):
    """모든 팝업/도움말/오버레이 닫기"""
    page.evaluate('''() => {
        // 도움말 닫기
        const h = document.querySelector('.se-help-panel-close-button');
        if (h) h.click();
        // 팝업 확인/닫기
        const popups = document.querySelectorAll('.se-popup-confirm-button, .se-popup-close, .se-popup-button-confirm');
        popups.forEach(p => { try { p.click(); } catch(e){} });
        // 오버레이 숨기기
        document.querySelectorAll('.se-popup-dim, .se-popup-alert').forEach(el => {
            el.style.display = 'none';
            el.style.pointerEvents = 'none';
        });
    }''')
    time.sleep(1)

def post_to_naver(title, body):
    """네이버 블로그에 포스팅"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=SESSION,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        print(f'글쓰기 페이지 이동...')
        page.goto(WRITE_URL)
        time.sleep(10)
        
        # 팝업 닫기
        close_all_popups(page)
        print('팝업 닫기 완료')
        
        # 제목 입력 — JS로 focus 후 keyboard 입력
        page.evaluate('''() => {
            // 제목 영역 찾기 — contenteditable 또는 textarea/input
            const titleArea = document.querySelector('.se-title-textarea, [data-testid="seTitleTextarea"], h1[contenteditable], h2[contenteditable]');
            if (titleArea) { titleArea.focus(); return 'title_found'; }
            // fallback: 첫번째 contenteditable이 보이는 것
            const editables = Array.from(document.querySelectorAll('[contenteditable="true"]'));
            const visible = editables.find(e => {
                const r = e.getBoundingClientRect();
                return r.x >= 0 && r.width > 100;
            });
            if (visible) { visible.focus(); return 'first_editable'; }
            return 'not_found';
        }''')
        time.sleep(0.5)
        page.keyboard.type(title, delay=30)
        print(f'제목 입력: {title[:40]}')
        time.sleep(1)
        
        # 본문 입력 — JS로 focus
        page.evaluate('''() => {
            const body = document.querySelector('.se-text-paragraph, [data-testid="seTextParagraph"]');
            if (body) { body.focus(); body.click(); return 'body_found'; }
            return 'not_found';
        }''')
        time.sleep(0.5)
        
        # 본문 타이핑
        for line in body.split('\n')[:150]:
            if line.strip():
                page.keyboard.type(line, delay=3)
            page.keyboard.press('Enter')
        print(f'본문 입력 완료 ({len(body)}자)')
        time.sleep(2)
        
        # 스크린샷 (발행 전)
        page.screenshot(path=os.path.join(BASE, 'naver_before_publish.png'))
        
        # 발행 버튼 — JS로 직접
        page.evaluate(f'''() => {{
            const btn = document.querySelector('{PUB_BTN}');
            if (btn) btn.click();
        }}''')
        print('발행 버튼 클릭')
        time.sleep(5)
        
        # 발행 확인 팝업 (있으면)
        page.evaluate('''() => {
            const btns = document.querySelectorAll('button');
            for (const b of btns) {
                const t = b.innerText.trim();
                if ((t === '발행' || t === '확인') && b.offsetParent) {
                    b.click();
                    return;
                }
            }
        }''')
        time.sleep(10)
        
        final_url = page.url
        page.screenshot(path=os.path.join(BASE, 'naver_after_publish.png'))
        print(f'최종 URL: {final_url}')
        
        success = 'PostWriteForm' not in final_url
        browser.close()
        return success, final_url

if __name__ == '__main__':
    # DB에서 글 가져오기
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM content WHERE campaign_id=1 AND platform="blog" AND status="pending" ORDER BY id LIMIT 1')
    row = c.fetchone()
    conn.close()
    
    if not row:
        print('대기 중인 블로그 글 없음')
        sys.exit()
    
    content = dict(row)
    text = content['text']
    lines = text.strip().split('\n')
    
    # 제목 추출
    title = ''
    for line in lines:
        t = line.replace('#','').replace('*','').strip()
        if t and t != '---' and len(t) > 5:
            title = t[:80]
            break
    if not title:
        title = '트릭컬 리바이브 솔직 후기'
    
    print(f'=== 네이버 블로그 포스팅 ===')
    print(f'제목: {title}')
    print(f'본문: {len(text)}자')
    print()
    
    success, url = post_to_naver(title, text)
    
    if success:
        print(f'\n✅ 포스팅 성공! URL: {url}')
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('UPDATE content SET status="posted", posted_at=datetime("now","localtime"), post_url=? WHERE id=?', (url, content['id']))
        conn.commit()
        conn.close()
        print('DB 업데이트 완료')
    else:
        print(f'\n❌ 발행 실패 — 수동 확인 필요')
        print(f'스크린샷: naver_before_publish.png, naver_after_publish.png')
