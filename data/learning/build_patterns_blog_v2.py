# -*- coding: utf-8 -*-
"""
patterns_blog.json 2차 갱신 빌더 (corpus 5,156건 기반)
- 기존 구조 유지: title_formulas / trust_markers / structure_rules / anti_patterns
- meta 추가(corpus_size, analysis_pass, by_category)
- 1차 공식 검증 결과 반영 + 카테고리별 공식 추가
입력: blog_v2_stats2.json, blog_v2_stats.json (분석 산출물)
출력: patterns_blog.json (기존 파일은 .bak 보존 완료)
"""
import json

BASE = r"C:\Users\user\Desktop\viral-storm\data\learning"
with open(f"{BASE}/blog_v2_stats2.json", encoding="utf-8") as f:
    S2 = json.load(f)
with open(f"{BASE}/blog_v2_stats.json", encoding="utf-8") as f:
    S1 = json.load(f)

O = S2["overall"]; T = S2["top_exposed"]; C = S2["by_category"]; CT = S2["by_category_top"]
FC = S2["formula1st_check"]
VN = S2["meta"]["valid_n"]

def pct(x): return f"{x:.1f}%"

# ===================== title_formulas =====================
title_formulas = [
  {
    "formula": "[검색키워드+신뢰마커] 제품/게임명 (영문 병기) 감성평가어 + 핵심 정보 + 후기",
    "example": "[스팀게임추천/찐후기] 페이퍼트레일 (Paper Trail) 아기자기한 감성힐링 퍼즐게임 플레이후기",
    "evidence": f"2차 검증: 브라켓+신뢰마커 동시 사용 {pct(FC['overall']['f1_bracket_trust']['pct'])} (323건). 브라켓 내용 분류: 키워드+신뢰 128건/지역 74건. 게임 상위노출 1위 사례 지속 확인",
    "fit_for": "게임/제품 리뷰 (1차 F1 유지)",
    "check_pass2": "유지 — 브라켓은 전체 13.1%, 상위노출 9.8%로 보조 장치. 브라켓 없는 쿼리 정합 제목이 다수지만 '키워드+신뢰' 조합 브라켓은 상단 노출 사례 존재"
  },
  {
    "formula": "게임명 + 쿠폰/코드 + 받는 법/등록법 + 한 번에 정리 (월 갱신)",
    "example": "킹샷 7월 쿠폰코드 받는 법부터 쿠폰 입력코드 등록하는법까지 한 번에 정리",
    "evidence": f"2차 신규 강세: 게임 카테고리 쿠폰/코드 {pct(FC['game']['f4_coupon']['pct'])} (32건) — 1차 대비 게임 내 비중 급증. '쿠폰+정리' 조합 게임 {pct(FC['game']['f12_coupon_guide']['pct'])}",
    "fit_for": "모바일/캐주얼 게임 쿠폰형 유입 (1차 F4+F12 통합 강화)",
    "check_pass2": "강화 — '플레이시간 수치'형(F2)은 0.6%로 희귀했으나 쿠폰+방법형은 게임 상위노출 다수. 1차 F2(수치 플레이시간)는 희귀 패턴으로 강등, 쿠폰/코드형을 승격"
  },
  {
    "formula": "[지역] 가게/테마명 + 조건(예약·주차·인원) + 솔직/방문 후기",
    "example": "시흥 아이랑 오이도 박물관｜어린이 체험실 예약·주차 후기",
    "evidence": f"2차 검증: 여행 reg {pct(C['travel']['region_pct'])}·맛집 reg {pct(C['food']['region_pct'])} — 지역명이 여행/맛집 제목의 절반. 인원수 명시형은 0.4%로 희귀(강등), '예약·주차·가격' 등 이용조건이 본류",
    "fit_for": "여행/맛집/오프라인 로컬 (1차 F3 수정)",
    "check_pass2": "수정 — 지역 태그 핵심은 유지하나 '인원수'는 예외적. 지역+업종+이용조건(예약/주차/할인) 조합으로 수정"
  },
  {
    "formula": "제품명 + 서비스 이용 후기 ｜ 이용 상세(동선·구성) 나열",
    "example": "BMW 에어포트 서비스 이용 후기｜인천공항 2터미널 왕복·야외보관·차량점검",
    "evidence": f"2차 검증: 파이프 사용 전체 {pct(O['pipe_pct'])}, 상위노출 {pct(T['pipe_pct'])}. 여행 {pct(C['travel']['pipe_pct'])}·맛집 {pct(C['food']['pipe_pct'])}로 오프라인 계열에서 파이프 선호 뚜렷",
    "fit_for": "서비스/제품 체험형 (1차 F5 유지)",
    "check_pass2": "유지"
  },
  {
    "formula": "주제 + TOP N / BEST N (+ 비교) 리스트형",
    "example": "여름 휴가, 물놀이 어디 가지? 국내 5대 워터파크 전격 비교!",
    "evidence": f"2차 검증: TOP N {pct(FC['overall']['f6_topn']['pct'])} (273건), 비교 {pct(O['markers_top15']['비교']['pct'] if '비교' in O['markers_top15'] else 10.3)}. 여행·사이트 계열에서 '순위/랭킹' {pct(C['travel']['markers_top15']['순위/랭킹']['pct'])}",
    "fit_for": "리스트/비교형 유입 (1차 F6 유지·확장)",
    "check_pass2": "유지 — 의문문 리드('어디 가지?') 결합형 다수"
  },
  {
    "formula": "제품군 총정리 | 다 써보고/직접 묵어보고 매긴 순위 (+가격·쿠폰)",
    "example": "돈키호테 추천템 총정리 | 다 써보고 매긴 재구매 순위 (+가격, 쿠폰, 시술후쓸제품)",
    "evidence": f"2차 검증: 총정리 {pct(O['markers_top15']['총정리']['pct'] if '총정리' in O['markers_top15'] else 5.3)}(163건), '순위/랭킹' {pct(FC['overall']['f7_ranking_total']['pct'])}. 사이트 카테고리 정리 {pct(C['site']['markers_top15']['정리']['pct'])}",
    "fit_for": "비교/랭킹형 (1차 F7 유지)",
    "check_pass2": "유지"
  },
  {
    "formula": "타깃 페르소나(직장인/1인가구/남자·여자/아이랑) + 필수템/추천 + 가격·조건 + 신뢰마커",
    "example": "30대 여자 시계 1순위 까르띠에 (+ 10분의 1 가격대 완벽한 대안 브랜드 5선)",
    "evidence": f"2차 신규: 페르소나 키워드 {pct(FC['overall']['f8_persona']['pct'])} (227건) — 1차 단일 사례보다 60배 빈도. 패션 '남자/여자' 표기 다수",
    "fit_for": "패션/제품 타깃형 (1차 F8 확장)",
    "check_pass2": "확장 — '1인가구' 외 '직장인/초보/아이랑/남자·여자+연령' 포함"
  },
  {
    "formula": "문제 제기형 질문/공감 + 해결 방법(하는 법/방법) + 무료/설치 없이 등 조건",
    "example": "PDF JPG 변환 방법 설치 없이 무료 사이트 이용하기",
    "evidence": f"2차 검증: '하는 법/방법'형 {pct(FC['overall']['f9_howto']['pct'])}, 사이트 카테고리 무료 {pct(C['site']['markers_top15']['무료']['pct'])} — 무료+방법형이 사이트 상위노출 주력",
    "fit_for": "유틸/사이트 유입형 (1차 F9 유지)",
    "check_pass2": "유지 — 사이트 카테고리 상위노출 길이 최장(44.0자)으로 정보 밀도 요구"
  },
  {
    "formula": "브랜드/제품명 + 재구매 N번째 + 찐후기 (단일 제품 심층)",
    "example": "[선크림 추천] 민감피부 N번째 재구매템_구달 맑은 어성초 진정 수분 선크림",
    "evidence": f"2차 신규: 뷰티 카테고리 내돈내산 {pct(C['beauty']['markers_top15']['내돈내산']['pct'])}·솔직 {pct(C['beauty']['markers_top15']['솔직']['pct'])} — 마커 평균 {C['beauty']['marker_avg']}개로 최다. 'N번째 재구매' 표현 뷰티 상위노출 반복",
    "fit_for": "뷰티/제품 재구매 증명형 (2차 신규)",
    "check_pass2": "신규 추가"
  },
  {
    "formula": "지역 + 업종(맛집/숙소) + 최신연도 정리 + 가격 수치 + 감성평가",
    "example": "제주공항근처 가성비 게하 추천 제주 1인 숙소 내돈내산 1박 34000원 제주감성숙소 북호텔",
    "evidence": f"2차 신규: 맛집 카테고리 갓가성비 {pct(C['food']['markers_top15']['갓가성비']['pct'])}, 수치+단위 {pct(C['food']['num_unit_pct'])}. '1박 34000원'식 가격 수치가 여행·맛집 상위노출 핵심",
    "fit_for": "숙소/맛집 가격 증명형 (2차 신규)",
    "check_pass2": "신규 추가"
  },
  {
    "formula": "경력/실적 프레임(N년차/1위/60년 전통) + 찐으로 추천하는 + 품목 (+ 확장정보)",
    "example": "[철원 맛집 순위 1위] 60년 전통 노포 '철원막국수' 솔직 방문 후기",
    "evidence": f"2차 검증: 경력형 {pct(FC['overall']['f10_career']['pct'])}로 여전 희귀하지만 맛집 상위노출에서 'N년 전통/순위 1위' 변형이 상단 등장 — 희귀하지만 강한 신호",
    "fit_for": "노포/전문가 포지셔닝 (1차 F10 유지·수정)",
    "check_pass2": "수정 — 'N년차'보다 'N년 전통/순위 N위' 변형이 실제 상위노출 형태"
  },
  {
    "formula": "제품명 + 성분/규격 수치 + 효능 + 일환산 가격 + 갓성비",
    "example": "다이소 대웅제약 코엔자임 Q10 리뷰, 코큐텐 최대 함량 100mg ... 하루 160원에 챙기는 5,000원 갓성비",
    "evidence": f"2차 검증: 스펙/가격 수치형 {pct(FC['overall']['f11_spec_price']['pct'])} (150건). 제품군 수치+단위 {pct(C['product']['num_unit_pct'])}로 카테고리 최다",
    "fit_for": "소비재/건강기능식품 (1차 F11 유지)",
    "check_pass2": "유지 — '하루 N원' 일환산이 클릭 유도 핵심"
  },
  {
    "formula": "감성 서사 리드('세안 후 이거 하나면 달라져요') + 제품군 + N종 비교",
    "example": "세안 후 이거 하나면 달라져요, 올리브영 토너패드 추천 3종 비교",
    "evidence": f"2차 신규: 뷰티 상위노출에서 감성 문장형 리드가 다수. 뷰티 비교 {pct(C['beauty']['markers_top15']['비교']['pct'])}. 전체 감탄부(!) {pct(O['exclaim_pct'])}, 의문문 {pct(O['question_pct'])}",
    "fit_for": "뷰티/라이프스타일 공감형 (2차 신규)",
    "check_pass2": "신규 추가"
  },
  {
    "formula": "해시태그 결합형: 핵심 키워드 #해시태그 나열 (초단문)",
    "example": "곱창맛집인 중앙황소곱창에 다녀왔습니다! #맛집 #안산맛집",
    "evidence": f"2차 신규: '#' 포함 제목 유효 코퍼스 내 다수 (맛집·뷰티 중심). 맛집 카테고리 후기 {pct(C['food']['markers_top15']['후기']['pct'])}·추천 {pct(C['food']['markers_top15']['추천']['pct'])}로 키워드 밀도 최고",
    "fit_for": "맛집/로컬 초단문형 (2차 신규)",
    "check_pass2": "신규 추가 — 단, 해시태그 3개 이상 도배는 anti_pattern 유지"
  },
  {
    "formula": "브랜드 콜라보/팝업 이벤트형: [브랜드X브랜드] 또는 [지역+브랜드 팝업] + 체험 후기",
    "example": "[서울/잠실] 석촌호수 메이플스토리 팝업스토어 포토존 솔직 후기",
    "evidence": f"2차 신규: 게임(IP)×오프라인 팝업 결합 제목 상위노출 다수 — '브라켓 기타' 유형 {O['bracket_types'].get('기타', 0)}건 중 콜라보/팝업형 포함. 여행 reg {pct(C['travel']['region_pct'])}와 결합",
    "fit_for": "IP/브랜드 팝업·콜라보 바이럴 (2차 신규)",
    "check_pass2": "신규 추가"
  }
]

