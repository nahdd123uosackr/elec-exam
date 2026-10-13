#!/usr/bin/env python3
"""
범용 회차 복구 스크립트: 
1. 전기기기로 잘못 분류된 문제 과목 재분류
2. 유사 중복 제거 (tikz포함 강력 클리닝)
3. 통계 출력
"""
import os
import psycopg2, os, re, sys
from difflib import SequenceMatcher

CYCLE = sys.argv[1] if len(sys.argv) > 1 else None
if not CYCLE:
    print("Usage: python3 fix_cycle.py <CYCLE>")
    sys.exit(1)

conn = psycopg2.connect(
    host=os.environ.get('PG_HOST', 'nhd.us.to'), user=os.environ.get('PG_USER', 'postgres'),
    password=os.environ.get('PG_PASSWORD', 'os.environ["PG_PASSWORD"]'), dbname=os.environ.get('PG_DATABASE', 'elec'))
cur = conn.cursor()

RE_RULES = [
    (r'전위함수|등전위선|전기력선', '전기자기학'),
    (r'포인팅.*벡터', '전기자기학'),
    (r'유전율.*경계면|경계면.*유전율', '전기자기학'),
    (r'자속밀도.*평등.*자계|평등.*자계.*자속밀도', '전기자기학'),
    (r'반자성체|비투자율|자화율', '전기자기학'),
    (r'진공.*중.*평행판|평행판.*무한평판', '전기자기학'),
    (r'비유전율.*배인가|유전체의 분극률', '전기자기학'),
    (r'무한히.*긴.*직선.*도선|직선.*도선.*전류', '전기자기학'),
    (r'평행.*판.*도체.*판.*수평|도체.*판.*수평.*배치', '전기자기학'),
    (r'자기.*인덕턴스와.*상호.*인덕턴스.*결합계수', '전기자기학'),
    (r'보드선도.*이득여유|이득여유.*보드선도', '회로이론 및 제어공학'),
    (r'임피던스.*복소전력|복소전력', '회로이론 및 제어공학'),
    (r'전달함수가.*제어기|제어기.*전달함수', '회로이론 및 제어공학'),
    (r'개루프.*전달함수.*근궤적|근궤적.*점근선', '회로이론 및 제어공학'),
    (r'특성방정식.*안정', '회로이론 및 제어공학'),
    (r'RLC.*직렬회로.*과도.*응답|과도.*응답특성', '회로이론 및 제어공학'),
    (r'실효값.*크기.*[Vv]\(t\)|v\(t\).*실효값', '회로이론 및 제어공학'),
    (r'회로정수.*평형.*2회선|평형.*2회선.*회로정수', '회로이론 및 제어공학'),
    (r'정상분.*전류|영상분|대칭분', '회로이론 및 제어공학'),
    (r'3상.*3선식.*전선.*한.*가닥', '회로이론 및 제어공학'),
    (r'단상.*전파.*정류.*제어|전파정류제어.*점호각', '회로이론 및 제어공학'),
    (r'Still.*송전전압|송전하는데.*필요한.*전압', '전력공학'),
    (r'수전단.*전력원.*방정식|조상설비.*없이.*전압', '전력공학'),
    (r'변압기의.*%Z|%Z.*단락전류', '전력공학'),
    (r'절탄기|화력발전소.*절탄기', '전력공학'),
    (r'댐의.*부속설비', '전력공학'),
    (r'송배전.*선로.*선택지락계전기|SGR|선택지락계전기', '전력공학'),
    (r'송전선로.*가공지선', '전력공학'),
    (r'변전소.*비접지.*선로.*계전기|계전기.*영상전류', '전력공학'),
    (r'사고.*예비전원용.*배전선로|예비전원.*전환', '전력공학'),
    (r'고장.*즉시.*동작.*계전기|계전기.*고장.*즉시', '전력공학'),
    (r'시설기준.*적합|적합.*시설기준|시설기준.*틀린', '전기설비기술기준'),
    (r'절연내력시험|내력시험.*시험전압', '전기설비기술기준'),
    (r'옥내배선|옥내.*전로.*대지전압|대지전압', '전기설비기술기준'),
    (r'수상전선로|옥상전선로', '전기설비기술기준'),
    (r'가공전선로.*지지물.*풍압|풍압하중.*저온계절', '전기설비기술기준'),
    (r'지중.*전선로.*직접.*매설|직접.*매설식.*지중', '전기설비기술기준'),
    (r'통신선.*보안장치.*피뢰기|피뢰기.*동작전압', '전기설비기술기준'),
    (r'가공전선.*경동선.*굵기|경동선.*지름', '전기설비기술기준'),
    (r'연료전지|태양전지.*모듈.*절연|태양전지.*시설기준', '전기설비기술기준'),
    (r'전차선.*삭도|삭도.*이격거리', '전기설비기술기준'),
    (r'케이블.*트레이.*적합하지.*않은|트레이.*공사', '전기설비기술기준'),
    (r'수소.*냉각식.*발전기.*시설기준', '전기설비기술기준'),
    (r'출퇴표시등.*변압기', '전기설비기술기준'),
    (r'유원지.*유희용.*전차|유희용.*전차', '전기설비기술기준'),
    (r'절연저항.*최소값', '전기설비기술기준'),
    (r'지선으로.*연선|연선을.*사용.*지선|소선.*최소.*몇.*가닥', '전기설비기술기준'),
    (r'저압전로.*0\.5초|0\.5초.*전로를.*차단', '전기설비기술기준'),
    (r'가공.*약전류.*전선로.*병행|약전류.*유도작용', '전기설비기술기준'),
]

