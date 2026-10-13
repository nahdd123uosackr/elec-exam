#!/usr/bin/env python3
"""2020-02: 유사 중복 제거 (fuzzy match on problem text) + 과수 조정"""
import os
import psycopg2, os, re, sys
from difflib import SequenceMatcher

conn = psycopg2.connect(
    host=os.environ.get('PG_HOST') or os.environ.get('DB_HOST', 'nhd.us.to'),
    user=os.environ.get('PG_USER') or os.environ.get('DB_USER', 'postgres'),
    password=os.environ.get('PG_PASSWORD') or os.environ.get('DB_PASSWORD', 'os.environ["PG_PASSWORD"]'),
    dbname=os.environ.get('PG_DATABASE') or os.environ.get('DB_NAME', 'elec'))
cur = conn.cursor()

CYCLE = '2020-02'

def clean_text(t):
    """이미지/수식 태그 제거 후 순수 텍스트 비교"""
    t = re.sub(r'<img[^>]*>', '', t)
    t = re.sub(r'\$\$[^$]+\$\$', '', t)
    t = re.sub(r'\$[^$]+\$', '', t)
    t = re.sub(r'\[이미지:[^\]]*\]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def score_row(row):
    """유지 우선순위 점수: (has_img_문제, has_img_보기, 긴_보기, 비어있지_않은_정답, 긴_문제)"""
    pid, 문제, 정답, 보기, 과목 = row
    has_img_q = 1 if '<img' in (문제 or '') else 0
    has_img_c = 1 if '<img' in (보기 or '') else 0
    choice_len = len(보기 or '')
    has_answer = 0 if 정답 in ('', None) else 1
    prob_len = len(문제 or '')
    return (has_img_q, has_img_c, choice_len, has_answer, prob_len)

# 1. 유사 중복 그룹 찾기
cur.execute("""
  SELECT id, "문제", "정답", "보기", "과목"
  FROM problems WHERE "회차" = %s
  ORDER BY "문제"
""", (CYCLE,))
all_rows = cur.fetchall()

# Group by cleaned text (first 50 chars of cleaned)
groups = {}
for r in all_rows:
    cleaned = clean_text(r[1])
    key = cleaned[:60]  # first 60 chars of cleaned text
    groups.setdefault(key, []).append(r)

del_count = 0
del_ids = []
for key, items in groups.items():
    if len(items) <= 1:
        continue
    # Sort by comprehensive score
    items.sort(key=score_row, reverse=True)
    keep = items[0]
    for item in items[1:]:
        # Check if REALLY same problem (high similarity)
        clean_keep = clean_text(keep[1])
        clean_item = clean_text(item[1])
        ratio = SequenceMatcher(None, clean_keep, clean_item).ratio()
        if ratio > 0.7:  # high similarity threshold
            del_ids.append(item[0])
            del_count += 1
            print(f"  DEL {item[4]:12s} sim={ratio:.2f} | {clean_item[:50]}")

print(f"\n=== 삭제 대상: {del_count}개 ===")

if del_count > 0:
    cur.execute("DELETE FROM problems WHERE id = ANY(%s)", (del_ids,))
    conn.commit()
    print(f"  {del_count}개 삭제 완료")

# 2. 최종 통계
cur.execute("""
  SELECT "과목", COUNT(*) FROM problems
  WHERE "회차" = %s GROUP BY "과목" ORDER BY "과목"
""", (CYCLE,))
print("\n=== 최종 통계 ===")
for subj, cnt in cur.fetchall():
    print(f"  {subj}: {cnt}")

cur.execute("SELECT COUNT(*) FROM problems WHERE \"회차\" = %s", (CYCLE,))
total = cur.fetchone()[0]
print(f"  총 {total}문제")

conn.close()
