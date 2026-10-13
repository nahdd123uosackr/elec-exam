#!/usr/bin/env python3
"""comcbt.com 전기기사 문제 스크래핑"""
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
BASE = "https://www.comcbt.com"
LIST_URL = f"{BASE}/xe/kt"
PROBLEM_URL = f"{BASE}/cbt/problem/{{exam_id}}/{{num}}"

IMG_DIR = Path(__file__).parent.parent / "public" / "images" / "comcbt"
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


def parse_exam_list(html: str) -> list[dict]:
    """Parse /xe/kt listing to get exam post IDs and titles."""
    soup = BeautifulSoup(html, "html.parser")
    exams = []
    # The board list usually has entries in <tr> with links
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        m = re.search(r"/xe/kt/(\d+)", href)
        if not m:
            continue
        title = a.get_text(strip=True)
        if not title or "공지" in title:
            continue
        post_id = int(m.group(1))
        # Extract year/no from title like "전기기사 필기 기출문제 및 CBT 2022년 04월 24일(2회)"
        year_match = re.search(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", title)
        no_match = re.search(r"\((\d+)회\)", title)
        if year_match:
            year = year_match.group(1)
            month = year_match.group(2)
            day = year_match.group(3)
            cycle = f"{year}. {int(month)}. {int(day)}."
            if no_match:
                cycle += f" ({no_match.group(1)}회)"
        else:
            cycle = title
        exams.append({"post_id": post_id, "title": title, "cycle": cycle})
    return exams


def parse_problem_page(html: str, exam_id: int, num: int) -> dict | None:
    """Parse individual problem page."""
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "exam_id": exam_id,
        "num": num,
        "문제": "",
        "보기": "",
        "정답": "",
        "해설": "",
    }

    # Extract title/cycle info from page
    title_tag = soup.select_one("h1")
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        # Extract cycle from title
        year_match = re.search(r"(\d{4})년\s*(\d{2})월\s*(\d{2})일", title_text)
        no_match = re.search(r"\((\d+)회\)", title_text)
        if year_match:
            year = year_match.group(1)
            month = year_match.group(2)
            day = year_match.group(3)
            result["회차"] = f"{year}. {int(month)}. {int(day)}."
            if no_match:
                result["회차"] += f" ({no_match.group(1)}회)"
        # Extract subject
        subj_match = re.search(r"^(.+?)\s*필기", title_text)
        if subj_match:
            result["과목"] = "전기기사"

    # The grid-box contains the problem
    grid = soup.select_one("div.grid-box")
    if not grid:
        return None

    # Extract question number and text
    q_header = grid.select_one("table tr td b")
    if q_header:
        q_text = q_header.get_text(strip=True)
        # Should be like "24. "
        result["문제번호"] = re.search(r"(\d+)", q_text).group(1) if re.search(r"(\d+)", q_text) else str(num)

    # Extract question text (the h2 after the first table)
    h2 = grid.select_one("h2")
    if h2:
        result["문제"] = h2.get_text(strip=True)
    else:
        # Try to get text from the second cell of first row
        first_tables = grid.select("table")
        if len(first_tables) > 1:
            # The question is in the h2 or the second td of the first tr
            first_tr = first_tables[0].select_one("tr")
            if first_tr:
                tds = first_tr.select("td")
                if len(tds) >= 2:
                    result["문제"] = tds[1].get_text(strip=True)

    # Extract choices
    choices = []
    tables = grid.select("table")
    # After the question table, choice tables follow
    for tbl in tables[1:]:
        tr = tbl.select_one("tr")
        if not tr:
            continue
        tds = tr.select("td")
        if len(tds) < 2:
            continue
        choice_num = tds[0].get_text(strip=True).rstrip(". ")
        choice_text = tds[1].get_text(strip=True)
        if choice_text and choice_text not in ("정답", "정답률", "문제 해설"):
            choices.append(f"{choice_num}. {choice_text}")
        # Stop when we hit the answer section
        if "정답" in choice_text and len(choices) > 0:
            break

    result["보기"] = "\n".join(choices) if choices else ""

    # Extract answer - it's in a div with id like jungdabcolor24
    answer_div = grid.select_one("div[id^='jungdabcolor']")
    if answer_div:
        ans = answer_div.get_text(strip=True)
        # Convert 1,2,3,4 to circled numbers
        circled = {"1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤"}
        result["정답"] = circled.get(ans, ans)
    else:
        # Try hidden input or other patterns
        m = re.search(r"정답\s*:\s*\[?\]?\s*<[^>]*>(\d+)", str(grid))
        if m:
            circled = {"1": "①", "2": "②", "3": "③", "4": "④", "5": "⑤"}
            result["정답"] = circled.get(m.group(1), m.group(1))

    # Extract explanation
    font_blue = grid.select_one("font[color=blue]")
    if font_blue:
        expl = font_blue.get_text(separator="\n", strip=True)
        # Remove "<문제 해설>" prefix
        expl = re.sub(r"^<문제 해설>\s*", "", expl).strip()
        # Remove [해설작성자 : ...]
        expl = re.sub(r"\[해설작성자\s*:\s*[^\]]+\]", "", expl).strip()
        result["해설"] = expl

    # Extract images from question and choices
    images = []
    for img in grid.select("img"):
        src = img.get("src", "")
        if src:
            if not src.startswith("http"):
                src = BASE + src
            images.append(src)

    if images:
        result["원본이미지"] = images

    return result