def strong_clean(t):
    t = re.sub(r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}', '', t, flags=re.DOTALL)
    t = re.sub(r'<img[^>]*>', '', t)
    t = re.sub(r'\$\$[^$]+\$\$', '', t)
    t = re.sub(r'\[이미지:[^\]]*\]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:60]

print(f"=== {CYCLE} ===")

# 1. 과목 재분류 (전기기기로 잘못된 것)
cur.execute("""
  SELECT id, "문제", "과목" FROM problems
  WHERE "회차" = %s AND "과목" = '전기기기'
""", (CYCLE,))
mis = cur.fetchall()
fix_count = 0
for pid, prob, old in mis:
    new = None
    for pat, subj in RE_RULES:
        if re.search(pat, prob):
            new = subj
            break
    if new:
        cur.execute('UPDATE problems SET "과목" = %s WHERE id = %s', (new, pid))
        fix_count += 1
if fix_count:
    print(f"  과목 변경: {fix_count}개")
    conn.commit()

# 2. 유사 중복 제거 (강력 클리닝)
cur.execute("""
  SELECT id, "문제", "정답", "보기", "과목"
  FROM problems WHERE "회차" = %s ORDER BY "문제"
""", (CYCLE,))
rows = cur.fetchall()

groups = {}
for r in rows:
    key = strong_clean(r[1])
    groups.setdefault(key, []).append(r)

del_count = 0
for key, items in groups.items():
    if len(items) <= 1:
        continue
    # Score: has answer + has img in choices + long choices + long problem
    def score(r):
        return (0 if r[2] in ('', None) else 1, 1 if '<img' in (r[3] or '') else 0, len(r[3] or ''), len(r[1] or ''))
    items.sort(key=score, reverse=True)
    for item in items[1:]:
        cur.execute("DELETE FROM problems WHERE id = %s", (item[0],))
        del_count += 1

if del_count:
    conn.commit()
    print(f"  중복 삭제: {del_count}개")

# 3. 최종 통계
cur.execute("""
  SELECT "과목", COUNT(*) FROM problems
  WHERE "회차" = %s GROUP BY "과목" ORDER BY "과목"
""", (CYCLE,))
for s, c in cur.fetchall():
    print(f"  {s}: {c}")
cur.execute('SELECT COUNT(*) FROM problems WHERE "회차" = %s', (CYCLE,))
print(f"  총 {cur.fetchone()[0]}문제")

conn.close()
