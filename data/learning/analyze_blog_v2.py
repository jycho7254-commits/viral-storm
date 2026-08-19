# -*- coding: utf-8 -*-
"""
네이버 블로그 바이럴 패턴 2차 전수 분석 (corpus_naver.json 5,156건)
- 노이즈 필터링 (위젯/블로그명/URL파편/쿼리무관 제목)
- 제목 구조 통계: 브라켓/지역/파이프/콤마/수치디테일
- 신뢰 마커 빈도 (전체 목록)
- 카테고리별(게임/패션/뷰티/제품/사이트/여행/맛집) 제목 패턴 차이
- 제목 길이 분포 (상위노출 = 각 쿼리 첫 등장 포스트 기준)
출력: blog_v2_stats.json + 콘솔 요약
"""
import json
import re
import collections
import statistics

BASE = r"C:\Users\user\Desktop\viral-storm\data\learning"
PY = None  # placeholder

with open(f"{BASE}/corpus_naver.json", encoding="utf-8") as f:
    data = json.load(f)

TOTAL = len(data)

# ---------------------------------------------------------------
# 1. 카테고리 매핑 (쿼리 기반: 게임/패션/뷰티/제품/사이트/여행/맛집)
# ---------------------------------------------------------------
CAT_KEYS = {
    "game": ["게임", "메이플", "로블록스", "발로란트", "블루아카이브", "바르디안", "서든", "리그오브", "배틀그라운드", "엘든", "젤다", "마인크래프트", "스팀", "쿠키런", "던전앤파이터", "lostark", "로스트아크"],
    "fashion": ["레더자켓", "아디다스", "코듀로이", "스니커즈", "백팩", "선글라스", "패션", "코트", "니트", "부츠", "슬랙스", "티셔츠", "청바지", "셔츠", "원피스", "스커트", "자켓", "운동화", "골프웨어", "후드", "가방", "시계", "지갑", "모자", "삭스", "레깅스"],
    "beauty": ["쿠션", "선크림", "향수", "립", "메이크업", "블러셔", "파운데이션", "더모", "토너", "미스트", "뷰티", "샴푸", "클렌징", "마스크팩", "아이라이너", "블러", "컨실러", "선케어", "스킨케어", "에센스", "로션", "체지수분", "네일", "뷰러"],
    "site": ["chatgpt", "노션", "무료 사이트", "이미지 편집", "사이트", "사용법", "어플", "앱테크", "클라우드", "툴", "번역", "유튜브 다운", "pdf", "ai ", "정부24", "홈택스", "프로그램", "웹툰 사이트", "토렌트", "링크"],
    "travel": ["여행", "경주", "제주", "워터파크", "놀이공원", "캠핑", "박물관", "전시회", "찜질방", "스파", "숙소", "호텔", "펜션", "리조트", "콘도", "아쿠아", "휴양지", "당일치기", "드라이브", "캠핑장", "글램핑", "국내여행", "해외여행", "일본", "오사카", "도쿄", "바다", "계곡", "섬"],
    "food": ["맛집", "카페", "식당", "음식", "맥주", "와인", "빵", "베이커리", "디저트", "커피", "떡", "초콜릿", "간식", "반찬", "마트", "이마트", "코스트코", "트레이더스", "다이소", "배달", "한우", "회", "초밥", "라면", "위스키", "막걸리", "소주", "맛집탐방", "브런치"],
}

def cat_of(query: str) -> str:
    q = query.lower()
    for cat, keys in CAT_KEYS.items():
        for k in keys:
            if k in q:
                return cat
    return "product"

for d in data:
    d["category"] = cat_of(d["query"])

# ---------------------------------------------------------------
# 2. 노이즈 필터링
# ---------------------------------------------------------------
WIDGET_RE = re.compile(r"\d+(\.\d+)?만 인용|제공하는 블로그입니다|블로그입니다\.?$|네이버 블로그\.?$")
URL_FRAG_RE = re.compile(r"(blog\.naver\.com|naver\.com)›|›\s*$|https?://")
MAGAZINE_RE = re.compile(r"^\s*[A-Z][A-Za-z ]{2,20}(MAGAZINE|매거진)\s*$", re.I)

