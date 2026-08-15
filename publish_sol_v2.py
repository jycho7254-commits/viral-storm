# -*- coding: utf-8 -*-
"""SOL: enchant v2 — 검증된 정보 + 이미지 첨부 발행"""
import time, re, sqlite3
from datetime import datetime
from playwright.sync_api import sync_playwright

BASE = r'C:\Users\user\Desktop\viral-storm'
SESSION = BASE + r'\config\naver_viral_session.json'
BLOG_ID = 'gamereviewlab'
IMAGES = [
    BASE + r'\data\sol_shot1.png',   # 넷마블 로고/키아트
    BASE + r'\data\sol_shot2.png',
    BASE + r'\data\sol_shot3.png',
]

def open_editor(page, retries=3):
    """에디터 열기 — 로딩 실패 시 새로고침 재시도"""
    for i in range(retries):
        page.goto(f'https://blog.naver.com/PostWriteForm.naver?blogId={BLOG_ID}', wait_until='domcontentloaded')
        try:
            page.locator('.se-title-text').first.wait_for(state='visible', timeout=100000)
            time.sleep(3)
            return True
        except Exception:
            print(f'  에디터 로딩 실패 ({i+1}/{retries}) — 새로고침 재시도')
            time.sleep(5)
    return False

def publish_with_images(title, body, image_paths):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=SESSION, user_agent='Mozilla/5.0', viewport={'width': 1280, 'height': 900})
        page = context.new_page()

        if not open_editor(page):
            page.screenshot(path=BASE + r'\editor_failed.png')
            browser.close()
            raise RuntimeError('에디터 로딩 3회 실패')

        # 도움말 패널 닫기
        try:
            page.locator('.se-help-panel-close-button').first.click(timeout=5000)
            time.sleep(1)
        except Exception:
            pass

        # 제목
        page.locator('.se-title-text').first.click()
        time.sleep(0.5)
        page.keyboard.type(title, delay=25)
        time.sleep(1)

        # 본문 — 문단별 입력, 중간에 이미지 삽입
        lines = [l for l in body.split('\n')]
        non_empty = [l for l in lines if l.strip() and not l.startswith('#')]
        img_points = {len(non_empty)//3: 0, 2*len(non_empty)//3: 1}  # 1/3, 2/3 지점에 이미지

        body_el = page.frame_locator('#se_editor_iframe') if page.locator('#se_editor_iframe').count() else page
        # 본문 영역 클릭
        page.evaluate('''() => {
            const el = document.querySelector('.se-section-text, .se-text-paragraph');
            if (el) { el.focus(); el.click(); }
        }''')
        time.sleep(0.5)

        typed = 0
        for line in lines:
            if line.startswith('#'):
                continue
            if line.strip():
                page.keyboard.type(line, delay=3)
                typed += 1
                # 이미지 삽입 지점
                if typed in img_points:
                    img_idx = img_points[typed]
                    if img_idx < len(image_paths):
                        try:
                            # 이미지 버튼 (사진 아이콘) — 툴바에서
                            page.locator('.se-toolbar-button-image, button[data-id="image"]').first.click(timeout=5000)
                            time.sleep(2)
                            # 파일 입력
                            file_input = page.locator('input[type="file"]').last
                            file_input.set_input_files(image_paths[img_idx])
                            time.sleep(5)  # 업로드 대기
                            # 확인 버튼 (있으면)
                            try:
                                page.locator('.se-image-dialog-confirm, .se-popup-button-confirm').first.click(timeout=3000)
                            except Exception:
                                pass
                            time.sleep(2)
                            # 본문으로 포커스 복귀
                            page.evaluate('''() => {
                                const els = document.querySelectorAll('.se-text-paragraph');
                                const last = els[els.length-1];
                                if (last) { last.focus(); }
                            }''')
                            time.sleep(0.5)
                        except Exception as e:
                            print(f'  이미지 {img_idx+1} 삽입 실패: {str(e)[:60]} — 텍스트 계속')
            page.keyboard.press('Enter')

        print(f'본문 입력 완료 ({typed}줄)')
        time.sleep(2)
        page.screenshot(path=BASE + r'\v2_before_publish.png')

        # 발행
        page.mouse.click(1215, 22)
        time.sleep(4)
        page.screenshot(path=BASE + r'\v2_publish_popup.png')
        # 발행 설정 팝업의 발행 버튼
        page.mouse.click(1174, 556)
        time.sleep(12)

        final_url = page.url
        page.screenshot(path=BASE + r'\v2_after_publish.png')
        print(f'최종 URL: {final_url}')

        # logNo 추출
        page.goto(f'https://blog.naver.com/PostList.naver?blogId={BLOG_ID}')
        time.sleep(6)
        lognos = re.findall(r'logNo=(\d+)', page.content())
        logno = list(dict.fromkeys(lognos))
        print(f'logNo: {logno[:3]}')

        browser.close()
        return final_url, logno

if __name__ == '__main__':
    text = open(BASE + r'\data\sol_v2_generated.txt', encoding='utf-8').read()
    lines = text.strip().split('\n')
    title = lines[0].lstrip('# ').strip()
    body = '\n'.join(lines[1:]).strip()
    print(f'제목: {title}')
    print(f'본문: {len(body)}자, 이미지: {len(IMAGES)}장')

    url, logno = publish_with_images(title, body, IMAGES)

    # DB 기록
    conn = sqlite3.connect(BASE + r'\data\viral_storm.db')
    c = conn.cursor()
    c.execute('''INSERT INTO content (campaign_id, platform, title, body, persona, status, post_url, created_at)
                 VALUES (2, 'blog', ?, ?, 'commuter_gamer', 'posted', ?, ?)''',
              (title, body, f'https://blog.naver.com/{BLOG_ID}/{logno[0]}' if logno else url,
               datetime.now().isoformat()))
    conn.commit()
    print(f'DB 기록 완료 (id={c.lastrowid})')
    conn.close()
