# Viral Storm — 시스템 아키텍처 v1.0

## 전체 구성도

```
┌──────────────────────────────────────────────────────────────┐
│                    웹 대시보드 (Next.js)                       │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐   │
│  │ 캠페인 생성  │  │ 플랫폼 설정  │  │ 성과 대시보드     │   │
│  │             │  │              │  │                   │   │
│  │ 게임명      │  │ ☑ X         │  │ 조회수/반응/클릭  │   │
│  │ 장르        │  │ ☑ YouTube   │  │ 플랫폼별 성과     │   │
│  │ 타겟연령대  │  │ ☑ 네이버    │  │ A/B 테스트       │   │
│  │ 게임소개    │  │ ☑ DC        │  │ 일일/주간 리포트  │   │
│  │ 경쟁작      │  │ ☑ 아카      │  │                   │   │
│  │ 핵심특징    │  │              │  │                   │   │
│  └──────┬──────┘  └──────┬───────┘  └─────────┬─────────┘   │
│         └────────┬───────┘                    │             │
│                  ▼                            │             │
│  ┌──────────────────────────────┐             │             │
│  │    캠페인 관리 + 이력        │             │             │
│  │    (진행중/완료/일시정지)    │             │             │
│  └──────────────┬───────────────┘             │             │
└─────────────────┼────────────────────────────┼─────────────┘
                  │                            │
                  ▼                            │
┌──────────────────────────────────────────────┼─────────────┐
│              백엔드 API (FastAPI)              │             │
│                  localhost:8000               │             │
│                                               │             │
│  ┌────────────────────────────────────────┐   │             │
│  │         AI 글 생성 엔진 (Core)         │   │             │
│  │                                        │   │             │
│  │  ┌──────────────────────────────────┐  │   │             │
│  │  │ Step 1: 키워드 리서치            │  │   │             │
│  │  │ - 네이버 연관검색어 수집         │  │   │             │
│  │  │ - 메인 + 서브 키워드 선정        │  │   │             │
│  │  │ - 검색량/경쟁도 분석             │  │   │             │
│  │  └──────────────────────────────────┘  │   │             │
│  │                 ▼                      │   │             │
│  │  ┌──────────────────────────────────┐  │   │             │
│  │  │ Step 2: 경쟁글 수집/분석         │  │   │             │
│  │  │ - 네이버 블로그 상위 5개 크롤링  │  │   │             │
│  │  │ - 제목/구조/키워드밀도/이미지수  │  │   │             │
│  │  │ - 베스트 댓글 패턴 분석          │  │   │             │
│  │  └──────────────────────────────────┘  │   │             │
│  │                 ▼                      │   │             │
│  │  ┌──────────────────────────────────┐  │   │             │
│  │  │ Step 3: 페르소나별 글 생성       │  │   │             │
│  │  │                                  │  │   │             │
│  │  │  ① 20대 직장인 (가벼운 후기)    │  │   │             │
│  │  │  ② 30대 게이머 (전문적 분석)    │  │   │             │
│  │  │  ③ 대학생 (열정적 리뷰)         │  │   │             │
│  │  │  ④ 일반인 (호기심 유발)         │  │   │             │
│  │  │  ⑤ 오타쿠 (깊이 있는 분석)      │  │   │             │
│  │  │                                  │  │   │             │
│  │  │  각 페르소나별 3회 생성          │  │   │             │
│  │  │  (temperature=0.8, top_p=0.9)   │  │   │             │
│  │  └──────────────────────────────────┘  │   │             │
│  │                 ▼                      │   │             │
│  │  ┌──────────────────────────────────┐  │   │             │
│  │  │ Step 4: AI 냄새 제거             │  │   │             │
│  │  │                                  │  │   │             │
│  │  │  ▶ Burstiness 조정               │  │   │             │
│  │  │    짧은 문장(5~10자) + 긴 문장   │  │   │             │
│  │  │    (40~60자) 무작위 배치          │  │   │             │
│  │  │                                  │  │   │             │
│  │  │  ▶ 구어체 주입                   │  │   │             │
│  │  │    "~더라고요", "~임", "헐"     │  │   │             │
│  │  │    감탄사, 줄임말                 │  │   │             │
│  │  │                                  │  │   │             │
│  │  │  ▶ 인간적 불완전성               │  │   │             │
│  │  │    의도적 오타 1~2개             │  │   │             │
│  │  │    ("재밌다"→"재미따")          │  │   │             │
│  │  │    비문 1개 포함                 │  │   │             │
│  │  │                                  │  │   │             │
│  │  │  ▶ 개인적 디테일                 │  │   │             │
│  │  │    시간/장소/상황 추가           │  │   │             │
│  │  │    감정 묘사                     │  │   │             │
│  │  └──────────────────────────────────┘  │   │             │
│  │                 ▼                      │   │             │
│  │  ┌──────────────────────────────────┐  │   │             │
│  │  │ Step 5: 품질 검증                │  │   │             │
│  │  │                                  │  │   │             │
│  │  │  ▶ 키워드 밀도 2~3% 확인        │  │   │             │
│  │  │  ▶ 글자 수 1,500~2,000자        │  │   │             │
│  │  │  ▶ AI 냄새 체크리스트 7항목     │  │   │             │
│  │  │  ▶ GPTZero 유사도 추정           │  │   │             │
│  │  │  ▶ 통과한 글만 업로드 큐 적재    │  │   │             │
│  │  └──────────────────────────────────┘  │   │             │
│  └────────────────────────────────────────┘   │             │
│                                               │             │
│  ┌────────────────────────────────────────┐   │             │
│  │         스케줄러 + 배포 엔진          │   │             │
│  │                                        │   │             │
│  │  - 하루 X개 업로드 (설정 가능)        │   │             │
│  │  - 시간대 분산 (9~11시, 19~21시)     │   │             │
│  │  - 플랫폼 분산 (동일 글 중복 방지)   │   │             │
│  │  - 계정 풀 로테이션                   │   │             │
│  │  - 랜덤 딜레이 (사람처럼)             │   │             │
│  └────────────────────┬───────────────────┘   │             │
│                       │                       │             │
└───────────────────────┼───────────────────────┼─────────────┘
                        │                       │
                        ▼                       │
┌───────────────────────────────────────────────┼─────────────┐
│           멀티 플랫폼 배포 엔진                 │             │
│                                                │             │
│  ┌─────────────┐  ┌─────────────────────┐    │             │
│  │ X (트위터)  │  │ YouTube Shorts      │    │             │
│  │             │  │                     │    │             │
│  │ tweepy      │  │ google-api-python   │    │             │
│  │ API v2      │  │                     │    │             │
│  │             │  │ 텍스트 → TTS        │    │             │
│  │ 스레드 생성 │  │ 이미지 → FFmpeg     │    │             │
│  │ 미디어 첨부 │  │ 세로 9:16, 60초    │    │             │
│  │             │  │ 자막 자동 생성      │    │             │
│  │ 비용: 무료  │  │ 비용: 무료          │    │             │
│  └─────────────┘  └─────────────────────┘    │             │
│                                                │             │
│  ┌─────────────────────┐  ┌─────────────────┐│             │
│  │ 네이버 블로그       │  │ DC 인사이드     ││             │
│  │                     │  │                 ││             │
│  │ 방식1: 네이버 API   │  │ Playwright      ││             │
│  │ (OAuth, SEO 페널티)│  │ + stealth       ││             │
│  │                     │  │                 ││             │
│  │ 방식2: Playwright   │  │ 캡차 서비스     ││             │
│  │ (스마트에디터 조작)│  │ (2Captcha 연동) ││             │
│  │ (SEO 우회)         │  │                 ││             │
│  │                     │  │ IP 로테이션     ││             │
│  │ 이미지 자동 업로드  │  │ 계정 풀         ││             │
│  └─────────────────────┘  └─────────────────┘│             │
│                                                │             │
│  ┌─────────────────────┐                      │             │
│  │ 아카라이브          │                      │             │
│  │                     │                      │             │
│  │ Playwright + stealth│                      │             │
│  │ Cloudflare 우회     │                      │             │
│  │ 마크다운 에디터     │                      │             │
│  │ (단순 텍스트 입력)  │                      │             │
│  └─────────────────────┘                      │             │
│                                                │             │
│  ┌──────────────────────────────────────────┐ │             │
│  │          공통 인프라                     │ │             │
│  │                                          │ │             │
│  │  - Residential Proxy (IP 로테이션)      │ │             │
│  │  - 계정 풀 관리 (다중 계정)             │ │             │
│  │  - 2Captcha API (캡차 해결)            │ │             │
│  │  - User-Agent / 지문 관리               │ │             │
│  │  - 랜덤 딜레이 (3~15초)                 │ │             │
│  └──────────────────────────────────────────┘ │             │
└───────────────────────────────────────────────┼─────────────┘
                                                │
                                                ▼
┌──────────────────────────────────────────────────────────────┐
│                    데이터 레이어                               │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ 학습 DB      │  │ 생성 글 이력 │  │ 성과 추적 DB     │   │
│  │              │  │              │  │                  │   │
│  │ 바이럴 글    │  │ 생성된 글    │  │ 업로드 로그      │   │
│  │ 경쟁글 패턴  │  │ 품질 점수    │  │ 조회수/좋아요    │   │
│  │ 키워드 DB    │  │ 페르소나 태그│  │ 클릭률           │   │
│  │ 감정 사전    │  │ 검증 결과    │  │ 플랫폼별 성과    │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## 디렉토리 구조

```
viral-storm/
├── README.md
├── ARCHITECTURE.md          # 이 파일
├── requirements.txt
├── docker-compose.yml
├── .env.example
│
├── config/
│   ├── platforms.yaml       # 플랫폼별 설정 (API키, 계정정보)
│   ├── personas.yaml        # 페르소나 5종 정의
│   └── prompts/             # 프롬프트 템플릿
│       ├── blog_post.txt    # 네이버 블로그용
│       ├── twitter.txt      # X용 (짧은 글)
│       ├── dc_post.txt      # DC/아카용 (커뮤니티 글)
│       └── youtube_script.txt # YouTube Shorts 대본
│
├── src/
│   ├── engine/              # AI 글 생성 엔진
│   │   ├── keyword_research.py   # 키워드 리서치
│   │   ├── competitor_analysis.py # 경쟁글 수집/분석
│   │   ├── content_generator.py  # 페르소나별 글 생성
│   │   ├── humanizer.py          # AI 냄새 제거
│   │   ├── quality_checker.py    # 품질 검증
│   │   └── pipeline.py           # 전체 파이프라인 orchestrator
│   │
│   ├── platforms/           # 플랫폼별 배포 모듈
│   │   ├── base.py          # 공통 인터페이스
│   │   ├── twitter_x.py     # X (tweepy)
│   │   ├── youtube.py       # YouTube Shorts (google-api)
│   │   ├── naver_blog.py    # 네이버 블로그 (API + Playwright)
│   │   ├── dc_inside.py     # DC인사이드 (Playwright)
│   │   └── arca_live.py     # 아카라이브 (Playwright)
│   │
│   ├── scheduler/           # 스케줄러
│   │   ├── campaign.py      # 캠페인 관리
│   │   ├── scheduler.py     # APScheduler 래퍼
│   │   └── account_pool.py  # 계정 풀 + IP 로테이션
│   │
│   ├── api/                 # FastAPI 백엔드
│   │   ├── main.py          # 앱 진입점
│   │   ├── routes/
│   │   │   ├── campaigns.py # 캠페인 CRUD
│   │   │   ├── content.py   # 글 생성/조회
│   │   │   └── analytics.py # 성과 조회
│   │   └── models.py        # DB 모델
│   │
│   └── web/                 # Next.js 프론트엔드
│       ├── package.json
│       ├── src/
│       │   ├── app/
│       │   │   ├── page.tsx          # 대시보드
│       │   │   ├── campaigns/        # 캠페인 관리
│       │   │   └── analytics/        # 성과 분석
│       │   └── components/
│       └── tailwind.config.js
│
├── data/
│   ├── templates/           # 글 템플릿
│   ├── personas/            # 페르소나 샘플 글
│   └── samples/             # 학습용 바이럴 글 샘플
│
└── docs/
    ├── PLATFORM_RESEARCH.md # 플랫폼별 리서치 결과
    ├── PROMPT_ENGINEERING.md # 프롬프트 엔지니어링 가이드
    └── DEPLOYMENT.md        # 배포 가이드
