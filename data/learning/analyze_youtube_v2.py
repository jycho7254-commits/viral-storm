# -*- coding: utf-8 -*-
"""유튜브 바이럴 패턴 2차 재분석 — 탐색용 (corpus_youtube.json 10,335건)
재현: python analyze_youtube_v2.py
"""
import json, re, math, statistics
from collections import Counter, defaultdict

PY = None
BASE = r"C:\Users\user\Desktop\viral-storm\data\learning"
CORPUS = BASE + r"\corpus_youtube.json"

data = json.load(open(CORPUS, encoding="utf-8"))
print("total:", len(data))

items = [d for d in data if isinstance(d.get("views"), int) and d["views"] > 0 and d.get("title")]
print("views>0 & title:", len(items))

views_all = [d["views"] for d in items]
overall_avg = sum(views_all) / len(views_all)
overall_med = statistics.median(views_all)
print(f"overall avg={overall_avg:,.0f} median={overall_med:,.0f}")
print("views min/max:", min(views_all), max(views_all))

# ---------- 1. 로그 구간 분포 ----------
buckets = [("<1K", 0, 1_000), ("1K-10K", 1_000, 10_000), ("10K-100K", 10_000, 100_000),
           ("100K-1M", 100_000, 1_000_000), ("1M+", 1_000_000, float("inf"))]
print("\n== views dist ==")
for name, lo, hi in buckets:
    sub = [v for v in views_all if lo <= v < hi]
    print(f"{name:>10}: n={len(sub):5d} ({len(sub)/len(views_all)*100:5.1f}%)")

# ---------- 카테고리 분류 ----------
GAME = ['게임','로블록스','마비노기','메이플','명일방주','붕괴','스타레일','브롤스타즈','블루 아카이브','블루아카이브',
        '서든어택','FC 온라인','PS5','플스5','스위치','닌텐도','스팀게임','스팀 인디','스팀 게임','RPG','VR 게임',
        '로맨스 게임','로스트아크','로얄매치','로열매치','리니지','리그오브레전드','발로란트','배틀그라운드','보드게임',
        '아이온','엑스박스','우마무스메','원신','젠레스','캐주얼게임','쿠키런','킹샷','트릭컬','검은사막','인디게임',
        '라스트워','모바일게임','모바일 게임']
BEAUTY = ['샴푸','세럼','마스크팩','립틴트','선크림','쿠션','클렌징','토너','스킨케어','향수','다이슨 에어랩']
CLOTH = ['OOTD','니트','레더자켓','로퍼','모자','무신사','부츠','샌들','선글라스','선캡','셔츠','스니커즈','스커트',
         '슬랙스','아디다스','오버사이즈','와이드팬츠','자켓','청바지','치노팬츠','코듀로이','트렌치코트','패션','후드집업',
         '패딩','러닝화','나이키','니케','에어포스','삼선','운동화','구두','원피스','맨투맨','양말','벨트','ankle','코디','룩북','옷']
FOOD = ['간식','맥주','맛집','반찬','도시락','레시피','와인','위스키','커피 원두','다이어트 식단','카페']
SITE = ['사이트','ChatGPT','chatgpt','AI ','노션','PDF','깃허브','리눅스','미드저니','블로그 시작','클라우드','엑셀',
        '이미지 편집','유튜브 알고리즘','인스타 마케팅','작업 사이트','프리미어','피그마','포토샵','스프레드시트',
        '디자인 툴','동영상 편집','stable diffusion','앱 추천','iot','번역','미러']
PLACE = ['경주 여행','골프장','놀이공원','박물관','부산 여행','스키장','전시회','제주 숙소','찜질방','워터파크','여행']
PROD = ['가방','갤럭시','게이밍마우스','골프채','공기청정기','기계식키보드','노트북','드라이기','등산용품','레저매트',
        '무선이어폰','무선청소기','버즈','블루투스 스피커','모니터암','아이맥','아이패드','아이폰','안마의자','애플워치',
        '에어팟','요가매트','전기밥솥','전기자전거','캐리어','캠핑의자','캠핑텐트','커피머신','킨들','헬스용품','맥북',
        '지갑','nas','홈서버','인생템','요즘 핫한 제품','제품 리뷰','정품 리뷰']

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

