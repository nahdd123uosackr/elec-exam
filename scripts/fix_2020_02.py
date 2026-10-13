#!/usr/bin/env python3
"""2020-02 회차 복구: 중복 제거 + 잘못 분류된 과목 재분류"""
import psycopg2, os, re, sys

conn = psycopg2.connect(
    host=os.environ.get('PG_HOST') or os.environ.get('DB_HOST', 'nhd.us.to'),
    user=os.environ.get('PG_USER') or os.environ.get('DB_USER', 'postgres'),
    password=os.environ.get('PG_PASSWORD') or os.environ.get('DB_PASSWORD', 'os.environ["PG_PASSWORD"]'),
    dbname=os.environ.get('PG_DATABASE') or os.environ.get('DB_NAME', 'elec'))
cur = conn.cursor()

CYCLE = '2020-02'

# 1. 중복 제거: 같은 문제 텍스트가 여러 행이면 <img> 있는 행 유지, 없으면 긴 보기 유지
print("=== 1. 중복 제거 ===")
cur.execute("""
  SELECT id, "문제", "과목", LENGTH("보기") as 보기길이,
         "문제" LIKE '%%<img%%' as has_img, "보기" LIKE '%%<img%%' as choices_have_img
  FROM problems WHERE "회차" = %s
  ORDER BY "문제", LENGTH("보기") DESC
""", (CYCLE,))
import os
rows = cur.fetchall()

# Group by exact problem text for dedup
groups = {}
for r in rows:
    key = r[1]  # full 문제 text
    groups.setdefault(key, []).append(r)

del_count = 0
for key, items in groups.items():
    if len(items) <= 1:
        continue
    # Sort: has_img in 문제 first, then has_img in 보기, then longer 보기
    items.sort(key=lambda x: (
        -(1 if x[4] else 0),  # has_img in 문제
        -(1 if x[5] else 0),  # has_img in 보기
        -(x[3] or 0)  # longer 보기
    ))
    keep = items[0]
    for item in items[1:]:
        cur.execute("DELETE FROM problems WHERE id = %s", (item[0],))
        del_count += 1
        print(f"  삭제: {item[2]:12s} {item[1][:50]}")

print(f"  총 {del_count}개 중복 삭제")