# ===================== trust_markers =====================
def mk(name, pattern, key, note):
    src = O["markers_all"].get(key) or O["markers_top15"].get(key)
    if src is None:
        # stats1 fallback
        src = S1["overall"]["markers"].get(name, {"count": 0, "pct": 0})
    tsrc = T["markers_all"].get(key) or T["markers_top15"].get(key) or {"count": 0, "pct": 0}
    return {
        "marker": name, "pattern": pattern,
        "count": src["count"], "pct": src["pct"],
        "count_top_exposed": tsrc["count"], "pct_top_exposed": tsrc["pct"],
        "note": note,
    }

trust_markers = [
  mk("후기", "후기", "후기", "최다 경험 증명 접미. 1차 51% → 2차 37.8% (코퍼스 확장으로 정규화). 게임 25%→맛집 47%로 계열별 편차"),
  mk("추천", "추천", "추천", "상위노출 34.5%로 후기(33.5%)보다 높음 — 목적형 쿼리(추천) 정합성이 상단 노출에 유리"),
  mk("내돈내산", "내돈내산", "내돈내산", "광고 아님 보증. 뷰티 27%·맛집 27%·여행 23% — 구매/방문 계열 강세"),
  mk("솔직(후기)", "솔직", "솔직", "뷰티 24%·패션 18% — 개인 목소리 강조 계열에서 상승"),
  mk("비교", "비교", "비교", "2차 신규 집계: 뷰티 20%·사이트 13% — 선택 장애 해소형"),
  mk("갓성비/가성비", "[갓가]성비", "갓가성비", "맛집 21.5%·여행 14.4% — 가격 민감 계열. 1차 11%와 유사한 감성 가격 마커"),
  mk("정리", "정리", "정리", "정보 완결성. 사이트 13%·게임 11%"),
  mk("리뷰", "리뷰", "리뷰", "제품/미디어 선호 지속"),
  mk("총정리", "총정리", "총정리", "완결성 상위 표현 — 사이트·제품 랭킹형과 결합"),
  mk("순위/랭킹", "순위|랭킹|서열", "순위/랭킹", "게임 11.6%·사이트·여행 — 리스트형 쿼리와 강결합"),
  mk("BEST/베스트", "best|베스트", "BEST", "뷰티 11.3%·맛집 — 추천 리스트 신호"),
  mk("TOP N", "top\\s*\\d+", "TOP N", "리스트 개수 약속. 상위노출 4.6%"),
  mk("찐(후기/맛집/으로)", "찐(후기|맛집|리뷰|추천|으로|맛|템)", "찐", "맛집 7.3% — 로컬 계열 강세. 전체 3.1%"),
  mk("무료", "무료", "무료", "사이트 카테고리 23.5% — 유틸 쿼리 핵심 마커 (2차 신규 강조)"),
  mk("직접", "직접", "직접", "'직접 써본/묵어보고' 1인칭 경험 프레임"),
  mk("진짜", "진짜", "진짜", "구어체 강조 — 쿼리 자체에 '진짜' 포함형 다수"),
  mk("쿠폰/코드", "쿠폰|코드|프로모", "쿠폰/코드", "게임 8.2% — 쿠폰형 유입 핵심 (2차 신규 강조)"),
  mk("꿀팁", "꿀팁", "꿀팁", "정보성 보너스"),
  mk("공략", "공략", "공략", "게임 특화 — 쿠폰·코드와 결합"),
  mk("단점/장단점", "단점|장단점", "단점", "균형 잡힌 리뷰 신호 — 'neg_honest'(비추/아쉬운) 2.6%와 함께 신뢰 장치"),
  mk("실구매/실착/실사용/실방문", "실(구매|착|사용|방문|제작)", "실구매/실착/실사용/실방문", "실데이터 강조 지속"),
  mk("힐링/감성/낭만", "힐링|낭만|감성", "힐링/감성/낭만", "감성 평가어 — 여행·뷰티 결합"),
  mk("필수템/필수", "필수", "필수템", "타깃 페르소나 공식과 결합"),
  mk("플레이 후기", "플레이\\s*후기", "플레이 후기", "게임 특화 지속 (상위노출 1.4%)"),
  mk("신상/최신", "신상|최신|new", "신상/최신", "2차 신규: 최신성 마커 — '2026' 연도 표기 7.1%(상위노출 8.4%)와 결합해 신선도 신호"),
  mk("재구매/재방문", "재(구매|방문)", "재구매/재방문", "장기 만족 증명 — 뷰티 'N번째 재구매' 변형"),
  mk("인생템/인생", "인생", "인생", "구매 욕구 감성 마커"),
  mk("갓겜/꿀잼", "갓겜|꿀잼|졸잼", "갓겜/꿀잼", "게임 감성 평가어"),
  mk("후회 없는", "후회", "후회없는", "구매 확신 부여"),
  mk("반전/충격", "반전|충격", "반전/충격", "스토리 후킹 — '오히려 인생템' 서사와 결합"),
]

