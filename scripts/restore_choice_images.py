#!/usr/bin/env python3
"""DB의 '보기' 컬럼에 [이미지] placeholder가 있는 row를 실제 이미지로 교체.

기존 restore_images.py는 '문제' 컬럼의 placeholder만 처리했음.
이 스크립트는 '보기' 컬럼의 [이미지]만 처리 (문제 본문은 이미 처리됨).
"""
import os
import re
import sys
import time
from pathlib import Path
from collections import defaultdict
import pg8000.dbapi as pg

sys.path.insert(0, str(Path(__file__).parent))
from restore_images import (
    fetch_kinz_page, find_image_for_problem, download_image, extract_korean_sequences
)

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


def count_choice_placeholders(choice_text: str) -> int:
    """보기 텍스트의 [이미지] placeholder 개수."""
    return choice_text.count("[이미지]") - choice_text.count("[이미지:")


def main():
    conn = pg.connect(database="elec", **PG)
    conn.autocommit = False
    cur = conn.cursor()

    # 보기에 [이미지]가 있는 kinz.kr row 조회
    print("=== DB 스캔 (보기 이미지 placeholder) ===")
    cur.execute("""
        SELECT id, "문제", "보기", "출처"
        FROM problems
        WHERE "출처" LIKE '%kinz.kr%'
          AND "보기" LIKE '%[이미지]%'
        ORDER BY id
    """)
    rows = cur.fetchall()
    print(f"  보기 이미지 placeholder row: {len(rows)}")

    if not rows:
        cur.close()
        conn.close()
        return

    # 출처 페이지별로 그룹화
    by_exam = defaultdict(list)
    for pid, problem, choices, src in rows:
        m = re.search(r'/exam/(\d+)', src or '')
        if m:
            exam_id = int(m.group(1))
            by_exam[exam_id].append((pid, problem, choices, src))

    print(f"  고유 출처 페이지: {len(by_exam)}")

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

        for pid, problem, choices_text, src in entries:
            choice_count = count_choice_placeholders(choices_text)
            if choice_count == 0:
                continue

            # find_image_for_problem은 본문 + 보기 이미지 모두 추출
            # expected_count = 본문 placeholder + 보기 placeholder
            main_m = re.search(r'\[이미지:\s*(\d+)개?\]', problem)
            main_count = int(main_m.group(1)) if main_m else 0
            # 단, 이미 처리된 본문 placeholder는 [이미지: /images/...]로 들어가 있음
            # 이건 count에서 제외 (이미 URL임)
            # 다시 카운트: problem에 [이미지: / 또는 problem에 [이미지: 숫자만]
            main_count = len(re.findall(r'\[이미지:\s*\d+개?\]', problem))

            total_expected = main_count + choice_count

            img_paths = find_image_for_problem(html, problem, total_expected)
            if not img_paths:
                continue

            # 다운로드
            local_urls = []
            for img_url in img_paths:
                local = download_image(img_url)
                if local:
                    local_urls.append(local)

            if not local_urls:
                continue

            # 본문 placeholder 처리 (있다면)
            new_problem = problem
            url_iter = iter(local_urls)
            if main_count > 0:
                placeholder = f"[이미지: {main_count}개]" if main_count > 1 else "[이미지: 1개]"
                if placeholder in new_problem:
                    replacement = "".join(f"[이미지: {next(url_iter)}]" for _ in range(main_count))
                    new_problem = new_problem.replace(placeholder, replacement, 1)

            # 보기 placeholder 처리
            new_choices = choices_text
            while '[이미지]' in new_choices:
                try:
                    url = next(url_iter)
                except StopIteration:
                    break
                new_choices = new_choices.replace('[이미지]', f'[이미지: {url}]', 1)

            if new_choices != choices_text or new_problem != problem:
                updates.append((new_problem, new_choices, pid))
                print(f"  ✓ {pid}: 보기 {choice_count}개 처리")

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
    for new_q, new_c, pid in updates[:5]:
        print(f"  {pid}")
        print(f"    문제: {new_q[:120]}")
        print(f"    보기: {new_c[:120]}")

    print(f"\n업데이트 중...")
    CHUNK = 200
    try:
        for i in range(0, len(updates), CHUNK):
            chunk = updates[i:i + CHUNK]
            cur.executemany(
                'UPDATE problems SET "문제" = %s, "보기" = %s WHERE id = %s;',
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