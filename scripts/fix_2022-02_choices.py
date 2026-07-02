#!/usr/bin/env python3
import re, urllib.request, psycopg2, json, os

IMG_DIR = '/root/elec-exam/public/images/kinz'
os.makedirs(IMG_DIR, exist_ok=True)

# Parse kinz page
url = 'https://www.kinz.kr/exam/351693'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
html = urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='replace')
pattern = re.compile(r'<h5[^>]*>\s*(\d+)\.\s*(.*?)</h5>', re.DOTALL)

kinz_data = {}
for m in pattern.finditer(html):
    pn = int(m.group(1))
    text = m.group(2).strip()
    start = m.end()
    next_h = pattern.search(html, start)
    block = html[start:next_h.start()] if next_h else html[start:]
    lis = re.findall(r'<li[^>]*>(.*?)</li>', block, re.DOTALL)

    choices = []
    for li in lis:
        imgs = re.findall(r'<img[^>]*src="([^"]*)"', li)
        txt = re.sub(r'<[^>]+>', '', li).strip()
        choices.append({'text': txt, 'images': imgs, 'has_img': len(imgs) > 0})
    kinz_data[pn] = {'text': text, 'choices': choices}

# DB
conn = psycopg2.connect(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
cur = conn.cursor()

cur.execute("SELECT id, 문제, 정답 FROM problems WHERE 회차='2022-02' AND 보기 = '①\n②\n③\n④' ORDER BY 문제")
empty_rows = cur.fetchall()

updated = 0
for pid, qtext, ans in empty_rows:
    q_short = re.sub(r'<[^>]+>', '', qtext).strip()[:80]
    best_pn = None
    for pn, kd in kinz_data.items():
        ktext = kd['text'].replace('...', '').strip()
        common = len(set(ktext.split()) & set(q_short.split()))
        if common >= 3:
            best_pn = pn
            break

    if best_pn and kinz_data[best_pn]['choices']:
        kd = kinz_data[best_pn]
        has_img = any(c['has_img'] for c in kd['choices'][:4])
        if not has_img:
            continue

        parts = []
        for i, c in enumerate(kd['choices'][:4]):
            label = ['①', '②', '③', '④'][i]
            if c['has_img']:
                img_url = c['images'][0]
                fname = img_url.split('/')[-1]
                parts.append(f'{label} <img src="/images/kinz/{fname}" alt="보기{label}" style="max-width:200px;vertical-align:middle;margin:2px"/>')
            else:
                txt = c['text']
                if txt.startswith('①'):
                    txt = txt[1:].strip()
                elif txt.startswith(tuple('①②③④⑤')):
                    txt = txt[1:].strip()
                parts.append(f'{label} {txt}'.strip())

        new_bo = '\n'.join(parts)
        cur.execute("UPDATE problems SET 보기=%s WHERE id=%s", (new_bo, pid))
        updated += 1
        print(f"  #{best_pn:2d} → {pid[:8]}: {new_bo[:60]}...")

conn.commit()
print(f"\nTotal updated: {updated}")

cur.execute("SELECT COUNT(*) FROM problems WHERE 회차='2022-02' AND 보기 = '①\n②\n③\n④'")
print(f"Remaining empty: {cur.fetchone()[0]}")

# Also download any missing images
print("\nDownloading missing images...")
for pn, kd in kinz_data.items():
    for c in kd['choices']:
        for img_url in c['images']:
            fname = img_url.split('/')[-1]
            local_path = f'{IMG_DIR}/{fname}'
            if not os.path.exists(local_path):
                if img_url.startswith('/'):
                    img_url = f'https://www.kinz.kr{img_url}'
                try:
                    urllib.request.urlretrieve(img_url, local_path)
                except:
                    pass

conn.close()
print("Done")
