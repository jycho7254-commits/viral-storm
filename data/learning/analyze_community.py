# -*- coding: utf-8 -*-
"""DC인사이드 + 루리웹 커뮤니티 바이럴 패턴 분석 (데이터 기반)

입력: learning_summary.json (dc_top100, dc_patterns, ruliweb_titles)
      corpus_dc.json (전체 9,428건 — 성공/실패 비교용)
출력: patterns_community.json (stdout로 통계 리포트)
"""
import json
import re
import statistics
import collections

BASE = r"C:\Users\user\Desktop\viral-storm\data\learning"
PY_OUT = BASE + r"\patterns_community.json"

with open(BASE + r"\learning_summary.json", encoding="utf-8") as f:
    summary = json.load(f)
with open(BASE + r"\corpus_dc.json", encoding="utf-8") as f:
    corpus = json.load(f)

dc_top = summary["dc_top100"]           # [{t, r, g}]
dc_patterns = summary["dc_patterns"]    # {패턴명: 카운트}
ruli = [x if isinstance(x, str) else x.get("t", "") for x in summary["ruliweb_titles"]]

# ------------------------------------------------------------------
# 1. 후킹 유형 분류기 (정규식, 배타적이지 않음: 한 제목에 여러 후킹 가능)
# ------------------------------------------------------------------
RE_QUESTION = re.compile(r"(\?|ㄹ까|ㄹ게|~나|인가|왜 |어떻게|뭐 살|뭐사|추천해|알려줘|알아보자|일까|까\?)")
RE_FIRST_PERSON = re.compile(r"(했습니다|해봤다|해봤습니다|먹었다|먹어봄|입문|후기|리뷰|당했다|느꼈다|갈아탔다|써봄|직접)")
RE_COMPARE = re.compile(r"(vs|VS|Vs\.?|versus|비교|대결|차이|갈아탄|갈아타|전환|이전엔|예전엔|~보다)")
RE_SLANG = re.compile(r"(ㅋ{2,}|ㅠ+|ㅎ{2,}|ㄹㅇ|ㄷㄷ|ㄱㄷ|ㅈㄴ|ㅅㅂ|꿀|찐|혜자|어그로|레게노|실화|ㅈㄷ|개꿀|존맛|존망|정줄|허세|폭망)")
RE_CHOSEONG = re.compile(r"[ㄱ-ㅎ]{2,}")  # 자모 은어 (ㅋㅋ 포함, 초성형)
RE_INFOGAP = re.compile(r"(모음|정리|총정리|목록|모음집|가이드|팁|방법|알아보자|해부|분석|비밀|꿀팁|모든 것|정리판|총모음|리스트)")
RE_NUMBER = re.compile(r"[0-9０-９]+")
RE_TIME = re.compile(r"(D-\d|오늘|내일|어제|방금|실시간|지금|새벽|아침|저녁|\d월|\d일|\d년|시즌|버전|ver|초|분 전)")
RE_FREE = re.compile(r"(무료|공짜|free|덤|증정|이벤트)")
RE_SHOCK = re.compile(r"(충격|소름|미쳤|실화|헐|개소름|레전드|역대급|미친|폭망|실패|망했|사고|터졌|터진|사건)")
RE_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2764\u2728\u2934\u2935\u3030❥◆◇★☆▶►]")
RE_EXCL = re.compile(r"!")
RE_NOTICE = re.compile(r"(공지|이용 안내|이용안내|필독|규정|안내)")

def classify(title):
    tags = set()
    if RE_QUESTION.search(title): tags.add("질문형")
    if RE_SHOCK.search(title): tags.add("충격/과장")
    if RE_FIRST_PERSON.search(title): tags.add("1인칭 경험담")
    if RE_COMPARE.search(title): tags.add("비교/갈아타기")
    if RE_SLANG.search(title): tags.add("커뮤니티 은어")
    if RE_INFOGAP.search(title): tags.add("정보격차(모음/가이드)")
    if RE_NUMBER.search(title): tags.add("숫자 구체성")
    if RE_TIME.search(title): tags.add("시간 정보성")
    if RE_FREE.search(title): tags.add("무료/혜택 강조")
    if RE_EMOJI.search(title): tags.add("이모지/장식기호")
    if RE_EXCL.search(title): tags.add("느낌표")
    if RE_NOTICE.search(title): tags.add("공지형")
    return tags