# 2. 과목 재분류: 전기기기(69) → 실제 과목으로
# Keyword-based classification rules (ordered by specificity)
RULES = [
    # 전기자기학
    (r'전위함수|등전위선|전기력선', '전기자기학'),
    (r'포인팅\s*벡터', '전기자기학'),
    (r'유전율.*경계면|경계면.*유전율', '전기자기학'),
    (r'자속밀도.*평등\s*자계|평등\s*자계.*자속밀도', '전기자기학'),
    (r'반자성체|비투자율|자화율', '전기자기학'),
    (r'진공\s*중.*평행판|평행판.*무한평판|무한평판.*도체', '전기자기학'),
    (r'비유전율.*배인가|유전체의 분극률', '전기자기학'),
    (r'무한히\s*긴\s*직선\s*도선|직선\s*도선.*전류', '전기자기학'),
    (r'평행\s*판.*도체\s*판.*수평|도체\s*판.*수평.*배치', '전기자기학'),
    (r'자기\s*인덕턴스와\s*상호\s*인덕턴스.*결합계수', '전기자기학'),

    # 회로이론 및 제어공학
    (r'보드선도.*이득여유|이득여유.*보드선도', '회로이론 및 제어공학'),
    (r'임피던스.*복소전력|복소전력', '회로이론 및 제어공학'),
    (r'전달함수가.*제어기|제어기.*전달함수', '회로이론 및 제어공학'),
    (r'개루프\s*전달함수.*근궤적|근궤적.*점근선', '회로이론 및 제어공학'),
    (r'특성방정식.*안정', '회로이론 및 제어공학'),
    (r'RLC\s*직렬회로.*과도\s*응답|과도\s*응답특성', '회로이론 및 제어공학'),
    (r'실효값\s*크기.*[Vv]\(t\)|v\(t\).*실효값', '회로이론 및 제어공학'),
    (r'회로정수.*평형\s*2회선|평형\s*2회선.*회로정수', '회로이론 및 제어공학'),
    (r'정상분\s*전류|영상분|대칭분', '회로이론 및 제어공학'),
    (r'3상\s*3선식.*전선\s*한\s*가닥', '회로이론 및 제어공학'),
    (r'단상\s*전파\s*정류\s*제어|전파정류제어.*점호각', '회로이론 및 제어공학'),
    (r'SCR.*차단|도통.*SCR', '회로이론 및 제어공학'),

    # 전력공학
    (r'Still의\s*식|Still.*송전전압|송전하는데\s*필요한\s*전압', '전력공학'),
    (r'수전단.*전력원\s*방정식|조상설비\s*없이\s*전압', '전력공학'),
    (r'변압기의\s*%Z|%Z.*단락전류', '전력공학'),
    (r'절탄기|화력발전소.*절탄기', '전력공학'),
    (r'댐의\s*부속설비', '전력공학'),
    (r'송배전\s*선로.*선택지락계전기|SGR|선택지락계전기', '전력공학'),
    (r'송전선로.*가공지선', '전력공학'),
    (r'변전소.*비접지\s*선로.*계전기|계전기.*영상전류', '전력공학'),
    (r'사고.*예비전원용\s*배전선로|예비전원.*전환', '전력공학'),
    (r'고장\s*즉시\s*동작.*계전기|계전기.*고장\s*즉시', '전력공학'),

    # 전기설비기술기준
    (r'시설기준.*적합|적합.*시설기준|시설기준.*틀린', '전기설비기술기준'),
    (r'절연내력시험|내력시험.*시험전압', '전기설비기술기준'),
    (r'옥내배선|옥내\s*전로.*대지전압|대지전압', '전기설비기술기준'),
    (r'수상전선로|옥상전선로', '전기설비기술기준'),
    (r'가공전선로.*지지물.*풍압|풍압하중.*저온계절', '전기설비기술기준'),
    (r'지중\s*전선로.*직접\s*매설|직접\s*매설식.*지중', '전기설비기술기준'),
    (r'통신선\s*보안장치.*피뢰기|피뢰기.*동작전압', '전기설비기술기준'),
    (r'가공전선.*경동선.*굵기|경동선.*지름', '전기설비기술기준'),
    (r'연료전지|태양전지.*모듈.*절연|태양전지.*시설기준', '전기설비기술기준'),
    (r'전차선.*삭도|삭도.*이격거리', '전기설비기술기준'),
    (r'케이블\s*트레이.*적합하지\s*않은|트레이\s*공사', '전기설비기술기준'),
    (r'지락.*0\.5초\s*이내|0\.5초\s*이내.*차단', '전기설비기술기준'),
    (r'수소\s*냉각식\s*발전기.*시설기준', '전기설비기술기준'),
    (r'출퇴표시등.*변압기', '전기설비기술기준'),
    (r'유원지.*유희용\s*전차|유희용\s*전차', '전기설비기술기준'),
    (r'절연저항\s*최소값', '전기설비기술기준'),
    (r'지선으로\s*연선|연선을\s*사용.*지선|소선.*최소\s*몇\s*가닥', '전기설비기술기준'),
    (r'저압전로.*0\.5초|0\.5초.*전로를\s*차단', '전기설비기술기준'),
    (r'가공\s*약전류\s*전선로.*병행|약전류.*유도작용', '전기설비기술기준'),
]

print("\n=== 2. 과목 재분류 ===")
cur.execute("""
  SELECT id, "문제", "과목" FROM problems
  WHERE "회차" = %s AND "과목" = '전기기기'
""", (CYCLE,))
misclassified = cur.fetchall()

fix_count = 0
keep_as_machine = 0
for pid, problem, old_subj in misclassified:
    new_subj = None
    for pattern, subject in RULES:
        if re.search(pattern, problem):
            new_subj = subject
            break
    if new_subj:
        cur.execute('UPDATE problems SET "과목" = %s WHERE id = %s', (new_subj, pid))
        fix_count += 1
        print(f"  {old_subj:12s} → {new_subj:12s} | {problem[:50]}")
    else:
        keep_as_machine += 1
        if keep_as_machine <= 5:
            print(f"  {old_subj:12s} → (미분류, 유지) | {problem[:50]}")

print(f"\n  {fix_count}개 과목 변경, {keep_as_machine}개 전기기기 유지")

# 3. 최종 통계
cur.execute("""
  SELECT "과목", COUNT(*) FROM problems
  WHERE "회차" = %s GROUP BY "과목" ORDER BY "과목"
""", (CYCLE,))
print("\n=== 3. 최종 통계 ===")
for subj, cnt in cur.fetchall():
    print(f"  {subj}: {cnt}")

cur.execute("SELECT COUNT(*) FROM problems WHERE \"회차\" = %s", (CYCLE,))
total = cur.fetchone()[0]
print(f"  총 {total}문제")

conn.commit()
cur.close()
conn.close()
