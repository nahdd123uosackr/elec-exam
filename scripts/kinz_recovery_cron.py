#!/usr/bin/env python3
"""
kinz.kr 자동 복구 cron 스크립트 v2
- Primary: crawl4ai MCP (mcp__crawl4ai__html) — reCAPTCHA 우회 가능
- Failover: urllib 직접 접속
- 12시간마다 실행. kinz 접속 성공 시 깨진 회차를 파싱하여 DB 보강
"""
import os
import json, os, sys, re, subprocess
from datetime import datetime, timezone

STATE_FILE = os.path.expanduser("~/.hermes/kinz_recovery_state.json")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIX_CYCLE = os.path.join(SCRIPT_DIR, "fix_cycle.py")

# 회차 → kinz exam ID 매핑
CYCLE_TO_KINZ = {
    "2003-01": 6853, "2003-02": 6852, "2003-03": 6851,
    "2004-01": 6850, "2004-02": 6849, "2004-03": 6848,
    "2005-02": 6846, "2005-03": 6845,
    "2006-03": 6842,
    "2007-03": 6839,
    "2009-01": 6835,
    "2010-01": 6832,  # 2010-01(3월)
}

# 과목 매핑 (kinz 표시 → DB 과목명)
SUBJECT_MAP = {
    "전기자기학": "전기자기학",
    "전력공학": "전력공학",
    "전기기기": "전기기기",
    "회로이론 및 제어공학": "회로이론 및 제어공학",
    "전기설비기술기준 및 판단기준": "전기설비기술기준",
    "전기설비기술기준": "전기설비기술기준",
}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"broken": list(CYCLE_TO_KINZ.keys()), "last_attempt": None, "fixed": []}

def save_state(state):
    state["last_attempt"] = datetime.now(timezone.utc).isoformat()
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def get_db_conn():
    import psycopg2
    return psycopg2.connect(
        host=os.environ.get('PG_HOST', 'nhd.us.to'),
        user=os.environ.get('PG_USER', 'postgres'),
        password=os.environ.get('PG_PASSWORD', 'os.environ["PG_PASSWORD"]'),
        dbname=os.environ.get('PG_DATABASE', 'elec'))

def parse_kinz_html(html):
    """kinz.kr HTML에서 과목별 문제 추출. Returns list of dicts."""
    from html.parser import HTMLParser
    import html as html_mod

    problems = []
    current_subject = None
    current_q = None

    # 과목 헤더 패턴: <div class="bg-dark text-white">N과목 : 과목명</div>
    subj_pat = re.compile(r'(\d+)과목\s*:\s*(.+?)(?:<|$)')
    # 문제 번호 패턴
    qnum_pat = re.compile(r'^(\d+)\.\s*(.+)')

    # 과목 추출
    subj_matches = list(re.finditer(
        r'bg-dark text-white[^>]*>(\d+)과목\s*:\s*([^<]+)', html))
    if not subj_matches:
        return []

    # 문제 블록 추출: <div class="exam-question" id="NNNN">
    q_blocks = list(re.finditer(
        r'<div[^>]*exam-question[^>]*id="(\d+)"[^>]*>(.*?)(?=<div[^>]*exam-question|<div[^>]*bg-dark|$)',
        html, re.DOTALL))

    # 과목 범위 계산
    subj_ranges = []
    for i, m in enumerate(subj_matches):
        start = m.start()
        end = subj_matches[i+1].start() if i+1 < len(subj_matches) else len(html)
        raw_name = m.group(2).strip()
        db_name = SUBJECT_MAP.get(raw_name, raw_name)
        subj_ranges.append((start, end, db_name))

    for qm in q_blocks:
        q_id = qm.group(1)
        q_html = qm.group(2)
        q_pos = qm.start()

        # 어떤 과목에 속하는지
        subject = None
        for s_start, s_end, s_name in subj_ranges:
            if s_start <= q_pos < s_end:
                subject = s_name
                break
        if not subject:
            continue

        # h5에서 문제 텍스트 추출
        h5_m = re.search(r'<h5[^>]*>(.*?)</h5>', q_html, re.DOTALL)
        if not h5_m:
            continue
        q_text = h5_m.group(1)
        # HTML 태그 정리 (img 유지)
        q_text = re.sub(r'<(?!img)[^>]+>', '', q_text).strip()
        q_text = re.sub(r'\s+', ' ', q_text)

        # 문제 번호 제거
        num_m = re.match(r'(\d+)\.\s*', q_text)
        q_num = int(num_m.group(1)) if num_m else 0
        q_text_clean = q_text[num_m.end():].strip() if num_m else q_text

        # 보기 추출: <li value="N">텍스트</li>
        choices = []
        for li_m in re.finditer(r'<li\s+value="(\d+)"[^>]*>(.*?)</li>', q_html, re.DOTALL):
            choice_text = li_m.group(2).strip()
            # 기본 태그 정리 (img src 유지)
            choice_text = re.sub(r'<(?!img)[^>]+>', '', choice_text).strip()
            choices.append(choice_text)

        # img 태그에서 src 추출 (문제 본문)
        imgs_in_q = re.findall(r'<img[^>]*src="([^"]*)"[^>]*/?\s*>', q_html)

        # 보기를 ①②③④ 형식으로 조합
        markers = ['①', '②', '③', '④']
        formatted_choices = []
        for i, c in enumerate(choices[:4]):
            marker = markers[i] if i < len(markers) else f'({i+1})'
            formatted_choices.append(f"{marker} {c}")
        choices_str = '\n'.join(formatted_choices)

        problems.append({
            "과목": subject,
            "문제": q_text_clean,
            "보기": choices_str,
            "번호": q_num,
            "kinz_id": q_id,
            "images": imgs_in_q,
        })

    return problems