cat_counter = Counter()
cat_etc_queries = []
for d in items:
    c = classify(d.get("query"))
    d["_cat"] = c
    cat_counter[c] += 1
    if c == "etc": cat_etc_queries.append(d.get("query"))
print("\n== categories ==")
for c, n in cat_counter.most_common(): print(f"{c:>13}: {n}")
print("etc queries:", Counter(cat_etc_queries).most_common(20))

# ---------- 카테고리별 조회수 ----------
print("\n== by category stats ==")
for c in [k for k, _ in cat_counter.most_common()]:
    vs = [d["views"] for d in items if d["_cat"] == c]
    ls = [len(d["title"]) for d in items if d["_cat"] == c]
    print(f"{c:>13}: n={len(vs):5d} avg={sum(vs)/len(vs):>12,.0f} med={statistics.median(vs):>10,.0f} len={sum(ls)/len(ls):.1f}")

# ---------- 2. Top10% vs Bottom10% ----------
sv = sorted(items, key=lambda d: d["views"])
n = len(sv)
bot = sv[:n//10]; top = sv[-n//10:]

HANGUL = re.compile(r"[가-힣]")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]")

def flags(t):
    tl = t.lower()
    return {
        "question": "?" in t,
        "vs": bool(re.search(r"\bvs\.?\b", tl)),
        "first_person": any(k in t for k in ["저는","저희","제가","나는","내 ","내가","내돈"]),
        "experience_verb": bool(re.search(r"봤습니다|해 ?봤|써 ?봤|사 ?봤|가 ?봤|먹어 ?봤|마셔 ?봤|깔아 ?봤|직접|실사용|체험|내돈내산|직접 해봄", t)),
        "slang": bool(re.search(r"ㄹㅇ|ㅈㄴ|ㅋㅋ|ㅠㅠ|ㄷㄷ|개꿀|개빡|개소리|찐|소름|미쳤|헐|오지다|억수로|왤캐", t)),
        "neg_emotion": bool(re.search(r"실패|실망|빡|화나|별로|후회|날린|손해|쓰레기|차별|논란|사기|충격|주의|함정|개망|망했", t)),
        "superlative": bool(re.search(r"최고|베스트|1위|갓|전설|끝판왕|인생|완벽|제일", t)),
        "has_digit": bool(re.search(r"\d", t)),
        "ad_ref": ("광고" in t or "협찬" in t),
        "bracket": ("[" in t),
        "emoji": bool(EMOJI.search(t)),
        "exclam": ("!" in t),
        "is_korean": bool(HANGUL.search(t)),
        "shorts_ref": bool(re.search(r"쇼츠|숏츠|shorts|short", tl)),
        "price_ref": bool(re.search(r"[0-9]+만원|[0-9,]+원|\$|만원짜리|원짜리|가성비|저렴|싸게|할인|반값", t)),
        "listy": bool(re.search(r"top\s*\d|베스트\s*\d|\d+가지|\d+개|\d+곳|\d+일|\d+위|모음|총정리|추천\s*\d|리스트|순위", tl)),
    }

def flag_share(rows):
    cnt = Counter()
    for r in rows:
        for k, v in flags(r["title"]).items():
            if v: cnt[k] += 1
    return {k: cnt[k]/len(rows) for k in flags(rows[0]["title"])}

ts, bs = flag_share(top), flag_share(bot)
print(f"\n== top10% (n={len(top)}, med={statistics.median([r['views'] for r in top]):,.0f}) vs bottom10% (n={len(bot)}, med={statistics.median([r['views'] for r in bot]):,.0f}) ==")
print(f"{'flag':>18} {'top':>8} {'bot':>8} {'diff':>8}")
for k in ts:
    print(f"{k:>18} {ts[k]:8.3f} {bs[k]:8.3f} {ts[k]-bs[k]:+8.3f}")

