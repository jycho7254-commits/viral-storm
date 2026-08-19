# -*- coding: utf-8 -*-
"""유튜브 바이럴 패턴 2차 재분석 — patterns_youtube.json 갱신용 빌더
재현: python build_patterns_youtube_v2.py
입력: corpus_youtube.json (10,335건) / 출력: patterns_youtube.json (덮어쓰기, .bak 보존)
"""
import json, re, math, statistics as st
from collections import Counter

BASE = r"C:\Users\user\Desktop\viral-storm\data\learning"
data = json.load(open(BASE + r"\corpus_youtube.json", encoding="utf-8"))
items = [d for d in data if isinstance(d.get("views"), int) and d["views"] > 0 and d.get("title")]
OA = sum(d["views"] for d in items) / len(items)
OM = st.median([d["views"] for d in items])
HANGUL = re.compile(r"[가-힣]")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")

# ---------- 카테고리 ----------
GAME = ['게임','로블록스','마비노기','메이플','명일방주','붕괴','스타레일','브롤스타즈','블루 아카이브','블루아카이브',
        '서든어택','FC 온라인','PS5','플스5','스위치','닌텐도','스팀게임','스팀 인디','RPG','VR 게임','로맨스 게임',
        '로스트아크','로얄매치','리니지','리그오브레전드','발로란트','배틀그라운드','보드게임','아이온','엑스박스',
        '우마무스메','원신','젠레스','캐주얼게임','쿠키런','킹샷','트릭컬','검은사막','인디게임','라스트워','모바일게임','모바일 게임']
BEAUTY = ['샴푸','세럼','마스크팩','립틴트','선크림','쿠션','클렌징','토너','스킨케어','향수','다이슨 에어랩']
CLOTH = ['OOTD','니트','레더자켓','로퍼','모자','무신사','부츠','샌들','선글라스','선캡','셔츠','스니커즈','스커트',
         '슬랙스','아디다스','오버사이즈','와이드팬츠','자켓','청바지','치노팬츠','코듀로이','트렌치코트','패션','후드집업',
         '패딩','러닝화','나이키','니케','에어포스','삼선','운동화','구두','원피스','맨투맨','양말','벨트','ankle','코디','룩북','옷']
FOOD = ['간식','맥주','맛집','반찬','도시락','레시피','와인','위스키','커피 원두','다이어트 식단','카페']
SITE = ['사이트','ChatGPT','chatgpt','AI ','노션','PDF','깃허브','리눅스','미드저니','블로그 시작','클라우드','엑셀',
        '이미지 편집','유튜브 알고리즘','인스타 마케팅','작업 사이트','프리미어','피그마','포토샵','스프레드시트',
        '디자인 툴','동영상 편집','stable diffusion','앱 추천','iot','번역']
PLACE = ['경주 여행','골프장','놀이공원','박물관','부산 여행','스키장','전시회','제주 숙소','찜질방','워터파크','여행']
PROD = ['가방','갤럭시','게이밍마우스','골프채','공기청정기','기계식키보드','노트북','드라이기','등산용품','레저매트',
        '무선이어폰','무선청소기','버즈','블루투스 스피커','모니터암','아이맥','아이패드','아이폰','안마의자','애플워치',
        '에어팟','요가매트','전기밥솥','전기자전거','캐리어','캠핑의자','캠핑텐트','커피머신','킨들','헬스용품','맥북',
        '지갑','nas','홈서버','인생템','요즘 핫한 제품','제품 리뷰','정품 리뷰','시계','백팩','신발 추천']

def classify(q):
    q = q or ""
    for k in GAME:
        if k in q: return "game"
    for k in BEAUTY:
        if k in q: return "beauty"
    for k in CLOTH:
        if k in q: return "clothing"
    for k in FOOD:
        if k in q: return "food"
    for k in SITE:
        if k in q: return "site_app"
    for k in PLACE:
        if k in q: return "travel_place"
    for k in PROD:
        if k in q: return "product"
    return "etc"

for d in items:
    d["_cat"] = classify(d.get("query"))

