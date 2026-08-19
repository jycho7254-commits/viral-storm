# -*- coding: utf-8 -*-
"""
2차 분석 보완 스크립트:
- 필터 완화(복합명사 부분일치) 후 재계산 + 노이즈 세부 분류
- 브라켓 내용물 유형, 키워드 위치, 연도/신선도 마커, 질문형/감탄부, 이모지, 구분자 혼용
- 카테고리별 심층: 신뢰마커 상위, 브라켓 예시, 공식 시그니처
출력: blog_v2_stats2.json
"""
import json
import re
import collections
import statistics

BASE = r"C:\Users\user\Desktop\viral-storm\data\learning"
with open(f"{BASE}/corpus_naver.json", encoding="utf-8") as f:
    data = json.load(f)
TOTAL = len(data)

CAT_KEYS = {
    "game": ["게임", "메이플", "로블록스", "발로란트", "블루아카이브", "바르디안", "서든", "리그오브", "배틀그라운드", "엘든", "젤다", "마인크래프트", "스팀", "쿠키런", "던전앤파이터", "로스트아크", "킹샷", "트릭컬", "로얄매치", "캐주얼게임"],
    "fashion": ["레더자켓", "아디다스", "코듀로이", "스니커즈", "백팩", "선글라스", "패션", "코트", "니트", "부츠", "슬랙스", "티셔츠", "청바지", "셔츠", "원피스", "스커트", "자켓", "운동화", "골프웨어", "후드", "가방", "시계", "지갑", "모자", "삭스", "레깅스", "코디", "골프"],
    "beauty": ["쿠션", "선크림", "향수", "립", "메이크업", "블러셔", "파운데이션", "더모", "토너", "미스트", "뷰티", "샴푸", "클렌징", "마스크팩", "아이라이너", "블러", "컨실러", "선케어", "스킨케어", "에센스", "로션", "네일", "뷰러", "틴트", "마스카라", "파우더"],
    "site": ["chatgpt", "노션", "무료 사이트", "이미지 편집", "사이트", "사용법", "어플", "앱테크", "클라우드", "툴", "번역", "유튜브 다운", "pdf", "ai ", "정부24", "홈택스", "프로그램", "웹툰 사이트", "토렌트", "링크", "gpt", "홈페이지", "사진"],
    "travel": ["여행", "경주", "제주", "워터파크", "놀이공원", "캠핑", "박물관", "전시회", "찜질방", "스파", "숙소", "호텔", "펜션", "리조트", "콘도", "아쿠아", "휴양지", "당일치기", "드라이브", "캠핑장", "글램핑", "국내여행", "해외여행", "일본", "오사카", "도쿄", "바다", "계곡", "섬", "스키장", "레저", "아쿠아플랜", "눈꽃축제", "페스티벌", "축제", "수족관", "아쿠아리움", "동물원", "아이랑", "아이와", "카페거리"],
    "food": ["맛집", "카페", "식당", "음식", "맥주", "와인", "빵", "베이커리", "디저트", "커피", "떡", "초콜릿", "간식", "반찬", "마트", "이마트", "코스트코", "트레이더스", "다이소", "배달", "한우", "회", "초밥", "라면", "위스키", "막걸리", "소주", "맛집탐방", "브런치", "맛", "복국", "국밥", "고깃집", "치킨", "피자", "버거", "초", "샐러드", "도시락", "편의점", "추어탕", "해장국", "양꼬치", "족발", "보쌈", "냉면", "만두", "텐동", "우동", "라멘", "스시", "오마카세"],
}

def cat_of(query):
    q = query.lower()
    for cat, keys in CAT_KEYS.items():
        for k in keys:
            if k in q:
                return cat
    return "product"

for d in data:
    d["category"] = cat_of(d["query"])

WIDGET_RE = re.compile(r"\d+(\.\d+)?만 인용|제공하는 블로그입니다|블로그입니다\.?$")
URL_FRAG_RE = re.compile(r"(blog\.naver\.com|naver\.com)›|https?://")
BLOGNAME_RE = re.compile(r"님의\s*블로그|블로그$|일상로그|다이어리\s*:?\)|MAGAZINE|매거진")

META_WORDS = {"솔직", "후기", "추천", "내돈내산", "찐후기", "best", "최신", "2026", "2025", "비교", "순위", "가성비", "사용법", "리뷰", "진짜", "갓성비", "리스트", "랭킹", "총정리", "정리", "팁", "꿀팁", "top", "갓겜", "졸잼", "필독", "베스트"}

