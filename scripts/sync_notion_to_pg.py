#!/usr/bin/env python3
"""전기기사 Notion → Postgres 동기화 (매일 01:00 KST cron)."""
import requests, time, re, json, shutil, os, sys
from collections import Counter

NOTION_TOKEN = "ntn_d56118619483PjQVzpTLOCNriwIUqCQvMfovD6QB3MQg1U"
DATA_SOURCE_ID = "35414e7e-37bc-811c-a4e3-000b57ab5e00"
HEADERS = {"Authorization": f"Bearer {NOTION_TOKEN}",
           "Notion-Version": "2025-09-03"}

PG = dict(host="nhd.us.to", port=5432, user="postgres",
          password="Hyeongdong1", timeout=30)


def fetch_notion():
    out = {}
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query",
            headers=HEADERS, json=payload, timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        for page in data["results"]:
            props = page["properties"]
            def txt(k):
                p = props.get(k, {})
                if p.get("rich_text"):
                    return "".join(t.get("plain_text", "") for t in p["rich_text"])
                if p.get("title"):
                    return "".join(t.get("plain_text", "") for t in p["title"])
                if p.get("select"):
                    return p["select"].get("name", "")
                return ""
            out[page["id"]] = {
                "id": page["id"],
                "문제": txt("문제"), "정답": txt("정답"), "해설": txt("해설"),
                "사용공식": txt("사용공식"), "회차": txt("회차"),
                "과목": txt("과목"), "난이도": txt("난이도"),
                "보기": txt("보기"),
                "출처": (props.get("출처") or {}).get("url", ""),
            }
        cursor = data.get("next_cursor")
        if not data.get("has_more"):
            break
    return out


def filter_pages(pages):
    kept = {}
    test_removed = 0
    for pid, r in pages.items():
        if "[테스트]" in r["문제"]:
            test_removed += 1; continue
        if "/exam/test" in r["출처"]:
            test_removed += 1; continue
        if r["회차"] == "9999. 1. 1.":
            test_removed += 1; continue
        kept[pid] = r
    return kept, test_removed


def sync_db(items):
    import pg8000.dbapi as pg
    conn = pg.connect(database="elec", **PG)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE problems;")
    CHUNK = 200
    for i in range(0, len(items), CHUNK):
        batch = items[i:i+CHUNK]
        cur.executemany(
            """INSERT INTO problems (id, 문제, 정답, 해설, 사용공식, 출처, 회차, 과목, 난이도, 보기)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (id) DO UPDATE SET
                   문제=EXCLUDED.문제, 정답=EXCLUDED.정답, 해설=EXCLUDED.해설,
                   사용공식=EXCLUDED.사용공식, 출처=EXCLUDED.출처,
                   회차=EXCLUDED.회차, 과목=EXCLUDED.과목, 난이도=EXCLUDED.난이도,
                   보기=EXCLUDED.보기, updated_at=now();""",
            [(r["id"], r["문제"], r["정답"], r["해설"], r["사용공식"], r["출처"],
              r["회차"], r["과목"], r["난이도"], r["보기"]) for r in batch],
        )
    cur.execute("SELECT COUNT(*) FROM problems;")
    db_total = cur.fetchone()[0]
    return conn, cur, db_total


ITEM_RE = re.compile(
    r"^\s*\d+\.\s*[①-⑤]\s*(.+?)\s*$"
    r"|^\s*[①-⑤]\s*(.+?)\s*$"
    r"|^\s*[\(]?\d[\)\.]\s*(.+?)\s*$"
)
NOISE_RE = re.compile(r"\.\s*[<>]\s*$")
LABELS = ["①", "②", "③", "④", "⑤"]


def normalize(raw):
    if not raw:
        return ""
    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    out = []
    for ln in lines:
        m = ITEM_RE.match(ln)
        if m:
            t = next((g for g in m.groups() if g), "").strip()
            t = NOISE_RE.sub("", t).strip()
            if t:
                out.append(t)
        else:
            t = NOISE_RE.sub("", ln).strip()
            if t:
                out.append(t)
    return "\n".join(f"{LABELS[i]} {t}" for i, t in enumerate(out) if i < 5)


def normalize_view(conn, cur):
    cur.execute("SELECT id, 보기 FROM problems WHERE 보기 <> '';")
    rows = cur.fetchall()
    n = 0
    for i in range(0, len(rows), 1000):
        batch = [(normalize(t), pid) for pid, t in rows[i:i+1000]]
        cur.executemany(
            "UPDATE problems SET 보기=%s, updated_at=now() WHERE id=%s;",
            batch,
        )
        n += len(batch)
    return len(rows)


def export_json(conn, cur):
    cur.execute(
        """SELECT id, 문제, 정답, 해설, 사용공식, 출처, 회차, 과목, 난이도, 보기
           FROM problems ORDER BY 회차 DESC, 과목, 문제;"""
    )
    cols = [d[0] for d in cur.description]
    data = [dict(zip(cols, r)) for r in cur.fetchall()]
    with open("/root/elec-exam/data/problems.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    shutil.copy(
        "/root/elec-exam/data/problems.json",
        "/root/elec-exam/public/data/problems.json",
    )
    return data, os.path.getsize("/root/elec-exam/data/problems.json") / (1024 * 1024)


def write_stats(data, with_보기):
    cy = Counter(r["회차"] for r in data)
    sj = Counter(r["과목"] for r in data if r["과목"])
    stats = {
        "total": len(data),
        "with_answer": sum(1 for r in data if r["정답"]),
        "with_보기": with_보기,
        "cycles": len(cy),
        "subjects": len(sj),
        "cycle_breakdown": dict(cy),
        "subject_breakdown": dict(sj),
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open("/root/elec-exam/data/stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    return stats


def main():
    t0 = time.time()
    raw = fetch_notion()
    notion_total = len(raw)
    filtered, test_removed = filter_pages(raw)
    print(f"Notion fetched: {notion_total}, test_removed: {test_removed}, kept: {len(filtered)}", flush=True)

    conn, cur, db_total = sync_db(list(filtered.values()))
    print(f"DB rows after sync: {db_total}", flush=True)

    with_보기_raw = normalize_view(conn, cur)
    print(f"Normalized 보기 rows: {with_보기_raw}", flush=True)

    data, size_mb = export_json(conn, cur)
    print(f"JSON exported: {size_mb:.2f} MB", flush=True)

    cur.execute("SELECT COUNT(*) FROM problems WHERE 보기 <> '';")
    with_보기 = cur.fetchone()[0]

    stats = write_stats(data, with_보기)
    conn.close()

    elapsed = (time.time() - t0) / 60
    print(f"\n=== DONE in {elapsed:.1f}min ===")
    print(f"Notion pages: {notion_total}, DB rows: {db_total}, with_보기: {with_보기}")
    print(f"Test removed: {test_removed}, JSON: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()