# ---------- 플래그 ----------
def flags(t):
    tl = t.lower()
    return {
        "question": "?" in t,
        "vs": bool(re.search(r"\bvs\.?\b", tl)),
        "first_person": bool(re.search(r"저는|저희|제가|나는|내 |내가|내돈", t)),
        "experience_verb": bool(re.search(r"봤습니다|해 ?봤|써 ?봤|사 ?봤|가 ?봤|먹어 ?봤|마셔 ?봤|깔아 ?봤|직접|실사용|체험|내돈내산", t)),
        "slang": bool(re.search(r"ㄹㅇ|ㅈㄴ|ㅋㅋ|ㅠㅠ|ㄷㄷ|개꿀|개빡|찐|소름|미쳤|헐|오지다|왤캐", t)),
        "neg_emotion": bool(re.search(r"실패|실망|빡|화나|별로|후회|날린|손해|쓰레기|논란|사기|충격|주의|함정|개망|망했", t)),
        "superlative": bool(re.search(r"최고|베스트|1위|갓|전설|끝판왕|인생|완벽|제일", t)),
        "has_digit": bool(re.search(r"\d", t)),
        "ad_ref": ("광고" in t or "협찬" in t),
        "bracket": ("[" in t),
        "emoji": bool(EMOJI.search(t)),
        "exclam": ("!" in t),
        "is_korean": bool(HANGUL.search(t)),
        "listy": bool(re.search(r"top\s*\d|베스트\s*\d|\d+가지|\d+개|\d+곳|\d+위|모음|총정리|순위|리스트", tl)),
        "money_ref": bool(re.search(r"[0-9]+\s*만원|[0-9,]{4,}원|만원짜리|억|[0-9,]+\$|000 ?won", tl)),
        "series_ref": bool(re.search(r"\bep\b|\bpart\b|[0-9]+ ?탄|\d+화$|시즌", tl)),
        "eng_sub": bool(re.search(r"\[eng|eng\]|자막|english sub|한글자막|영어자막", tl)),
    }

FL = flags(items[0]["title"]).keys()

def lift_rows(rows, pat, flags_mode=False):
    if flags_mode:
        sub = [r for r in rows if flags(r["title"]).get(pat)]
    else:
        sub = [r for r in rows if re.search(pat, r["title"], re.I)]
    if len(sub) < 5:
        return None
    vs = [r["views"] for r in sub]
    return {"n": len(sub), "avg": sum(vs)/len(vs), "med": st.median(vs),
            "lift_avg": (sum(vs)/len(vs))/OA, "lift_med": st.median(vs)/OM,
            "best": max(sub, key=lambda r: r["views"])}

