# -*- coding: utf-8 -*-
"""10분 대기 후 에디터 재시도 → 성공 시 발행까지"""
import time
from playwright.sync_api import sync_playwright

SESSION = r'C:\Users\user\Desktop\viral-storm\config\naver_viral_session.json'
print('10분 대기 시작...')
time.sleep(600)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state=SESSION, user_agent='Mozilla/5.0', viewport={'width': 1280, 'height': 900})
    page = context.new_page()
    page.on('dialog', lambda d: d.accept())
    
    page.goto('https://blog.naver.com/PostWriteForm.naver?blogId=gamereviewlab', wait_until='load', timeout=60000)
    
    ok = False
    for i in range(24):  # 최대 2분
        time.sleep(5)
        if page.locator('.se-title-text').count() > 0:
            ok = True
            break
    
    print(f'에디터: {"성공" if ok else "실패"}')
    page.screenshot(path=r'C:\Users\user\Desktop\viral-storm\retry_result.png')
    browser.close()