META_WORDS = {
    "솔직", "후기", "추천", "내돈내산", "찐후기", "best", "최신", "2026", "2025",
    "비교", "순위", "가성비", "사용법", "리뷰", "진짜", "갓성비", "리스트", "랭킹",
    "총정리", "정리", "팁", "꿀팁", "top", "갓겜", "졸잼", "필독", "베스트",
}

def norm_token(t: str) -> str:
    t = t.lower().replace(" ", "")
    if t in ("chatgpt",):
        return "gpt"
    return t

def query_core_tokens(query: str):
    toks = [norm_token(t) for t in query.split() if norm_token(t) not in META_WORDS]
    return toks

noise_types = collections.Counter()
valid = []
for d in data:
    t = d["title"].strip()
    if WIDGET_RE.search(t):
        noise_types["widget(블로그 N만 인용/블로그입니다)"] += 1
        continue
    if URL_FRAG_RE.search(t):
        noise_types["url_fragment"] += 1
        continue
    if MAGAZINE_RE.match(t):
        noise_types["blog_name_only"] += 1
        continue
    if len(t) < 8:
        noise_types["too_short(<8자)"] += 1
        continue
    core = query_core_tokens(d["query"])
    tl = t.lower().replace(" ", "")
    if core and not any(c in tl for c in core):
        noise_types["query_unrelated(쿼리 핵심어 0개)"] += 1
        continue
    d["title_clean"] = t
    valid.append(d)

VALID_N = len(valid)
print(f"전체 {TOTAL} → 유효 {VALID_N} (노이즈 {TOTAL - VALID_N})")
for k, v in noise_types.most_common():
    print(f"  노이즈[{k}] {v} ({v/TOTAL*100:.1f}%)")

# ---------------------------------------------------------------
# 3. 구조 지표 정의
# ---------------------------------------------------------------
REGIONS = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종", "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
           "홍대", "강남", "건대", "신촌", "이태원", "명동", "종로", "동대문", "성수", "연남", "망원", "마포", "여의도", "잠실", "송파", "성동",
           "분당", "일산", "안성", "범계", "안양", "신림", "노원", "강북", "은평", "용산", "영등포", "구로", "금천", "관악", "동작", "서초",
           "강서", "양천", "중구", "중랑", "광진", "성신", "왕십리", "회기", "태릉", "미아", "정자", "판교", "수원", "천안", "청주", "전주", "광주",
           "대전", "포항", "창원", "진주", "통영", "거제", "남해", "여수", "순천", "목포", "군산", "익산", "춘천", "원주", "강릉", "속초", "양양",
           "동해", "삼척", "태백", "제주", "서귀포", "성산", "애월", "한라", "우도", "마포", "합정", "상수", "외대", "고려대", "연세대",
           "인천", "송도", "부평", "부천", "시흥", "안산", "용인", "화성", "평택", "오산", "동탄", "김포", "파주", "의정부", "남양주", "구리", "하남",
           "광주", "이천", "여주", "가평", "양평", "포천", "연천", "가평", "동두천", "의왕", "과천", "안양", "군포", "수원",
           "경주", "포항", "경산", "김천", "구미", "안동", "영주", "문경", "상주", "영천", "청도", "고령", "성주", "칠곡", "예천", "봉화", "울진", "울릉",
           "오사카", "도쿄", "교토", "후쿠오카", "삿포로", "훗카이도", "나고야", "오키나와", "상하이", "베이징", "타이베이", "홍콩", "싱가포르", "방콕", "다낭", "호치민", "발리", "세부", "괌", "사이판", "하와이", "LA", "뉴욕", "파리", "런던", "로마"]

BRACKET_RE = re.compile(r"[\[\]]")
PIPE_RE = re.compile(r"[|｜ㅣ]")
NUM_UNIT_RE = re.compile(r"\d+(?:[,.]\d+)?\s*(만원|천원|원|시간|분|초|일|주|개월|년|년차|인|명|개|종|가지|건|mg|g|kg|ml|L|mm|cm|인치|도|%|배|위|차|kcal|km|m|tb|gb|gbp|db|탕|박|코|일차|회|k|p|fps|gb)")