tl_top = statistics.mean(len(r["title"]) for r in top)
tl_bot = statistics.mean(len(r["title"]) for r in bot)
tl_all = statistics.mean(len(r["title"]) for r in items)
print(f"title len: top={tl_top:.1f} bot={tl_bot:.1f} all={tl_all:.1f}")

# ---------- 6. 제목 길이 vs 조회수 ----------
print("\n== title length vs views (median per bucket) ==")
lenrows = [(len(d["title"]), d["views"]) for d in items]
for lo in range(0, 80, 10):
    sub = [v for L, v in lenrows if lo <= L < lo+10]
    if sub:
        print(f"len {lo:2d}-{lo+10:2d}: n={len(sub):5d} med={statistics.median(sub):>10,.0f}")

def spearman(pairs):
    def rank(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0]*len(vals); i = 0
        while i < len(order):
            j = i
            while j+1 < len(order) and vals[order[j+1]] == vals[order[i]]: j += 1
            avg = (i + j)/2 + 1
            for k in range(i, j+1): r[order[k]] = avg
            i = j+1
        return r
    xs = [p[0] for p in pairs]; ys = [p[1] for p in pairs]
    rx, ry = rank(xs), rank(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a-mx)*(b-my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a-mx)**2 for a in rx) * sum((b-my)**2 for b in ry))
    return num/den

rho = spearman(lenrows)
rho_log = spearman([(L, math.log10(v)) for L, v in lenrows])
print(f"spearman(len, views)={rho:.4f}  spearman(len, log10 views)={rho_log:.4f}")

# ---------- 5. 훅 워드 리프트 (1차 12개 + 확장) ----------
HOOKS = ["봤습니다","직접","vs","최고","정품","비교","꿀팁","모르는","베스트","후기","광고","리뷰","꿀","인생","쇼츠",
         "총정리","언박싱","추천","내돈내산","찐후기","솔직","실패","가성비","실사용","진짜","브이로그","숏츠","모음",
         "순위","필수","템","무료","공짜","은근","몰랐","숨겨진","미쳤","소름","충격","실화","생긴 일","일까","맞나요",
         "1위","top","best","not an ad","협찬","체험단","리얼","openbox","구매 가이드","초보","장단점","차이","이유",
         "이거","이것","주의","후회","별로","실망","비추","꿀템","국민","만인","다들","요즘","요새","핫한","대란","plpick",
         "존맛","꿀맛","찐","오질라","신기","미친","개꿀","ㄹㅇ"]
print("\n== hook word lift (count>=15) ==")
res = []
for h in HOOKS:
    rows = [d for d in items if h.lower() in d["title"].lower()]
    if len(rows) < 15: continue
    vs = [r["views"] for r in rows]
    res.append((h, len(rows), sum(vs)/len(vs), statistics.median(vs), (sum(vs)/len(vs))/overall_avg, statistics.median(vs)/overall_med))
res.sort(key=lambda x: -x[2])
print(f"{'word':>14} {'n':>5} {'avg':>12} {'med':>10} {'lift_avg':>9} {'lift_med':>9}")
for h, c, a, m, la, lm in res:
    print(f"{h:>14} {c:5d} {a:12,.0f} {m:10,.0f} {la:9.2f} {lm:9.2f}")

# ---------- 신규 후보 자동 발굴 (n-gram 스캔) ----------
print("\n== auto ngram scan (n>=40, top by median) ==")
def tokens(t):
    return [w for w in re.split(r"[^\w가-힣]+", t.lower()) if len(w) >= 2]

uni = Counter(); big = Counter()
for d in items:
    ts_ = tokens(d["title"])
    uni.update(ts_)
    big.update(zip(ts_, ts_[1:]))