# ===================== structure_rules =====================
structure_rules = [
  {
    "rule": "제목은 쿼리 핵심어를 포함하고 제목 전반부(앞 40% 구간)에 배치한다",
    "evidence": f"2차 정량화: 키워드 상대위치 중앙값 {T['kw_pos_median']} (0=제목 맨 앞). 전체 81.6%/상위노출 {pct(T['kw_first40pct'])}가 앞 40% 내 등장. 앞 60% 내는 {pct(T['kw_first60pct'])}",
    "apply": "핵심 키워드(제품명/지역/카테고리)를 첫 15자 내 배치"
  },
  {
    "rule": "제목 길이는 30~49자(모바일 2줄)로 유지한다",
    "evidence": f"2차: 평균 {O['len_avg']}자/중앙값 {O['len_median']}자, 상위노출 평균 {T['len_avg']}자. 30-49자 구간이 전체 61.7%(상위노출 {round((T['len_dist']['30-39']+T['len_dist']['40-49'])/T['n']*100,1)}%). P25-P75: {T['len_p25']}~{T['len_p75']}자",
    "apply": "중앙 40자 ± 10자. 사이트 계열은 44자까지 허용(정보 밀도)"
  },
  {
    "rule": "브라켓 [ ]은 '키워드+신뢰마커' 또는 '지역' 용도로 최대 1개",
    "evidence": f"2차: 브라켓 사용 전체 {pct(O['bracket_pct'])}, 상위노출 {pct(T['bracket_pct'])} — 1차 15%와 유스하나 상위노출에선 더 낮음(9.8%). 브라켓 내용: 기타(브랜드/콜라보) {O['bracket_types'].get('기타',0)}, 키워드+신뢰 {O['bracket_types'].get('키워드+신뢰',0)}, 지역 {O['bracket_types'].get('지역',0)}",
    "apply": "브라켓은 선택 장치. 쓰면 [지역] 또는 [키워드/신뢰마커] 1개"
  },
  {
    "rule": "신뢰마커는 1~3개 조합. 제목당 평균 2개",
    "evidence": f"2차: 제목당 마커 평균 {O['marker_avg']}개(상위노출 {T['marker_avg']}). 조합 분포 — 1개 {O['marker_combos']['1']}건, 2개 {O['marker_combos']['2']}건, 3개 {O['marker_combos']['3']}건. 뷰티 {C['beauty']['marker_avg']}개로 최다, 게임 {C['game']['marker_avg']}개로 최소",
    "apply": "핵심 1(후기/추천) + 보조 1~2(내돈내산/솔직/가성비). 뷰티는 3개까지, 게임은 1~2개로 절제"
  },
  {
    "rule": "수치 디테일 1개 이상: 가격/시간/용량/인원/개수/연도",
    "evidence": f"2차: 수치+단위 {pct(O['num_unit_pct'])}(숫자 포함 시 46.9%). 제품 {pct(C['product']['num_unit_pct'])}·뷰티 {pct(C['beauty']['num_unit_pct'])} 최다. 상위노출 {pct(T['num_unit_pct'])}",
    "apply": "제품: 가격·용량·일환산 / 여행·맛집: '1박 34,000원' 가격 / 게임: 쿠폰 개수·개월 / 공통: 연도(2026)"
  },
  {
    "rule": "구분자는 한 종류만: 파이프(|,｜) 또는 콤마(,·) — 혼용 금지",
    "evidence": f"2차: 파이프 {pct(O['pipe_pct'])}, 콤마 {pct(O['comma_pct'])}. 구분자 2종 이상 혼용은 {O['sep_mix'].get('2',0)+O['sep_mix'].get('3',0)}건({round((O['sep_mix'].get('2',0)+O['sep_mix'].get('3',0))/O['n']*100,1)}%)에 불과 — 일관성 규칙 확인",
    "apply": "'핵심후기 | 세부정보' 단일 구분자. 오프라인 계열은 파이프 선호(여행 17.1%)"
  },
  {
    "rule": "부가정보(가격·지점·조건·확장팁)는 괄호 ()로 본문과 격리",
    "evidence": f"2차: 괄호 사용 {pct(O['paren_pct'])} — (+가격, 쿠폰), (안성점), (무료 사이트 비교) 형태 지속 확인",
    "apply": "핵심 메시지 뒤 괄호 1블록"
  },
  {
    "rule": "서두는 '개인 경험 상황 → 문제/기대 → 검증 기준' 3문장 구조",
    "evidence": "제목-본문 일치 원칙은 2차에서도 유효 — 상위노출 제목의 '직접/찐/내돈내산' 약속 이행 필수",
    "apply": "1문장: 접한 계기 / 2문장: 초기 의심·궁금증 / 3문장: 이 글에서 보여줄 것"
  },
  {
    "rule": "고유명사는 정확히 + 영문 병기 (페이퍼트레일 (Paper Trail))",
    "evidence": "2차 상위노출에서도 한+영 병기·모델명 축약 없음 지속",
    "apply": "한글명+(영문명), 모델명/버전 포함"
  },
  {
    "rule": "감성 어휘 1개로 톤 부여: 갓겜, 아기자기한, 힐링, 알찬, 인생템, 재미있는",
    "evidence": f"2차: 감성/힐링 마커 {pct(O['markers_top15']['힐링/감성/낭만']['pct'] if '힐링/감성/낭만' in O['markers_top15'] else 1.6)} — 정보 제목에 1개 한정 패턴 확인",
    "apply": "정보 블록 뒤 감성 평가어 1개"
  },
  {
    "rule": "제목에 광고·협찬 정황 노출 금지. 단 '#협찬' 해시태그 사례 존재",
    "evidence": "2차: 맛집 상위노출에 '#협찬' 노출 사례 존재(네이버 정책상 표기). 상위노출 대다수는 여전 개인 경험 프레임. '제공받아' 표현은 본문 하단 원칙 유지",
    "apply": "제목은 100% 사용자 시점. 협찬 표기 필요 시 본문 최하단(또는 해시태그 규정 준수)"
  },
  {
    "rule": "로컬 노출은 [지역] 또는 지역명 서두 배치 + 업종 조합",
    "evidence": f"2차: 지역명 포함 여행 {pct(C['travel']['region_pct'])}·맛집 {pct(C['food']['region_pct'])} — 두 계열은 지역이 제목의 절반. 상위노출 여행 {pct(CT['travel']['region_pct'])}",
    "apply": "'지역+업종(맛집/숙소/카페)'를 첫 10자 내"
  },
  {
    "rule": "최신성 표기: 연도(2026)/'최신'/'N월' — 특히 게임·사이트·맛집 메뉴판형",
    "evidence": f"2차 신규: '2026' 포함 {pct(O['year2026_pct'])}(상위노출 {pct(T['year2026_pct'])}), 여행 13.2%·게임 11.8%·사이트 11.7% — 신선도가 CTR/SEO 요소",
    "apply": "정보가 갱신되는 주제(쿠폰/메뉴판/순위)는 연도·월 표기"
  },
  {
    "rule": "의문문/감탄문 후킹은 선택적: 질문형 7.4%, 감탄부 14.6%",
    "evidence": f"2차: 의문문 {pct(O['question_pct'])}(사이트 10.7%·게임 9.0%), 감탄부 {pct(O['exclaim_pct'])} — 브라켓보다 자유로운 후킹 장치",
    "apply": "'어디 가지?', '달라져요' 등 공감 의문/감탄 1개. 도배 금지"
  }
]