def nt(t):
    t = t.lower().replace(" ", "")
    return "gpt" if t == "chatgpt" else t

def token_match(token, tl):
    """full match OR prefix2+suffix2 (복합명사 변형: 무선이어폰→무선게이밍이어폰)"""
    if token in tl:
        return True
    if len(token) >= 4 and token[:2] in tl and token[-2:] in tl:
        return True
    return False

noise = collections.Counter()
valid = []
for d in data:
    t = d["title"].strip()
    if WIDGET_RE.search(t):
        noise["widget(N만 인용/블로그입니다)"] += 1; continue
    if URL_FRAG_RE.search(t):
        noise["url_fragment"] += 1; continue
    if len(t) < 8:
        noise["too_short"] += 1; continue
    core = [nt(x) for x in d["query"].split() if nt(x) not in META_WORDS]
    tl = t.lower().replace(" ", "")
    if core and not any(token_match(c, tl) for c in core):
        if BLOGNAME_RE.search(t):
            noise["blog_name_only(쿼리무관+블로그명형)"] += 1
        else:
            noise["query_unrelated(쿼리 핵심어 0개)"] += 1
        continue
    d["title_clean"] = t
    valid.append(d)

VALID_N = len(valid)
print(f"전체 {TOTAL} → 유효 {VALID_N} (노이즈 {TOTAL - VALID_N}, {round((TOTAL-VALID_N)/TOTAL*100,1)}%)")
for k, v in noise.most_common():
    print(f"  {k}: {v} ({v/TOTAL*100:.1f}%)")

# ---------- 지표 ----------
REGIONS = list(dict.fromkeys(["서울","부산","대구","인천","광주","대전","울산","세종","경기","강원","충북","충남","전북","전남","경북","경남","제주",
  "홍대","강남","건대","신촌","이태원","명동","종로","동대문","성수","연남","망원","마포","여의도","잠실","송파","성동","합정","상수","왕십리","회기",
  "분당","일산","안성","범계","안양","신림","노원","은평","용산","영등포","구로","관악","동작","서초","강서","양천","중랑","광진","정자","판교",
  "수원","천안","청주","전주","포항","창원","진주","통영","거제","남해","여수","순천","목포","군산","익산","춘천","원주","강릉","속초","양양","동해",
  "서귀포","성산","애월","우도","송도","부평","부천","시흥","안산","용인","화성","평택","오산","동탄","김포","파주","의정부","남양주","구리","하남",
  "이천","여주","가평","양평","포천","동두천","의왕","과천","군포","경산","김천","구미","안동","영주","문경","상주","영천","칠곡","예천",
  "오사카","도쿄","교토","후쿠오카","삿포로","훗카이도","나고야","오키나와","상하이","베이징","타이베이","홍콩","싱가포르","방콕","다낭","호치민","발리","세부","괌","사이판","하와이","파리","런던","로마","베를린","프라하"]))
BRACKET_RE = re.compile(r"[\[\]]")
BRACKET_GET = re.compile(r"\[([^\[\]]{1,30})\]")
PIPE_RE = re.compile(r"[|｜ㅣ]")
NUM_UNIT_RE = re.compile(r"\d+(?:[,.]\d+)?\s*(만원|천원|원|시간|분|초|일|주|개월|년|년차|인|명|개|종|가지|건|mg|g|kg|ml|L|mm|cm|인치|도|%|배|위|차|kcal|km|m|gb|tb|db|박|코|일차|회|k|p|fps|타입|세트|짝|켤레|통|박스|판|장|층|평|py)")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F✨❤️️♀️♂️]")

def classify_bracket(content):
    c = content.strip()
    if any(r in c for r in REGIONS):
        return "지역"
    if re.search(r"찐|후기|내돈내산|솔직|리뷰|추천", c):
        return "키워드+신뢰"
    if "/" in c or re.search(r"추천|리뷰|후기|정리|비교", c):
        return "키워드 조합"
    return "기타"