```

## 데이터 흐름

```
[사용자 입력]
       │
       ▼
[1. 키워드 리서치] ─── 네이버 연관검색어, 경쟁작 분석
       │
       ▼
[2. 경쟁글 수집]   ─── 네이버 블로그/커뮤니티 상위 글 크롤링
       │
       ▼
[3. 글 생성]       ─── 5종 페르소나 × 3회 = 최대 15개 후보
       │
       ▼
[4. AI 냄새 제거]  ─── Burstiness 조정, 구어체, 오타, 디테일
       │
       ▼
[5. 품질 검증]     ─── 키워드 밀도, 글자수, AI 탐지 우회
       │
       ▼
[업로드 큐]         ─── 통과한 글만 적재
       │
       ▼
[스케줄러]          ─── 시간대/플랫폼/계정 분산
       │
       ├──▶ X (트위터)
       ├──▶ YouTube Shorts
       ├──▶ 네이버 블로그
       ├──▶ DC 인사이드
       └──▶ 아카라이브
       │
       ▼
[성과 추적]         ─── 조회수, 반응, 클릭 추적
```

## 플랫폼별 구현 상세

### 1. X (트위터) — 등급 A

```python
# src/platforms/twitter_x.py
import tweepy

class TwitterPlatform:
    def __init__(self, credentials):
        self.client = tweepy.Client(
            consumer_key=credentials['consumer_key'],
            consumer_secret=credentials['consumer_secret'],
            access_token=credentials['access_token'],
            access_token_secret=credentials['access_token_secret']
        )

    def post(self, content):
        # 스레드 (최대 4 tweets)
        tweets = self._split_thread(content['text'], max_tweets=4)
        prev_id = None
        for tweet in tweets:
            resp = self.client.create_tweet(
                text=tweet,
                in_reply_to_tweet_id=prev_id,
                media_ids=self._upload_media(content.get('images', []))
            )
            prev_id = resp.data['id']
        return {'id': prev_id, 'url': f'https://x.com/user/status/{prev_id}'}