def fetch_via_crawl4ai(kinz_id, timeout=60):
    """crawl4ai MCP — SSE transport + Auth. Hermes agent cron에서 호출 시 사용.
    스크립트 단독 실행 시에는 실패하고 urllib failover로 넘어감."""
    url = f"https://www.kinz.kr/exam/{kinz_id}"
    TOKEN = '4ad309a5c881be5a832196bbbaa8fdc15bb44900d7e1fe6c8ea8d1023730b959'
    # StreamableHTTP 시도 (SSE가 아닌 일반 HTTP POST)
    script = f'''
import httpx, json, sys
TOKEN = "{TOKEN}"
url = "{url}"
try:
    with httpx.Client(timeout={timeout}) as client:
        # /mcp endpoint (non-SSE) 시도
        resp = client.post(
            "https://crawl4ai.nhd.us.to/mcp",
            json={{"jsonrpc": "2.0", "method": "tools/call", "id": 1,
                   "params": {{"name": "html", "arguments": {{"url": url}}}}}},
            headers={{"Content-Type": "application/json",
                      "Accept": "application/json",
                      "Authorization": f"Bearer {{TOKEN}}"}},
        )
        if resp.status_code == 200:
            data = resp.json()
            if "result" in data:
                content = data["result"].get("content", [])
                for c in content:
                    if c.get("type") == "text":
                        inner = json.loads(c["text"])
                        print(inner.get("html", ""))
                        sys.exit(0)
            print(resp.text[:200000])
        else:
            print(f"HTTP {{resp.status_code}}: {{resp.text[:200]}}", file=sys.stderr)
            sys.exit(1)
except Exception as e:
    print(f"ERROR: {{e}}", file=sys.stderr)
    sys.exit(1)
'''
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=timeout+10
        )
        if result.returncode == 0 and result.stdout and 'exam-question' in result.stdout:
            return result.stdout, "crawl4ai"
        return None, f"crawl4ai: {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return None, "crawl4ai timeout"
    except Exception as e:
        return None, f"crawl4ai error: {e}"

