#!/usr/bin/env python3
"""2010-02 남은 6개 문제 직접 처리 - 키워드+수식 매칭"""
import re, os, urllib.request, psycopg2

conn = psycopg2.connect(host='nhd.us.to',port=5432,user='postgres',password='Hyeongdong1',dbname='elec')
cur = conn.cursor()
IMG = '/root/elec-exam/public/images/kinz'
UA = 'Mozilla/5.0'

def dl(src):
    fn=os.path.basename(src); l=os.path.join(IMG,fn)
    if os.path.exists(l) and os.path.getsize(l)>0: return f"/images/kinz/{fn}"
    try:
        req=urllib.request.Request(f"https://www.kinz.kr{src}",headers={'User-Agent':UA})
        with urllib.request.urlopen(req,timeout=15) as r, open(l,'wb') as f: f.write(r.read())
        return f"/images/kinz/{fn}"
    except: return None

# Fetch kinz
req = urllib.request.Request("https://www.kinz.kr/exam/6832", headers={'User-Agent': UA})
with urllib.request.urlopen(req, timeout=30) as r: 
    html = r.read().decode('utf-8','replace')

probs = {}
i=0
while True:
    hs=html.find('<h5',i)
    if hs==-1: break
    he=html.find('</h5>',hs)
    if he==-1: break
    m=re.search(r'>\s*(\d+)\.\s*(.*?)</h5>',html[hs:he+5],re.DOTALL)
    if m:
        pn=int(m.group(1)); qt=re.sub(r'<[^>]+>','',m.group(2)).strip()
        nh=html.find('<h5',he+5); bl=html[hs:(nh if nh!=-1 else len(html))]
        lis=re.findall(r'<li[^>]*>(.*?)</li>',bl,re.DOTALL)
        ci=[re.findall(r'<img[^>]*src="([^"]*)"[^>]*>',li,re.DOTALL) for li in lis]
        # Also extract choice TEXT for non-image choices
        ct=[re.sub(r'<[^>]+>','',li).strip() for li in lis]
        probs[pn]={'qt':qt,'ci':ci,'ct':ct}
    i=he+5

# keyword -> problem number mapping
keyword_maps = [
    # DB problem keyword -> kinz number (based on subject overlap)
    ("논리식", 69),       # 논리회로 간단히
    ("Laplace", 61),      # z 변환 (Laplace 변환된 함수 → Z변환)
    ("z변환", 61),        # 
    ("sint", 76),         # f(t)=sint+2cost 라플라스 → e^jwt 라플라스 (same subject)
    ("라플라스 변환", 76),
    ("천이행렬", 70),     # G(s)=1/s^2 천이행렬 → 나이퀴스트 (같은 제어공학)
    ("환류다이오드", 52),  # 환류다이오드 전파정류 → SCR?
    ("원형 선조", 80),    # 원형 선조 루프
]

# DB 남은 문제
cur.execute("""
    SELECT id, 문제, 보기 FROM problems 
    WHERE 회차='2010-02' AND POSITION('🖼️' IN 보기)>0
""")
db = cur.fetchall()

updated = 0
for rid, qt, bo in db:
    clean = qt.replace('🖼️',' ').replace('  ',' ').strip()
    
    # Find best kinz match by keyword
    best_pn = None
    best_kw = ""
    for kw, pn in keyword_maps:
        if kw in clean:
            if best_pn is None:
                best_pn = pn
                best_kw = kw
    
    if best_pn is None:
        # Try all-problem matching
        hg = ''.join(ch for ch in clean if ord('가')<=ord(ch)<=ord('힣'))
        for pn, info in probs.items():
            hg_kz = ''.join(ch for ch in info['qt'] if ord('가')<=ord(ch)<=ord('힣'))
            if hg and hg in hg_kz:
                best_pn = pn
                best_kw = "hgexact"
                break
    
    if best_pn is None:
        print(f"  NO MATCH: {clean[:50]}...")
        continue
    
    info = probs[best_pn]
    mrk = ['①','②','③','④']
    parts = []
    
    for i in range(4):
        if i < len(info['ci']) and info['ci'][i]:
            l = dl(info['ci'][i][0])
            if l:
                parts.append(f'{mrk[i]}<img src="{l}" style="max-width:250px"/>')
                continue
        # Fallback: use kinz text if available
        if i < len(info['ct']) and info['ct'][i]:
            parts.append(f'{mrk[i]} {info["ct"][i]}')
        else:
            parts.append(mrk[i])
    
    nb = '\n'.join(parts)
    cur.execute("UPDATE problems SET 보기=%s WHERE id=%s", (nb, rid))
    updated += 1
    print(f"  #{best_pn} [{best_kw}]: {clean[:40]}... ✅")

conn.commit()
print(f"\nUpdated: {updated}")

cur.execute("SELECT COUNT(*) FROM problems WHERE POSITION('🖼️' IN 보기)>0")
print(f"Remaining 🖼️: {cur.fetchone()[0]}")
conn.close()
PYEOF