TRUST_MARKER_PATTERNS = [
    ("후기", r"후기"),
    ("리뷰", r"리뷰"),
    ("추천", r"추천"),
    ("찐(후기/맛집/으로)", r"찐(후기|맛집|리뷰|추천|으로|맛)"),
    ("내돈내산", r"내돈내산"),
    ("갓성비/가성비", r"[갓가]성비"),
    ("솔직(후기)", r"솔직"),
    ("플레이 후기", r"플레이\s*후기"),
    ("이용 후기", r"이용\s*후기"),
    ("직접", r"직접"),
    ("실구매/실착/실사용/실방문", r"실(구매|착|사용|방문|제작|리뷰)"),
    ("총정리", r"총정리"),
    ("정리", r"정리"),
    ("꿀팁", r"꿀팁"),
    ("인생템/인생", r"인생(템|맛집|브랜드|템$)"),
    ("재구매/재방문", r"재(구매|방문|구매율)"),
    ("달성", r"달성"),
    ("비교", r"비교"),
    ("순위/랭킹", r"(순위|랭킹|서열)"),
    ("TOP N", r"top\s*\d+|BEST\s*\d+|베스트\s*\d+"),
    ("BEST/베스트", r"best|베스트"),
    ("쿠폰/코드", r"(쿠폰|코드|프로모)"),
    ("공략", r"공략"),
    ("무료", r"무료"),
    ("필수템/필수", r"필수(템|품목)?"),
    ("충격/반전", r"(충격|반전|근황)"),
    ("갓겜/핵꿀잼", r"(갓겜|꿀잼|핵꿀잼|졸잼|겜_)"),
    ("다이어리/브이로그", r"(다이어리|브이로그|vlog)"),
    ("1위", r"1위"),
    ("정품/공식", r"(정품|공식|공식)"),
    ("후회없는/후회안함", r"후회(없는|안|하지|안 함)"),
    ("리얼/real", r"리얼|real"),
    ("경험", r"경험"),
    ("장단점", r"장단점"),
    ("단점", r"단점"),
    ("솔직하게", r"솔직하"),
    ("진짜", r"진짜"),
    ("초보", r"초보"),
    ("낭만/힐링 감성", r"(힐링|낭만|감성)"),
]

def struct_flags(title: str):
    return {
        "bracket": bool(BRACKET_RE.search(title)),
        "region": any(r in title for r in REGIONS),
        "pipe": bool(PIPE_RE.search(title)),
        "comma": "," in title or "," in title,
        "num_unit": bool(NUM_UNIT_RE.search(title)),
        "any_digit": bool(re.search(r"\d", title)),
        "paren": bool(re.search(r"[（(]", title)),
        "plus_tail": bool(re.search(r"\(\+", title)) or "(+" in title,
    }

def marker_hits(title: str):
    tl = title.lower()
    hits = []
    for name, pat in TRUST_MARKER_PATTERNS:
        if re.search(pat, tl):
            hits.append(name)
    return hits

