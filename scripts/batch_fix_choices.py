#!/usr/bin/env python3
"""
전체 회차 🖼️ 플레이스홀더 → kinz 이미지 일괄 교체
"""
import re, os, sys, time, urllib.request, psycopg2

conn = psycopg2.connect(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
cur = conn.cursor()

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
IMG_DIR = '/root/elec-exam/public/images/kinz'
os.makedirs(IMG_DIR, exist_ok=True)

KINZ_IDS = {
    "2010-01": 6831, "2010-02": 6832, "2010-03": 6830,
    "2011-01": 6829, "2011-02": 6828, "2011-03": 6827,
    "2012-01": 6826, "2012-02": 6825, "2012-03": 6824,
    "2013-01": 6823, "2013-02": 6822, "2013-03": 6821,
    "2014-01": 6820, "2014-02": 6819, "2014-03": 6818,
    "2015-01": 6817, "2015-02": 6816, "2015-03": 6815,
    "2016-01": 6814, "2016-02": 6813, "2016-03": 6812,
    "2017-01": 6811, "2017-02": 6810, "2017-03": 6809,
    "2018-01": 6808, "2018-02": 6807, "2018-03": 6806,
    "2019-01": 6805, "2019-02": 6804, "2019-03": 6803,
    "2020-02": 109511, "2020-03": 172940, "2020-04": 217966,
    "2021-01": 257755, "2021-02": 269009, "2021-03": 294393,
    "2022-01": 337511, "2022-02": 351693,
}

def esc_like(s):
    """psycopg2 LIKE 이스케이프"""
    return s.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

def check_remaining(cycle):
    cur.execute(
        "SELECT COUNT(*) FROM problems WHERE 회차=%s AND POSITION('🖼️' IN 보기) > 0",
        (cycle,)
    )
    return cur.fetchone()[0]

def fetch_page(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8', errors='replace')

def download_image(src_path):
    fname = os.path.basename(src_path)
    local = os.path.join(IMG_DIR, fname)
    if os.path.exists(local) and os.path.getsize(local) > 0:
        return f"/images/kinz/{fname}"
    try:
        url = f"https://www.kinz.kr{src_path}"
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            with open(local, 'wb') as f:
                f.write(r.read())
        return f"/images/kinz/{fname}"
    except Exception as e:
        return None

def parse_kinz_problems(html):
    problems = {}
    idx = 0
    while True:
        h5_start = html.find('<h5', idx)
        if h5_start == -1: break
        h5_end = html.find('</h5>', h5_start)
        if h5_end == -1: break
        header = html[h5_start:h5_end+5]
        nm = re.search(r'>\s*(\d+)\.\s*(.*?)</h5>', header, re.DOTALL)
        if nm:
            pn = int(nm.group(1))
            qtext = re.sub(r'<[^>]+>', '', nm.group(2)).strip()
            next_h5 = html.find('<h5', h5_end + 5)
            block_end = next_h5 if next_h5 != -1 else len(html)
            block = html[h5_start:block_end]
            lis = re.findall(r'<li[^>]*>(.*?)</li>', block, re.DOTALL)
            choice_imgs = []
            for li in lis:
                imgs = re.findall(r'<img[^>]*src="([^"]*)"[^>]*>', li, re.DOTALL)
                choice_imgs.append(imgs)
            if any(choice_imgs):
                problems[pn] = {'qtext': qtext, 'choice_imgs': choice_imgs}
        idx = h5_end + 5
    return problems

def hangul_only(s):
    return ''.join(ch for ch in s if ord('가') <= ord(ch) <= ord('힣'))

def score_match(q1, q2):
    h1, h2 = hangul_only(q1), hangul_only(q2)
    if not h1 or not h2: return 0
    s1, s2 = set(h1), set(h2)
    return len(s1 & s2) / max(len(s1 | s2), 1) * 100

total = 0
for cycle, kid in sorted(KINZ_IDS.items()):
    rem = check_remaining(cycle)
    if rem == 0: continue
    
    print(f"\n{'='*40}")
    print(f"{cycle} (kinz {kid}): {rem}개")
    
    html = fetch_page(f"https://www.kinz.kr/exam/{kid}")
    kinz = parse_kinz_problems(html)
    if not kinz:
        print(f"  보기 이미지 있는 문제 없음")
        continue
    print(f"  kinz 보기이미지 문제: {len(kinz)}개")
    
    cur.execute(
        "SELECT id, LEFT(문제,200) as qt, 보기, 정답 FROM problems "
        "WHERE 회차=%s AND POSITION('🖼️' IN 보기) > 0",
        (cycle,)
    )
    db_rows = cur.fetchall()
    
    updated = 0
    for rid, db_qt, old_bo, ans in db_rows:
        db_clean = hangul_only(db_qt.replace('🖼️', '').replace('  ', ' ').strip())
        best_pn = None
        best_score = 0
        for pn, info in kinz.items():
            s = score_match(db_clean, info['qtext'])
            if s > best_score:
                best_score = s
                best_pn = pn
        
        if best_pn is None or best_score < 30:
            print(f"  NO MATCH({best_score:.0f}): {db_qt[:30]}...")
            continue
        
        info = kinz[best_pn]
        choices = info['choice_imgs']
        markers = ['①','②','③','④']
        parts = []
        for i in range(4):
            if i < len(choices) and choices[i]:
                local = download_image(choices[i][0])
                if local:
                    parts.append(f'{markers[i]} <img src="{local}" alt="보기{i+1}" style="max-width:250px;vertical-align:middle;margin:2px"/>')
                    continue
            # fallback: keep original
            lines = old_bo.split('\n')
            if i < len(lines):
                txt = re.sub(r'^[①-④]\s*🖼?\s*', '', lines[i]).strip()
                parts.append(f'{markers[i]} {txt}' if txt else markers[i])
            else:
                parts.append(markers[i])
        
        new_bo = '\n'.join(parts)
        if '<img' in new_bo:
            cur.execute("UPDATE problems SET 보기=%s WHERE id=%s", (new_bo, rid))
            updated += 1
    
    conn.commit()
    print(f"  업데이트: {updated}개")
    total += updated
    time.sleep(0.5)  # rate limit

print(f"\n{'='*40}")
print(f"총 업데이트: {total}개")
cur.execute("SELECT COUNT(*) FROM problems WHERE POSITION('🖼️' IN 보기) > 0")
print(f"남은 🖼️: {cur.fetchone()[0]}개")
conn.close()