def fetch_via_urllib(kinz_id, timeout=15):
    """Failover: urllib 직접 접속"""
    import urllib.request, urllib.error
    url = f"https://www.kinz.kr/exam/{kinz_id}"
    try:
        req = urllib.request.Request(url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode('utf-8', errors='replace')
            if 'reCAPTCHA' in html or 'captcha' in html.lower():
                return None, "reCAPTCHA"
            if 'exam-question' in html:
                return html, "urllib"
            return None, f"unexpected response ({len(html)} bytes)"
    except Exception as e:
        return None, f"urllib error: {e}"

def fetch_kinz(kinz_id):
    """Primary crawl4ai → Failover urllib → Failover 캐시 파일"""
    # 1. 캐시된 HTML 파일이 있으면 사용 (agent cron이 MCP로 저장한 것)
    cache_dir = os.path.expanduser("~/.hermes/kinz_cache")
    cache_file = os.path.join(cache_dir, f"{kinz_id}.html")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            html = f.read()
        if 'exam-question' in html:
            print(f"  캐시 파일 사용: {cache_file}")
            return html, "cache"
    
    # 2. crawl4ai MCP 시도
    html, method = fetch_via_crawl4ai(kinz_id)
    if html:
        # 캐시 저장
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w') as f:
            f.write(html)
        return html, method

    # 3. urllib failover
    print(f"  crawl4ai 실패 ({method}), urllib fallback 시도...")
    html, method = fetch_via_urllib(kinz_id)
    if html:
        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w') as f:
            f.write(html)
    return html, method

def upsert_problems(conn, cycle, problems, dry_run=False):
    """DB에 문제 upsert (기존 문제와 비교하여 누락분만 삽입)"""
    cur = conn.cursor()

    # 기존 문제 조회
    cur.execute('''
        SELECT id, "문제", "과목", "보기"
        FROM problems WHERE "회차" = %s
    ''', (cycle,))
    existing = cur.fetchall()

    # 기존 문제 텍스트 → ID 매핑 (60자 prefix로 비교)
    def clean_key(text):
        t = re.sub(r'<img[^>]*>', '', text or '')
        t = re.sub(r'\s+', ' ', t).strip()
        return t[:60]

    existing_keys = {}
    for eid, eq, es, eb in existing:
        key = clean_key(eq)
        existing_keys[key] = eid

    inserted = 0
    skipped = 0
    for p in problems:
        key = clean_key(p["문제"])
        if key in existing_keys:
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY] INSERT: [{p['과목']}] {p['문제'][:50]}...")
            inserted += 1
            continue

        cur.execute('''
            INSERT INTO problems ("id", "회차", "과목", "문제", "보기", "정답", "해설")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (p["kinz_id"], cycle, p["과목"], p["문제"], p["보기"], '', ''))
        inserted += 1

    if not dry_run and inserted > 0:
        conn.commit()

    return inserted, skipped

def check_cycle_status(conn, cycle):
    """회차 상태 확인: (총문제수, 과목별 dict)"""
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM problems WHERE "회차" = %s', (cycle,))
    total = cur.fetchone()[0]
    cur.execute('SELECT "과목", COUNT(*) FROM problems WHERE "회차" = %s GROUP BY "과목"', (cycle,))
    by_subj = dict(cur.fetchall())
    cur.close()
    return total, by_subj

def is_cycle_ok(total, by_subj):
    """100문제/5과목×20 균등 여부"""
    if total != 100:
        return False
    subjects = ['전기기기', '전력공학', '전기자기학', '전기설비기술기준', '회로이론 및 제어공학']
    return all(by_subj.get(s, 0) == 20 for s in subjects)

def main():
    state = load_state()
    state["broken"] = list(CYCLE_TO_KINZ.keys())
    state["fixed"] = []
    state["last_fixed"] = []
    broken = state["broken"]
    if not broken:
        print("✅ 모든 회차 복구 완료!")
        return

    print(f"🔄 복구 대상: {broken}")
    print(f"⏱ 마지막 시도: {state.get('last_attempt', '없음')}")

    # 1. crawl4ai 접속 확인 (6850으로 테스트)
    print("\n--- kinz.kr 접속 확인 ---")
    test_html, method = fetch_kinz(6850)
    if not test_html:
        print(f"⛔ kinz.kr 접속 불가 (method: {method})")
        save_state(state)
        return
    print(f"✅ kinz.kr 접속 성공 ({method})")

    # 2. 깨진 회차 처리
    conn = get_db_conn()
    newly_fixed = []
    still_broken = []

    for cycle in list(broken):
        kinz_id = CYCLE_TO_KINZ.get(cycle)
        if not kinz_id:
            print(f"\n⚠️ {cycle}: kinz ID 없음, 스킵")
            still_broken.append(cycle)
            continue

        print(f"\n--- {cycle} (kinz #{kinz_id}) ---")

        # 현재 상태 확인
        total, by_subj = check_cycle_status(conn, cycle)
        print(f"  현재: {total}문제 {dict(by_subj)}")

        if is_cycle_ok(total, by_subj):
            print(f"  ✅ 이미 정상!")
            newly_fixed.append(cycle)
            continue

        # kinz에서 가져오기
        html, method = fetch_kinz(kinz_id)
        if not html:
            print(f"  ⛔ 가져오기 실패: {method}")
            still_broken.append(cycle)
            # 중간에 막히면 나머지도 스킵
            remaining = [c for c in broken if c not in newly_fixed and c not in still_broken]
            still_broken.extend(remaining)
            break

        # HTML 파싱
        problems = parse_kinz_html(html)
        print(f"  파싱: {len(problems)}문제 ({method})")

        if len(problems) < 80:
            print(f"  ⚠️ 파싱 결과 부족 ({len(problems)}), 스킵")
            still_broken.append(cycle)
            continue

        # DB upsert
        inserted, skipped = upsert_problems(conn, cycle, problems)
        print(f"  삽입: {inserted}개 / 스킵(중복): {skipped}개")

        # fix_cycle.py 실행 (과목 재분류 + 중복 제거)
        print(f"  fix_cycle.py 실행...")
        env = os.environ.copy()
        try:
            result = subprocess.run(
                [sys.executable, FIX_CYCLE, cycle],
                capture_output=True, text=True, timeout=30, env=env
            )
            print(f"  {result.stdout.strip()[:200]}")
        except Exception as e:
            print(f"  fix_cycle 오류: {e}")

        # 최종 확인
        total, by_subj = check_cycle_status(conn, cycle)
        print(f"  결과: {total}문제 {dict(by_subj)}")

        if is_cycle_ok(total, by_subj):
            newly_fixed.append(cycle)
            print(f"  ✅ {cycle} 복구 완료!")
        else:
            still_broken.append(cycle)
            print(f"  ⚠️ {cycle} 아직 불완전 (수동 확인 필요)")

    conn.close()

    # 3. 상태 업데이트
    fixed_all = state.get("fixed", []) + newly_fixed
    state["broken"] = still_broken
    state["fixed"] = list(set(fixed_all))
    if newly_fixed:
        state["last_fixed"] = newly_fixed
        print(f"\n🎉 이번 실행에서 복구: {newly_fixed}")
    save_state(state)

    if not state["broken"]:
        print("\n🎉 ALL DONE! 모든 회차 복구 완료!")
    else:
        print(f"\n⏳ 남은 회차: {state['broken']}")

if __name__ == "__main__":
    main()
