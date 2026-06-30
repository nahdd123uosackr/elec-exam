#!/usr/bin/env python3
"""빠른 중복출제 마킹 — psycopg2 사용"""
import re, psycopg2
from collections import defaultdict

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')

def fp(s: str) -> str:
    s = re.sub(r'\s+', '', s or '')
    s = re.sub(r'[\[\]\(\)\.\,\-\:\;\?\!\'·◆◇※【】]', '', s)
    s = re.sub(r'\d+', '', s)
    return s

conn = psycopg2.connect(**DB)
cur = conn.cursor()

print("loading problems...")
cur.execute("SELECT id, 회차, 문제 FROM problems")
rows = cur.fetchall()
print(f"  {len(rows)} rows")

print("computing fingerprints...")
fp_to_entries = defaultdict(list)
for pid, raw, body in rows:
    cycle = (raw or '').strip()
    f = fp(body)
    if len(f) < 10:
        continue
    fp_to_entries[f].append((pid, cycle))

print("marking duplicates...")
updates = []
dup_groups = 0
for f, entries in fp_to_entries.items():
    cycles_set = {c for _, c in entries if c}
    if len(cycles_set) < 2:
        continue
    dup_groups += 1
    sorted_cycles = sorted(cycles_set)
    for pid, own_cycle in entries:
        others = [c for c in sorted_cycles if c != own_cycle]
        if others:
            updates.append((','.join(others), pid))

print(f"  중복 그룹: {dup_groups}")
print(f"  마킹할 행: {len(updates)}")

if not updates:
    print("nothing to update")
    cur.close()
    conn.close()
    exit()

print("updating DB...")
CHUNK = 2000
for i in range(0, len(updates), CHUNK):
    chunk = updates[i:i+CHUNK]
    for csv_str, pid in chunk:
        cur.execute('UPDATE problems SET "중복출제" = %s WHERE id = %s', (csv_str, pid))

conn.commit()

cur.execute('SELECT count(*) FROM problems WHERE "중복출제" IS NOT NULL AND "중복출제" != \'\'')
n_marked = cur.fetchone()[0]
print(f"  marked rows: {n_marked}")

cur.execute('SELECT "중복출제", count(*) FROM problems WHERE "중복출제" IS NOT NULL AND "중복출제" != \'\' GROUP BY "중복출제" ORDER BY count(*) DESC')
for v, c in cur.fetchmany(5):
    print(f"  {v}: {c}")

# 분포
cur.execute("""
    SELECT
        CASE WHEN "중복출제" IS NULL OR "중복출제" = '' THEN '0-빈값'
             WHEN "중복출제" NOT LIKE '%,%' THEN '1-2회출제'
             ELSE '2-3회이상'
        END AS bucket,
        count(*)
    FROM problems GROUP BY 1 ORDER BY 1
""")
for b, c in cur.fetchall():
    print(f"  {b}: {c}")

cur.close()
conn.close()
print("done")
