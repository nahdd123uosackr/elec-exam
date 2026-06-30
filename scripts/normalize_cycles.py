#!/usr/bin/env python3
"""회차명 정규화: 날짜/한글 형식 → YYYY-NN 통일"""
import psycopg2, re, uuid
from collections import defaultdict

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')

# Mapping: old 회차 → normalized YYYY-NN
MAPPING = {
    "2003.03.16 1회차": "2003-01",
    "2003 년 03 월 16 일 (2003-03-16)": "2003-01",
    "2003년 1회차": "2003-01",
    "2003. 3. 16.": "2003-01",
    "2003년 2회차": "2003-02",
    "2003. 5. 25.": "2003-02",
    "2003년 3회차": "2003-03",
    "2003. 8. 10.": "2003-03",
    "2004. 3. 7.": "2004-01",
    "2004. 5. 23.": "2004-02",
    "2010. 5. 9.": "2010-01",
    "2010. 7. 25.": "2010-02",
    "2011. 3. 20.": "2011-01",
    "2011. 6. 12.": "2011-02",
    "2011. 8. 21.": "2011-03",
    "2012. 3. 4.": "2012-01",
    "2012. 5. 20.": "2012-02",
    "2012. 8. 26.": "2012-03",
    "2013. 3. 10.": "2013-01",
    "2013. 6. 2.": "2013-02",
    "2013. 8. 18.": "2013-03",
    "2014. 3. 2.": "2014-01",
    "2014. 5. 25.": "2014-02",
    "2014. 8. 17.": "2014-03",
    "2015. 3. 8.": "2015-01",
    "2015. 5. 31.": "2015-02",
    "2015. 8. 16.": "2015-03",
    "2016. 3. 6.": "2016-01",
    "2016. 5. 8.": "2016-02",
    "2016. 8. 21.": "2016-03",
    "2017. 3. 5.": "2017-01",
    "2017. 5. 7.": "2017-02",
    "2017. 8. 26.": "2017-03",
    "2018. 3. 4.": "2018-01",
    "2018. 4. 28.": "2018-02",
    "2018. 8. 19.": "2018-03",
    "2019. 3. 3.": "2019-01",
    "2019. 4. 27.": "2019-02",
    "2019. 8. 4.": "2019-03",
    "2020 년 06 월 06 일 (2020-06-06)": "2020-02",
    "2020. 6. 6.": "2020-02",
    "2020. 8. 22.": "2020-03",
    "2020. 9. 26.": "2020-04",
    "2021. 3. 7.": "2021-01",
    "2021. 5. 15.": "2021-02",
    "2021. 8. 14.": "2021-03",
    "2022. 3. 5.": "2022-01",
    "2022. 4. 24.": "2022-02",
}

def fp(s):
    """Fingerprint: normalize whitespace, remove answer markers, truncate"""
    t = re.sub(r'[\s　]+', ' ', str(s).strip())[:200]
    t = re.sub(r'[①②③④]', '', t)
    return t

conn = psycopg2.connect(**DB)
cur = conn.cursor()

# Step 1: Rename 회차
print("=== Step 1: 회차명 정규화 ===")
for old_name, new_name in MAPPING.items():
    cur.execute("UPDATE problems SET 회차=%s WHERE 회차=%s", (new_name, old_name))
    if cur.rowcount > 0:
        print(f"  {old_name:45s} → {new_name:10s} ({cur.rowcount:4d}개 업데이트)")
conn.commit()

# Step 2: 통합된 회차 내 중복 정리
print("\n=== Step 2: 통합 회차 내 중복 정리 ===")
# Get all problems ordered by 회차
cur.execute("""
    SELECT id, 문제, 회차, 정답, 해설, 사용공식 
    FROM problems 
    WHERE 문제 IS NOT NULL AND 문제 != '' 
    ORDER BY 회차
""")
rows = cur.fetchall()

by_cycle_fp = defaultdict(lambda: defaultdict(list))
for row in rows:
    f = fp(row[1])
    by_cycle_fp[row[2]][f].append((row[0], row[3], row[4], row[5]))

del_rows = 0
for cycle, fps in sorted(by_cycle_fp.items()):
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
print(f"  중복 삭제: {del_rows}개")

# Step 3: 중복출제 재마킹
print("\n=== Step 3: 중복출제 재마킹 ===")
cur.execute("SELECT id, 문제, 회차 FROM problems WHERE 문제 IS NOT NULL AND 문제 != ''")
rows = cur.fetchall()
by_fp = defaultdict(list)
for row in rows:
    f = fp(row[1])
    by_fp[f].append((row[0], row[2]))

dup_groups = dup2 = dup3 = 0
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
print(f"  중복출제: {dup_groups}그룹 (2회:{dup2}, 3회+:{dup3})")

# Step 4: 최종 현황
print("\n=== Step 4: 최종 현황 ===")
cur.execute("SELECT COUNT(*), COUNT(NULLIF(정답,'')), COUNT(DISTINCT 회차) FROM problems")
total, answered, cycles = cur.fetchone()
print(f"  전체: {total}문제, 정답 {answered}개 ({answered*100//max(total,1)}%), {cycles}회차")

cur.execute("SELECT 회차, COUNT(*), COUNT(NULLIF(정답,'')) FROM problems GROUP BY 회차 ORDER BY 회차")
for cycle, tot, ans in cur.fetchall():
    bar = '✅' if tot == ans else '⏳'
    print(f"  {bar} {cycle}: {ans}/{tot}")

cur.close()
conn.close()
