#!/usr/bin/env python3
"""kinz.kr에서 특정 연도 범위의 문제/보기를 스크래이프하고,
브라우저로 정답을 추출하여 DB에 삽입"""
import sys, re, json, time, urllib.parse, os
import psycopg2
import requests
from bs4 import BeautifulSoup

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')

# 2005~2009 kinz exam ID → (회차표기, 시험날짜)
EXAMS = {
    6847: ('2005-01', '2005. 3. 6.'),
    6846: ('2005-02', '2005. 5. 29.'),
    6845: ('2005-03', '2005. 8. 7.'),
    6844: ('2006-01', '2006. 3. 5.'),
    6843: ('2006-02', '2006. 5. 14.'),
    6842: ('2006-03', '2006. 8. 6.'),
    6841: ('2007-01', '2007. 3. 4.'),
    6840: ('2007-02', '2007. 5. 13.'),
    6839: ('2007-03', '2007. 8. 5.'),
    6838: ('2008-01', '2008. 3. 2.'),
    6837: ('2008-02', '2008. 5. 11.'),
    6836: ('2008-03', '2008. 7. 27.'),
    6835: ('2009-01', '2009. 3. 1.'),
    6834: ('2009-02', '2009. 5. 10.'),
    6833: ('2009-03', '2009. 7. 26.'),
}

def scrape_kinz_problems(exam_id):
    """kinz.kr에서 문제/보기 HTML 파싱"""
    url = f'https://www.kinz.kr/exam/{exam_id}'
    resp = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(resp.text, 'html.parser')

    current_subject = None
    problems = []

    # 과목 마커: content-template 안에 "1과목 : 전기자기학" 형식의 text
    content = soup.find('div', class_='content-template')
    if not content:
        content = soup.find('main') or soup

    # 1) 과목 시퀀스 추출 — content-template 안의 모든 텍스트에서 과목 마커 순서대로
    subject_order = []
    for text_node in content.find_all(string=True):
        text = text_node.strip()
        m = re.match(r'(\d)과목\s*:\s*(.+)', text)
        if m:
            subject_order.append((m.group(1), m.group(2).strip()))

    # 2) exam-question div로 문제 파싱
    for q_div in content.find_all('div', class_='exam-question'):
        h5 = q_div.find('h5')
        if not h5:
            continue
        pnum_text = h5.get_text(strip=True)
        pnum_match = re.match(r'(\d+)\.\s*(.*)', pnum_text)
        if not pnum_match:
            continue

        ul = q_div.find('ul')
        choices = []
        if ul:
            for li in ul.find_all('li', recursive=False):
                choices.append(li.get_text(strip=True))

        imgs = []
        for img in q_div.find_all('img'):
            src = img.get('src', '')
            if src.startswith('/'):
                src = 'https://www.kinz.kr' + src
            if src:
                imgs.append(src)

        # 문제 번호로 현재 과목 결정 (20문제 단위)
        num = int(pnum_match.group(1))
        subj_idx = (num - 1) // 20
        current_subject = subject_order[subj_idx][1] if subj_idx < len(subject_order) else None

        problems.append({
            'subject': current_subject,
            'num': num,
            'question': pnum_match.group(2),
            'choices': '\n'.join(choices) if choices else '',
            'num_choices': len(choices),
            'images': imgs,
        })

    return problems


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    
    total_inserted = 0
    total_skipped = 0
    total_errors = 0
    
    for exam_id, (cycle, exam_date) in sorted(EXAMS.items()):
        print(f"\n{'='*60}")
        print(f"📋 {cycle} ({exam_date}) — exam/{exam_id}")
        print(f"{'='*60}")
        
        # 문제/보기 스크래이프
        try:
            problems = scrape_kinz_problems(exam_id)
        except Exception as e:
            print(f"  ❌ 스크래이프 실패: {e}")
            total_errors += 1
            continue
        
        print(f"  ✅ {len(problems)}문제 파싱 완료")
        
        inserted = 0
        skipped = 0
        
        for p in problems:
            # 중복 확인: 이미 같은 회차 + 같은 문제 fingerprint가 있는지
            # fingerprint로 확인
            fp_text = re.sub(r'\s+', '', p['question'] or '')
            fp_text = re.sub(r'[\[\]\(\)\.\,\-\:\;\?\!\'·◆◇※【】]', '', fp_text)
            fp_text = re.sub(r'\d+', '', fp_text)
            
            if len(fp_text) < 10:
                skipped += 1
                continue
            
            # 중복 체크 (같은 회차 + fingerprint)
            cur.execute("""
                SELECT id FROM problems 
                WHERE 회차 = %s AND (
                    replace(replace(문제, ' ', ''), '　', '') ILIKE %s
                    OR replace(replace(문제, ' ', ''), '　', '') ILIKE %s
                )
            """, (cycle, f'%{p["question"][:30]}%', f'%{p["question"][-30:]}%'))
            
            existing = cur.fetchone()
            if existing:
                skipped += 1
                continue
            
            # 새 UUID 생성
            import uuid
            pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f'kinz/{exam_id}/{p["num"]}'))
            
            # 이미지 URL을 마크업으로 변환
            img_markup = ''
            for img_url in p['images'][:5]:  # 최대 5개
                img_markup += f' [이미지: {img_url}]'
            question_text = p['question'] + img_markup
            
            # 과목명 표준화
            subject = p['subject']
            if subject == '회로이론':
                subject = '회로이론 및 제어공학'
            elif subject == '전기설비':
                subject = '전기설비기술기준'
            elif subject == '전기설비기술기준':
                subject = '전기설비기술기준 및 판단기준'
            
            cur.execute("""
                INSERT INTO problems (id, 문제, 정답, 해설, 사용공식, 출처, 회차, 과목, 보기, 중복출제)
                VALUES (%s, %s, '', '', '', %s, %s, %s, %s, '')
                ON CONFLICT (id) DO NOTHING
            """, (
                pid,
                question_text,
                f'https://www.kinz.kr/exam/{exam_id}',
                cycle,
                subject,
                p['choices'],
            ))
            
            if cur.rowcount > 0:
                inserted += 1
        
        conn.commit()
        total_inserted += inserted
        total_skipped += skipped
        print(f"  ✅ {inserted}개 삽입, {skipped}개 건너뜀")
    
    print(f"\n{'='*60}")
    print(f"📊 최종 통계")
    print(f"{'='*60}")
    print(f"  삽입: {total_inserted}")
    print(f"  건너뜀: {total_skipped}")
    print(f"  에러: {total_errors}")
    
    cur.close()
    conn.close()
    print("done")

if __name__ == '__main__':
    main()