# ------------------------------------------------------------------
# 2. 코퍼스 성공률 분석: 각 후킹 유형별 고추천 진입율/평균 추천수
# ------------------------------------------------------------------
corpus_valid = [c for c in corpus if isinstance(c.get("title"), str) and c["title"].strip()]
recs = sorted((c.get("recommends") or 0 for c in corpus_valid), reverse=True)
n = len(corpus_valid)
top5_cut = recs[max(0, int(n * 0.05) - 1)] if n else 0  # 상위 5% 커트라인
top10_cut = recs[max(0, int(n * 0.10) - 1)] if n else 0

def stats_for(items):
    if not items:
        return {"n": 0, "avg_rec": 0.0, "hit5_pct": 0.0, "hit10_pct": 0.0, "median_rec": 0.0}
    rs = [c.get("recommends") or 0 for c in items]
    hit5 = sum(1 for r in rs if r >= max(top5_cut, 1))
    hit10 = sum(1 for r in rs if r >= max(top10_cut, 1))
    return {
        "n": len(items),
        "avg_rec": round(statistics.mean(rs), 2),
        "median_rec": statistics.median(rs),
        "hit5_pct": round(100 * hit5 / len(rs), 2),
        "hit10_pct": round(100 * hit10 / len(rs), 2),
    }

base_stats = stats_for(corpus_valid)

type_stats = {}
for c in corpus_valid:
    for tg in classify(c["title"]):
        type_stats.setdefault(tg, []).append(c)
type_stats = {k: stats_for(v) for k, v in sorted(type_stats.items())}

# 유형별 성공 배율 (전체 대비 상위5% 진입율 배수)
lift5 = {k: round(v["hit5_pct"] / base_stats["hit5_pct"], 2) if base_stats["hit5_pct"] else 0 for k, v in type_stats.items()}

# ------------------------------------------------------------------
# 3. 제목 길이 분석
# ------------------------------------------------------------------
len_bins = [(0, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 100)]
len_stats = {}
for lo, hi in len_bins:
    grp = [c for c in corpus_valid if lo <= len(c["title"]) < hi]
    len_stats[f"{lo}-{hi if hi < 100 else '+'}"] = stats_for(grp)

top100_len = [len(x["t"]) for x in dc_top]
ruli_len = [len(x) for x in ruli if x]

# ------------------------------------------------------------------
# 4. 갤러리 그룹별 분석 (게임 vs 제품 vs 기타)
# ------------------------------------------------------------------
GAME_G = {"wutheringwaves", "limbuscompany", "solehchant", "royalmatch", "wow", "lostark"}
PRODUCT_G = {"smartphone", "watch", "cosmetic", "perfume"}
OTHER_G = {"food"}

def gallery_group(g):
    if g in GAME_G: return "game"
    if g in PRODUCT_G: return "product"
    if g in OTHER_G: return "food"
    return "other"

gall_stats = {}
for grp_name in ("game", "product", "food", "other"):
    grp = [c for c in corpus_valid if gallery_group(c.get("gallery", "")) == grp_name]
    if not grp: continue
    # 그룹 내 상위 10% 진입율 대신, 그룹별 후킹 분포와 평균 추천수
    tag_counter = collections.Counter()
    for c in grp:
        tag_counter.update(classify(c["title"]))
    st = stats_for(grp)
    top_tags = [{"tag": t, "pct": round(100 * cnt / len(grp), 1)} for t, cnt in tag_counter.most_common(6)]
    avg_len = round(statistics.mean(len(c["title"]) for c in grp), 1)
    gall_stats[grp_name] = {
        "galleries": sorted(set(c["gallery"] for c in grp)),
        "n": len(grp), "avg_rec": st["avg_rec"], "avg_title_len": avg_len,
        "hit5_pct": st["hit5_pct"], "top_hook_tags": top_tags,
    }

# 상위100(dc_top100)에서 그룹별 성공 후킹 예시
top_examples_by_grp = collections.defaultdict(list)
for x in sorted(dc_top, key=lambda z: -z["r"]):
    grp = gallery_group(x["g"])
    if len(top_examples_by_grp[grp]) < 5:
        top_examples_by_grp[grp].append({"t": x["t"], "r": x["r"], "g": x["g"]})

