# -*- coding: utf-8 -*-
"""1단계: corpus_naver.json 통계 분석 (노이즈 필터링 포함)"""
import json
import re
import sys
from collections import Counter

IO = __import__("io")
sys.stdout = IO.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

CORPUS = r"C:\Users\user\Desktop\viral-storm\data\learning\corpus_naver.json"

with open(CORPUS, encoding="utf-8") as f:
    docs = json.load(f)

print(f"총 문서수: {len(docs)}")

# ---- 노이즈 필터 ----
WIDGET = re.compile(r"\d+(\.\d+)?만\s*인용")          # 블로그 소개 위젯
URLNOISE = re.compile(r"blog\.naver\.com›")            # 검색 결과 URL 잔여물
DATEVIEW = re.compile(r"^\S+\d+주\s*전조회\s*\d+$")    # "모르밍3주 전조회 182"

def is_post(url: str) -> bool:
    """개별 포스트 URL 여부: /blogID/22xxxxxxxxx 형태"""
    return bool(re.search(r"/\d{8,}", url))

noise_widget, noise_url, noise_short, valid = [], [], [], []
for d in docs:
    t, u = d.get("title", ""), d.get("url", "")
    if WIDGET.search(t):
        noise_widget.append(t)
    elif URLNOISE.search(t):
        noise_url.append(t)
    elif DATEVIEW.match(t.strip()):
        noise_short.append(t)
    elif not is_post(u):
        noise_short.append(t)  # 블로그 루트 URL = 블로그명/소개 글
    else:
        valid.append(d)

print(f"노이즈-위젯(만 인용): {len(noise_widget)}")
print(f"노이즈-URL잔여: {len(noise_url)}")
print(f"노이즈-블로그명/기타: {len(noise_short)}")
print(f"유효 포스트 제목: {len(valid)}")

titles = [d["title"].strip() for d in valid]

# ---- 1. 브라켓 태그 ----
bracket_re = re.compile(r"\[([^\[\]]+)\]")
br_tagged = [t for t in titles if bracket_re.search(t)]
brackets = Counter()
for t in titles:
    for m in bracket_re.findall(t):
        brackets[m.strip()] += 1
print(f"\n[브라켓] 태그 포함 제목: {len(br_tagged)}/{len(titles)} ({len(br_tagged)/len(titles)*100:.0f}%)")
for k, v in brackets.most_common(20):
    print(f"   [{k}] x{v}")

# 지역 태그 (브라켓 내 지역명)
regions = ["마포", "분당", "서현", "안양", "범계", "신림", "강남", "서대문", "제주", "제천", "명동",
           "홍대", "일본", "도쿄", "오사카", "Osaka", "미국", "간사이", "인천", "다낭", "나트랑", "치앙마이"]
loc_hits = []
for t in titles:
    hit = [r for r in regions if r in t]
    if hit:
        loc_hits.append((t[:50], hit[0]))
print(f"\n지역명 포함 제목: {len(loc_hits)}/{len(titles)}")
for t, r in loc_hits[:15]:
    print(f"   ({r}) {t}")

# ---- 2. 구분자 ----
pipe_re = re.compile(r"[|｜ㅣ]")
piped = [t for t in titles if pipe_re.search(t)]
comma = [t for t in titles if "," in t]
plus = [t for t in titles if "+" in t]
qmark = [t for t in titles if "?" in t]
excl = [t for t in titles if "!" in t]
print(f"\n[구분자] 파이프(|,｜,ㅣ): {len(piped)}, 콤마: {len(comma)}, 플러스: {len(plus)}, 물음표: {len(qmark)}, 느낌표: {len(excl)}")

# ---- 3. 신뢰 마커 ----
TRUST = ["찐후기", "찐맛집", "찐으로", "솔직후기", "솔직 후기", "솔직 리뷰", "내돈내산", "직접",
         "실사용", "실착", "실구매", "플레이 후기", "플레이후기", "이용 후기", "이용후기", "사용후기",
         "방문 후기", "후기", "리뷰", "달성", "갓성비", "총정리", "재구매", "인생템", "꿀팁", "필수"]
tc = Counter()
for mk in TRUST:
    n = sum(1 for t in titles if mk in t)
    if n:
        tc[mk] = n
print(f"\n[신뢰 마커 빈도] (유효 {len(titles)}개 중)")
for k, v in tc.most_common():
    print(f"   {k}: {v} ({v/len(titles)*100:.0f}%)")

# ---- 4. 수치 디테일 ----
num_re = re.compile(r"\d+([.,]\d+)?\s*(시간|인|명|원|mg|일분|일치|곳|가지|개|년|주|회차|위|cm|번|대|기|일|주차|대차|초|월)")
num_titled = [t for t in titles if num_re.search(t)]
print(f"\n[수치+단위 포함]: {len(num_titled)}/{len(titles)} ({len(num_titled)/len(titles)*100:.0f}%)")
for t in num_titled[:12]:
    ms = ", ".join(m.group(1) or "" for m in num_re.finditer(t))
    print(f"   {t[:55]}  → {ms.strip(', ')}")

# 모든 숫자 토큰
numtok = Counter()
for t in titles:
    for m in re.finditer(r"\d+([.,]\d+)?", t):
        numtok[m.group(0)] += 1
print(f"\n숫자 토큰 top: {numtok.most_common(15)}")

# ---- 5. 제목 길이 ----
lens = [len(t) for t in titles]
print(f"\n제목 길이: 평균 {sum(lens)/len(lens):.1f}자, 최단 {min(lens)}, 최장 {max(lens)}")
import statistics
print(f"중앙값 {statistics.median(lens):.0f}자")

# ---- 6. 키워드 블록 ----
KW = ["추천", "후기", "리뷰", "공략", "쿠폰", "정리", "비교", "순위", "티어", "가격", "방법", "팁", "체험", "신작"]
kc = Counter()
for k in KW:
    n = sum(1 for t in titles if k in t)
    if n:
        kc[k] = n
print(f"\n[키워드 블록] {kc.most_common()}")

# 후보 마커: 추천+후기 동시 등
both = sum(1 for t in titles if "추천" in t and ("후기" in t or "리뷰" in t))
print(f"'추천'+'후기/리뷰' 동시: {both}")

# ---- 7. 광고/제휴 흔적 ----
ad = [t for t in titles if re.search(r"제공|지원받|협찬|체험단", t)]
print(f"\n제휴/협찬 명시 제목: {len(ad)} → {ad}")

# ---- 8. 상위 5개 (검색 상단 = 첫 등장) 샘플 ----
print("\n[유효 제목 전체]")
for i, t in enumerate(titles):
    print(f"{i+1:3d}. {t}")