def download_image(url: str) -> str | None:
    """Download image and return local path."""
    fname = url.split("/")[-1]
    if not fname or "." not in fname:
        # Generate hash-based filename
        fname = hashlib.md5(url.encode()).hexdigest() + ".img"
    dest = IMG_DIR / fname
    if dest.exists() and dest.stat().st_size > 0:
        return f"/images/comcbt/{fname}"
    try:
        r = session.get(url, timeout=30)
        if r.status_code == 200 and len(r.content) > 100:
            dest.write_bytes(r.content)
            return f"/images/comcbt/{fname}"
    except Exception as e:
        print(f"    img download fail: {url} -> {e}")
    return None


def process_exam(exam: dict, max_problems: int = 100, start: int = 1) -> list[dict]:
    """Scrape all problems from an exam."""
    problems = []
    exam_id = exam["post_id"]
    print(f"\n=== Exam {exam_id}: {exam['title']} ===")
    
    for num in range(start, max_problems + 1):
        url = PROBLEM_URL.format(exam_id=exam_id, num=num)
        html = fetch(url)
        if not html:
            print(f"  [{num}] fetch failed, stopping")
            break
        
        prob = parse_problem_page(html, exam_id, num)
        if not prob or not prob["문제"]:
            print(f"  [{num}] parse failed, stopping")
            break
        
        # Add metadata
        prob["출처"] = url
        prob["과목"] = exam.get("과목", "전기기사")
        if "회차" not in prob:
            prob["회차"] = exam.get("cycle", "")
        prob["id"] = hashlib.md5(f"comcbt-{exam_id}-{num}".encode()).hexdigest()[:32]
        
        # Download images
        if prob.get("원본이미지"):
            local_imgs = []
            for img_url in prob["원본이미지"]:
                local = download_image(img_url)
                if local:
                    local_imgs.append(local)
            if local_imgs:
                # Embed image URLs in problem text using [이미지: URL] format
                q = prob["문제"]
                for i, local_url in enumerate(local_imgs):
                    placeholder = f"[이미지: {local_url}]"
                    if i == 0:
                        q = f"{q}\n\n{placeholder}"
                    else:
                        q = f"{q} {placeholder}"
                prob["문제"] = q
                # Clean up raw image list
                del prob["원본이미지"]
        
        problems.append(prob)
        if num % 10 == 0:
            print(f"  [{num}] problems collected: {len(problems)}")
        time.sleep(0.3)  # Be polite
    
    print(f"  Total: {len(problems)} problems")
    return problems


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--exam-id", type=int, help="Specific exam post ID")
    parser.add_argument("--max-problems", type=int, default=100)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--output", default="data/problems_comcbt.json")
    args = parser.parse_args()

    if args.exam_id:
        exams = [{"post_id": args.exam_id, "title": f"Exam {args.exam_id}", "cycle": "", "과목": "전기기사"}]
    else:
        print("Fetching exam list...")
        html = fetch(LIST_URL)
        if not html:
            print("Failed to fetch exam list")
            sys.exit(1)
        exams = parse_exam_list(html)
        print(f"Found {len(exams)} exams")
        # Show first few
        for e in exams[:5]:
            print(f"  {e['post_id']}: {e['title']}")

    all_problems = []
    for exam in exams:
        probs = process_exam(exam, args.max_problems, args.start)
        all_problems.extend(probs)

    print(f"\nTotal problems: {len(all_problems)}")
    
    # Save
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_problems, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