# ---------------------------------------------------------------
# 4. 전체 통계 계산
# ---------------------------------------------------------------
def compute_stats(items):
    n = len(items)
    if n == 0:
        return {"n": 0}
    lens = [len(d["title_clean"]) for d in items]
    flags = [struct_flags(d["title_clean"]) for d in items]
    mk_counts = collections.Counter()
    mk_multi = collections.Counter()
    marker_total_per_title = []
    for d in items:
        hits = marker_hits(d["title_clean"])
        for h in hits:
            mk_counts[h] += 1
        mk_multi[min(len(hits), 5)] += 1
        marker_total_per_title.append(len(hits))
    # 상위노출 top-exposed 별도 계산은 밖에서
    return {
        "n": n,
        "len_avg": round(statistics.mean(lens), 1),
        "len_median": round(statistics.median(lens), 1),
        "len_p25": sorted(lens)[n // 4],
        "len_p75": sorted(lens)[(n * 3) // 4],
        "len_min": min(lens),
        "len_max": max(lens),
        "len_dist": {f"{lo}-{hi}": sum(1 for L in lens if lo <= L <= hi)
                     for lo, hi in [(0, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 200)]},
        "bracket_pct": round(sum(f["bracket"] for f in flags) / n * 100, 1),
        "region_pct": round(sum(f["region"] for f in flags) / n * 100, 1),
        "pipe_pct": round(sum(f["pipe"] for f in flags) / n * 100, 1),
        "comma_pct": round(sum(f["comma"] for f in flags) / n * 100, 1),
        "num_unit_pct": round(sum(f["num_unit"] for f in flags) / n * 100, 1),
        "any_digit_pct": round(sum(f["any_digit"] for f in flags) / n * 100, 1),
        "paren_pct": round(sum(f["paren"] for f in flags) / n * 100, 1),
        "plus_tail_pct": round(sum(f["plus_tail"] for f in flags) / n * 100, 1),
        "markers": {k: {"count": v, "pct": round(v / n * 100, 1)} for k, v in mk_counts.most_common()},
        "marker_combo": {str(k): v for k, v in sorted(mk_multi.items())},
        "marker_avg_per_title": round(statistics.mean(marker_total_per_title), 2),
    }

overall = compute_stats(valid)

# 상위노출 = 각 쿼리 첫 등장 포스트
seen = set()
top_exposed = []
for d in valid:  # corpus 순서 유지 (쿼리별 랭킹순)
    if d["query"] not in seen:
        seen.add(d["query"])
        top_exposed.append(d)
top_stats = compute_stats(top_exposed)

# 카테고리별 통계
by_cat = collections.defaultdict(list)
for d in valid:
    by_cat[d["category"]].append(d)
cat_stats = {c: compute_stats(items) for c, items in by_cat.items()}

# 카테고리별 상위노출
cat_top = collections.defaultdict(list)
seen = set()
for d in valid:
    key = d["query"]
    if key not in seen:
        seen.add(key)
        cat_top[d["category"]].append(d)
cat_top_stats = {c: compute_stats(items) for c, items in cat_top.items()}

# ---------------------------------------------------------------
# 5. 카테고리별 대표 제목 (상위노출 샘플)
# ---------------------------------------------------------------
cat_examples = {}
for c in by_cat:
    tops = cat_top[c][:400]
    ex = {
        "bracket": [d["title_clean"] for d in tops if struct_flags(d["title_clean"])["bracket"]][:6],
        "num": [d["title_clean"] for d in tops if struct_flags(d["title_clean"])["num_unit"]][:6],
        "pipe": [d["title_clean"] for d in tops if struct_flags(d["title_clean"])["pipe"]][:6],
        "plain_top": [d["title_clean"] for d in tops[:10]],
    }
    cat_examples[c] = ex

# ---------------------------------------------------------------
# 6. 1차 공식 12개 검증 시그니처
# ---------------------------------------------------------------
def formula_evidence(items):
    n = len(items)
    ev = {}
    ev["f1_bracket_trust"] = sum(1 for d in items if BRACKET_RE.search(d["title_clean"]) and re.search(r"찐|후기|리뷰|내돈내산|추천", d["title_clean"]))
    ev["f2_genre_num_playtime"] = sum(1 for d in items if re.search(r"\d+\s*시간|\d+\s*회차|\d+일차|\d+서버", d["title_clean"]))
    ev["f3_region_headcount"] = sum(1 for d in items if re.search(r"\d+(-|\s*~\s*)?\d*\s*인", d["title_clean"]))
    ev["f4_coupon"] = sum(1 for d in items if re.search(r"쿠폰|코드|프로모", d["title_clean"]))
    ev["f5_service_detail_pipe"] = sum(1 for d in items if PIPE_RE.search(d["title_clean"]) and re.search(r"이용|방문|다녀온", d["title_clean"]))
    ev["f6_topn_reversal"] = sum(1 for d in items if re.search(r"top\s*\d+|best\s*\d+|베스트\s*\d+", d["title_clean"].lower()))
    ev["f7_total_ranking"] = sum(1 for d in items if re.search(r"총정리|순위|랭킹|서열", d["title_clean"]))
    ev["f8_persona_price"] = sum(1 for d in items if re.search(r"1인가구|자취|직장인|학생|군인|엄마|아빠|신혼|초보|니트|직장", d["title_clean"]))
    ev["f9_howto"] = sum(1 for d in items if re.search(r"(하는 법|하는법|방법|줄이는|고치는|만드는)", d["title_clean"]))
    ev["f10_career"] = sum(1 for d in items if re.search(r"\d+\s*년차|\d+\s*년 경력|\d+위|만\d+\s*시간", d["title_clean"]))
    ev["f11_spec_price"] = sum(1 for d in items if re.search(r"\d+\s*(mg|ml|g|kg|%|mm|p|dpi|w)|하루\s*\d+원|일\s*\d+원", d["title_clean"].lower()))
    ev["f12_coupon_guide_play"] = sum(1 for d in items if re.search(r"쿠폰", d["title_clean"]) and re.search(r"공략|코드", d["title_clean"]))
    return {k: {"count": v, "pct": round(v / n * 100, 1)} for k, v in ev.items()}

formula_check = {"overall": formula_evidence(valid)}
for c, items in by_cat.items():
    formula_check[c] = formula_evidence(items)

# ---------------------------------------------------------------
# 7. 저장
# ---------------------------------------------------------------
out = {
    "meta": {
        "corpus_total": TOTAL,
        "valid_n": VALID_N,
        "noise_n": TOTAL - VALID_N,
        "noise_types": dict(noise_types),
        "unique_queries": len({d["query"] for d in data}),
        "analysis_pass": 2,
    },
    "overall": overall,
    "top_exposed": top_stats,
    "by_category": cat_stats,
    "by_category_top_exposed": cat_top_stats,
    "cat_examples": cat_examples,
    "formula1st_check": formula_check,
}
with open(f"{BASE}/blog_v2_stats.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

# ---------------------------------------------------------------
# 콘솔 요약
# ---------------------------------------------------------------
print("\n=== 전체(유효) vs 상위노출(쿼리 첫 포스트) ===")
for key in ["n", "len_avg", "len_median", "len_p25", "len_p75", "bracket_pct", "region_pct", "pipe_pct", "comma_pct", "num_unit_pct", "any_digit_pct", "paren_pct"]:
    print(f"  {key:15s} overall={overall.get(key)}  top={top_stats.get(key)}")

print("\n=== 길이 분포(전체) ===", overall["len_dist"])
print("=== 길이 분포(상위노출) ===", top_stats["len_dist"])
print("=== 마커 조합 개수 분포(전체) ===", overall["marker_combo"])
print("=== 마커 조합 개수 분포(상위노출) ===", top_stats["marker_combo"])

print("\n=== 신뢰마커 TOP25 (유효 전체) ===")
for k, v in list(overall["markers"].items())[:25]:
    print(f"  {k:20s} {v['count']:5d}  {v['pct']:5.1f}%")
print("\n=== 신뢰마커 TOP25 (상위노출) ===")
for k, v in list(top_stats["markers"].items())[:25]:
    print(f"  {k:20s} {v['count']:5d}  {v['pct']:5.1f}%")

print("\n=== 카테고리별 요약 ===")
print(f"{'cat':8s} {'n':>5s} {'len':>6s} {'brk%':>6s} {'reg%':>6s} {'pipe%':>6s} {'cma%':>6s} {'num%':>6s} {'mkavg':>6s}")
for c in ["game", "fashion", "beauty", "product", "site", "travel", "food"]:
    s = cat_stats[c]
    print(f"{c:8s} {s['n']:5d} {s['len_avg']:6.1f} {s['bracket_pct']:6.1f} {s['region_pct']:6.1f} {s['pipe_pct']:6.1f} {s['comma_pct']:6.1f} {s['num_unit_pct']:6.1f} {s['marker_avg_per_title']:6.2f}")

print("\n=== 카테고리별 상위노출 ===")
for c in ["game", "fashion", "beauty", "product", "site", "travel", "food"]:
    s = cat_top_stats[c]
    print(f"{c:8s} n={s['n']:4d} len={s['len_avg']:5.1f} brk={s['bracket_pct']:5.1f} reg={s['region_pct']:5.1f} pipe={s['pipe_pct']:5.1f} num={s['num_unit_pct']:5.1f}")

print("\n=== 1차 공식 시그니처 검증 (유효 전체 %) ===")
for k, v in formula_check["overall"].items():
    print(f"  {k:28s} {v['count']:5d}  {v['pct']:5.1f}%")

print("\nDone → blog_v2_stats.json")
