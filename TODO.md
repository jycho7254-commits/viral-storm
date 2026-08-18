# Viral Storm — TODO

> 매 작업 완료 시 이 파일을 갱신합니다. (마지막 갱신: 2026-08-18)

## 📊 진행률

| Phase | 진행률 | 상태 |
|-------|--------|------|
| Phase 1: AI 글 생성 엔진 | 100% | ✅ 완료 |
| Phase 2: 플랫폼 자동화 | 85% | 🔧 개발 중 |
| Phase 3: 웹 대시보드 + API | 80% | 🔧 개발 중 |
| Phase 4: 스케줄러 + 자동화 | 30% | 🔧 개발 중 |
| Phase 5: 성과 추적 | 0% | ⏸ 대기 |

---

## ✅ 완료된 작업

### Phase 1: AI 글 생성 엔진
- [x] 5종 페르소나 정의 (`config/personas.yaml`)
- [x] AI 냄새 제거 모듈 (`humanizer.py`)
- [x] 글 생성 + 품질 검증 파이프라인 (`content_generator.py`)
- [x] 사전 리서치 필수화 (`game_research.py`) — 08-15
- [x] 스타일 샘플 주입 (실제 블로그 3개 학습)
- [x] 마크다운 금지 + strip_markdown 후처리 — 08-15
- [x] 트릭컬 리바이브 E2E 발행 성공 (1768자+이미지3장) — 08-15

### Phase 2: 플랫폼 자동화
- [x] 네이버 블로그 자동화 (`NaverBlogAutomation`) — 좌표입력/2단계발행/paste이미지 확립
- [x] DC 인사이드 자동화 (`DCAutomation`)
- [x] **DC 프록시 지원 (http/socks5)** — 08-18, 신규 IP세션 분리
- [x] 아카라이브 자동화 (`ArcaAutomation`)
- [x] **채널별 실행 러너 (`viral_run.py`)** — 08-18, naver/dc/shorts/all + DB 제목추출
- [x] 네이버 바이럴 전용 블로그 개설 (gamereviewlab) — 08-14

### Phase 3: 웹 대시보드 + API
- [x] FastAPI 백엔드 (`src/api/main.py`)
- [x] 캠페인 CRUD / 콘텐츠 생성·발행 API
- [x] 웹 대시보드 UI (`src/web/index.html`)

### 🎬 유튜브 숏츠 파이프라인 — 08-18 구축
- [x] **무료 AI 영상 MCP 조사 완료** — 기성 MCP 전부 조건미충족(영어전용/유료), edge-tts+FFmpeg 자체구축 확정
- [x] shorts_maker.py — 한국어 TTS(3음성) + Ken Burns 줌 + 한글자막 + xfade
- [x] 실게임 스크린샷 수집 (Google Play w1067 세로)
- [x] 트릭컬 테스트 영상 제작 검증 (20초/1080x1920/4.2MB, 자막+오디오 정상)
- [x] youtube_upload.py — Data API v3 업로드 모듈 (unlisted 기본)
- [x] FFmpeg 9.0 설치 (winget)

---

## 🔧 진행 중 / 다음 작업

### 즉시 가능 (2호 단독)
- [ ] X 계정 잠금 해제 후 세션 저장
- [ ] OMP: 생성 글 9개 품질 검증 (AI 냄새 체크)
- [ ] 캠페인 통계 차트 (Chart.js)
- [ ] 숏츠 BGM 믹싱 (나레이션+배경음 볼륨 블렌딩)
- [ ] 숏츠 대본 자동 생성 (content_generator youtube 포맷 연결)
- [ ] 발행 스케줄러 (APScheduler) + 시간대 분산

### 명훈 준비물 필요
- [ ] **Oracle Cloud 가입** (영구무료, 신용카드 등록) → DC 프록시 인스턴스 — 가입 후 2호가 Squid 세팅
- [ ] **YouTube OAuth client_secret.json** — Google Cloud Console → viral-storm/config/ 에 저장 → 2호가 --auth 연결
- [ ] DC/아카 신규 계정 정보 (프록시 발급 후)

### Phase 4: 스케줄러 + 자동화
- [ ] APScheduler 통합
- [ ] 시간대별 자동 발행
- [ ] 계정 풀 로테이션
- [ ] 랜덤 딜레이 (사람처럼)
- [ ] 프록시 IP 로테이션

### Phase 5: 성과 추적
- [ ] 조회수/좋아요 추적
- [ ] 플랫폼별 성과 비교
- [ ] A/B 테스트 (페르소나별)
- [ ] 일일/주간 리포트

---

## 🔴 차단 사항 (Blocker)

| 항목 | 원인 | 해결 방법 | 담당 |
|------|------|----------|------|
| **DC 프록시 서버 없음** | 무료 프록시 전부 실패(08-15 실측) | Oracle Cloud 가입 → Squid 설치 | 명훈 가입 → 2호 세팅 |
| **숏츠 자동 업로드 불가** | OAuth 시크릿 없음 | Google Cloud Console에서 JSON 발급 | 명훈 |
| **X 계정 잠금** | 로그인 시도 누적 | 시간 경과 또는 본인 확인 | 명훈 |

---

## 📝 작업 이력

- **08-18**: 숏츠 파이프라인 구축(TTS/렌더/자막 검증), DC 프록시 지원, viral_run 러너, 무료 MCP 조사, 매일 10시 진행보고 크론 시작
- **08-15**: 사전 리서치 필수화, E2E 발행 성공, 마크다운 사고 해결, 이미지 paste 방식 확립
- **08-14**: 바이럴 전용 블로그 개설 (gamereviewlab)
