#!/usr/bin/env python3
"""Generic: download kinz images + update DB for a cycle"""
import psycopg2, re, json, urllib.request, os, sys

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
IMG_DIR = '/root/elec-exam/public/images/kinz'
os.makedirs(IMG_DIR, exist_ok=True)

CYCLE = sys.argv[1]   # e.g. '2022-01'
JSON_PATH = sys.argv[2]  # e.g. '/tmp/kinz_2022_01.json'

with open(JSON_PATH) as f:
    kinz = json.load(f)

# kinz is {probNum_str: {q, problem:[urls], choices:[urls]}}
# Build text map for matching
text_map = {int(k): v['q'] for k, v in kinz.items()}

#---- 1. Download images ----
print(f"=== {CYCLE} 이미지 다운로드 ===")
total_dl = 0
for k, v in kinz.items():
    for url in v.get('problem', []) + v.get('choices', []):
        fname = url.split('/')[-1]
        fpath = os.path.join(IMG_DIR, fname)
        if not os.path.exists(fpath):
            try:
                urllib.request.urlretrieve(url, fpath)
                total_dl += 1
            except Exception as e:
                print(f"  ✗ {fname}: {e}")
print(f"  새 다운로드: {total_dl}개")

#---- 2. Match DB problems ----
conn = psycopg2.connect(**DB)
cur = conn.cursor()

cur.execute("""
    SELECT id, 문제, 과목 FROM problems
    WHERE 회차=%s AND (문제 LIKE %s OR 보기 LIKE %s)
""", (CYCLE, '%🖼️%', '%🖼️%'))
rows = cur.fetchall()
print(f"🖼️ placeholder rows: {len(rows)}개")

def clean(t): return re.sub(r'[🖼️\s]+', ' ', t).strip()

def best_match(db_text):
    db_clean = clean(db_text)
    best, best_score = None, 0
    for pn, k_text in text_map.items():
        words = set(re.findall(r'[가-힣a-zA-Z0-9()]+', k_text))
        overlap = sum(1 for w in words if len(w) >= 2 and w in db_clean)
        if overlap > best_score:
            best_score = overlap
            best = pn
    return best, best_score

updated = 0
for pid, problem, subject in rows:
    pn, score = best_match(problem)
    if pn and score >= 5 and str(pn) in kinz:
        info = kinz[str(pn)]
        # All image URLs (problem + choices)
        all_urls = info.get('problem', []) + info.get('choices', [])
        # If problem image exists, put in 문제; if only choice images, put in 보기
        problem_urls = info.get('problem', [])
        choice_urls = info.get('choices', [])
        
        new_problem = problem
        if problem_urls:
            # Replace 🖼️ in 문제 with img tags
            imgs = ''.join(
                f'<img src="/images/kinz/{u.split("/")[-1]}" alt="문제이미지" style="max-width:300px;vertical-align:middle;margin:2px"/>'
                for u in problem_urls
            )
            new_problem = problem.replace('🖼️', imgs).replace('\n\n', '\n').strip()
            if '🖼️' not in problem and imgs not in new_problem:
                # append if no marker
                new_problem = problem + '\n' + imgs
        
        new_choice = ''
        if choice_urls:
            imgs = ''.join(
                f'<img src="/images/kinz/{u.split("/")[-1]}" alt="보기이미지" style="max-width:200px;vertical-align:middle;margin:2px"/>'
                for u in choice_urls
            )
            # If 기존 보기에 🖼️, replace; else add
            cur.execute("SELECT 보기 FROM problems WHERE id=%s", (pid,))
            cur_choice = cur.fetchone()[0] or ''
            if '🖼️' in cur_choice:
                new_choice = cur_choice.replace('🖼️', imgs)
            else:
                new_choice = imgs
        
        cur.execute("UPDATE problems SET 문제=%s, 보기=COALESCE(NULLIF(%s,''), 보기) WHERE id=%s",
                    (new_problem, new_choice, pid))
        updated += 1
        print(f"  ✓ #{pn} (score={score}): {problem[:50]}...")
    else:
        print(f"  ? No match (score={score}): {problem[:50]}...")

conn.commit()
print(f"\n업데이트: {updated}개")

cur.execute("SELECT COUNT(*) FROM problems WHERE 회차=%s AND (문제 LIKE %s OR 보기 LIKE %s)", (CYCLE, '%🖼️%', '%🖼️%'))
print(f"{CYCLE} 🖼️ 남음: {cur.fetchone()[0]}개")

cur.close();conn.close()