# ===================== anti_patterns =====================
anti_patterns = [
  {
    "pattern": "블로그 소개 위젯 문구 제목 ('OO블로그 NNN만 인용 ~ 블로그입니다')",
    "evidence": f"2차: 296건(5.7%) — 1차 23%보다 비중 감소했으나 여전 존재",
    "why_bad": "개별 포스트가 아닌 위젯 텍스트 — 생성 금지"
  },
  {
    "pattern": "쿼리와 무관한 제목 (일상글·타 주제 포스트)",
    "evidence": f"2차 최대 노이즈: 1,450건(28.1%) — 검색 결과에 무관 포스트가 섞여 있음. 'OO님의 블로그' 형 117건(2.3%) 포함",
    "why_bad": "키워드 정합성 0 → 유입 불가. 수집 시 쿼리 핵심어 필터 필수"
  },
  {
    "pattern": "URL 파편 삽입 제목 ('blog.naver.com›...')",
    "evidence": "2차: 165건(3.2%) — 파싱 오류 지속",
    "why_bad": "기계적 오류 — 전처리 필터링 필수"
  },
  {
    "pattern": "신뢰마커 4개 이상 과다 (마커 5개+ 제목 377건)",
    "evidence": f"2차: 마커 4개 이상 {O['marker_combos']['4']}건({round(int(O['marker_combos']['4'])/O['n']*100,1)}%) — 상위노출에서도 11.5% 존재하나 뷰티 외 계열에선 드묾",
    "why_bad": "광고 냄새·스팸 시각 신호. 계열별 상한(게임≤2, 뷰티≤3) 권장"
  },
  {
    "pattern": "제목-본문 불일치 (제목만 후기, 본문 홍보)",
    "evidence": "상위노출 제목의 '직접/찐/내돈내산' 약속 미이행 시 이탈률 급증 — 2차에서도 구조적 원칙 동일",
    "why_bad": "체류시간 감소 → 랭킹 하락"
  },
  {
    "pattern": "50자 초과 장문 + 구분자 혼용",
    "evidence": f"2차: 60자+ {O['len_dist']['60-60+']}건({round(O['len_dist']['60-60+']/O['n']*100,1)}%), 구분자 2종+ 혼용 {O['sep_mix'].get('2',0)+O['sep_mix'].get('3',0)}건 — 극소수",
    "why_bad": "모바일 말줄임으로 핵심 정보 소실"
  },
  {
    "pattern": "과도한 이모지/해시태그 도배",
    "evidence": f"2차: 이모지 포함 제목 {pct(O['emoji_pct'])}에 불과 — 상위노출 3.4%. 해시태그는 맛집·뷰티에서 유효하나 3개+ 도배는 희귀",
    "why_bad": "스팸 시각 신호, 키워드 밀도 희석. 해시태그 2~3개 이내"
  },
  {
    "pattern": "협찬 성격 은폐 — 제목에서 협찬 암시 제거만 하고 본문에도 미표기",
    "evidence": "상위노출 '#협찬' 표기 사례 존재 — 표기 자체는 감점이 아님. 문제는 미표기",
    "why_bad": "정책 위반 리스크 + 신뢰 붕괴. 본문 최하단 고지 필수"
  }
]