# ------------------------------------------------------------------
# 5. 루리웹 제목 분석 (뉴스형 vs 커뮤니티형)
# ------------------------------------------------------------------
ruli_tags = collections.Counter()
ruli_lens = []
for t in ruli:
    if not t: continue
    ruli_lens.append(len(t))
    for tg in classify(t):
        ruli_tags[tg] += 1
ruli_stats = {
    "n": len(ruli_lens),
    "avg_len": round(statistics.mean(ruli_lens), 1) if ruli_lens else 0,
    "median_len": statistics.median(ruli_lens) if ruli_lens else 0,
    "tag_pct": [{"tag": t, "pct": round(100 * c / len(ruli_lens), 1)} for t, c in ruli_tags.most_common(8)],
}

# ------------------------------------------------------------------
# 6. 안티패턴: 성공률이 낮은 패턴 (데이터로 검증)
# ------------------------------------------------------------------
anti = []
for k, v in type_stats.items():
    if v["n"] >= 50 and v["hit5_pct"] < base_stats["hit5_pct"] * 0.8:
        anti.append({"pattern": k, **v, "lift_vs_base": lift5[k]})
for k, v in len_stats.items():
    if v["n"] >= 50 and v["hit5_pct"] < base_stats["hit5_pct"] * 0.8:
        anti.append({"pattern": f"제목길이 {k}자", **v, "lift_vs_base": round(v["hit5_pct"]/base_stats["hit5_pct"], 2) if base_stats["hit5_pct"] else 0})

# ------------------------------------------------------------------
# 리포트 출력
# ------------------------------------------------------------------
print("=== 전체 코퍼스 ===", base_stats, "| top5 커트라인:", top5_cut, "| top10:", top10_cut)
print("\n=== 후킹 유형별 성공 통계 (lift=전체 대비 상위5% 진입 배율) ===")
for k in sorted(type_stats, key=lambda x: -lift5.get(x, 0)):
    v = type_stats[k]
    print(f"{k:14s} n={v['n']:5d} avg={v['avg_rec']:7.2f} hit5={v['hit5_pct']:5.2f}% lift={lift5[k]:5.2f} hit10={v['hit10_pct']:5.2f}%")
print("\n=== 제목 길이별 ===")
for k, v in len_stats.items():
    print(f"{k:8s} n={v['n']:5d} avg={v['avg_rec']:7.2f} hit5={v['hit5_pct']:5.2f}% hit10={v['hit10_pct']:5.2f}%")
print("\ntop100 평균 길이:", round(statistics.mean(top100_len),1), "중앙:", statistics.median(top100_len))
print("ruliweb:", ruli_stats["avg_len"], "중앙:", ruli_stats["median_len"])
print("\n=== 갤러리 그룹별 ===")
for k, v in gall_stats.items():
    print(f"[{k}] n={v['n']} avg_rec={v['avg_rec']} avg_len={v['avg_title_len']} hit5={v['hit5_pct']}% tags={[x['tag']+':'+str(x['pct']) for x in v['top_hook_tags']]}")
print("\n=== 루리웹 태그 분포 ===", ruli_stats["tag_pct"])
print("\n=== 안티패턴 후보 ===")
for a in anti: print(a)

# JSON 저장용 데이터 (통계 근거 포함) — 다음 단계에서 규칙으로 변환
dump = {
    "base": base_stats,
    "cutoffs": {"top5": top5_cut, "top10": top10_cut},
    "type_stats": type_stats,
    "lift5": lift5,
    "len_stats": len_stats,
    "gall_stats": gall_stats,
    "top_examples": dict(top_examples_by_grp),
    "ruli_stats": ruli_stats,
    "anti_raw": anti,
    "top100_len": {"avg": round(statistics.mean(top100_len),1), "median": statistics.median(top100_len)},
}
with open(BASE + r"\_analysis_tmp.json", "w", encoding="utf-8") as f:
    json.dump(dump, f, ensure_ascii=False, indent=1)
print("\nsaved _analysis_tmp.json")
