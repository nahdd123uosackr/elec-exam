#!/usr/bin/env python3
"""kinz.kr 전기기사 문제 스크래핑: 문제, 보기, 이미지 포함"""
import re
import os
import sys
import time
import json
import hashlib
import requests
from pathlib import Path
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
BASE = "https://www.kinz.kr"

# 전기기사 exam ID 목록 (최신순)
EXAMS = {
    # 2022
    257755: "2021. 3. 7.",
    261346: "2021. 5. 15.",
    265523: "2021. 8. 14.",
    # 2020
    240719: "2020. 6. 6.",
    244518: "2020. 8. 22.",
    248631: "2020. 9. 26.",
    # 2019
    220540: "2019. 3. 3.",
    224496: "2019. 4. 27.",
    228734: "2019. 8. 4.",
    # 2018
    200614: "2018. 3. 4.",
    204716: "2018. 4. 28.",
    209085: "2018. 8. 19.",
    # 2017
    184242: "2017. 3. 5.",
    188291: "2017. 5. 7.",
    192645: "2017. 8. 26.",
    # 2016
    168789: "2016. 3. 6.",
    172516: "2016. 5. 8.",
    176503: "2016. 8. 21.",
    # 2015
    152849: "2015. 3. 8.",
    156652: "2015. 5. 31.",
    160509: "2015. 8. 16.",
    # 2014
    136998: "2014. 3. 2.",
    140870: "2014. 5. 25.",
    145041: "2014. 8. 17.",
    # 2013
    121456: "2013. 3. 10.",
    125310: "2013. 6. 2.",
    129171: "2013. 8. 18.",
    # 2012
    105760: "2012. 3. 4.",
    109652: "2012. 5. 20.",
    113521: "2012. 8. 26.",
    # 2011
    89023: "2011. 3. 20.",
    92806: "2011. 6. 12.",
    96489: "2011. 8. 21.",
    # 2010
    73041: "2010. 5. 9.",
    77000: "2010. 7. 25.",
    # 2003-2009 need to be added
}

IMG_DIR = Path(__file__).parent.parent / "public" / "images" / "kinz"
IMG_DIR.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": UA})


def fetch(url: str) -> str | None:
    try:
        r = session.get(url, timeout=30)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"  fetch error {url}: {e}")
    return None


def parse_exam_page(html: str, exam_id: int, cycle: str) -> list[dict]:
    """Parse kinz.kr exam page to extract all problems."""
    soup = BeautifulSoup(html, "html.parser")
    problems = []

    # Find subject order from the page
    content = soup.find('div', class_='content-template')
    if not content:
        content = soup.find('main') or soup

    subject_order = []
    for text_node in content.find_all(string=True):
        text = text_node.strip()
        m = re.match(r'(\d)과목\s*:\s*(.+)', text)
        if m:
            subject_order.append((m.group(1), m.group(2).strip()))

    # Find all question divs
    for q_div in content.find_all('div', class_='exam-question'):
        h5 = q_div.find('h5')
        if not h5:
            continue

        pnum_text = h5.get_text(strip=True)
        pnum_match = re.match(r'(\d+)\.\s*(.*)', pnum_text)
        if not pnum_match:
            continue

        num = int(pnum_match.group(1))
        question_text = pnum_match.group(2)

        # Get choices
        ul = q_div.find('ul')
        choices = []
        if ul:
            for li in ul.find_all('li', recursive=False):
                choices.append(li.get_text(strip=True))

        # Get images
        imgs = []
        for img in q_div.find_all('img'):
            src = img.get('src', '')
            if src.startswith('/'):
                src = BASE + src
            if src:
                imgs.append(src)

        # Determine subject
        subj_idx = (num - 1) // 20
        subject = subject_order[subj_idx][1] if subj_idx < len(subject_order) else None

        problems.append({
            "id": hashlib.md5(f"kinz/{exam_id}/{num}".encode()).hexdigest()[:32],
            "문제": question_text,
            "보기": "\n".join(choices) if choices else "",
            "정답": "",  # Will be filled later
            "해설": "",
            "사용공식": "",
            "출처": f"https://www.kinz.kr/exam/{exam_id}",
            "회차": cycle,
            "과목": subject,
            "난이도": "",
            "중복출제": "",
            "images": imgs,
        })

    return problems


def download_image(url: str) -> str | None:
    """Download image and return local path."""
    fname = url.split("/")[-1]
    if not fname or "." not in fname:
        fname = hashlib.md5(url.encode()).hexdigest() + ".img"
    dest = IMG_DIR / fname
    if dest.exists() and dest.stat().st_size > 0:
        return f"/images/kinz/{fname}"
    try:
        r = session.get(url, timeout=30)
        if r.status_code == 200 and len(r.content) > 100:
            dest.write_bytes(r.content)
            return f"/images/kinz/{fname}"
    except Exception as e:
        print(f"    img download fail: {url} -> {e}")
    return None


def process_exam(exam_id: int, cycle: str, max_problems: int = 100) -> list[dict]:
    """Scrape all problems from an exam."""
    url = f"{BASE}/exam/{exam_id}"
    print(f"\n=== Exam {exam_id}: {cycle} ===")

    html = fetch(url)
    if not html:
        print(f"  Failed to fetch")
        return []

    problems = parse_exam_page(html, exam_id, cycle)
    print(f"  Parsed {len(problems)} problems")

    # Download images
    for prob in problems:
        local_imgs = []
        for img_url in prob.get("images", []):
            local = download_image(img_url)
            if local:
                local_imgs.append(local)
        if local_imgs:
            # Embed image URLs in problem text
            q = prob["문제"]
            for i, local_url in enumerate(local_imgs):
                if i == 0:
                    q = f"{q}\n\n[이미지: {local_url}]"
                else:
                    q = f"{q} [이미지: {local_url}]"
            prob["문제"] = q
            # Also add to choices if they have images
            # (images in choices are already in the choice text from kinz)
        prob.pop("images", None)

    return problems


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--exam-id", type=int, help="Specific exam ID")
    parser.add_argument("--max-exams", type=int, default=0, help="Max exams to process (0=all)")
    parser.add_argument("--output", default="data/problems_kinz.json")
    args = parser.parse_args()

    if args.exam_id:
        exams_to_process = {args.exam_id: EXAMS.get(args.exam_id, f"Exam {args.exam_id}")}
    else:
        exams_to_process = EXAMS.copy()

    if args.max_exams > 0:
        items = list(exams_to_process.items())[:args.max_exams]
        exams_to_process = dict(items)

    all_problems = []
    for exam_id, cycle in exams_to_process.items():
        probs = process_exam(exam_id, cycle)
        all_problems.extend(probs)
        time.sleep(0.5)

    print(f"\nTotal problems: {len(all_problems)}")

    # Save
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_problems, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
