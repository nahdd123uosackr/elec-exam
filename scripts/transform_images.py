#!/usr/bin/env python3
"""DB 변환: [이미지: ...] → 적절한 HTML/마커로 변경 + 이미지 파일 동기화"""
import psycopg2, re, os, urllib.request

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
IMG_DIR = "/root/elec-exam/public/images/kinz"

conn = psycopg2.connect(**DB)
cur = conn.cursor()

def process_text(txt):
    """문제/해설 텍스트에서 [이미지: ...] 처리"""
    if not txt:
        return txt
    
    # 1. [이미지: http://...] → <img src="/images/kinz/파일명">
    def replace_img_url(m):
        url = m.group(1)
        fname = url.split('/')[-1]
        local = f"/images/kinz/{fname}"
        # 파일 있으면 img 태그, 없으면 URL 그대로
        fullpath = os.path.join(IMG_DIR, fname)
        if os.path.exists(fullpath) and os.path.getsize(fullpath) > 50:
            return f'<img src="{local}" alt="이미지" style="max-width:300px;vertical-align:middle;margin:2px"/>'
        else:
            # 다운로드 시도
            try:
                urllib.request.urlretrieve(url, fullpath)
                if os.path.getsize(fullpath) > 50:
                    return f'<img src="{local}" alt="이미지" style="max-width:300px;vertical-align:middle;margin:2px"/>'
            except:
                pass
            return f'[이미지: {url}]'
    
    txt = re.sub(r'\[이미지:\s*(https?://[^\]]+)\]', replace_img_url, txt)
    
    # 2. [이미지: LaTeX 수식] → KaTeX 마커
    def replace_latex(m):
        formula = m.group(1).strip()
        # tikzpicture → 이미지 placeholder
        if 'tikzpicture' in formula:
            return '🖼️'
        # LaTeX 수식 → $$...$$
        return f'$${formula}$$'
    
    txt = re.sub(r'\[이미지:\s*(\\\\[^\]]+|\\begin{tikzpicture}[^\]]+)\]', replace_latex, txt)
    
    # 3. [이미지: N개] → 🖼️
    txt = re.sub(r'\[이미지:\s*\d+개\]', '🖼️', txt)
    
    # 4. 단순 [이미지] → 🖼️
    txt = re.sub(r'\[이미지\]', '🖼️', txt)
    
    return txt

# 문제 텍스트 변환
cur.execute("""
    SELECT id, 문제, 해설, 보기 
    FROM problems 
    WHERE 문제 LIKE '%[이미지%'
""")
updated_q = 0
for rid, q, s, choices in cur.fetchall():
    new_q = process_text(q or '')
    new_s = process_text(s or '')
    new_c = process_text(choices or '')
    if new_q != q or new_s != s or new_c != choices:
        cur.execute("UPDATE problems SET 문제=%s, 해설=%s, 보기=%s WHERE id=%s",
                     (new_q, new_s, new_c, rid))
        updated_q += 1

conn.commit()
print(f"  문제/해설 변환: {updated_q}개")

# LaTeX 변환 결과 체크
cur.execute("SELECT COUNT(*) FROM problems WHERE 문제 LIKE '%$$%'")
tex_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM problems WHERE 문제 LIKE '%<img%'")
img_count = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM problems WHERE 문제 LIKE '%🖼️%'")
placeholder_count = cur.fetchone()[0]
print(f"  LaTeX 수식 문제: {tex_count}개")
print(f"  <img> 태그 포함 문제: {img_count}개")
print(f"  🖼️ placeholder 문제: {placeholder_count}개")

# 보기 변환
cur.execute("""
    SELECT COUNT(*) FROM problems 
    WHERE NULLIF(보기,'') IS NOT NULL AND 보기 LIKE '%[이미지%'
""")
choices_with_img = cur.fetchone()[0]
print(f"  보기 이미지 포함: {choices_with_img}개")

# 샘플 확인
cur.execute("SELECT 문제 FROM problems WHERE 문제 LIKE '%<img%' LIMIT 3")
print("\n=== 변환 샘플 (<img> 태그) ===")
for (q,) in cur.fetchall():
    print(f"  {q[:200]}...")

cur.execute("SELECT 문제 FROM problems WHERE 문제 LIKE '%$$%' LIMIT 3")
print("\n=== 변환 샘플 (LaTeX) ===")
for (q,) in cur.fetchall():
    print(f"  {q[:200]}...")

cur.close()
conn.close()