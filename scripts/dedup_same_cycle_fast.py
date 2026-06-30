#!/usr/bin/env python3
"""회차 내 중복 row 제거 (psycopg2)"""
import re, psycopg2
from collections import defaultdict

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')

def fp(s: str) -> str:
    s = re.sub(r'\s+', '', s or '')
    s = re.sub(r'[\[\]\(\)\.\,\-\:\;\?\!\'·◆◇※【】]', '', s)
    s = re.sub(r'\d+', '', s)
    return s

def score_row(정답, 해설, 사용공식):
    s = 0
    if 정답: s += 1
    if 해설: s += len(str(해설))
    if 사용공식: s += len(str(사용공식))
    return s

conn = psycopg2.connect(**DB)
cur = conn.cursor()

print("loading problems...")
cur.execute('SELECT id, "회차", "문제", "정답", "해설", "사용공식" FROM problems')
rows = cur.fetchall()
print(f"  {len(rows)} rows")

# 회차 + fp 별 그룹
print("grouping by (cycle, fingerprint)...")
groups = defaultdict(list)
for pid, cycle, 문제, 정답, 해설, 사용공식 in rows:
    if not cycle:
        continue
    f = fp(문제)
    if len(f) < 10:
        continue
    groups[(cycle, f)].append((pid, 정답, 해설, 사용공식))

dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
print(f"  회차 내 중복 그룹: {len(dup_groups)}")

to_delete = []
preserved = 0
for (cycle, f), entries in dup_groups.items():
    scored = sorted(entries, key=lambda e: (-score_row(e[1], e[2], e[3]), e[0]))
    keep = scored[0][0]
    preserved += 1
    for pid, _, _, _ in scored[1:]:
        to_delete.append(pid)

print(f"  보존: {preserved}")
print(f"  삭제: {len(to_delete)}")

if not to_delete:
    print("nothing to delete")
    cur.close()
    conn.close()
    exit()

# 삭제
import time
start = time.time()
CHUNK = 500
deleted = 0
for i in range(0, len(to_delete), CHUNK):
    chunk = to_delete[i:i+CHUNK]
    cur.executemany('DELETE FROM problems WHERE id = %s', [(pid,) for pid in chunk])
    deleted += len(chunk)
    if (i // CHUNK) % 5 == 0:
        print(f"  {deleted}/{len(to_delete)} ({time.time()-start:.1f}s)")

conn.commit()
print(f"  ✓ deleted {deleted} rows in {time.time()-start:.1f}s")

# 결과 확인
cur.execute("""SELECT 회차, COUNT(*) as cnt FROM problems 
WHERE 회차 IS NOT NULL AND 회차 != '' GROUP BY 회차 ORDER BY 회차""")
print("\n=== 회차별 문제 수 (정리 후) ===")
for cycle, cnt in cur.fetchall():
    flag = "⚠️" if cnt > 120 else "✅"
    print(f"  {flag} {cycle}: {cnt}문제")

cur.close()
conn.close()
print("done")
