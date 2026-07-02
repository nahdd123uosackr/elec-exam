#!/usr/bin/env python3
"""2010-02 전체 kinz 문제 vs DB 문제 텍스트 매칭"""
import re, urllib.request, psycopg2

conn = psycopg2.connect(host='nhd.us.to',port=5432,user='postgres',password='Hyeongdong1',dbname='elec')
cur = conn.cursor()
UA = 'Mozilla/5.0'

# Fetch full kinz 2010-02 page
req = urllib.request.Request("https://www.kinz.kr/exam/6832", headers={'User-Agent': UA})
with urllib.request.urlopen(req, timeout=30) as r: 
    html = r.read().decode('utf-8','replace')

# Parse ALL problems (not just those with choice imgs)
all_probs = {}
i = 0
while True:
    hs=html.find('<h5',i)
    if hs==-1: break
    he=html.find('</h5>',hs)
    if he==-1: break
    m=re.search(r'>\s*(\d+)\.\s*(.*?)</h5>',html[hs:he+5],re.DOTALL)
    if m:
        pn=int(m.group(1))
        qt=re.sub(r'<[^>]+>','',m.group(2)).strip()
        nh=html.find('<h5',he+5)
        bl=html[hs:(nh if nh!=-1 else len(html))]
        lis=re.findall(r'<li[^>]*>(.*?)</li>',bl,re.DOTALL)
        ci=[]
        for li in lis:
            imgs=re.findall(r'<img[^>]*src="([^"]*)"[^>]*>',li,re.DOTALL)
            ci.append(imgs)
        all_probs[pn]={'qt':qt,'ci':ci}
    i=he+5

print(f"Total kinz problems: {len(all_probs)}")

# DB 남은 문제
cur.execute("""
    SELECT id, LEFT(문제,200) as qt, 보기 FROM problems 
    WHERE 회차='2010-02' AND POSITION('🖼️' IN 보기)>0
""")
db = cur.fetchall()

for rid, qt, bo in db:
    clean = qt.replace('🖼️',' ').replace('  ',' ').strip()
    # Extract numeric/LaTeX unique identifiers
    identifiers = re.findall(r'[A-Za-z0-9_()=＋＋/\^∞ω]+', clean)
    id_str = ' '.join(identifiers[:10])
    
    # Search all kinz problems for keywords
    print(f"\nDB: {clean[:60]}...")
    
    # Try to find matching kinz problem
    hg_db = ''.join(ch for ch in clean if ord('가')<=ord(ch)<=ord('힣'))
    best = []
    
    for pn, info in all_probs.items():
        hg_kz = ''.join(ch for ch in info['qt'] if ord('가')<=ord(ch)<=ord('힣'))
        shared = sum(1 for ch in set(hg_db) if ch in hg_kz)
        total = max(len(set(hg_db)|set(hg_kz)), 1)
        score = 100 * shared / total
        
        has_img = sum(len(imgs) for imgs in info['ci'])
        
        if score > 15 or (has_img and ('원형' in info['qt'] or '라플라스' in info['qt'] or '논리식' in info['qt'])):
            best.append((score, pn, info['qt'][:40], has_img))
    
    best.sort(reverse=True)
    for score, pn, kz_qt, has_img in best[:3]:
        ci_info = f"img={has_img}" if has_img else "txt"
        print(f"  -> #{pn} [{score:.0f}%] {kz_qt} ({ci_info})")

conn.close()
PYEOF