```

- **API**: v2 Free Tier (월 1,500 tweets)
- **비용**: 무료
- **라이브러리**: tweepy

### 2. YouTube Shorts — 등급 A

```python
# src/platforms/youtube.py
# 파이프라인: 텍스트 → TTS(음성) → 이미지 → FFmpeg(영상) → 업로드

class YouTubeShorts:
    def create_video(self, script_text, game_info):
        # 1. TTS 음성 생성
        audio = self._tts(script_text)
        # 2. 이미지 시퀀스 생성/수집
        images = self._get_images(game_info)
        # 3. FFmpeg로 영상 합성 (9:16, 60초 이하)
        video = self._ffmpeg_compose(audio, images, subtitles=script_text)
        # 4. YouTube Data API 업로드
        return self._upload(video, title=script_text[:50])
```

- **API**: YouTube Data API v3 (무료, 일일 10,000 units)
- **영상 생성**: FFmpeg + MoviePy
- **TTS**: edge-tts (무료) 또는 ElevenLabs
- **하루 약 6개 업로드 가능**

### 3. 네이버 블로그 — 등급 B

```python
# src/platforms/naver_blog.py
# 2가지 방식 병행:

class NaverBlog:
    def post_via_api(self, content):
        # 방식1: 네이버 블로그 API (OAuth 2.0)
        # SEO 페널티 감수, 안정적
        pass

    def post_via_playwright(self, content):
        # 방식2: Playwright로 스마트에디터 조작
        # SEO 우회 (사람이 쓴 것처럼)
        # - 네이버 로그인 (쿠키 유지)
        # - 스마트에디터에 타이핑
        # - 이미지 업로드
        # - 발행 버튼 클릭
        pass
