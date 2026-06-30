#!/usr/bin/env python3
"""
통합 DB 정리 스크립트 (정답 채움 후 실행)
"""
import psycopg2, uuid, re

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')

def fp(s):
    t = re.sub(r'[\s　]+', ' ', str(s).strip())[:200]
    t = re.sub(r'[①②③④]', '', t)
    return t

conn = psycopg2.connect(**DB)
cur = conn.cursor()

# 0. 전체 현황
cur.execute("SELECT COUNT(*), COUNT(NULLIF(정답,'')), COUNT(DISTINCT 회차) FROM problems")
total, answered, cycles = cur.fetchone()
print(f"📊 전체 문제: {total}, 정답 있음: {answered} ({answered*100//max(total,1)}%), 회차: {cycles}")

# 1. 중복출제 마킹
cur.execute("SELECT id, 문제, 회차 FROM problems WHERE 문제 IS NOT NULL AND 문제 != ''")
rows = cur.fetchall()
from collections import defaultdict
by_fp = defaultdict(list)
for row in rows:
    f = fp(row[1])
    by_fp[f].append((row[0], row[2]))

print(f"\n🔍 중복출제 분석 중...")
dup_groups = 0
dup2 = 0
dup3 = 0
for f, items in by_fp.items():
    cycles_set = set(c for _, c in items)
    if len(cycles_set) < 2:
        continue
    dup_groups += 1
    if len(cycles_set) >= 3:
        dup3 += 1
    else:
        dup2 += 1
    clist = ','.join(sorted(cycles_set))
    for rid, _ in items:
        cur.execute("UPDATE problems SET 중복출제=%s WHERE id=%s", (clist, rid))

conn.commit()
print(f"✅ 중복출제: {dup_groups}그룹 (2회:{dup2}, 3회+:{dup3})")

# 2. 회차 내 중복 정리
print(f"\n🔍 회차 내 중복 정리 중...")
cur.execute("SELECT id, 문제, 회차, 정답, 해설, 사용공식 FROM problems WHERE 문제 IS NOT NULL AND 문제 != '' ORDER BY 회차")
rows = cur.fetchall()

by_cycle_fp = defaultdict(lambda: defaultdict(list))
for row in rows:
    f = fp(row[1])
    by_cycle_fp[row[2]][f].append((row[0], row[3], row[4], row[5]))

del_rows = 0
for cycle, fps in by_cycle_fp.items():
    for f, items in fps.items():
        if len(items) < 2:
            continue
        scored = []
        for rid, a_val, e_val, f_val in items:
            score = (10 if a_val.strip() else 0) + (5 if e_val and e_val.strip() else 0) + (5 if f_val and f_val.strip() else 0) + (hash(rid) % 1000) / 1e6
            scored.append((score, rid))
        scored.sort(key=lambda x: -x[0])
        for _, rid in scored[1:]:
            cur.execute("DELETE FROM problems WHERE id=%s", (rid,))
            del_rows += 1

conn.commit()
print(f"✅ 회차 내 중복: {del_rows}개 삭제")

# 3. 최종 통계
cur.execute("SELECT COUNT(*), COUNT(NULLIF(정답,'')), COUNT(DISTINCT 회차) FROM problems")
total2, answered2, cycles2 = cur.fetchone()
print(f"\n📊 최종: {total2}문제, 정답 {answered2}개 ({answered2*100//max(total2,1)}%), {cycles2}회차")

# 4. 회차별 현황
cur.execute("SELECT 회차, COUNT(*), COUNT(NULLIF(정답,'')) FROM problems GROUP BY 회차 ORDER BY 회차")
for cycle, tot, ans in cur.fetchall():
    bar = '✅' if tot == ans else '⏳'
    print(f"  {bar} {cycle}: {ans}/{tot}")

cur.close()
conn.close()