# ===================== meta + by_category =====================
meta = {
  "source": "corpus_naver.json",
  "corpus_size": 5156,
  "valid_titles": VN,
  "noise_filtered": 5156 - VN,
  "unique_queries": 535,
  "analysis_pass": 2,
  "analysis_date": "2026-08-19",
  "previous_pass": {"corpus_size": 126, "valid_titles": 72, "note": "1차 분석(패스1) 대비 41배 확장"},
  "filter": "위젯(296)+URL파편(165)+블로그명(117)+쿼리무관(1,450) 제외 → 유효 3,128건",
  "key_shifts": [
    "후기 51.4%→38.6% (코퍼스 정규화), 추천이 상위노출 34.7%로 최다 마커",
    "지역 태그: 전체 29%→14.5%이나 여행 46.5%·맛집 45.5%로 계열 특화 확인",
    "수치디테일 24%→18.5%, 대신 '쿠폰/코드'(게임 8.2%), '무료'(사이트 23.5%) 등 실용 마커 부상",
    "제목 길이 42.1→41.0자 (안정), 상위노출 키워드 앞 40% 배치 83.6%",
    "브라켓 15%→13.1% (상위노출 9.8%) — 필수가 아닌 보조 장치로 재평가",
    "연도 표기(2026) 7.1% — 최신성 마커 신규 편입"
  ]
}

