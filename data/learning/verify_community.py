# -*- coding: utf-8 -*-
"""2차 검증: 질문형 하위유형, 조합 시너지, top100 태그 분포"""
import json, re, collections

BASE = r"C:\Users\user\Desktop\viral-storm\data\learning"
with open(BASE + r"\corpus_dc.json", encoding="utf-8") as f:
    corpus = json.load(f)
with open(BASE + r"\learning_summary.json", encoding="utf-8") as f:
    summ = json.load(f)

RE_QUESTION = re.compile(r"(\?|ㄹ까|ㄹ게|~나|인가|왜 |어떻게|뭐 살|뭐사|추천해|알려줘|알아보자|일까|까\?)")
RE_Q_INFO = re.compile(r"(추천해|추천좀|추천받|뭐 살|뭐사|어떻게 해|어떻게 먹|어디서 사|어디 사|알려주|가르쳐)")
RE_INFOGAP = re.compile(r"(모음|정리|총정리|목록|모음집|가이드|팁|방법|알아보자|해부|분석|비밀|꿀팁|모든 것|정리판|총모음|리스트)")
RE_SLANG = re.compile(r"(ㅋ{2,}|ㅠ+|ㄹㅇ|ㄷㄷ|ㅈㄴ|꿀|찐|혜자|어그로|레게노|실화|개꿀|존맛|존망)")
RE_FIRST = re.compile(r"(했습니다|해봤다|해봤습니다|먹었다|먹어봄|입문|후기|리뷰|당했다|느꼈다|갈아탔다|써봄|직접)")
RE_COMPARE = re.compile(r"(vs|VS|비교|대결|갈아탄|갈아타|전환)")
RE_TIME = re.compile(r"(D-\d|오늘|방금|실시간|지금|\d월|\d일|시즌|버전|ver)")
RE_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2764\u2728\u2934\u2935\u3030❥◆◇★☆▶►]")
RE_EXCL = re.compile(r"!")
RE_NUMBER = re.compile(r"[0-9０-９]+")

def tags(t):
    s = set()
    if RE_QUESTION.search(t): s.add("질문형")
    if RE_INFOGAP.search(t): s.add("정보격차")
    if RE_SLANG.search(t): s.add("은어")
    if RE_FIRST.search(t): s.add("1인칭")
    if RE_COMPARE.search(t): s.add("비교")
    if RE_TIME.search(t): s.add("시간")
    if RE_EMOJI.search(t): s.add("이모지")
    if RE_EXCL.search(t): s.add("느낌표")
    if RE_NUMBER.search(t): s.add("숫자")
    return s

def st(items, label):
    rs = [c.get("recommends") or 0 for c in items]
    if not rs:
        print(label, "n=0"); return
    hit5 = 100 * sum(1 for r in rs if r >= 5) / len(rs)
    print(f"{label:28s} n={len(rs):5d} avg={sum(rs)/len(rs):6.2f} hit5={hit5:5.1f}%")

cnt = collections.Counter()
for x in summ["dc_top100"]:
    cnt.update(tags(x["t"]))
print("top100 태그 분포(개):", cnt.most_common())

q = [c for c in corpus if RE_QUESTION.search(c["title"])]
qi = [c for c in q if RE_Q_INFO.search(c["title"])]
qr = [c for c in q if not RE_Q_INFO.search(c["title"])]
st(q, "질문형 전체")
st(qi, "질문-정보요청형(추천좀/어뜩해)")
st(qr, "질문-수사/공감형")

print("\n수사의문 고추천 예시:", [(c["title"][:40], c.get("recommends")) for c in sorted(qr, key=lambda c: -(c.get("recommends") or 0))[:6]])

st([c for c in corpus if RE_INFOGAP.search(c["title"]) and RE_FIRST.search(c["title"])], "정보격차+1인칭")
st([c for c in corpus if RE_SLANG.search(c["title"]) and RE_INFOGAP.search(c["title"])], "은어+정보격차")
st([c for c in corpus if RE_FIRST.search(c["title"]) and not RE_INFOGAP.search(c["title"])], "1인칭 단독")
st([c for c in corpus if RE_SLANG.search(c["title"]) and RE_FIRST.search(c["title"])], "은어+1인칭")

# 제목 첫 토큰 형태: 괄호 태그 [xxx] / 공지 etc.
bracket = [c for c in corpus if re.match(r"^\s*\[", c["title"])]
st(bracket, "괄호태그 시작 [xxx]")
# 느낌표+은어
st([c for c in corpus if RE_EXCL.search(c["title"]) and RE_SLANG.search(c["title"])], "느낌표+은어")
