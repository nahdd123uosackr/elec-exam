#!/usr/bin/env python3
"""전기기사 동기화 - Step 2: DB INSERT, 정규화, JSON export"""
import pg8000.dbapi as pg
import json, re, time, shutil

start = time.time()
with open('/tmp/notion_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
items = data['items']
print(f'Loaded {len(items)} items')

PG = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', database='elec', timeout=30)
conn = pg.connect(**PG)
conn.autocommit = True
cur = conn.cursor()

# TRUNCATE
print('TRUNCATE...')
cur.execute('TRUNCATE TABLE problems;')
print(f'TRUNCATE done: {time.time()-start:.1f}s')

# Batch insert
CHUNK = 200
total = len(items)
for i in range(0, total, CHUNK):
    batch = items[i:i+CHUNK]
    cur.executemany("""
        INSERT INTO problems (id,문제,정답,해설,사용공식,출처,회차,과목,난이도,보기)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET
            문제=EXCLUDED.문제, 정답=EXCLUDED.정답, 해설=EXCLUDED.해설,
            사용공식=EXCLUDED.사용공식, 출처=EXCLUDED.출처,
            회차=EXCLUDED.회차, 과목=EXCLUDED.과목, 난이도=EXCLUDED.난이도,
            보기=EXCLUDED.보기, updated_at=now();
    """, [(r["id"], r["문제"], r["정답"], r["해설"], r["사용공식"], r["출처"],
           r["회차"], r["과목"], r["난이도"], r["보기"]) for r in batch])
    if (i // CHUNK) % 5 == 0:
        print(f'  inserted {min(i+CHUNK,total)}/{total} ({time.time()-start:.1f}s)')

print(f'INSERT done: {total} rows ({time.time()-start:.1f}s)')

# === 3. 보기 정규화 ===
print('Normalize 보기...')
ITEM_RE = re.compile(r"^\s*\d+\.\s*[①-⑤]\s*(.+?)\s*$|^\s*[①-⑤]\s*(.+?)\s*$|^\s*[\(]?\d[\)\.]\s*(.+?)\s*$")
NOISE_RE = re.compile(r"\.\s*[<>]\s*$")

def normalize(raw):
    if not raw: return ""
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    out, labels = [], ["①","②","③","④","⑤"]
    for ln in lines:
        m = ITEM_RE.match(ln)
        if m:
            t = next((g for g in m.groups() if g), "").strip()
            t = NOISE_RE.sub("", t).strip()
            if t: out.append(t)
        else:
            t = NOISE_RE.sub("", ln).strip()
            if t: out.append(t)
    return "\n".join(f"{labels[i]} {t}" for i,t in enumerate(out) if i < 5)

cur.execute("SELECT id, 보기 FROM problems WHERE 보기 <> '';")
rows = cur.fetchall()
print(f'  rows to normalize: {len(rows)}')

normalized_count = 0
for i in range(0, len(rows), 1000):
    batch = [(normalize(t), pid) for pid, t in rows[i:i+1000]]
    cur.executemany("UPDATE problems SET 보기=%s, updated_at=now() WHERE id=%s;", batch)
    normalized_count += len(batch)
print(f'  normalized: {normalized_count}')

# === 4. JSON export ===
print('JSON export...')
cur.execute("""SELECT id, 문제, 정답, 해설, 사용공식, 출처, 회차, 과목, 난이도, 보기
               FROM problems ORDER BY 회차 DESC, 과목, 문제;""")
cols = [d[0] for d in cur.description]
json_data = [dict(zip(cols, r)) for r in cur.fetchall()]

with open("/root/elec-exam/data/problems.json", "w", encoding="utf-8") as f:
    json.dump(json_data, f, ensure_ascii=False)
shutil.copy("/root/elec-exam/data/problems.json", "/root/elec-exam/public/data/problems.json")

size_mb = len(json.dumps(json_data, ensure_ascii=False).encode("utf-8")) / (1024 * 1024)

# Statistics
cur.execute("SELECT COUNT(*) FROM problems;")
db_rows = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM problems WHERE 보기 <> '';")
view_count = cur.fetchone()[0]

conn.close()

elapsed_min = (time.time()-start) / 60

# Save stats for Telegram report
stats = {
    "page_count": data.get("page_count", len(items)),
    "test_removed": data.get("test_removed", 0),
    "db_rows": db_rows,
    "view_count": view_count,
    "size_mb": round(size_mb, 2),
    "elapsed_min": round(elapsed_min, 1)
}
print(json.dumps(stats))