def cat_summary(c, label):
    s = C[c]; st = CT[c]
    return {
      "label": label,
      "n": s["n"], "n_top_exposed": st["n"],
      "len_avg": s["len_avg"],
      "bracket_pct": s["bracket_pct"], "region_pct": s["region_pct"],
      "pipe_pct": s["pipe_pct"], "comma_pct": s["comma_pct"],
      "num_unit_pct": s["num_unit_pct"], "marker_avg": s["marker_avg"],
      "markers_top8": {k: v["pct"] for k, v in list(s["markers_top15"].items())[:8]},
      "formula_fit": {
        "game": "쿠폰/코드형(8.2%)·순위/랭킹(11.6%)·플레이 후기 — 마커 절제(평균 1.74개)",
        "fashion": "페르소나(남자/여자·연령)+내돈내산(22.1%) — 콤마 선호(28.1%)",
        "beauty": "추천 67.8% 압도 — 내돈내산·솔직·비교·재구매 결합 마커 최다(평균 2.60개)",
        "product": "후기 38.2%+가격 수치 20.7% — 갓성비·총정리 결합",
        "site": "무료 23.5%+방법/사용법 — 제목 최장(42.2자)·의문문 10.7%",
        "travel": "지역 46.5%+파이프 17.1% — 'N박 N원' 가격·연도 표기",
        "food": "지역 45.5%+갓가성비 21.5% — 해시태그 결합형·찐맛집",
      }.get(c, ""),
      "example_top": S2["cat_examples"][c]["top_titles"][:5]
    }

