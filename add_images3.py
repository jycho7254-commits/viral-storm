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
    
    # 커서를 본문 마지막으로
    page.evaluate('''() => {
        const paras = document.querySelectorAll('.se-text-paragraph');
        const last = paras[paras.length - 1];
        if (last) { last.scrollIntoView(); last.focus(); }
        const sel = window.getSelection();
        sel.selectAllChildren(last);
        sel.collapseToEnd();
    }''')
    time.sleep(1)
    
    # 이미지 버튼 클릭 → 숨겨진 file input에 직접 파일 지정
    page.locator('button.se-image-toolbar-button').first.click()
    time.sleep(2)
    
    file_input = page.locator('input[type="file"]').last
    try:
        file_input.set_input_files(IMAGES, timeout=10000)
        print('파일 지정 완료 — 업로드 대기')
        time.sleep(8)
    except Exception as e:
        print(f'직접 지정 실패: {str(e)[:80]}')
        # 대안: DataTransfer로 drop 이벤트 시뮬레이션
    
    page.screenshot(path=r'C:\Users\user\Desktop\viral-storm\img_direct.png')
    
    # 이미지가 본문에 들어갔는지 확인
    img_count = page.locator('.se-section-image, .se-image-wrap, img.se-image-resource').count()
    print(f'본문 이미지 섹션: {img_count}')
    
    if img_count >= 1:
        # 수정 저장
        page.mouse.click(1215, 22)
        time.sleep(4)
        page.screenshot(path=r'C:\Users\user\Desktop\viral-storm\img_save_popup.png')
        page.mouse.click(1174, 556)
        time.sleep(10)
        print('수정 발행 완료!')
    
    browser.close()