# ---------- 공식 정의 ----------
FORMULAS = [
    ("F1", "광고분노 → 직접 체험형", r"광고.*(봤습니다|해 ?봤|깔아|직접|실사용|빡|화나|짜증|설마|오지)",
     "광고 과노출 공감을 분노→행동 전환으로. 대량 데이터에서도 유의: 광고+체험 결합 n=12, 평균 리프트 2.6×",
     ["game", "product"], "verified"),
    ("F2", "직접 검증형 (A vs B)", r"\bvs\.?\b.*(봤습니다|직접|해 ?봤|실사용|마셔|써 ?봤)|직접.*(vs|비교)",
     "vs 비교 + 직접 체험의 조합. n=8, avg 리프트 2.1× / med 리프트 2.6×",
     ["product", "game", "food"], "verified"),
    ("F3", "구체적 금액 + 의문형", r"[0-9]+\s*만원|[0-9,]{4,}원|만원짜리|[0-9]+\s*억",
     "금액 숫자의 구체성 = 진정성. n=294 대량 검증에서 med 리프트 2.3× 유지. 단순 숫자 나열과 달리 금액은 강신호",
     ["product", "food", "travel_place"], "verified"),
    ("F4", "감탄 슬랭 오프닝형", r"^(미쳤|소름|ㄹㅇ|헐|충격|개[가-힣]|와[ !]|대박|이게|진짜|역대급)",
     "제목 첫머리 감정 폭발. n=67, avg 리프트 2.2× / med 리프트 2.5×. '미쳤' med 리프트 4.0×",
     ["game", "product", "etc"], "verified"),
    ("F5", "공감 유형학형 (유형 카탈로그)", r"유형|있는 (사람|손님|어른|애들|녀석)|들의 (특|공통점|특징)",
     "1차 '숨은 꿀정보형'의 대체. '~하면 꼭 있는 유형'은 자기 식별 → 공감 폭발. n=9 소표본이나 avg 170만(8.2×), TOP40 다수 ('찜질방 가면 꼭 있는 유형' 1,478만)",
     ["travel_place", "food", "game"], "new"),
    ("F6", "하우투 명령형", r"해 ?보세요|하 ?세요|드 ?세요|만들어|따라 ?하|이렇게 (만들|드|해)",
     "'이렇게 만들어 보세요' 식 즉시 실행 가능성 약속. n=219, avg 1.6× / med 1.5×. 레시피/실무 카테고리 강자",
     ["food", "site_app", "beauty"], "new"),
    ("F7", "경고/손실 회피형", r"주의|하지 ?마|절대|조심|낭비|헛 ?돈|버리지|알아두면|손해",
     "'돈 버리기 전에 보세요' 손실 회심리. '주의' med 리프트 2.4×, n=125 avg 1.4×/med 1.7×",
     ["product", "site_app"], "new"),
    ("F8", "광고 아님 표방형", r"not an ad|광고 ?x|광고 ?❌|협찬 ?x|no ad|무광고",
     "역설적 훅 — '광고 아님' 명시가 찐 후기 신호. n=133, med 리프트 2.8× (avg는 1.0× — 승자독식 분포)",
     ["product", "game"], "verified"),
    ("F9", "사건 서사형 ('~하다 생긴 일')", r"생긴 ?일|生긴",
     "평범한 행동 뒤 예상 밖 사건 예고. 대량 코퍼스에서 표본 1건(112만) — 희소하지만 유효. '반전/사연/충격' 확장판은 n=54 avg 1.6×",
     ["product", "etc"], "weak"),
    ("F10", "질문 미해결형 (?)", r"\?",
     "2차 최대 발견: 상위 10% 질문형 22.1% vs 하위 10% 4.0% (5.5배 격차). n=1,741, med 리프트 1.7×. 결론을 물음으로 남겨야 클릭",
     ["all"], "new_strong"),
    ("F11", "대공개/공개형", r"공개",
     "'~를 공개합니다' 정보 개봉 서사. n=108, avg 2.0× / med 2.9×. '대공개'는 3.8×",
     ["travel_place", "game"], "new"),
    ("F12", "시리즈화 (ep/Part/N탄)", r"\bep\b|\bpart\b|[0-9]+ ?탄|\d+화$|시즌 ?[0-9]",
     "n=171, avg 리프트 3.5× — 워크맨ep 등 대형 채널의 구독 록인 장치. 검색 유입보다 시리즈 팬 유입. 신규 채널은 1탄/2탄 구조로 설계",
     ["etc", "travel_place", "game"], "new"),
    ("F13", "글로벌 자막 진출형 ([ENG])", r"\[eng|eng\]|한글자막|영어자막|english sub",
     "n=36, avg 리프트 6.4× / med 리프트 7.6× — 국내 콘텐츠 + 영어 자막 = 글로벌 시장 진입. 1차 '영어 제목 금지' 결론의 정정축",
     ["etc", "game", "travel_place"], "new"),
    ("F14", "초단어 신뢰형 (≤10자)", None,
     "'팀 차이', '와 뜨거워', '계란 맛집' — n=63, avg 85만(4.1×)이지만 med 1.3만. 대형 채널의 여유 마커. 채널 파워 없으면 금물, 있으면 최강",
     ["game", "food"], "conditional"),
    ("F15", "전문가/내부자 입장형", r"전문가|스타일리스트|현직|직원|개발자|디자이너|알바|선배|사장|대표|기자",
     "n=163, avg 1.0× / med 1.2× — 약양성으로 강등. '현직'보다 '알바/사장' 같은 현장 밀착형이 실제 상위 사례",
     ["clothing", "product"], "weak"),
    ("F16", "기간 후기 디테일형", r"\d+\s*(일|년|개월)(차|째| ?후기| ?사용)",
     "n=83, avg 0.6× — 약화. '100일 후기' 자체는 이제 차별화 안 됨",
     ["etc"], "weak"),
]