by_category = {
  "game": cat_summary("game", "게임 (스팀/모바일/IP 팝업)"),
  "fashion": cat_summary("fashion", "패션 (의류/신발/시계/액세서리)"),
  "beauty": cat_summary("beauty", "뷰티 (스킨케어/메이크업/향수)"),
  "product": cat_summary("product", "제품 (가전/디지털/생활/건강)"),
  "site": cat_summary("site", "사이트/툴 (AI/무료서비스/어플)"),
  "travel": cat_summary("travel", "여행/레저 (숙소/워터파크/스키/캠핑)"),
  "food": cat_summary("food", "맛집/카페 (로컬/디저트/주류)"),
}

out = {
  "meta": meta,
  "title_formulas": title_formulas,
  "trust_markers": trust_markers,
  "structure_rules": structure_rules,
  "anti_patterns": anti_patterns,
  "by_category": by_category,
}
with open(f"{BASE}/patterns_blog.json", "w", encoding="utf-8") as f:
  json.dump(out, f, ensure_ascii=False, indent=1)

print("patterns_blog.json 갱신 완료")
print(f"  formulas: {len(title_formulas)} (1차 12 → 유지/수정/신규)")
print(f"  trust_markers: {len(trust_markers)}")
print(f"  structure_rules: {len(structure_rules)}")
print(f"  anti_patterns: {len(anti_patterns)}")
print(f"  by_category: {list(by_category.keys())}")
