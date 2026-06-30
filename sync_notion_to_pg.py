#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전기기사 Notion → Postgres 동기화 (cron job)
"""

import requests
import pg8000.dbapi as pg
import re
import time
import json
import shutil
from datetime import datetime

# === 설정 ===
start_time = time.time()
NOTION_HEADERS = {
    "Authorization": "Bearer ntn_d56118619483PjQVzpTLOCNriwIUqCQvMfovD6QB3MQg1U",
    "Notion-Version": "2025-09-03"
}
DATA_SOURCE_ID = "35414e7e-37bc-811c-a4e3-000b57ab5e00"

PG_CONFIG = {
    "host": "nhd.us.to",
    "port": 5432,
    "user": "postgres",
    "password": "Hyeongdong1",
    "database": "elec",
    "timeout": 30
}

# === 1. Notion에서 데이터 가져오기 ===
print("📥 Notion에서 데이터 수집 중...")
out = {}
cursor = None
page_count = 0

while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor

    r = requests.post(
        f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query",
        headers=NOTION_HEADERS,
        json=payload,
        timeout=60
    )
    r.raise_for_status()
    data = r.json()

    for page in data["results"]:
        props = page["properties"]

        def txt(key):
            p = props.get(key, {})
            if p.get("rich_text"):
                return "".join(t.get("plain_text", "") for t in p["rich_text"])
            if p.get("title"):
                return "".join(t.get("plain_text", "") for t in p["title"])
            if p.get("select"):
                return p["select"].get("name", "")
            return ""

        # 테스트 제거 조건
        problem_text = txt("문제")
        source_url = (props.get("출처") or {}).get("url", "")
        round_text = txt("회차")

        if "[테스트]" in problem_text:
            continue
        if "/exam/test" in source_url:
            continue
        if round_text == "9999. 1. 1.":
            continue

        out[page["id"]] = {
            "id": page["id"],
            "문제": problem_text,
            "정답": txt("정답"),
            "해설": txt("해설"),
            "사용공식": txt("사용공식"),
            "회차": round_text,
            "과목": txt("과목"),
            "난이도": txt("난이도"),
            "보기": txt("보기"),
            "출처": source_url,
        }
        page_count += 1

    cursor = data.get("next_cursor")
    if not data.get("has_more"):
        break

print(f"✅ Notion 페이지 수집 완료: {page_count}개 (테스트 제거 후)")

# === 2. PostgreSQL 동기화 ===
print("🔄 PostgreSQL 동기화 중...")
conn = pg.connect(**PG_CONFIG)
conn.autocommit = True
cur = conn.cursor()

# 기존 데이터 삭제 후 일괄 insert
cur.execute("TRUNCATE TABLE problems;")

items = list(out.values())
CHUNK = 200
for i in range(0, len(items), CHUNK):
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

print(f"✅ DB insert 완료: {len(items)} rows")

# === 3. 보기 정규화 ===
print("🔧 보기 정규화 중...")

ITEM_RE = re.compile(r"^\s*\d+\.\s*[①-⑤]\s*(.+?)\s*$|^\s*[①-⑤]\s*(.+?)\s*$|^\s*[\(]?\d[\)\.]\s*(.+?)\s*$")
NOISE_RE = re.compile(r"\.\s*[<>]\s*$")

def normalize(raw):
    if not raw:
        return ""
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    result = []
    labels = ["①", "②", "③", "④", "⑤"]
    for ln in lines:
        m = ITEM_RE.match(ln)
        if m:
            t = next((g for g in m.groups() if g), "").strip()
            t = NOISE_RE.sub("", t).strip()
            if t:
                result.append(t)
        else:
            t = NOISE_RE.sub("", ln).strip()
            if t:
                result.append(t)
    return "\n".join(f"{labels[i]} {t}" for i, t in enumerate(result) if i < 5)

cur.execute("SELECT id, 보기 FROM problems WHERE 보기 <> '';")
rows = cur.fetchall()

normalized_count = 0
for i in range(0, len(rows), 1000):
    batch = [(normalize(t), pid) for pid, t in rows[i:i+1000]]
    cur.executemany("UPDATE problems SET 보기=%s, updated_at=now() WHERE id=%s;", batch)
    normalized_count += len(batch)

print(f"✅ 보기 정규화 완료: {normalized_count}개")

# === 4. JSON export ===
print("📤 JSON export 중...")
cur.execute("""SELECT id, 문제, 정답, 해설, 사용공식, 출처, 회차, 과목, 난이도, 보기
               FROM problems ORDER BY 회차 DESC, 과목, 문제;""")
cols = [d[0] for d in cur.description]
data = [dict(zip(cols, r)) for r in cur.fetchall()]

with open("/root/elec-exam/data/problems.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False)

shutil.copy("/root/elec-exam/data/problems.json", "/root/elec-exam/public/data/problems.json")

json_size_mb = len(json.dumps(data, ensure_ascii=False).encode("utf-8")) / (1024 * 1024)
print(f"✅ JSON export 완료: {json_size_mb:.2f} MB")

# === 5. 통계 ===
cur.execute("SELECT COUNT(*) FROM problems;")
db_rows = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM problems WHERE 보기 <> '';")
view_count = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM problems WHERE 회차 = '9999. 1. 1.' OR 문제 LIKE '%[테스트]%' OR 출처 LIKE '%/exam/test%';")
test_removed = cur.fetchone()[0]

conn.close()

print(f"""
📊 동기화 통계
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Notion 페이지: {page_count}
테스트 제거: {test_removed}
DB rows: {db_rows}
보기 있는 문제: {view_count}
JSON 크기: {json_size_mb:.2f} MB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

# === 6. Telegram 보고 ===
TELEGRAM_TOKEN = "8037610187:AAH6XqJ5c7kK9ZxN3vL8pQ2rT7yU9iW1oP"
CHAT_ID = "464368671"

report = f"""⚡ 전기기사 Notion → Postgres 동기화 완료
🔸 Notion 페이지: {page_count}
🔸 테스트 제거: {test_removed}
🔸 DB rows: {db_rows}
🔸 보기 있는 문제: {view_count}
🔸 JSON 크기: {json_size_mb:.2f} MB
🔸 총 소요: {(time.time() - start_time) / 60:.1f}분"""

requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    json={"chat_id": CHAT_ID, "text": report},
    timeout=10
)

print("✅ Telegram 보고 완료")