def extra_flags(title):
    return {
        "bracket": bool(BRACKET_RE.search(title)),
        "region": any(r in title for r in REGIONS),
        "pipe": bool(PIPE_RE.search(title)),
        "comma": ("," in title) or ("," in title),
        "num_unit": bool(NUM_UNIT_RE.search(title)),
        "paren": bool(re.search(r"[（(]", title)),
        "question": "?" in title or "?" in title,
        "exclaim": "!" in title,
        "quote": bool(re.search(r"[\"'“”‘’]", title)),
        "emoji": bool(EMOJI_RE.search(title)),
        "year_2026": "2026" in title,
        "year_2025": "2025" in title,
        "neg_honest": bool(re.search(r"비추|단점|아쉬운|별로|싫|실망|주의", title)),
        "seq_tail": bool(re.search(r"(총정리|정리|모음|리스트|순위|탑|TOP)", title, re.I)),
    }

def sep_mix(title):
    kinds = 0
    if PIPE_RE.search(title): kinds += 1
    if ("," in title) or ("," in title): kinds += 1
    if BRACKET_RE.search(title): kinds += 1
    return kinds

def keyword_pos(title, query):
    core = [nt(x) for x in query.split() if nt(x) not in META_WORDS]
    tl = title.lower().replace(" ", "")
    L = len(title)
    positions = []
    for c in core:
        i = tl.find(c)
        if i >= 0:
            positions.append(i / max(L, 1))
    return min(positions) if positions else None

TRUST_MARKERS = [
    ("후기", r"후기"), ("추천", r"추천"), ("내돈내산", r"내돈내산"),
    ("솔직", r"솔직"), ("비교", r"비교"), ("갓가성비", r"[갓가]성비"),
    ("정리", r"정리"), ("리뷰", r"리뷰"), ("총정리", r"총정리"),
    ("순위/랭킹", r"순위|랭킹|서열"), ("BEST", r"best|베스트"), ("TOP N", r"top\s*\d+"),
    ("찐", r"찐(후기|맛집|리뷰|추천|으로|맛|템)"), ("무료", r"무료"), ("직접", r"직접"),
    ("진짜", r"진짜"), ("쿠폰/코드", r"쿠폰|코드|프로모"), ("꿀팁", r"꿀팁"), ("공략", r"공략"),
    ("단점", r"단점"), ("실구매/실착/실사용/실방문", r"실(구매|착|사용|방문|제작)"),
    ("힐링/감성/낭만", r"힐링|낭만|감성"), ("장단점", r"장단점"), ("필수템", r"필수"),
    ("초보", r"초보"), ("플레이 후기", r"플레이\s*후기"), ("이용 후기", r"이용\s*후기"),
    ("인생템", r"인생"), ("재구매/재방문", r"재(구매|방문)"), ("달성", r"달성"),
    ("갓겜/꿀잼", r"갓겜|꿀잼|졸잼"), ("신상/최신", r"신상|최신| new|new "), ("후회없는", r"후회"),
    ("반전/충격", r"반전|충격"), ("꿀", r"꿀(팁|머지|정)"), ("리얼", r"리얼|real"),
    ("다이어리/브이로그", r"다이어리|브이로그|vlog"), ("질문형", r"\?|\?"),
]
def marker_hits(title):
    tl = title.lower()
    return [n for n, p in TRUST_MARKERS if re.search(p, tl)]

