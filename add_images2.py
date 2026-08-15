# -*- coding: utf-8 -*-
import time, json
from playwright.sync_api import sync_playwright

SESSION = r'C:\Users\user\Desktop\viral-storm\config\naver_viral_session.json'
LOGNO = '224379370553'
IMAGES = [
    r'C:\Users\user\Desktop\viral-storm\data\sol_shot1.png',
    r'C:\Users\user\Desktop\viral-storm\data\sol_shot2.png',
    r'C:\Users\user\Desktop\viral-storm\data\sol_shot3.png',
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    session_data = json.load(open(SESSION, encoding='utf-8'))
    context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', viewport={'width': 1280, 'height': 900})
    context.add_cookies(session_data['cookies'])
    page = context.new_page()
    page.on('dialog', lambda d: d.accept())
    
    page.goto(f'https://blog.naver.com/PostUpdateForm.naver?blogId=gamereviewlab&logNo={LOGNO}', wait_until='load')
    page.locator('.se-title-text').first.wait_for(state='visible', timeout=60000)
    time.sleep(3)
    try:
        page.locator('.se-help-panel-close-button').first.click(timeout=4000)
        time.sleep(1)
    except Exception:
        pass
    
    # ① 본문 마지막으로 커서 이동 (이미지가 마지막에 추가되도록)
    page.evaluate('''() => {
        const paras = document.querySelectorAll('.se-text-paragraph');
        const last = paras[paras.length - 1];
        if (last) { last.scrollIntoView(); last.focus(); }
        const sel = window.getSelection();
        sel.selectAllChildren(last);
        sel.collapseToEnd();
    }''')
    time.sleep(1)
    
    # ② 정확한 클래스로 이미지 버튼 클릭
    page.locator('button.se-image-toolbar-button').first.click()
    time.sleep(3)
    page.screenshot(path=r'C:\Users\user\Desktop\viral-storm\img_popup_check.png')
    
    # ③ 떠 있는 팝업/다이얼로그 탐색
    popups = page.evaluate('''() => {
        const out = [];
        document.querySelectorAll('[class*=popup], [class*=dialog], [class*=modal], [class*=drop]').forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.width > 100 && r.height > 50) {
                out.push({cls: el.className.toString().substring(0, 60), w: Math.round(r.width), h: Math.round(r.height)});
            }
        });
        return out.slice(0, 8);
    }''')
    print('팝업 요소:', popups)
    
    # ④ file input 존재 여부 (숨겨져 있어도)
    inputs = page.evaluate('''() => Array.from(document.querySelectorAll('input[type=file]')).map(i => ({cls: (i.className||'').toString().substring(0,40), visible: i.offsetParent !== null}))''')
    print('file inputs:', inputs)
    
    browser.close()
