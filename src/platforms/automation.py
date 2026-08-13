# -*- coding: utf-8 -*-
"""
Viral Storm — 네이버 블로그 자동화 모듈
Playwright 기반 스마트에디터 조작 + 세션 관리
"""
import os, time, json, random
from playwright.sync_api import sync_playwright

SESSION_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'config')

class NaverBlogAutomation:
    """네이버 블로그 자동 포스팅"""
    
    def __init__(self, session_file=None):
        self.session_file = session_file or os.path.join(SESSION_DIR, 'naver_session.json')
        self.browser = None
        self.context = None
        self.page = None
    
    def init_browser(self, headless=False):
        """브라우저 초기화"""
        pw = sync_playwright().start()
        self.browser = pw.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # 세션 파일이 있으면 로드
        if os.path.exists(self.session_file):
            self.context = self.browser.new_context(
                storage_state=self.session_file,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800}
            )
            print('✅ 저장된 세션으로 브라우저 시작')
        else:
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800}
            )
            print('⚠️ 세션 없음. 로그인 필요.')
        
        # anti-bot 설정
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['ko-KR', 'ko', 'en'] });
            window.chrome = { runtime: {} };
        """)
        
        self.page = self.context.new_page()
        self._playwright = pw
    
    def login(self, naver_id, password):
        """네이버 로그인"""
        print('네이버 로그인 시도...')
        self.page.goto('https://nid.naver.com/nidlogin.login')
        time.sleep(3)
        
        # ID 입력
        id_input = self.page.wait_for_selector('#id', timeout=10000)
        id_input.click()
        self.page.keyboard.type(naver_id, delay=random.uniform(50, 150))
        time.sleep(1)
        
        # 비밀번호 입력
        pw_input = self.page.wait_for_selector('#pw', timeout=5000)
        pw_input.click()
        self.page.keyboard.type(password, delay=random.uniform(50, 150))
        time.sleep(1)
        
        # 로그인 버튼
        login_btn = self.page.wait_for_selector('button:has-text("로그인"), .btn_login', timeout=5000)
        login_btn.click()
        time.sleep(8)
        
        # 로그인 확인
        if 'nid.naver.com' not in self.page.url or 'login' not in self.page.url:
            print('✅ 네이버 로그인 성공')
            self.save_session()
            return True
        else:
            # 캡차 또는 2FA 확인
            print('⚠️ 로그인 추가 인증 필요 가능성 (캡차/2FA)')
            # 30초 대기 후 재확인
            time.sleep(15)
            if 'login' not in self.page.url:
                print('✅ 로그인 성공 (추가 인증 후)')
                self.save_session()
                return True
            return False
    
    def save_session(self):
        """세션 저장"""
        self.context.storage_state(path=self.session_file)
        print(f'세션 저장: {self.session_file}')
    
    def post(self, title, content, tags=None, images=None):
        """블로그 포스팅 작성
        
        Args:
            title: 제목
            content: 본문 (마크다운 또는 일반 텍스트)
            tags: 해시태그 리스트
            images: 이미지 파일 경로 리스트
        """
        if not self.page:
            self.init_browser()
        
        print(f'블로그 포스팅 시작: {title[:30]}...')
        
        # 1. 글쓰기 페이지로 이동
        self.page.goto('https://blog.naver.com/PostWrite.naver')
        time.sleep(5)
        
        # 로그인 확인
        if 'nid.naver.com' in self.page.url and 'login' in self.page.url:
            print('❌ 로그인 필요')
            return {'success': False, 'error': '로그인 필요'}
        
        try:
            # 2. 제목 입력
            title_input = self.page.wait_for_selector('textarea[name="title"], .se-title-textarea, [placeholder*="제목"]', timeout=10000)
            title_input.click()
            time.sleep(0.5)
            self.page.keyboard.type(title, delay=random.uniform(30, 80))
            print('✅ 제목 입력')
            time.sleep(1)
            
            # 3. 이미지 업로드 (있는 경우)
            if images:
                for img_path in images[:5]:  # 최대 5장
                    try:
                        # 이미지 업로드 버튼 또는 드래그앤드롭
                        file_input = self.page.query_selector('input[type="file"]')
                        if file_input:
                            file_input.set_input_files(img_path)
                            time.sleep(3)
                            print(f'✅ 이미지 업로드: {os.path.basename(img_path)}')
                    except Exception as e:
                        print(f'⚠️ 이미지 업로드 실패: {e}')
            
            # 4. 본문 입력
            # 스마트에디터 3.0 — contenteditable div
            body_editor = self.page.wait_for_selector(
                '.se-edit-container .se-text-paragraph, [contenteditable="true"]', 
                timeout=10000
            )
            body_editor.click()
            time.sleep(0.5)
            
            # 내용 입력 — 줄 단위로
            lines = content.split('\n')
            for i, line in enumerate(lines):
                self.page.keyboard.type(line, delay=random.uniform(20, 60))
                if i < len(lines) - 1:
                    self.page.keyboard.press('Enter')
                    time.sleep(random.uniform(0.1, 0.3))
            
            print('✅ 본문 입력')
            time.sleep(1)
            
            # 5. 해시태그 입력
            if tags:
                try:
                    tag_input = self.page.wait_for_selector(
                        '.blog2_tag_area input, [placeholder*="태그"]', timeout=5000
                    )
                    for tag in tags[:5]:
                        tag_input.click()
                        self.page.keyboard.type(tag, delay=30)
                        self.page.keyboard.press('Enter')
                        time.sleep(0.5)
                    print('✅ 해시태그 입력')
                except:
                    print('⚠️ 해시태그 입력 불가 (스마트에디터 버전 차이)')
            
            # 6. 발행 버튼 클릭
            time.sleep(2)
            
            # 발행 버튼 찾기
            publish_btn = None
            for selector in [
                'button:has-text("발행")',
                '.btn_upload',
                'button:has-text("등록")',
                'a:has-text("발행")',
                '.se-publish-button'
            ]:
                try:
                    el = self.page.wait_for_selector(selector, timeout=3000)
                    if el:
                        publish_btn = el
                        break
                except:
                    continue
            
            if publish_btn:
                # 랜덤 딜레이 (사람처럼)
                time.sleep(random.uniform(1, 3))
                publish_btn.click()
                print('✅ 발행 버튼 클릭')
                time.sleep(5)
                
                # 발행 확인
                self.page.screenshot(path=os.path.join(SESSION_DIR, '..', 'data', 'naver_post_result.png'))
                
                # URL 확인
                current_url = self.page.url
                print(f'포스팅 URL: {current_url}')
                
                return {
                    'success': True,
                    'url': current_url,
                    'title': title
                }
            else:
                print('❌ 발행 버튼 찾기 실패')
                self.page.screenshot(path=os.path.join(SESSION_DIR, '..', 'data', 'naver_error.png'))
                return {'success': False, 'error': '발행 버튼 없음'}
                
        except Exception as e:
            print(f'❌ 포스팅 에러: {e}')
            self.page.screenshot(path=os.path.join(SESSION_DIR, '..', 'data', 'naver_error.png'))
            return {'success': False, 'error': str(e)}
    
    def close(self):
        """브라우저 종료"""
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()
    
    def check_login_status(self):
        """로그인 상태 확인"""
        self.page.goto('https://blog.naver.com')
        time.sleep(3)
        
        # 로그인 버튼이 보이면 미로그인
        login_check = self.page.query_selector('a:has-text("로그인")')
        if login_check:
            return False
        return True


# === DC 인사이드 자동화 ===
class DCAutomation:
    """DC 인사이드 자동 포스팅"""
    
    def __init__(self, session_file=None):
        self.session_file = session_file or os.path.join(SESSION_DIR, 'dc_session.json')
        self.browser = None
        self.context = None
        self.page = None
    
    def init_browser(self, headless=False):
        pw = sync_playwright().start()
        self.browser = pw.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        if os.path.exists(self.session_file):
            self.context = self.browser.new_context(
                storage_state=self.session_file,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1280, 'height': 800}
            )
        else:
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1280, 'height': 800}
            )
        
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        self.page = self.context.new_page()
        self._playwright = pw
    
    def login(self, dc_id, password):
        """DC 인사이드 로그인"""
        print('DC 인사이드 로그인...')
        self.page.goto('https://sign.dcinside.com/login')
        time.sleep(3)
        
        try:
            id_input = self.page.wait_for_selector('input[name="user_id"], input[id="id"]', timeout=10000)
            id_input.fill(dc_id)
            time.sleep(1)
            
            pw_input = self.page.wait_for_selector('input[name="user_pwd"], input[type="password"]', timeout=5000)
            pw_input.fill(password)
            time.sleep(1)
            
            login_btn = self.page.wait_for_selector('button:has-text("로그인"), input[type="submit"], .btn-login', timeout=5000)
            login_btn.click()
            time.sleep(8)
            
            if 'sign.dcinside.com/login' not in self.page.url:
                print('✅ DC 로그인 성공')
                self.save_session()
                return True
            else:
                print('⚠️ DC 로그인 실패 (캡차/2FA 가능성)')
                return False
        except Exception as e:
            print(f'❌ DC 로그인 에러: {e}')
            return False
    
    def save_session(self):
        self.context.storage_state(path=self.session_file)
    
    def post(self, gallery_id, title, content):
        """DC 갤러리에 글 작성"""
        if not self.page:
            self.init_browser()
        
        print(f'DC 포스팅: 갤러리={gallery_id}, 제목={title[:30]}...')
        
        try:
            # 글쓰기 페이지로 이동
            self.page.goto(f'https://gall.dcinside.com/board/write/{gallery_id}')
            time.sleep(5)
            
            # 로그인 확인
            if 'sign.dcinside.com/login' in self.page.url:
                return {'success': False, 'error': '로그인 필요'}
            
            # 제목 입력
            title_input = self.page.wait_for_selector('input[name="subject"], #subject', timeout=10000)
            title_input.fill(title)
            time.sleep(0.5)
            
            # 본문 입력 (contenteditable 또는 textarea)
            body = self.page.query_selector('.write_textarea, [name="memo"], [contenteditable="true"]')
            if body:
                body.click()
                time.sleep(0.3)
                self.page.keyboard.type(content[:2000], delay=20)
            
            # 캡차 처리 (수동 대기)
            captcha_exists = self.page.query_selector('.captcha, #captcha, img[src*="captcha"]')
            if captcha_exists:
                print('⚠️ 캡차 감지. 30초간 수동 해결 대기...')
                self.page.screenshot(path=os.path.join(SESSION_DIR, '..', 'data', 'dc_captcha.png'))
                time.sleep(30)  # 수동 캡차 해결 대기
            
            # 등록 버튼
            submit_btn = self.page.wait_for_selector('button:has-text("등록"), input[type="submit"], .btn-write', timeout=5000)
            submit_btn.click()
            time.sleep(5)
            
            return {
                'success': 'write' not in self.page.url,
                'url': self.page.url
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def close(self):
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()


# === 아카라이브 자동화 ===
class ArcaAutomation:
    """아카라이브 자동 포스팅"""
    
    def __init__(self, session_file=None):
        self.session_file = session_file or os.path.join(SESSION_DIR, 'arca_session.json')
        self.browser = None
        self.context = None
        self.page = None
    
    def init_browser(self, headless=False):
        pw = sync_playwright().start()
        self.browser = pw.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        if os.path.exists(self.session_file):
            self.context = self.browser.new_context(
                storage_state=self.session_file,
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1280, 'height': 800}
            )
        else:
            self.context = self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                viewport={'width': 1280, 'height': 800}
            )
        
        self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)
        
        self.page = self.context.new_page()
        self._playwright = pw
    
    def save_session(self):
        self.context.storage_state(path=self.session_file)
    
    def post(self, board_slug, title, content):
        """아카라이브 게시판에 글 작성"""
        if not self.page:
            self.init_browser()
        
        print(f'아카라이브 포스팅: {board_slug}, {title[:30]}...')
        
        try:
            # 글쓰기 페이지
            self.page.goto(f'https://arca.live/b/{board_slug}/new')
            time.sleep(5)
            
            # 로그인 확인
            if 'login' in self.page.url:
                return {'success': False, 'error': '로그인 필요'}
            
            # 제목 입력
            title_input = self.page.wait_for_selector('input[name="title"], #title', timeout=10000)
            title_input.fill(title)
            time.sleep(0.5)
            
            # 본문 입력 (마크다운 에디터)
            body = self.page.wait_for_selector('textarea[name="content"], .CodeMirror-code, [contenteditable="true"]', timeout=10000)
            if body:
                body.click()
                time.sleep(0.3)
                self.page.keyboard.type(content[:5000], delay=20)
            
            # 등록
            submit_btn = self.page.wait_for_selector('button:has-text("등록"), button:has-text("작성"), .btn-submit', timeout=5000)
            submit_btn.click()
            time.sleep(5)
            
            return {
                'success': 'new' not in self.page.url,
                'url': self.page.url
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def close(self):
        if self.browser:
            self.browser.close()
        if self._playwright:
            self._playwright.stop()


if __name__ == '__main__':
    # 모듈 테스트
    print('Viral Storm 플랫폼 모듈 로드 완료')
    print('  - NaverBlogAutomation')
    print('  - DCAutomation')
    print('  - ArcaAutomation')