```

### 4. DC 인사이드 — 등급 C

```python
# src/platforms/dc_inside.py
# Playwright + 캡차 서비스

class DCInside:
    def post(self, content, gallery_id):
        # 1. Playwright로 갤러리 글쓰기 페이지 접속
        # 2. 캡차 이미지 캡처 → 2Captcha API 전송
        # 3. 캡차 해결 대기 (10~30초)
        # 4. 제목 + 내용 입력
        # 5. 글 작성 버튼 클릭
        # 6. 성공 여부 확인
        pass
```

### 5. 아카라이브 — 등급 C

```python
# src/platforms/arca_live.py
# Playwright + Cloudflare 우회

class ArcaLive:
    def post(self, content, board_name):
        # 1. playwright-stealth로 Cloudflare 우회
        # 2. 로그인 (소셜 로그인 쿠키)
        # 3. 마크다운 에디터에 텍스트 입력
        # 4. 이미지 업로드 (있는 경우)
        # 5. 발행
        pass
```

## 보안 및 운영 고려사항

| 항목 | 조치 |
|------|------|
| **계정 차단 방지** | 계정 풀 (3~5개), IP 로테이션, 랜덤 딜레이 |
| **캡차** | 2Captcha API 연동 (건당 ~$0.5~3) |
| **Cloudflare** | playwright-stealth, undetected-chromedriver |
| **프록시** | Residential Proxy (IP 로테이션) |
| **글 다양성** | 동일 글 반복 업로드 금지, 변형 필수 |
| **발행 시간대** | 9~11시, 19~21시 (트래픽 피크) |

## API 엔드포인트

```
POST   /api/campaigns              # 캠페인 생성
GET    /api/campaigns              # 캠페인 목록
GET    /api/campaigns/{id}         # 캠페인 상세
POST   /api/campaigns/{id}/start   # 캠페인 시작
POST   /api/campaigns/{id}/pause   # 일시정지
DELETE /api/campaigns/{id}         # 삭제

POST   /api/content/generate       # 글 생성 (수동)
GET    /api/content/{id}           # 생성된 글 조회
GET    /api/content/pending        # 업로드 대기 글 목록

GET    /api/analytics/overview     # 전체 성과
GET    /api/analytics/{campaign_id} # 캠페인별 성과

GET    /api/platforms/status       # 플랫폼 연결 상태
POST   /api/platforms/test         # 플랫폼 연결 테스트
```

## 개발 로드맵

| Phase | 내용 | 기간 | 산출물 |
|-------|------|------|--------|
| **1** | AI 글 생성 엔진 | 1~2주 | 자연스러운 글 5종 생성 |
| **2** | X + YouTube 연동 | 1주 | 자동 포스팅 |
| **3** | 네이버 블로그 + DC + 아카 | 2주 | 5개 플랫폼 동시 |
| **4** | 웹 대시보드 | 1주 | 관리자 UI |
| **5** | 스케줄러 + 계정 풀 | 1주 | 자동 배포 |
| **6** | 성과 추적 + 최적화 | 지속 | A/B 테스트 |
