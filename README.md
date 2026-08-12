# 🌩️ Viral Storm — 게임 바이럴 마케팅 자동화

AI 기반 게임 바이럴 마케팅 자동화 플랫폼. 자연스러운 글을 생성하여 다수 플랫폼에 자동 배포.

## 핵심 기능

- **AI 글 생성 엔진**: "AI 냄새"를 제거한 자연스러운 바이럴 글 자동 작성
- **멀티 플랫폼 배포**: X, YouTube Shorts, 네이버 블로그, DC인사이드, 아카라이브 동시 배포
- **스케줄러**: 하루 X개, 시간대 분산, 플랫폼 분산 자동 업로드
- **성과 추적**: 조회수, 반응, 클릭 추적

## 플랫폼별 배포 방식

| 플랫폼 | 방식 | 우회 | 등급 |
|--------|------|------|------|
| X (트위터) | API v2 (tweepy) | 불필요 | A |
| YouTube Shorts | Data API v3 + FFmpeg | 불필요 | A |
| 네이버 블로그 | OAuth API + Playwright | SEO 페널티 우회 | B |
| 아카라이브 | Playwright (stealth) | Cloudflare 우회 | C |
| DC인사이드 | Playwright (stealth) | 캡차 서비스 연동 | C |

## 기술 스택

| 계층 | 기술 |
|------|------|
| 프론트엔드 | Next.js + Tailwind |
| 백엔드 | Python FastAPI |
| AI 모델 | GLM-5.2 / GPT-4o |
| 브라우저 자동화 | Playwright + playwright-stealth |
| DB | SQLite → PostgreSQL |
| 스케줄러 | APScheduler |
| 영상 생성 | FFmpeg + MoviePy |
| 배포 | Docker |

## 게임 입력 조건

```yaml
게임명: "트릭컬 리바이브"
장르: "서브컬처 RPG"
타겟연령대: "20~30대"
타겟장르: "오타쿠, 서브컬처 팬"
게임연령등급: "전체이용가"
플랫폼: "모바일 (iOS/Android)"
플랫폼지원: "iOS, Android"
게임소개: "3등신 캐릭터가 등장하는 서브컬처 RPG..."
핵심특징: "풀더빙, 3등신 볼따구 아트, 한정캐 없음"
경쟁작: "원신, 붕괴 스타레일, 승리의 여신 니케"
```

## 빠른 시작

```bash
# 설치
pip install -r requirements.txt

# 백엔드 실행
uvicorn src.api.main:app --reload

# 프론트엔드 실행
cd src/web && npm run dev
```

## 라이선스

Private — Internal Use Only
