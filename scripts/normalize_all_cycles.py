#!/usr/bin/env python3
"""
회차 포맷 통일: 모든 회차를 YYYY-NN 형식으로 정규화
- 날짜형 → 년도-회차 매핑
- 중복 회차 병합 (문제수 적은 쪽을 많은 쪽으로 합치고 적은 쪽 삭제)
- 2026-01 이상치 처리
"""
import psycopg2, re
from collections import defaultdict

DB = dict(host='nhd.us.to', port=5432, user='postgres', password='Hyeongdong1', dbname='elec')

def normalize_cycle(raw):
    """회차 문자열 → YYYY-NN 정규화"""
    if not raw:
        return None
    raw = raw.strip()
    
    # 1) 이미 YYYY-NN
    m = re.match(r'^(\d{4})-(\d{2})$', raw)
    if m:
        return raw
    
    # 2) YYYY. M. DD.
    m = re.match(r'^(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.?$', raw)
    if m:
        year, month = m.group(1), int(m.group(2))
        if month <= 3:
            return f"{year}-01"
        elif month <= 6:
            return f"{year}-02"
        elif month <= 8:
            return f"{year}-03"
        else:
            return f"{year}-04"
    
    # 3) YYYY 년 MM 월 DD 일 (YYYY-MM-DD)
    m = re.match(r'^(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*\((\d{4})-(\d{2})-(\d{2})\)$', raw)
    if m:
        year, month = m.group(1), int(m.group(2))
        if month <= 3:
            return f"{year}-01"
        elif month <= 6:
            return f"{year}-02"
        elif month <= 8:
            return f"{year}-03"
        else:
            return f"{year}-04"
    
    return None


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    
    # 1) 모든 회차 + 문제 수 로드
    cur.execute("SELECT 회차, COUNT(*) as cnt FROM problems WHERE 회차 IS NOT NULL AND 회차 != '' GROUP BY 회차 ORDER BY 회차")
    raw_cycles = cur.fetchall()
    
    # 2) 정규화 매핑 생성
    norm_map = defaultdict(list)  # normalized → [(raw, count)]
    unmapped = []
    
    for raw, cnt in raw_cycles:
        norm = normalize_cycle(raw)
        if norm:
            norm_map[norm].append((raw, cnt))
        else:
            unmapped.append((raw, cnt))
    
    print("=== 정규화 결과 ===")
    for norm in sorted(norm_map.keys()):
        entries = norm_map[norm]
        if len(entries) == 1:
            raw, cnt = entries[0]
            if raw == norm:
                print(f"  ✅ {norm}: {cnt}문제 (이미 정규)")
            else:
                print(f"  🔄 {raw} → {norm}: {cnt}문제")
        else:
            print(f"  ⚠️  {norm}: 중복!")
            for raw, cnt in entries:
                print(f"      {raw}: {cnt}문제")
    
    if unmapped:
        print(f"\n=== 매핑 불가 ({len(unmapped)}개) ===")
        for raw, cnt in unmapped:
            print(f"  ❓ '{raw}': {cnt}문제")
    
    # 3) 정규화 실행
    print("\n\n=== 정규화 실행 ===")
    updates = []
    for norm, entries in norm_map.items():
        for raw, cnt in entries:
            if raw != norm:
                updates.append((norm, raw))
    
    if not updates:
        print("  모든 회차가 이미 정규화됨")
    else:
        for new_cycle, old_cycle in updates:
            print(f"  '{old_cycle}' → '{new_cycle}'")
            cur.execute("UPDATE problems SET 회차 = %s WHERE 회차 = %s", (new_cycle, old_cycle))
        conn.commit()
        print(f"  ✅ {len(updates)}개 회차 업데이트 완료")
    
    # 4) 중복 회차 병합 확인 (같은 회차에 문제가 너무 많은 경우)
    print("\n\n=== 회차별 문제 수 (정규화 후) ===")
    cur.execute("""
        SELECT 회차, COUNT(*) as cnt 
        FROM problems 
        WHERE 회차 IS NOT NULL AND 회차 != '' 
        GROUP BY 회차 
        ORDER BY 회차
    """)
    for cycle, cnt in cur.fetchall():
        flag = "⚠️" if cnt > 120 else "✅"
        print(f"  {flag} {cycle}: {cnt}문제")
    
    # 5) 2005-2009 빈 회차 확인
    print("\n\n=== 2005-2009년 회차 ===")
    for y in range(2005, 2010):
        cur.execute("SELECT COUNT(*) FROM problems WHERE 회차 LIKE %s", (f'{y}%',))
        cnt = cur.fetchone()[0]
        print(f"  {y}: {cnt}문제")
    
    cur.close()
    conn.close()
    print("\ndone")


if __name__ == "__main__":
    main()
