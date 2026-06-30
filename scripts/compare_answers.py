#!/usr/bin/env python3
"""Notion 데이터와 DB 데이터의 정답 비교"""
import json
import psycopg2
import sys

DB = dict(
    host='nhd.us.to',
    port=5432,
    user='postgres',
    password='Hyeongdong1',
    dbname='elec'
)

# Load Notion data
with open('/root/elec-exam/data/problems.json') as f:
    notion_data = json.load(f)

print("=== Notion 데이터 로드 완료 ===")
print(f"Notion 총 문제: {len(notion_data)}")

# Connect to DB
conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Fetch all DB data
cur.execute("SELECT id, 문제, 정답, 회차 FROM problems ORDER BY 회차")
db_rows = {r[0]: dict(id=r[0], 문제=r[1], 정답=r[2], 회차=r[3]) for r in cur.fetchall()}
print(f"DB 총 문제: {len(db_rows)}")
print()

# ============================================================
# 1) Compare by ID: check if Notion answer matches DB answer
# ============================================================
print("=== ID별 정답 비교 ===")
notion_by_id = {r['id']: r for r in notion_data}
db_by_id = db_rows

matched = 0
mismatched = 0
not_in_notion = 0  # in DB but not in Notion
not_in_db = 0      # in Notion but not in DB
mismatch_details = []

for pid, nr in notion_by_id.items():
    if pid in db_by_id:
        n_ans = nr['정답'].strip()
        d_ans = db_by_id[pid]['정답'].strip()
        if n_ans == d_ans:
            matched += 1
        else:
            mismatched += 1
            mismatch_details.append({
                'id': pid,
                '회차': nr['회차'],
                'notion_ans': n_ans,
                'db_ans': d_ans,
                '문제': nr['문제'][:60]
            })
    else:
        not_in_db += 1

for pid in db_by_id:
    if pid not in notion_by_id:
        not_in_notion += 1

print(f"정답 일치: {matched}")
print(f"정답 불일치: {mismatched}")
print(f"DB에만 있는 문제 (Notion 미존재): {not_in_notion}")
print(f"Notion에만 있는 문제 (DB 미존재): {not_in_db}")

if mismatch_details:
    print(f"\n=== 정답 불일치 상세 (최대 20개) ===")
    for m in mismatch_details[:20]:
        print(f"  [{m['회차']}] id={m['id'][:12]}...")
        print(f"    문제: {m['문제']}")
        print(f"    Notion 정답: '{m['notion_ans']}'")
        print(f"    DB 정답:     '{m['db_ans']}'")
        print()

# ============================================================
# 2) Compare by 회차: aggregate answer statistics
# ============================================================
print("\n=== 회차별 정답 통계 비교 ===")
from collections import Counter

notion_cycles = Counter(r['회차'] for r in notion_data)
db_cycles = Counter(r['회차'] for r in db_rows.values())

all_cycles = sorted(set(list(notion_cycles.keys()) + list(db_cycles.keys())))
for cyc in all_cycles:
    n_cnt = notion_cycles.get(cyc, 0)
    d_cnt = db_cycles.get(cyc, 0)
    n_ans = sum(1 for r in notion_data if r['회차'] == cyc and r['정답'].strip())
    d_ans = sum(1 for r in db_rows.values() if r['회차'] == cyc and r['정답'].strip())
    marker = " ***" if (n_cnt != d_cnt or n_ans != d_ans) else ""
    if marker:
        print(f"{cyc}: Notion={n_cnt}문제(정답={n_ans}) vs DB={d_cnt}문제(정답={d_ans}){marker}")

# ============================================================
# 3) Check 2005~2009 in Notion
# ============================================================
print("\n=== 2005~2009 데이터 확인 ===")
notion_years = set()
db_years = set()
for r in notion_data:
    cyc = r['회차']
    if cyc.startswith('200') or cyc.startswith('2005') or cyc.startswith('2006') or cyc.startswith('2007') or cyc.startswith('2008') or cyc.startswith('2009'):
        if any(f'200{y}' in cyc for y in range(5,10)):
            notion_years.add(cyc)
for pid, r in db_rows.items():
    cyc = r['회차']
    if any(f'200{y}' in cyc for y in range(5,10)):
        db_years.add(cyc)

print(f"Notion의 2005~2009 회차: {sorted(notion_years) if notion_years else '없음'}")
print(f"DB의 2005~2009 회차: {sorted(db_years)}")

# Check if answers in DB for 2005~2009
for cyc in sorted(db_years):
    ans_cnt = sum(1 for r in db_rows.values() if r['회차'] == cyc and r['정답'].strip())
    print(f"  {cyc}: DB에 {db_cycles.get(cyc,0)}문제, 정답={ans_cnt}")

# ============================================================
# 4) Compare Notion 회차 with DB cycle distribution for shared cycles
# ============================================================
print("\n=== Notion vs DB 공통 회차별 존재 여부 ===")
for cyc in all_cycles:
    n_ids = set(r['id'] for r in notion_data if r['회차'] == cyc)
    d_ids = set(k for k, v in db_rows.items() if v['회차'] == cyc)
    common = n_ids & d_ids
    only_notion = n_ids - d_ids
    only_db = d_ids - n_ids
    if only_notion or only_db:
        print(f"{cyc}: 공통={len(common)} / Notion만={len(only_notion)} / DB만={len(only_db)}")

cur.close()
conn.close()
print("\n=== 비교 완료 ===")