cand = {w for w, c in uni.items() if c >= 40}
cand |= {" ".join(b) for b, c in big.items() if c >= 40}
scored = []
for h in cand:
    rows = [d for d in items if h in d["title"].lower()]
    if len(rows) < 40: continue
    vs = [r["views"] for r in rows]
    scored.append((h, len(rows), sum(vs)/len(vs), statistics.median(vs), statistics.median(vs)/overall_med))
scored.sort(key=lambda x: -x[3])
print("-- by median lift --")
for h, c, a, m, lm in scored[:40]:
    print(f"{h:>22} {c:5d} {a:12,.0f} {m:10,.0f} {lm:8.2f}")
scored.sort(key=lambda x: -x[2])
print("-- by avg lift --")
for h, c, a, m, lm in scored[:40]:
    print(f"{h:>22} {c:5d} {a:12,.0f} {m:10,.0f} {a/overall_avg:8.2f}")

# ---------- 쿼리 intent suffix 비교 (수집 실험 변수, 참고용) ----------
print("\n== query intent suffix vs views (참고: 수집쿼리 실험변수) ==")
SUF = ["내돈내산","실패","가성비","진짜","찐후기","총정리","최신","언박싱","비교","순위","best","2026","꿀팁","리뷰",
       "후기","브이로그","직접 해봄","실사용","장단점","초보","구매 가이드","추천","솔직 후기"]
for s in SUF:
    rows = [d for d in items if (d.get("query") or "").endswith(s)]
    if len(rows) < 30: continue
    vs = [r["views"] for r in rows]
    print(f"{s:>10}: n={len(rows):5d} avg={sum(vs)/len(vs):>11,.0f} med={statistics.median(vs):>10,.0f}")

# ---------- 대량 데이터 신규 패턴 후보 ----------
print("\n== pattern candidates ==")
def med(rows): return statistics.median([r["views"] for r in rows])

cands = {
    "shorts_ref": [d for d in items if re.search(r"쇼츠|숏츠|shorts", d["title"].lower())],
    "emoji_yes": [d for d in items if EMOJI.search(d["title"])],
    "emoji_no": [d for d in items if not EMOJI.search(d["title"])],
    "bracket_yes": [d for d in items if "[" in d["title"]],
    "korean_yes": [d for d in items if HANGUL.search(d["title"])],
    "korean_no": [d for d in items if not HANGUL.search(d["title"])],
    "naemyon": [d for d in items if "내돈내산" in d["title"]],
    "jjinhugi": [d for d in items if "찐후기" in d["title"]],
    "soljik": [d for d in items if "솔직" in d["title"]],
    "question": [d for d in items if "?" in d["title"]],
    "exclam": [d for d in items if "!" in d["title"]],
    "digit": [d for d in items if re.search(r"\d", d["title"])],
    "ad_ref": [d for d in items if "광고" in d["title"] or "협찬" in d["title"]],
    "first_person": [d for d in items if re.search(r"저는|저희|제가|나는|내가|내돈", d["title"])],
    "experience": [d for d in items if re.search(r"봤습니다|해 ?봤|직접|실사용|체험|내돈내산|직접 해봄", d["title"])],
    "period_days": [d for d in items if re.search(r"\d+\s*(일|년|개월|주) (동안|간|째|사용|후기)|\d+일차|\d+일 사용", d["title"])],
}
for name, rows in cands.items():
    if not rows: print(f"{name:>14}: n=0"); continue
    print(f"{name:>14}: n={len(rows):5d} avg={sum(r['views'] for r in rows)/len(rows):>11,.0f} med={med(rows):>10,.0f}")

# 상위 제목 샘플 (새 공식 발굴용)
print("\n== TOP 40 titles ==")
for d in sorted(items, key=lambda x: -x["views"])[:40]:
    print(f"{d['views']:>10,}  [{d['_cat']:>12}] {d['title'][:80]}  <{d.get('query','')}>")