# 안티/강등된 1차 공식 (문서화용)
DEMOTED = [
    {"was": "F5(1차) 숨은 꿀정보형", "verdict": "무신호",
     "evidence": "'모르는/은근/몰랐' n=24 med 리프트 0.85, '꿀팁' n=263 med 0.95, '꿀' n=335 med 1.04 — 240건 샘플의 오탐"},
    {"was": "F6(1차) 장기 대량 검증→축약형", "verdict": "안티패턴 강등",
     "evidence": "'N년 동안 ... 베스트 M' 패턴 n=76, 중간값 80뷰 (전체 중간값 28,006의 0.3%). '베스트' 단어 자체 med 148"},
    {"was": "F10(1차) 인생 보증형 + 숫자 리스트", "verdict": "안티패턴 강등",
     "evidence": "'인생맛집/인생템' n=15 med 리프트 0.08. '인생' 단어 med 49,239(1.8×)지만 '인생+N리스트' 조합은 하락"},
    {"was": "F11(1차) 공감 반전 꿀팁형", "verdict": "약화",
     "evidence": "n=9, avg 리프트 0.71 — 소표본에서 유의미했으나 대량 데이터에서 무신호"},
]

# ---------- 상/하위 10% 비교 ----------
sv = sorted(items, key=lambda d: d["views"])
n10 = len(sv)//10
bot, top = sv[:n10], sv[-n10:]
def share(rows):
    c = Counter()
    for r in rows:
        for k, v in flags(r["title"]).items():
            if v: c[k] += 1
    return {k: round(c[k]/len(rows), 3) for k in FL}
ts, bs = share(top), share(bot)
avg_when = {}
for k in FL:
    sub = [d for d in items if flags(d["title"])[k]]
    if sub:
        avg_when[k] = {"share": round(len(sub)/len(items), 3), "avg_views": round(sum(x["views"] for x in sub)/len(sub))}

lenrows = [(len(d["title"]), d["views"]) for d in items]
def spearman(pairs):
    def rank(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0]*len(vals); i = 0
        while i < len(order):
            j = i
            while j+1 < len(order) and vals[order[j+1]] == vals[order[i]]: j += 1
            avg = (i+j)/2 + 1
            for k2 in range(i, j+1): r[order[k2]] = avg
            i = j+1
        return r
    xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
    rx, ry = rank(xs), rank(ys)
    mx, my = st.mean(rx), st.mean(ry)
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a-mx)**2 for a in rx)*sum((b-my)**2 for b in ry))
    return num/den

rho = spearman(lenrows); rho_log = spearman([(L, math.log10(v)) for L, v in lenrows])
len_buckets = {}
for lo in range(0, 80, 10):
    sub = [v for L, v in lenrows if lo <= L < lo+10]
    if sub: len_buckets[f"{lo}-{lo+10}"] = {"n": len(sub), "median_views": round(st.median(sub))}

# ---------- 훅 워드 ----------
HOOKS = ["봤습니다","직접","정품","차이","주의","미친","미쳤","충격","1위","최고","공개","대공개","유형","신기","진짜",
         "이유","vs","광고","이거","이것","요즘","인생","일까","핫한","꿀","꿀팁","꿀템","모음","모르는","과연","반전",
         "사연","역대급","feat","만원","억","수","초보","장단점","베스트","best","top","총정리","순위","1위","추천",
         "후기","리뷰","내돈내산","찐후기","솔직","실패","가성비","실사용","언박싱","비교","브이로그","쇼츠","숏츠","무료","템"]
lifts = {}
for h in HOOKS:
    r = lift_rows(items, re.escape(h))
    if r and r["n"] >= 15:
        lifts[h] = r
hook_lifts = sorted(
    [{"word": h, "count": r["n"], "avg_views": round(r["avg"]), "median_views": round(r["med"]),
      "lift_vs_overall": round(r["lift_avg"], 2), "lift_median": round(r["lift_med"], 2)}
     for h, r in lifts.items()], key=lambda x: -x["lift_vs_overall"])

# ---------- 카테고리 ----------
CAT_LABEL = {"game": "게임", "clothing": "옷/패션", "product": "제품/가전/IT", "site_app": "사이트/앱/툴",
             "food": "음식/맛집/레시피", "travel_place": "여행/장소/체험", "beauty": "뷰티", "etc": "기타"}
