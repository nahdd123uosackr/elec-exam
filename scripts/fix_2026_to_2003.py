#!/usr/bin/env python3
"""2026-01 → 2003-03 재매핑 + 중복 row 자동 제거"""
import re, psycopg2

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')

def fp(s: str) -> str:
    s = re.sub(r'\s+', '', s or '')
    s = re.sub(r'[\[\]\(\)\.\,\-\:\;\?\!\'·◆◇※【】]', '', s)
    s = re.sub(r'\d+', '', s)
    return s

conn = psycopg2.connect(**DB)
cur = conn.cursor()

# 2026-01 문제들
cur.execute("SELECT id, 문제, 정답, 해설, 사용공식 FROM problems WHERE 회차 = '2026-01'")
rows_2026 = cur.fetchall()
print(f"2026-01: {len(rows_2026)}문제")

# 2003-03 문제 fingerprint set
cur.execute("SELECT 문제 FROM problems WHERE 회차 = '2003-03'")
fps_2003 = {fp(r[0]) for r in cur.fetchall() if len(fp(r[0])) > 10}
print(f"2003-03: {len(fps_2003)} unique fingerprints")

# 중복 검사
dup_ids = []  # 2003-03에 이미 있는 문제면 삭제
move_ids = []  # 새로 옮길 문제
for pid, 문제, _, _, _ in rows_2026:
    f = fp(문제)
    if f in fps_2003:
        dup_ids.append(pid)
    else:
        move_ids.append(pid)

print(f"  중복 (2003-03에 이미 있음): {len(dup_ids)}")
print(f"  이동: {len(move_ids)}")

# 중복 삭제
if dup_ids:
    cur.executemany('DELETE FROM problems WHERE id = %s', [(pid,) for pid in dup_ids])
    print(f"  ✓ {len(dup_ids)}개 중복 삭제")

# 이동: 회차 변경
if move_ids:
    cur.executemany("UPDATE problems SET 회차 = '2003-03' WHERE id = %s", [(pid,) for pid in move_ids])
    print(f"  ✓ {len(move_ids)}개 2003-03으로 이동")

conn.commit()

# 결과
cur.execute("""
    SELECT 회차, COUNT(*) FROM problems 
    WHERE 회차 IN ('2003-03', '2026-01')
    GROUP BY 회차 ORDER BY 회차
""")
for cycle, cnt in cur.fetchall():
    print(f"  결과: {cycle} = {cnt}문제")

cur.close()
conn.close()
print("done")