#!/usr/bin/env python3
"""모든 회차의 🖼️ 플레이스홀더를 동일 문제의 <img> 버전으로 덮어쓰기"""
import psycopg2, re

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
conn = psycopg2.connect(**DB)
cur = conn.cursor()

def base_text(t):
    t = re.sub(r'^\d+\.\s*', '', t or '')
    t = re.sub(r'<img[^>]*>', '', t)
    t = t.replace('🖼️', '').replace('[이미지]', '').strip()
    return t[:80]

# <img> 있는 모든 문제 (회차별)
cur.execute("""
    SELECT 회차, id, 문제, 보기 FROM problems 
    WHERE 문제 LIKE '%<img%' OR 보기 LIKE '%<img%'
    ORDER BY 회차
""")
img_map = {}
for cycle, rid, q, b in cur.fetchall():
    key = (cycle, base_text(q))
    if key not in img_map:
        img_map[key] = (rid, q, b)

# 🖼️ 있는 모든 문제
cur.execute("""
    SELECT 회차, id, 문제, 보기 FROM problems 
    WHERE (문제 LIKE '%🖼️%' OR 보기 LIKE '%🖼️%')
      AND (문제 NOT LIKE '%<img%' AND 보기 NOT LIKE '%<img%')
    ORDER BY 회차
""")
fixed = 0
remaining_by_cycle = {}
for cycle, pid, pq, pb in cur.fetchall():
    key = (cycle, base_text(pq))
    if key in img_map:
        iid, iq, ib = img_map[key]
        cur.execute("UPDATE problems SET 문제=%s, 보기=%s WHERE id=%s", (iq, ib, pid))
        fixed += 1
    else:
        remaining_by_cycle.setdefault(cycle, 0)
        remaining_by_cycle[cycle] += 1

conn.commit()

print(f"🖼️ → <img> 전환: {fixed}개")
print(f"\n=== 처리 불가 (🖼️ ↔ <img> 미매칭) 회차별 ===")
for c, n in sorted(remaining_by_cycle.items()):
    print(f"  {c}: {n}개")

total_remaining = sum(remaining_by_cycle.values())
print(f"\n남은 🖼️ 총계: {total_remaining}개")

cur.close();conn.close()
EOF