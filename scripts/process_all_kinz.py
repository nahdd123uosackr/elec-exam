#!/usr/bin/env python3
"""Process all 2010-2020 kinz data: download images + update DB"""
import json, psycopg2, re, urllib.request, os

IMG_DIR = '/root/elec-exam/public/images/kinz'
os.makedirs(IMG_DIR, exist_ok=True)
DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')

CYCLES = [
    '2010-01','2010-02','2010-03','2011-01','2011-02','2011-03',
    '2012-01','2012-02','2012-03','2013-01','2013-02','2013-03',
    '2014-01','2014-02','2014-03','2015-01','2015-02','2015-03',
    '2016-01','2016-02','2016-03','2017-01','2017-02','2017-03',
    '2018-01','2018-02','2018-03','2019-01','2019-02','2019-03',
    '2020-02','2020-03','2020-04'
]

def clean(t):
    t = re.sub(r'<img[^>]*>', '', t)
    t = re.sub(r'[🖼️\[\]이미지\s:\n]+', ' ', t)
    t = re.sub(r'[①②③④❶❷❸❹▶●○◇■□]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()[:100]
    return t

for cycle in CYCLES:
    path = f'/tmp/kinz_{cycle}.json'
    try:
        with open(path) as f:
            raw = json.load(f)
    except FileNotFoundError:
        print(f"SKIP {cycle}: no file")
        continue
    
    kinz = raw.get('questions', raw) if isinstance(raw, dict) else raw
    if isinstance(kinz, list):
        kinz = {str(item.get('q', i+1)): {'q': str(item.get('q_text', item.get('q',''))), 'problem': item.get('problem',[]), 'choices': item.get('choices',[])} for i, item in enumerate(kinz)}
    
    dl = 0
    for info in kinz.values():
        for url in info.get('problem', []) + info.get('choices', []):
            fname = url.split('/')[-1]
            fpath = os.path.join(IMG_DIR, fname)
            if not os.path.exists(fpath):
                try:
                    urllib.request.urlretrieve(url, fpath)
                    dl += 1
                except:
                    pass
    
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT id, 문제, 보기 FROM problems WHERE 회차=%s AND (문제 LIKE %s OR 보기 LIKE %s)",
                (cycle, '%🖼️%', '%🖼️%'))
    rows = cur.fetchall()
    
    updated = 0
    for pid, problem, choice in rows:
        clean_prob = clean(problem)
        best_pn, best_score = None, 0
        for pn, info in kinz.items():
            k_clean = re.sub(r'^\d+\.\s*', '', info.get('q', ''))
            k_clean = re.sub(r'<[^>]+>', '', k_clean)
            k_clean = re.sub(r'\s+', ' ', k_clean).strip()[:60]
            words = set(re.findall(r'[가-힣a-zA-Z0-9()]+', k_clean))
            overlap = sum(1 for w in words if len(w) >= 2 and w in clean_prob)
            if overlap > best_score:
                best_score = overlap
                best_pn = pn

        if best_pn and best_score >= 3:
            info = kinz[best_pn]
            # Skip if kinz has no images at all
            if not info.get('problem') and not info.get('choices'):
                continue
            new_prob = problem
            if info.get('problem'):
                imgs = ''.join(f'<img src="/images/kinz/{u.split("/")[-1]}" alt="문제이미지" style="max-width:300px;vertical-align:middle;margin:2px"/>' for u in info['problem'])
                new_prob = problem.replace('🖼️', imgs) if '🖼️' in problem else problem + '\n' + imgs
            
            new_choice = choice if choice else ''
            if info.get('choices'):
                imgs = ''.join(f'<img src="/images/kinz/{u.split("/")[-1]}" alt="보기이미지" style="max-width:200px;vertical-align:middle;margin:2px"/>' for u in info['choices'])
                if '🖼️' in (choice or ''):
                    new_choice = choice.replace('🖼️', imgs)
                else:
                    new_choice = imgs
            
            cur.execute("UPDATE problems SET 문제=%s, 보기=COALESCE(NULLIF(%s,''), 보기) WHERE id=%s",
                       (new_prob, new_choice, pid))
            updated += 1
    
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM problems WHERE 회차=%s AND (문제 LIKE %s OR 보기 LIKE %s)",
                (cycle, '%🖼️%', '%🖼️%'))
    remaining = cur.fetchone()[0]
    print(f"{cycle}: {len(kinz)}개->{dl}다운, {updated}업데이트, {remaining}🖼️")
    cur.close(); conn.close()
