# Viral Storm — 바이럴 마케팅 자동화

게임/제품 바이럴 콘텐츠 자동 생성·발행 시스템 (26,222건 실측 코퍼스 학습)

## 아키텍처 (08-24 기준)

```
src/
├── engine/
│   ├── content_generator.py   # AI 글 생성 (플랫폼별 패턴 주입)
│   ├── shorts_maker.py        # 숏츠 제작 (TTS+BGM사이드체인+ASS자막+Ken Burns)
│   │                          # 08-24: 자막 drawtext→ASS 전환(잘림 수정), 
│   │                          #        저해상도 원본 블러배경+contain(왜곡 수정)
│   ├── wan_fast.py            # WAN 2.1 로컬 영상생성 (그룹오프로딩, 8스텝)
│   │                          # ⚠️ 한계: 1.3B 모델 — 추상장면 기괴함 해결 안됨
│   ├── hybrid_shorts.py       # WAN클립+TTS+자막 통합 파이프라인
│   ├── ai_video.py            # CogVideoX-3 API (Z.AI, $0.2/영상) — 차세대 주력 후보
│   ├── publish_scheduler.py   # 발행 스케줄러 (APScheduler, 시간대 분산)
│   ├── product_research.py    # 제품 리서치
│   └── product_images.py      # 제품 이미지 수집 (네이버)
├── publishers/                # 플랫폼 발행기 (네이버블로그 등)
├── api/                       # FastAPI 백엔드 + 웹 대시보드 (8100)
└── learning/                  # 코퍼스 수집·분석 (DC/유튜브/블로그/마케팅영상 1,023)

## 품질 학습 시스템 (08-24 신설)
- docs/AI영상_품질학습_0824.md — 레퍼런스 분석(22.9만조회 AI숏츠) + 프롬프트 전략
- data/learning/ref_ai_shorts/ — 레퍼런스 영상 보관
- 핵심 발견: 성공 AI숏츠 = "환상적 ASMR 제품시연" 콘셉트. WAN 1.3B로는 미달 → CogVideoX-3 전환 검토

## 상태
- 글: 11종 생성 (발행1/대기8) — 마크다운 정화 완료
- 영상: 제품 레이아웃 버그 2종 수정 완료 (08-24)
- 크론: 데일리보고 10시 / 코퍼스갱신 월 4시 / GMI점검 9시
```
