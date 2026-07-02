#!/usr/bin/env python3
"""2020-03 🖼️ 보기를 kinz 이미지로 대체"""
import re, os, psycopg2, json
from urllib.request import urlretrieve

conn = psycopg2.connect(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
cur = conn.cursor()

IMG_DIR = '/root/elec-exam/public/images/kinz'
os.makedirs(IMG_DIR, exist_ok=True)

# Parse kinz page
with open('/tmp/kinz_172940.html') as f:
    html = f.read()

# Extract all problems with their choice images
problems_with_choices = {}
# Pattern: <h5...>N. 문제텍스트 ... (혹시 ... <img...>) ... <ul><li>①...<img...></li></ul>
# Find question blocks
idx = 0
while True:
    h5_start = html.find('<h5', idx)
    if h5_start == -1:
        break
    h5_end = html.find('</h5>', h5_start)
    if h5_end == -1:
        break
    
    # Get problem number and text
    header = html[h5_start:h5_end+5]
    num_match = re.search(r'>\s*(\d+)\.\s*(.*?)</h5>', header, re.DOTALL)
    if not num_match:
        idx = h5_end + 5
        continue
    
    pn = num_match.group(1)
    qtext = re.sub(r'<[^>]+>', '', num_match.group(2)).strip()
    
    # Get next h5 position to find block boundaries
    next_h5 = html.find('<h5', h5_end + 5)
    block_end = next_h5 if next_h5 != -1 else len(html)
    block = html[h5_start:block_end]
    
    # Find all <img> tags in the block (choices section)
    imgs = re.findall(r'<img[^>]*src="([^"]*)"[^>]*>', block, re.DOTALL)
    
    # Find choice li elements and their images
    lis = re.findall(r'<li[^>]*>(.*?)</li>', block, re.DOTALL)
    choice_imgs = []
    for li in lis:
        li_imgs = re.findall(r'<img[^>]*src="([^"]*)"[^>]*>', li, re.DOTALL)
        choice_imgs.append(li_imgs)
    
    if any(choice_imgs):  # has at least one choice image
        problems_with_choices[pn] = {
            'qtext': qtext,
            'choice_imgs': choice_imgs,
            'all_imgs': imgs
        }
    
    idx = block_end

print(f"Kinz problems with choice images: {len(problems_with_choices)}")
for pn, info in list(problems_with_choices.items())[:10]:
    print(f"  #{pn}: {info['qtext'][:40]}... choices={[len(c) for c in info['choice_imgs']]}")

# Now match DB problems with 🖼️ in 보기
cur.execute("""
    SELECT id, LEFT(문제,80) as 문제_text, 보기, 정답
    FROM problems 
    WHERE 회차='2020-03' AND 보기 LIKE '%🖼️%'
""")
db_problems = cur.fetchall()
print(f"\nDB problems with 🖼️ choices: {len(db_problems)}")

# Download images and generate 보기
def download_and_reference(src_path):
    """Download kinz image and return local path"""
    fname = os.path.basename(src_path)
    local_path = os.path.join(IMG_DIR, fname)
    if not os.path.exists(local_path):
        try:
            url = f"https://www.kinz.kr{src_path}"
            import urllib.request
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as r:
                with open(local_path, 'wb') as f:
                    f.write(r.read())
        except Exception as e:
            print(f"  DL FAIL: {src_path} -> {e}")
            return None
    return f"/images/kinz/{fname}"

updated = 0
for rid, qtext, bo, answer in db_problems:
    # Clean text for matching
    clean = qtext.replace('🖼️', '').replace('  ', ' ').strip()
    
    # Try to find best matching kinz problem
    best_match = None
    best_score = 0
    
    clean_short = clean[:30].replace(' ', '')
    
    for pn, info in problems_with_choices.items():
        kinz_clean = info['qtext'].replace(' ', '')[:30]
        score = 0
        for ch in clean_short:
            if ch in kinz_clean:
                score += 1
        if score > best_score:
            best_score = score
            best_match = pn
    
    if best_match and best_score > 5:
        info = problems_with_choices[best_match]
        choices = info['choice_imgs']
        
        # Generate new 보기 with <img> tags
        markers = ['①', '②', '③', '④']
        new_bo_parts = []
        
        for i, li_imgs in enumerate(choices):
            if i >= 4:
                break
            if li_imgs:
                local_ref = download_and_reference(li_imgs[0])
                if local_ref:
                    new_bo_parts.append(f'{markers[i]} <img src="{local_ref}" alt="보기{i+1}" style="max-width:250px;vertical-align:middle;margin:2px"/>')
                    continue
            # Fallback: keep original choice text for this position
            lines = bo.split('\n')
            if i < len(lines):
                orig = lines[i]
                txt = re.sub(r'^[①-④]\s*🖼️', '', orig).strip()
                if txt:
                    new_bo_parts.append(f'{markers[i]} {txt}')
                else:
                    new_bo_parts.append(markers[i])
            else:
                new_bo_parts.append(markers[i])
        
        new_bo = '\n'.join(new_bo_parts)
        
        # Only update if we got at least some images
        if '<img' in new_bo:
            cur.execute("UPDATE problems SET 보기=%s WHERE id=%s", (new_bo, rid))
            updated += 1
            print(f"  UPDATED #{best_match} ({cur.rowcount}): {clean[:30]}...")
        else:
            print(f"  SKIP #{best_match} (no img downloaded): {clean[:30]}...")
    else:
        print(f"  NO MATCH ({best_match}, score={best_score}): {clean[:30]}...")

conn.commit()
print(f"\nTotal updated: {updated}")

# Verify
cur.execute("SELECT COUNT(*) FROM problems WHERE 회차='2020-03' AND 보기 LIKE '%🖼️%'")
print(f"Remaining 🖼️ in 2020-03: {cur.fetchone()[0]}")
conn.close()
