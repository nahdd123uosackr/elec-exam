#!/usr/bin/env python3
import psycopg2
conn = psycopg2.connect(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
cur = conn.cursor()

# Count Y-graph problems
cur.execute("SELECT COUNT(*) FROM problems WHERE 회차='2022-02' AND 문제 LIKE '%Y&선%△%'")
print(f"Y결선 count: {cur.fetchone()[0]}")

# Show current
cur.execute("SELECT id, LEFT(문제,50), LEFT(보기,20), LENGTH(보기), 정답 FROM problems WHERE 회차='2022-02' AND 문제 LIKE '%Y%선%△%' ORDER BY id")
for r in cur.fetchall():
    print(f"  {r[0][:8]} | {r[1]}... | 보기={repr(r[2])} | len={r[3]} | 정답={r[4]}")

# Update
bo77 = '① <img src="/images/kinz/kt20220424m77b1-NuHMtxQIfud.gif" alt="보기1" style="max-width:200px;vertical-align:middle;margin:2px"/>\n② <img src="/images/kinz/kt20220424m77b2-B4Mlap-24jW.gif" alt="보기2" style="max-width:200px;vertical-align:middle;margin:2px"/>\n③ <img src="/images/kinz/kt20220424m77b3-aKRkMaUxxrl.gif" alt="보기3" style="max-width:200px;vertical-align:middle;margin:2px"/>\n④ <img src="/images/kinz/kt20220424m77b4-FOWcGmmDQ85.gif" alt="보기4" style="max-width:200px;vertical-align:middle;margin:2px"/>'
cur.execute("UPDATE problems SET 보기=%s WHERE 회차='2022-02' AND 문제 LIKE '%Y%선%△%' AND LENGTH(보기) < 20", (bo77,))
print(f"Updated: {cur.rowcount}")
conn.commit()

# Final check
cur.execute("SELECT COUNT(*) FROM problems WHERE 회차='2022-02' AND LENGTH(보기) < 20")
print(f"Empty/short 보기 remaining in 2022-02: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM problems WHERE 회차='2022-02'")
print(f"Total 2022-02 rows: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM problems WHERE 회차='2022-02' AND 보기 LIKE '%<img%'")
print(f"With img choices: {cur.fetchone()[0]}")

conn.close()
