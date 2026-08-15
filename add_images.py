# -*- coding: utf-8 -*-
"""발행된 글에 이미지 3장 추가 (수정 모드)"""
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
    
    # 글 수정 모드 진입 — PostUpdateForm
    page.goto(f'https://blog.naver.com/PostUpdateForm.naver?blogId=gamereviewlab&logNo={LOGNO}', wait_until='load')
    
    # 에디터 로딩 대기
    page.locator('.se-title-text').first.wait_for(state='visible', timeout=60000)
    time.sleep(3)
    print('에디터 로딩 (수정 모드)')
    
    # 도움말 패널 닫기
    try:
        page.locator('.se-help-panel-close-button').first.click(timeout=4000)
        time.sleep(1)
    except Exception:
        pass
    
    # 툴바의 이미지 버튼 정확한 셀렉터 탐색
    img_btns = page.evaluate('''() => {
        const out = [];
        document.querySelectorAll('button').forEach(b => {
            const cls = (b.className || '').toString();
            const attr = b.outerHTML.substring(0, 150);
            if (cls.includes('image') || attr.includes('사진') || attr.includes('image')) {
                const r = b.getBoundingClientRect();
                if (r.width > 0) out.push({cls: cls.substring(0, 50), x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)});
            }
        });
        return out;
    }''')
    print('이미지 버튼 후보:', img_btns[:5])
    
    # 가장 유력한 버튼 클릭 → 파일 업로드
    added = 0
    if img_btns:
        btn = img_btns[0]
        page.mouse.click(btn['x'], btn['y'])
        time.sleep(2)
        
        # 파일 입력 대기 + 업로드 (1장씩)
        try:
            # 여러 파일 한번에
            file_input = page.locator('input[type="file"]').last
            file_input.wait_for(state='visible', timeout=8000)
            file_input.set_input_files(IMAGES)
            time.sleep(6)  # 업로드 진행
            
            # 확인 버튼 (있으면)
            for sel in ['.se-popup-button-confirm', '.se-image-dialog-confirm', '.btn_confirm']:
                try:
                    page.locator(sel).first.click(timeout=3000)
                    print(f'확인 클릭: {sel}')
                    break
                except Exception:
                    continue
            time.sleep(3)
            added = 3
        except Exception as e:
            print(f'업로드 실패: {str(e)[:80]}')
    
    print(f'추가된 이미지: {added}장')
    page.screenshot(path=r'C:\Users\user\Desktop\viral-storm\img_added.png')
    
    if added:
        # 수정 저장 (발행 버튼)
        page.mouse.click(1215, 22)
        time.sleep(4)
        page.screenshot(path=r'C:\Users\user\Desktop\viral-storm\img_publish_popup.png')
        page.mouse.click(1174, 556)
        time.sleep(10)
        print('수정 발행 완료')
    
    browser.close()
