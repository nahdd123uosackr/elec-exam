#!/usr/bin/env python3
"""문제의 [이미지: N개] placeholder를 실제 이미지 URL로 교체합니다.

지원 출처:
- kinz.kr: https://www.kinz.kr/exam/<id> - /data/exam/<dir>/kt<date>m<num><idx>-<hash>.<gif|jpg>

전략:
1. DB에서 출처 URL이 kinz.kr이고, 문제에 [이미지: N개]가 있는 row 조회
2. 출처 페이지 fetch, 문제 텍스트(예: '파고율')로 위치 검색
3. 주변 <img src> 추출하여 우리 public/images/kinz/에 다운로드
4. DB 문제의 [이미지: 1개]를 [이미지: /images/kinz/<파일>]로 교체
"""
import os
import re
import sys
import time
import requests
from pathlib import Path
from collections import defaultdict
import pg8000.dbapi as pg

_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

PG = dict(
    host=os.environ["PG_HOST"],
    port=int(os.environ.get("PG_PORT", "5432")),
    user=os.environ["PG_USER"],
    password=os.environ["PG_PASSWORD"],
)

IMG_DIR = Path(__file__).parent.parent / "public" / "images" / "kinz"
IMG_DIR.mkdir(parents=True, exist_ok=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def fetch_kinz_page(exam_id: int) -> str | None:
    try:
        r = requests.get(f"https://www.kinz.kr/exam/{exam_id}", headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200:
            return None
        return r.text
    except Exception:
        return None


def extract_korean_sequences(text: str, min_len: int = 5) -> list[str]:
    """한글 시퀀스 추출 (공백/특수문자 무시).

    Returns:
        가능한 한글 부분 시퀀스 (min_len 이상, 길이 내림차순).
    """
    # ASCII 아닌 모든 글자(한글+한자 등)를 보존하면서 ASCII는 공백으로 치환
    cleaned = []
    for ch in text:
        if ord(ch) < 128 and not ch.isspace():
            cleaned.append(' ')
        else:
            cleaned.append(ch)
    cleaned_text = ''.join(cleaned)
    # 공백으로 split하여 한글 시퀀스 추출
    seqs = [s for s in cleaned_text.split() if len(s) >= min_len]
    # 너무 긴 건 30자로 제한
    seqs = [s[:30] for s in seqs]
    return seqs


def find_image_for_problem(html: str, problem_text: str, expected_count: int = 1) -> list[str]:
    """문제 본문 영역 안의 이미지 src를 추출.

    kinz.kr 페이지 구조:
    <div class="col-lg exam-question" id="<qid>">
      <h5>N. 문제 본문</h5>
      <img src="/data/exam/...">
      <ul><li value="1">① ...</li>...
    </div>
    """
    # 한글 시퀀스 추출 (공백/특수문자 무시)
    anchors = extract_korean_sequences(problem_text, min_len=4)
    # 영문 fallback: 영문 알파벳 연속 5자 이상
    if not anchors:
        cur = []
        for ch in problem_text:
            if ch.isascii() and ch.isalpha():
                cur.append(ch)
            else:
                if len(cur) >= 5:
                    anchors.append(''.join(cur))
                cur = []
        if len(cur) >= 5:
            anchors.append(''.join(cur))

    if not anchors:
        return []

    anchors.sort(key=len, reverse=True)

    pos = -1
    for a in anchors:
        pos = html.find(a)
        if pos >= 0:
            break

    if pos < 0:
        return []

    # 'exam-question' div 영역 찾기
    div_start = html.rfind('exam-question', 0, pos)
    if div_start < 0:
        div_start = max(0, pos - 500)

    next_div = html.find('exam-question', pos + 100)
    if next_div < 0:
        next_div = pos + 10000
    region = html[div_start:next_div]

    # 보기 이미지 제외: <ul> 위치 찾고 그 전까지만
    ul_pos = region.find('<ul>')
    if ul_pos > 0:
        region = region[:ul_pos]

    imgs = re.findall(r'src="(/data/exam/[^"]+\.(?:gif|jpg|jpeg|png|webp))"', region)

    seen = []
    for src in imgs:
        if src not in seen:
            seen.append(src)
        if len(seen) >= expected_count:
            break
    return seen


def download_image(relative_url: str) -> str | None:
    """kinz.kr 이미지 다운로드, 우리 public/images/kinz/에 저장.

    Returns: 우리 서버에서 사용할 경로 (/images/kinz/...) 또는 None
    """
    # 절대 URL
    abs_url = f"https://www.kinz.kr{relative_url}"
    # 파일명: 경로 마지막
    filename = relative_url.split("/")[-1]
    # 이미 존재하면 스킵
    dest = IMG_DIR / filename
    if dest.exists() and dest.stat().st_size > 0:
        return f"/images/kinz/{filename}"

    try:
        r = requests.get(abs_url, headers={"User-Agent": UA}, timeout=30)
        if r.status_code != 200 or len(r.content) < 100:
            return None
        dest.write_bytes(r.content)
        return f"/images/kinz/{filename}"
    except Exception:
        return None


def main():
    conn = pg.connect(database="elec", **PG)
    conn.autocommit = False
    cur = conn.cursor()

    # 이미지 placeholder가 있는 kinz.kr row 조회
    print("=== DB 스캔 ===")
    cur.execute("""
        SELECT id, "문제", "출처"
        FROM problems
        WHERE "출처" LIKE '%kinz.kr%'
          AND "문제" LIKE '%[이미지:%'
        ORDER BY id
    """)
    rows = cur.fetchall()
    print(f"  kinz.kr 이미지 placeholder row: {len(rows)}")

    if not rows:
        cur.close()
        conn.close()
        return

    # 출처 ID별로 그룹화 (한 번의 페이지 fetch로 여러 문제 처리)
    by_exam = defaultdict(list)
    for pid, problem, src in rows:
        m = re.search(r'/exam/(\d+)', src or '')
        if m:
            exam_id = int(m.group(1))
            by_exam[exam_id].append((pid, problem, src))

    print(f"  고유 출처 페이지: {len(by_exam)}")

    # 각 페이지 처리
    updates = []
    processed_pages = 0
    for exam_id, entries in sorted(by_exam.items()):
        if processed_pages < 5 or processed_pages % 20 == 0:
            print(f"\n[{exam_id}] {len(entries)}개 row 처리...", flush=True)
        html = fetch_kinz_page(exam_id)
        if not html:
            if processed_pages < 5 or processed_pages % 20 == 0:
                print(f"  ✗ 페이지 fetch 실패", flush=True)
            continue
        processed_pages += 1

        for pid, problem, src in entries:
            # placeholder에서 이미지 개수 추출
            m = re.search(r'\[이미지:\s*(\d+)개?\]', problem)
            expected = int(m.group(1)) if m else 1

            # 이미지 찾기
            img_paths = find_image_for_problem(html, problem, expected)
            if not img_paths:
                # 못 찾은 경우 - 다음으로
                continue

            # 다운로드
            local_urls = []
            for img_url in img_paths:
                local = download_image(img_url)
                if local:
                    local_urls.append(local)

            if not local_urls:
                continue

            # 문제 텍스트에서 placeholder를 실제 URL로 교체
            placeholder = f"[이미지: {expected}개]" if expected > 1 else "[이미지: 1개]"
            if placeholder in problem:
                replacement = "".join(f"[이미지: {url}]" for url in local_urls)
                new_problem = problem.replace(placeholder, replacement)
                updates.append((new_problem, pid))
                print(f"  ✓ {pid}: {len(local_urls)}개 이미지 복원")

        # 페이지 10개마다 진행 상황
        if processed_pages % 5 == 0:
            print(f"  -- 진행: {len(updates)}개 업데이트 대기 중 --")

        # rate limit
        time.sleep(0.5)

    print(f"\n=== 총 {len(updates)}개 row 업데이트 ===")
    if not updates:
        cur.close()
        conn.close()
        return

    # 미리보기
    print("\n=== 미리보기 (5개) ===")
    for new_q, pid in updates[:5]:
        print(f"  {pid}")
        print(f"    {new_q[:200]}...")

    print(f"\n업데이트 중...")
    CHUNK = 200
    try:
        for i in range(0, len(updates), CHUNK):
            chunk = updates[i:i + CHUNK]
            cur.executemany(
                'UPDATE problems SET "문제" = %s WHERE id = %s;',
                chunk,
            )
        conn.commit()
        print(f"  ✓ {len(updates)} updated")
    except Exception as e:
        conn.rollback()
        print(f"  ✗ error: {e}")
        raise

    cur.close()
    conn.close()
    print("done")


if __name__ == "__main__":
    main()
