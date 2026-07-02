#!/usr/bin/env python3
"""2020-02 남은 🖼️ 보기 처리"""
import re, os, urllib.request, psycopg2

conn = psycopg2.connect(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
cur = conn.cursor()
IMG_DIR = '/root/elec-exam/public/images/kinz'
UA = 'Mozilla/5.0'

def hangul(s): return ''.join(ch for ch in s if ord('가') <= ord(ch) <= ord('힣'))

def dl(src):
    fname = os.path.basename(src)
    local = os.path.join(IMG_DIR, fname)
    if os.path.exists(local) and os.path.getsize(local) > 0:
        return f"/images/kinz/{fname}"
    try:
        req = urllib.request.Request(f"https://www.kinz.kr{src}", headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            with open(local, 'wb') as f: f.write(r.read())
        return f"/images/kinz/{fname}"
    except: return None

# Parse kinz 2020-02
with open('/tmp/kinz_109511.html') as f: h = f.read()
probs = {}
i = 0
while True:
    hs = h.find('<h5', i)
    if hs == -1: break
    he = h.find('</h5>', hs)
    if he == -1: break
    m = re.search(r'>\s*(\d+)\.\s*(.*?)</h5>', h[hs:he+5], re.DOTALL)
    if m:
        pn = int(m.group(1))
        qt = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        nh = h.find('<h5', he+5)
        bl = h[hs:(nh if nh!=-1 else len(h))]
        lis = re.findall(r'<li[^>]*>(.*?)</li>', bl, re.DOTALL)
        ci = []
        for li in lis:
            ci.append(re.findall(r'<img[^>]*src="([^"]*)"[^>]*>', li, re.DOTALL))
        if any(ci):
            probs[pn] = {'qt': qt, 'ci': ci}
    i = he+5

print(f"2020-02 kinz problems with choice imgs: {len(probs)}")

cur.execute("""
    SELECT id, LEFT(문제,200), 보기, 정답 FROM problems 
    WHERE 회차='2020-02' AND POSITION('🖼️' IN 보기) > 0
""")
db_rows = cur.fetchall()
print(f"DB 🖼️ 보기: {len(db_rows)}개")

updated = 0
for rid, qt, bo, ans in db_rows:
    db_h = hangul(qt.replace('🖼️','').replace('  ',' ').strip())
    best = (None, 0)
    for pn, info in probs.items():
        s = len(set(db_h) & set(hangul(info['qt']))) / max(len(set(db_h) | set(hangul(info['qt']))), 1) * 100
        if s > best[1]: best = (pn, s)
    
    pn, sc = best
    if pn is None or sc < 25:
        print(f"  NO MATCH ({sc:.0f}): {qt[:40]}...")
        continue
    
    info = probs[pn]
    mrk = ['①','②','③','④']
    parts = []
    for i in range(4):
        if i < len(info['ci']) and info['ci'][i]:
            local = dl(info['ci'][i][0])
            if local:
                parts.append(f'{mrk[i]} <img src="{local}" style="max-width:250px"/>')
                continue
        lines = bo.split('\n')
        if i < len(lines):
            parts.append(re.sub(r'^[①-④]\s*🖼?\s*', '', lines[i]) or mrk[i])
        else:
            parts.append(mrk[i])
    
    nb = '\n'.join(parts)
    if '<img' in nb:
        cur.execute("UPDATE problems SET 보기=%s WHERE id=%s", (nb, rid))
        updated += 1
        print(f"  #{pn} ({sc:.0f}%): {qt[:40]}...")

conn.commit()
print(f"\n2020-02 updated: {updated}")

# Same for 2020-04
print(f"\n{'='*40}\nFetching 2020-04...")
import time
time.sleep(1)
curl -s --connect-timeout 10 --max-time 30 "https://www.kinz.kr/exam/217966" -o /tmp/kinz_217966.html
print("Done")
PYEOF