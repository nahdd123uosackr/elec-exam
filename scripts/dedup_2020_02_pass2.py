#!/usr/bin/env python3
"""2020-02: 2차 중복 제거 (더 긴 clean prefix로 매칭)"""
import psycopg2, os, re
from difflib import SequenceMatcher

conn = psycopg2.connect(
    host=os.environ.get('PG_HOST', 'nhd.us.to'), user=os.environ.get('PG_USER', 'postgres'),
    password=os.environ.get('PG_PASSWORD', 'os.environ["PG_PASSWORD"]'), dbname=os.environ.get('PG_DATABASE', 'elec'))
cur = conn.cursor()

CYCLE = '2020-02'

def clean_text(t):
    t = re.sub(r'<img[^>]*>', '', t)
    t = re.sub(r'\$\$[^$]+\$\$', '', t)
    t = re.sub(r'\[이미지:[^\]]*\]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

cur.execute("""
  SELECT id, "문제", "정답", "보기", "과목"
  FROM problems WHERE "회차" = %s ORDER BY "문제"
""", (CYCLE,))
import os
rows = cur.fetchall()

# Compare every pair within same subject, using full cleaned text
pairs_to_remove = []
for i in range(len(rows)):
    for j in range(i+1, len(rows)):
        if rows[i][4] != rows[j][4]:
            continue  # same subject only
        ci = clean_text(rows[i][1])
        cj = clean_text(rows[j][1])
        ratio = SequenceMatcher(None, ci, cj).ratio()
        if ratio > 0.85:  # high similarity
            # Score: keep the better one
            def score(r): return (1 if '<img' in (r[3] or '') else 0, len(r[3] or ''), len(r[1] or ''))
            keep, remove = (rows[i], rows[j]) if score(rows[i]) >= score(rows[j]) else (rows[j], rows[i])
            pairs_to_remove.append((remove, keep, ratio))

# Deduplicate removal list by id
seen_ids = set()
del_ids = []
for remove, keep, ratio in pairs_to_remove:
    if remove[0] not in seen_ids and keep[0] not in [x[0] for x in del_ids]:
        seen_ids.add(remove[0])
        del_ids.append(remove)
        print(f"  DEL {remove[4]:12s} sim={ratio:.2f} | {clean_text(remove[1])[:50]}")

print(f"\n=== 2차 삭제: {len(del_ids)}개 ===")
if del_ids:
    ids = [d[0] for d in del_ids]
    cur.execute("DELETE FROM problems WHERE id = ANY(%s)", (ids,))
    conn.commit()

# 최종 통계
cur.execute("SELECT \"과목\", COUNT(*) FROM problems WHERE \"회차\" = %s GROUP BY \"과목\" ORDER BY \"과목\"", (CYCLE,))
for subj, cnt in cur.fetchall():
    print(f"  {subj}: {cnt}")
cur.execute("SELECT COUNT(*) FROM problems WHERE \"회차\" = %s", (CYCLE,))
print(f"  총 {cur.fetchone()[0]}문제")
conn.close()