# ---------- 집계 ----------
def analyze(items):
    n = len(items)
    if n == 0: return {"n": 0}
    lens = [len(d["title_clean"]) for d in items]
    fl = [extra_flags(d["title_clean"]) for d in items]
    mk = collections.Counter()
    combos = collections.Counter()
    for d in items:
        hits = marker_hits(d["title_clean"])
        for h in hits: mk[h] += 1
        combos[min(len(hits), 4)] += 1
    br_types = collections.Counter()
    for d in items:
        for m in BRACKET_GET.findall(d["title_clean"]):
            br_types[classify_bracket(m)] += 1
    kpos = [keyword_pos(d["title_clean"], d["query"]) for d in items]
    kpos_valid = [p for p in kpos if p is not None]
    sep = collections.Counter(sep_mix(d["title_clean"]) for d in items)
    return {
        "n": n,
        "len_avg": round(statistics.mean(lens), 1), "len_median": statistics.median(lens),
        "len_p25": sorted(lens)[n//4], "len_p75": sorted(lens)[(n*3)//4],
        "len_dist": {f"{lo}-{hi if hi<200 else '60+'}": sum(1 for L in lens if lo <= L <= hi)
                     for lo, hi in [(1,19),(20,29),(30,39),(40,49),(50,59),(60,200)]},
        "bracket_pct": round(sum(f["bracket"] for f in fl)/n*100,1),
        "bracket_types": dict(br_types.most_common()),
        "region_pct": round(sum(f["region"] for f in fl)/n*100,1),
        "pipe_pct": round(sum(f["pipe"] for f in fl)/n*100,1),
        "comma_pct": round(sum(f["comma"] for f in fl)/n*100,1),
        "num_unit_pct": round(sum(f["num_unit"] for f in fl)/n*100,1),
        "paren_pct": round(sum(f["paren"] for f in fl)/n*100,1),
        "question_pct": round(sum(f["question"] for f in fl)/n*100,1),
        "exclaim_pct": round(sum(f["exclaim"] for f in fl)/n*100,1),
        "quote_pct": round(sum(f["quote"] for f in fl)/n*100,1),
        "emoji_pct": round(sum(f["emoji"] for f in fl)/n*100,1),
        "year2026_pct": round(sum(f["year_2026"] for f in fl)/n*100,1),
        "year2025_pct": round(sum(f["year_2025"] for f in fl)/n*100,1),
        "neg_honest_pct": round(sum(f["neg_honest"] for f in fl)/n*100,1),
        "seq_tail_pct": round(sum(f["seq_tail"] for f in fl)/n*100,1),
        "sep_mix": {str(k): v for k, v in sorted(sep.items())},
        "kw_pos_median": round(statistics.median(kpos_valid), 2) if kpos_valid else None,
        "kw_first40pct": round(sum(1 for p in kpos_valid if p <= 0.4)/len(kpos_valid)*100, 1) if kpos_valid else None,
        "kw_first60pct": round(sum(1 for p in kpos_valid if p <= 0.6)/len(kpos_valid)*100, 1) if kpos_valid else None,
        "markers_top15": {k: {"count": v, "pct": round(v/n*100,1)} for k, v in mk.most_common(15)},
        "markers_all": {k: {"count": v, "pct": round(v/n*100,1)} for k, v in mk.most_common()},
        "marker_combos": {str(k): v for k, v in sorted(combos.items())},
        "marker_avg": round(sum(len(marker_hits(d['title_clean'])) for d in items)/n, 2),
    }

seen = set(); top_exposed = []
for d in valid:
    if d["query"] not in seen:
        seen.add(d["query"]); top_exposed.append(d)

by_cat = collections.defaultdict(list)
for d in valid: by_cat[d["category"]].append(d)
cat_top = collections.defaultdict(list)
seen = set()
for d in valid:
    if d["query"] not in seen:
        seen.add(d["query"]); cat_top[d["category"]].append(d)

overall = analyze(valid)
top = analyze(top_exposed)
cats = {c: analyze(v) for c, v in by_cat.items()}
cats_top = {c: analyze(v) for c, v in cat_top.items()}

# 카테고리별 대표 예시 (상위노출)
cat_examples = {}
for c in by_cat:
    tops = cat_top[c]
    cat_examples[c] = {
        "top_titles": [d["title_clean"] for d in tops[:12]],
        "bracket_titles": [d["title_clean"] for d in tops if BRACKET_RE.search(d["title_clean"])][:6],
        "num_titles": [d["title_clean"] for d in tops if NUM_UNIT_RE.search(d["title_clean"])][:6],
    }

# 1차 공식 재검증 (완화 필터 기준)
def formula_evidence(items):
    n = len(items)
    ev = {}
    ev["f1_bracket_trust"] = sum(1 for d in items if BRACKET_RE.search(d["title_clean"]) and re.search(r"찐|후기|리뷰|내돈내산|추천", d["title_clean"]))
    ev["f2_playtime_num"] = sum(1 for d in items if re.search(r"\d+\s*시간|\d+\s*회차|\d+일차|\d+서버", d["title_clean"]))
    ev["f3_region_headcount"] = sum(1 for d in items if any(r in d["title_clean"] for r in REGIONS) and re.search(r"\d+\s*인", d["title_clean"]))
    ev["f4_coupon"] = sum(1 for d in items if re.search(r"쿠폰|코드|프로모", d["title_clean"]))
    ev["f5_service_pipe"] = sum(1 for d in items if PIPE_RE.search(d["title_clean"]))
    ev["f6_topn"] = sum(1 for d in items if re.search(r"top\s*\d+|best\s*\d+|베스트\s*\d+|\d+\s*가지|\d+\s*곳|\d+\s*일코스", d["title_clean"].lower()))
    ev["f7_ranking_total"] = sum(1 for d in items if re.search(r"총정리|순위|랭킹|서열", d["title_clean"]))
    ev["f8_persona"] = sum(1 for d in items if re.search(r"1인가구|자취|직장인|학생|신혼|초보|엄마|아빠|남자|여자|중년|시니어|아이랑| kids|키즈", d["title_clean"]))
    ev["f9_howto"] = sum(1 for d in items if re.search(r"하는 법|하는법|방법|줄이는|고르는|만드는|고치는", d["title_clean"]))
    ev["f10_career"] = sum(1 for d in items if re.search(r"\d+\s*년차|\d+\s*년\s*경력|\d+위|만\s*시간", d["title_clean"]))
    ev["f11_spec_price"] = sum(1 for d in items if re.search(r"\d+\s*(mg|ml|g|kg|%|mm|p|w|tb)|하루\s*\d+원|일\s*\d+원|\d+만원|\d+,\d+원|\d+원", d["title_clean"].lower()))
    ev["f12_coupon_guide"] = sum(1 for d in items if re.search(r"쿠폰", d["title_clean"]) and re.search(r"공략|코드|정리", d["title_clean"]))
    return {k: {"count": v, "pct": round(v/n*100,1)} for k, v in ev.items()}

formula_check = {"overall": formula_evidence(valid)}
for c, items in by_cat.items():
    formula_check[c] = formula_evidence(items)

out = {
    "meta": {"corpus_total": TOTAL, "valid_n": VALID_N, "noise_n": TOTAL - VALID_N,
             "noise_types": dict(noise.most_common()),
             "unique_queries_total": len({d['query'] for d in data}),
             "unique_queries_valid": len({d['query'] for d in valid}),
             "analysis_pass": 2, "filter": "widget/url/쿼리핵심어(복합명사 부분일치 완화)"},
    "overall": overall, "top_exposed": top,
    "by_category": cats, "by_category_top": cats_top,
    "cat_examples": cat_examples,
    "formula1st_check": formula_check,
}
with open(f"{BASE}/blog_v2_stats2.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

print("\n=== 유효 전체 vs 상위노출 (보조지표) ===")
for k in ["n","len_avg","len_median","len_p25","len_p75","bracket_pct","region_pct","pipe_pct","comma_pct","num_unit_pct","paren_pct","question_pct","exclaim_pct","quote_pct","emoji_pct","year2026_pct","year2025_pct","neg_honest_pct","seq_tail_pct","kw_pos_median","kw_first40pct","kw_first60pct","marker_avg"]:
    print(f"  {k:16s} overall={overall.get(k)}  top={top.get(k)}")
print("  sep_mix overall:", overall["sep_mix"], " top:", top["sep_mix"])
print("  marker_combos overall:", overall["marker_combos"], " top:", top["marker_combos"])
print("  bracket_types overall:", overall["bracket_types"], " top:", top["bracket_types"])

print("\n=== 카테고리별 (유효) ===")
hdr = f"{'cat':9s}{'n':>5s}{'len':>6s}{'brk%':>6s}{'reg%':>6s}{'pipe%':>6s}{'cma%':>6s}{'num%':>6s}{'mkavg':>6s}{'Q?%':>5s}{'26%':>5s}"
print(hdr)
for c in ["game","fashion","beauty","product","site","travel","food"]:
    s = cats[c]
    print(f"{c:9s}{s['n']:5d}{s['len_avg']:6.1f}{s['bracket_pct']:6.1f}{s['region_pct']:6.1f}{s['pipe_pct']:6.1f}{s['comma_pct']:6.1f}{s['num_unit_pct']:6.1f}{s['marker_avg']:6.2f}{s['question_pct']:5.1f}{s['year2026_pct']:5.1f}")

print("\n=== 카테고리별 마커 TOP8 ===")
for c in ["game","fashion","beauty","product","site","travel","food"]:
    print(f"[{c}]", ", ".join(f"{k}({v['pct']}%)" for k, v in list(cats[c]["markers_top15"].items())[:8]))

print("\n=== 1차 공식 검증(완화필터) ===")
for k, v in formula_check["overall"].items():
    print(f"  {k:22s} {v['count']:5d} {v['pct']:5.1f}%")
print("\n=== 게임 카테고리 공식 ===")
for k, v in formula_check.get("game", {}).items():
    print(f"  {k:22s} {v['count']:4d} {v['pct']:5.1f}%")
print("\nDone → blog_v2_stats2.json")
