#!/usr/bin/env python3
"""Download kinz images + update DB for 2022-02 remaining 🖼️ problems"""
import psycopg2, re, json, urllib.request, os

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')
IMG_DIR = '/root/elec-exam/public/images/kinz'
os.makedirs(IMG_DIR, exist_ok=True)

#---- kinz image map from page ----
KINZ = {
    3:  ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m3b1-C1zrosBGI.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m3b2-oLfeeLslcn.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m3b3-J9WbPyatf_.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m3b4-70AZAxdwgF.gif'],
    9:  ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m9b1-r1mB5Cs7V7.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m9b2-jAjmza3SPP.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m9b3-X2xxjHCl6l.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m9b4-oYeQjAJX6u.gif'],
    11: ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m11b1-IH1egdbTuu.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m11b2-TxAJFqFrn7.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m11b3-EjfmYd2YND.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m11b4-ZEoqFRW10j.gif'],
    12: ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m12b1-bn44e_tlztm.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m12b2-Ibod3YpfVNp.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m12b3-m17rKwOTycm.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m12b4-M6QlV2rM4iC.gif'],
    31: ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m31b1-iGE29ySS6Gl.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m31b2-A_YSSA8Q5AO.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m31b3-YxujeEdFlzm.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m31b4-W4sh1pn4efb.gif'],
    45: ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m45b1-lDu9r7HJRKu.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m45b2-25LDg4BHHMu.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m45b3-yzdYa13hUz9.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m45b4-9FGanQdg7pq.gif'],
    52: ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m52b1-pctgD7HpIY8.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m52b2-n-de-PoZ7g3.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m52b3-NkHH6fgpuwT.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m52b4-R-u-dlMA4iY.gif'],
    56: ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m56b1-jFL9MFYmFdQ.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m56b2-5pcBcLORgG2.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m56b3-PsANQYLxDZF.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m56b4-NqRoyf4jUTw.gif'],
    66: ['https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m66b3-UoWQffiZ0RB.gif',
         'https://www.kinz.kr/data/exam/BTkACJ3Yu/kt20220424m66b4-J6USs-MBUYV.gif'],
}

#---- 1. Download all images ----
print("=== 이미지 다운로드 ===")
for prob, urls in KINZ.items():
    for url in urls:
        fname = url.split('/')[-1]
        fpath = os.path.join(IMG_DIR, fname)
        if not os.path.exists(fpath):
            try:
                urllib.request.urlretrieve(url, fpath)
                print(f"  ✓ {fname}")
            except:
                print(f"  ✗ {fname}")

#---- 2. Match DB problems to kinz prob numbers ----
conn = psycopg2.connect(**DB)
cur = conn.cursor()

cur.execute("""
    SELECT id, 문제, 과목 FROM problems
    WHERE 회차='2022-02' AND (문제 LIKE '%🖼️%' OR 보기 LIKE '%🖼️%')
""")
placeholder_rows = cur.fetchall()

def clean_text(t):
    """Remove 🖼️, normalize spaces"""
    return re.sub(r'[🖼️\s]+', ' ', t).strip()

# Build keyword-based matching
# Each kinz problem has distinct keywords → match DB problems
# Map kinz prob nums to text (extracted from page)
# We need text for each jjn prob num
kinz_text_map = {
    3:  "진공 중에 무한 평면도체와 d(m)만큼 떨어진 곳에 선전하밀도 λ(C/m)의 무한 직선도체가 평행하게 놓여 있는 경우 직선 도체의 단위 길이당 받는 힘은 몇 N/m 인가",
    9:  "투자율이 μ(H/m), 단면적이 S(m2), 길이가 l(m)인 자성체에 권신을 N희 감아서 I(A)의 전류를 흘렸을 때 이 자성체의 단면적 S(m2)를 통과하는 자속(Wb)은?",
    11: "진공 중에서 점(1, 3)m의 위치에 -2×10-9C의 전하가 있을 때",
    12: "정전용량이 C0(μF)인 평행판의 공기 커패시터가 있다. 두 극판 사이에 극판과 평행하게 절반을 비유전율이 εr인 유전체로 채우면",
    31: "승압기에 의하여 전압 Ve에서 Vh로 승압할 때 2차 정격전압 e 자기용량 W인 단상 승압기가 공급할 수 있는 부하용량은",
    45: "슬립 st에서 최대 토크를 발생하는 3상 유도전동기에 2차측 한상의 저황을 r2라 하면 최대 토크로 기동하기 위한 2차측 한 상에 외부로부터 가해 주어야 할 저항",
    52: "권수비가 a인 단상변압기 3대가 있다 이것을 1차에 △ 2차에 Y로 결선하여 3상 교류 평형회로에 접속할 때",
    56: "동기발전기에서 무부하 정격전압일 때의 여자전류를 Ifo 정격부하 정격전압일 때의 여자전류를 If1 3상 단락 정격전류에 대한 여자전류를 Ifs라 하면 정격속도에서의 단락비",
    66: "기본 제어요소인 비례요소의 전달함수는 (단, K는 상수이다.)",
}

def best_match(db_text):
    """Find kinz prob number by keyword overlap"""
    db_clean = clean_text(db_text)
    best = None
    best_score = 0
    for pn, k_text in kinz_text_map.items():
        words = set(re.findall(r'[가-힣a-zA-Z0-9()]+', k_text))
        overlap = sum(1 for w in words if len(w) >= 2 and w in db_clean)
        if overlap > best_score:
            best_score = overlap
            best = pn
    return best, best_score

updated = 0
for pid, problem, subject in placeholder_rows:
    pn, score = best_match(problem)
    if pn and score >= 5:
        urls = KINZ[pn]
        choice_imgs = ''.join(
            f'<img src="/images/kinz/{u.split("/")[-1]}" alt="보기이미지" style="max-width:200px;vertical-align:middle;margin:2px"/>'
            for u in urls
        )
        # Clear 🖼️ from 문제, add images to 보기
        new_problem = problem.replace('🖼️', '').replace('\n🖼️', '').replace('\n\n', '\n').strip()
        new_choice = choice_imgs
        cur.execute("UPDATE problems SET 문제=%s, 보기=%s WHERE id=%s", (new_problem, new_choice, pid))
        updated += 1
        print(f"  ✓ #{pn} (score={score}): {problem[:40]}...")
    else:
        print(f"  ? No match (score={score}): {problem[:40]}...")

conn.commit()
print(f"\n업데이트: {updated}개")

cur.execute("SELECT COUNT(*) FROM problems WHERE 회차='2022-02' AND (문제 LIKE '%🖼️%')")
print(f"2022-02 문제 🖼️ 남음: {cur.fetchone()[0]}개")
cur.execute("SELECT COUNT(*) FROM problems WHERE 회차='2022-02' AND (보기 LIKE '%🖼️%')")
print(f"2022-02 보기 🖼️ 남음: {cur.fetchone()[0]}개")

cur.close();conn.close()
EOF