CAT_ORDER = ["game", "food", "travel_place", "product", "beauty", "site_app", "clothing", "etc"]
by_cat = {}
for c in CAT_ORDER:
    rows = [d for d in items if d["_cat"] == c]
    if not rows: continue
    rows_sorted = sorted(rows, key=lambda d: -d["views"])
    cat_n10 = max(len(rows)//10, 1)
    ctop, cbot = rows_sorted[:cat_n10], rows_sorted[-cat_n10:]
    cts, cbs = share(ctop), share(cbs := cbot)
    dom = {k: cts[k] for k in ["question", "has_digit", "emoji", "vs", "listy", "slang", "money_ref", "series_ref", "is_korean"] if cts.get(k, 0) >= 0.05}
    # 카테고리별 공식 리프트 → 추천
    recs = []
    for fid, name, pat, mech, bestfor, status in FORMULAS:
        if status == "conditional":
            if c in bestfor: recs.append(f"{fid} {name}")
            continue
        r = lift_rows(rows, pat)
        if r and r["n"] >= 5 and (r["lift_med"] >= 1.3 or r["lift_avg"] >= 1.5):
            recs.append(f"{fid} {name}")
        elif c in bestfor and r and r["n"] >= 3:
            recs.append(f"{fid} {name}")
    if not recs:
        recs = ["F10 질문 미해결형 (?)", "F4 감탄 슬랭 오프닝형"]
    by_cat[c] = {
        "label": CAT_LABEL[c],
        "stats": {"sample": len(rows), "avg_views": round(sum(x["views"] for x in rows)/len(rows)),
                  "median_views": round(st.median([x["views"] for x in rows])),
                  "avg_title_len": round(st.mean(len(x["title"]) for x in rows), 1)},
        "dominant_hooks_top10pct": dom,
        "top_titles": [{"title": d["title"][:90], "views": d["views"], "query": d.get("query", "")}
                       for d in rows_sorted[:3]],
        "recommended_formulas": recs[:7],
    }

# ---------- 조립 ----------
out = {
    "meta": {
        "generated": "2026-08-19",
        "analysis_pass": 2,
        "source_corpus": "corpus_youtube.json",
        "corpus_size": 10335,
        "corpus_size_views_available": len(items),
        "queries": 904,
        "overall": {"avg_views": round(OA), "median_views": round(OM),
                    "views_range": [min(d["views"] for d in items), max(d["views"] for d in items)]},
        "views_dist_logscale": {
            "<1K": 1761, "1K-10K": 1933, "10K-100K": 3548, "100K-1M": 2573, "1M+": 454,
            "note": "10K-100K가 34.6% 최다. 롱테일: 1M+는 4.4%뿐 — 승자독식 분포"},
        "top10pct_vs_bottom10pct_flags": {"top_share": ts, "bottom_share": bs,
            "key_gaps": {
                "question(+0.181)": "상위 22.1% vs 하위 4.0% — 최대 격차. 질문형이 2차 최대 발견",
                "listy(-0.342)": "하위 48.5% vs 상위 14.3% — 'Top N/모음/순위' 리스트형은 하위 신호로 반전",
                "is_korean(-0.243)": "하위 92.2% 한글 vs 상위 67.9% — 짧은 한글 키워드 나열형이 하위 대량 포진",
                "has_digit(-0.155)": "숫자 남발은 하위 신호(단 금액 '만원/억'은 별도 강신호 med 2.3×)",
                "emoji(+0.104)": "상위 17.1% vs 하위 6.7%, 이모지 有 med 48,300 vs 無 23,771 — 2배",
                "bracket(+0.055)": "[브랜드/ENG] 마커는 상위 우위"}},
        "title_len": {
            "top10pct_avg": round(st.mean(len(r["title"]) for r in top), 1),
            "bottom10pct_avg": round(st.mean(len(r["title"]) for r in bot), 1),
            "overall_avg": round(st.mean(len(r["title"]) for r in items), 1),
            "median_views_by_bucket": len_buckets,
            "spearman_len_vs_views": round(rho, 4),
            "spearman_len_vs_log10views": round(rho_log, 4),
            "note": "상관 +0.15 약양성. 40-70자 구간 med 상승. 1차 '짧게(48자)' 결론 정정: 하위 10% 평균이 39.6자로 오히려 짧음 — 짧은 키워드 나열형=소형채널 SEO. 단 ≤10자 초단어는 채널 파워 있을 때 최강(avg 4.1×)"},
        "language": {
            "korean_share": round(sum(1 for d in items if HANGUL.search(d["title"]))/len(items), 3),
            "korean_median_views": 18515, "non_korean_median_views": 50918,
            "note": "1차 '한국어 필수' 결론 정정: 비한글 제목 med가 2.7× 높음. 단 교란 변수 — 대형/글로벌 채널 + [ENG] 자막 전략. 신규 소형 채널은 한글+영어자막 병행이 정답"},
        "first_pass_overturned": [
            "1차 '숨은 꿀정보(은근/모르는/꿀팁)' → 무신호 (med 0.85-1.04)",
            "1차 '장기대량검증 N곳 중 베스트 M' → 안티 (med 80뷰)",
            "1차 '인생 보증형' → 안티 (med 리프트 0.08)",
            "1차 '짧은 제목(48자) 선호' → 정정 (하위 10%가 더 짧음 39.6자)",
            "1차 '영어 제목 지양' → 정정 (비한글 med 2.7×, [ENG] 자막 7.6×)",
            "1차 '감정어(neg_emotion) 강함' → 정정 (하위에서 더 많음 — 분노 저품질 마케팅과 혼동된 것)",
        ],
    },
    "title_formulas": [],
    "demoted_formulas_1st_pass": DEMOTED,
    "by_category": by_cat,
    "hook_words": [],
    "hook_word_lifts": hook_lifts,
    "anti_patterns": [],
}

# formulas with real evidence
for fid, name, pat, mech, bestfor, status in FORMULAS:
    ev = {"best_example": "", "views": 0, "query": ""}
    if pat is None:
        sub = [d for d in items if len(d["title"]) <= 10]
    else:
        sub = [d for d in items if re.search(pat, d["title"], re.I)]
    if sub:
        b = max(sub, key=lambda r: r["views"])
        stats = {"n": len(sub), "avg_views": round(sum(x["views"] for x in sub)/len(sub)),
                 "median_views": round(st.median([x["views"] for x in sub])),
                 "lift_avg": round((sum(x["views"] for x in sub)/len(sub))/OA, 2),
                 "lift_med": round(st.median([x["views"] for x in sub])/OM, 2)}
        ev = {"best_example": b["title"][:90], "views": b["views"], "query": b.get("query", "")}
    else:
        stats = {"n": 0}
    out["title_formulas"].append({
        "id": fid, "name": name, "template_hint": name, "mechanism": mech,
        "best_for": bestfor, "status": status, "stats": stats, "evidence": ev,
    })

# hook_words (role 중심 사전)
out["hook_words"] = [
    {"word": "? / ~일까? / 이게 맞나요?", "role": "결론 미해결 — 최강 클릭 버튼", "stats": {"count": 1741, "median_views": 48852, "lift_median": 1.74}, "note": "상위10% 22.1% vs 하위10% 4.0%"},
    {"word": "봤습니다 (체험 종결)", "role": "경험 완료 사실 보고 — 결과 궁금증", "stats": {"count": 93, "median_views": 96388, "lift_median": 3.44}},
    {"word": "1위 / 최고", "role": "명확한 1등 지정", "stats": {"count": 70, "median_views": 151534, "lift_median": 5.41}, "note": "'1위'는 med 5.4× — 최고 훅. 단 '베스트N/Top N' 나열과 반대"},
    {"word": "정품", "role": "진품 검증 프레임 (짝퉁 시대 신뢰)", "stats": {"count": 19, "median_views": 118462, "lift_median": 4.23}},
    {"word": "미쳤다/충격/소름", "role": "감탄 반응 — 뇌가 기대하는 각성", "stats": {"count": 51, "median_views": 101555, "lift_median": 3.63}},
    {"word": "대공개/공개", "role": "정보 개봉 서사", "stats": {"count": 108, "median_views": 80462, "lift_median": 2.87}},
    {"word": "유형/~하는 사람", "role": "자기 식별 유도 — '이거 나잖아' 공감", "stats": {"avg_views": 1698353, "lift_avg": 8.25}, "note": "n=9 소표본, TOP40 다수 차지"},
    {"word": "직접", "role": "검증자=본인 — 신뢰 코어", "stats": {"count": 88, "median_views": 70050, "lift_median": 2.5}},
    {"word": "차이", "role": "비교 결과 예고 ('팀 차이' 1,080만)", "stats": {"count": 40, "lift_avg": 2.5}},
    {"word": "주의/헛돈", "role": "손실 회피 본능 자극", "stats": {"count": 37, "median_views": 67019, "lift_median": 2.39}},
    {"word": "[ENG]/한글자막", "role": "글로벌 시장 진입 마커", "stats": {"count": 36, "median_views": 213920, "lift_median": 7.64}},
    {"word": "ep/Part/2탄", "role": "시리즈 록인 — 구독 유입", "stats": {"count": 171, "avg_views": 714379, "lift_avg": 3.47}},
    {"word": "만원/억 (구체 금액)", "role": "숫자가 아니라 '돈' — 진정성", "stats": {"count": 294, "median_views": 64273, "lift_median": 2.29}},
    {"word": "반전/사연", "role": "스토리 궁금증", "stats": {"count": 54, "lift_avg": 1.6}},
    {"word": "ㄹㅇ/ㅈㄴ/개/찐", "role": "신세대 강조 — 구어 톤 (상위 7.6% vs 하위 4.5%)"},
    {"word": "이렇게/해 보세요", "role": "즉시 실행 가능성 약속", "stats": {"count": 219, "lift_avg": 1.62}},
]

out["anti_patterns"] = [
    {"pattern": "'찐후기/솔직후기/내돈내산' 레이블 자체",
     "evidence": "찐후기 n=66 med 32뷰 · 솔직 n=238 med 8,996 · 내돈내산 n=300 med 9,987 — 전부 전체 med(28,006)의 0.1-0.4배",
     "why": "2026년 기준 이 단어들은 이미 전 시장이 쓰는 '성의 없는 신뢰 표방'. 레이블이 아니라 내용(금액/기간/질문)으로 신뢰를 증명해야 함"},
    {"pattern": "Top N / 베스트 N / 모음 / 총정리 / 순위 리스트형",
     "evidence": "listy 플래그: 하위10% 48.5% vs 상위10% 14.3% — 격차 -0.34로 전체 최악. '베스트' med 148 · '순위' med 86 · 'top' med 641",
     "why": "정보를 다 주겠다는 약속은 클릭 이유를 없앰 + 경쟁 과포화. 숫자는 '1위' 또는 '금액'으로만"},
    {"pattern": "언박싱/개봉 콘텐츠의 '언박싱' 제목 명시",
     "evidence": "n=388, med 2,905 (0.10×)",
     "why": "행위 자체가 식상. 개봉 순간의 반전/결과를 제목으로"},
    {"pattern": "숫자 나열형 (Top10, 3가지, 7개...)",
     "evidence": "has_digit: 하위10% 68.4% vs 상위10% 53.0%",
     "why": "숫자가 리소스 약속으로만 쓰이면 실패. 단 금액(만원/억)·기간(일차)은 예외적으로 강신호"},
    {"pattern": "짧은 키워드 나열형 제목 (≤30자)",
     "evidence": "하위10% 평균 39.6자, 10-30자 구간 med 최저(1.3-1.5만). 상위10% 평균 53.4자",
     "why": "1차 '짧은 제목' 결론의 정정. 짧은 제목은 소형 채널의 SEO 키워드 나열. 예외: 대형 채널의 ≤10자 초단어(avg 85만)는 여유의 신뢰 마커"},
    {"pattern": "'실패' 키워드 단독 사용",
     "evidence": "n=225, med 2,432 (0.09×)",
     "why": "실패 콘텐츠 자체는 유효하나 '실패'를 제목에 그대로 쓰면 저품질 시그널. '헛돈/주의/버리기 전에'로 재포장"},
    {"pattern": "분노/비난 저품질 감정어 (사기/쓰레기/차별 등)",
     "evidence": "neg_emotion: 하위10% 7.5% vs 상위10% 5.6%",
     "why": "1차에 '부정 감정 강함'으로 오기록된 패턴 — 240건 샘플 편향. 대량 데이터에서는 역방향"},
    {"pattern": "'~브이로그' 명시",
     "evidence": "n=314, med 6,735 (0.24×)",
     "why": "장르 라벨은 훅이 아님. 브이로그라도 사건/질문/공개로 제목"},
    {"pattern": "가성비 강조",
     "evidence": "n=414, med 8,050 (0.29×)",
     "why": "모두가 가성비를 말하는 시장에서 무차별화. '헛돈/낭비' 프레임이 2.4×"},
]

json.dump(out, open(BASE + r"\patterns_youtube.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("written. formulas:", len(out["title_formulas"]), "| categories:", len(by_cat), "| hook_lifts:", len(hook_lifts))
print("meta corpus_size:", out["meta"]["corpus_size"], "views_available:", out["meta"]["corpus_size_views_available"])
for f in out["title_formulas"]:
    print(f"{f['id']:>4} [{f['status']:>10}] n={f['stats'].get('n',0):4d} lA={f['stats'].get('lift_avg','-'):>5} lM={f['stats'].get('lift_med','-'):>5}  {f['name']}")
