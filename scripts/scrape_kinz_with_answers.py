#!/usr/bin/env python3
"""kinz.kr 전기기사 문제 + 정답 스크래핑 (Playwright 사용, 브라우저 재사용)"""
import re
import os
import sys
import time
import json
import hashlib
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
BASE = "https://www.kinz.kr"

EXAMS = {
    351693: "2022. 4. 24.",
    337511: "2022. 3. 5.",
    294393: "2021. 8. 14.",
    269009: "2021. 5. 15.",
    257755: "2021. 3. 7.",
    217966: "2020. 9. 26.",
    172940: "2020. 8. 22.",
    109511: "2020. 6. 6.",
    6803: "2019. 8. 4.",
    6804: "2019. 4. 27.",
    6805: "2019. 3. 3.",
    6806: "2018. 8. 19.",
    6807: "2018. 4. 28.",
    6808: "2018. 3. 4.",
    6809: "2017. 8. 26.",
    6810: "2017. 5. 7.",
    6811: "2017. 3. 5.",
    6812: "2016. 8. 21.",
    6813: "2016. 5. 8.",
    6814: "2016. 3. 6.",
    6815: "2015. 8. 16.",
    6816: "2015. 5. 31.",
    6817: "2015. 3. 8.",
    6818: "2014. 8. 17.",
    6819: "2014. 5. 25.",
    6820: "2014. 3. 2.",
    6821: "2013. 8. 18.",
    6822: "2013. 6. 2.",
    6823: "2013. 3. 10.",
    6824: "2012. 8. 26.",
    6825: "2012. 5. 20.",
    6826: "2012. 3. 4.",
    6827: "2011. 8. 21.",
    6828: "2011. 6. 12.",
    6829: "2011. 3. 20.",
    6830: "2010. 7. 25.",
    6831: "2010. 5. 9.",
    6832: "2010. 3. 7.",
    6833: "2009. 7. 26.",
    6834: "2009. 5. 10.",
    6835: "2009. 3. 1.",
    6836: "2008. 7. 27.",
    6837: "2008. 5. 11.",
    6838: "2008. 3. 2.",
    6839: "2007. 8. 5.",
    6840: "2007. 5. 13.",
    6841: "2007. 3. 4.",
    6842: "2006. 8. 6.",
    6843: "2006. 5. 14.",
    6844: "2006. 3. 5.",
    6845: "2005. 8. 7.",
    6846: "2005. 5. 29.",
    6847: "2005. 3. 6.",
    6848: "2004. 8. 8.",
    6849: "2004. 5. 23.",
    6850: "2004. 3. 7.",
    6851: "2003. 8. 10.",
    6852: "2003. 5. 25.",
    6853: "2003. 3. 16.",
}

IMG_DIR = Path(__file__).parent.parent / "public" / "images" / "kinz"
IMG_DIR.mkdir(parents=True, exist_ok=True)


def download_image(session: requests.Session, url: str) -> str | None:
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


def scrape_exam_with_answers(page, exam_id: int, cycle: str) -> list[dict]:
    """Scrape exam page with Playwright to get answers."""
    print(f"\n=== Exam {exam_id}: {cycle} ===")
    problems = []

    page.goto(f"{BASE}/exam/{exam_id}", timeout=30000)
    time.sleep(3)

    # Click show-answer buttons one by one with delay
    buttons = page.query_selector_all('.show-answer')
    print(f"  Found {len(buttons)} show-answer buttons")
    for i, btn in enumerate(buttons):
        try:
            btn.click()
            time.sleep(0.3)
        except Exception:
            pass

    time.sleep(2)

    # Read all answers
    answers_json = page.evaluate('''(() => {
        const results = [];
        for (let i = 0; i < 100; i++) {
            const numEl = document.querySelector('#correctAnswer' + i + ' .correct-answer-number');
            const textEl = document.querySelector('#correctAnswer' + i + ' .correct-answer-text');
            if (numEl) {
                const numText = numEl.textContent.replace(/[^0-9]/g, '');
                const num = numText ? parseInt(numText) : 0;
                const text = textEl ? textEl.textContent.trim() : '';
                results.push({num: num || 0, text: text.substring(0, 100)});
            }
        }
        return JSON.stringify(results);
    })''')

    answers = json.loads(answers_json)
    with_answers = sum(1 for a in answers if a['num'] > 0)
    print(f"  Answers found: {with_answers}/{len(answers)}")

    # Parse questions from the page
    html = page.content()

    # Parse with BeautifulSoup
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Find subject order
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
    q_idx = 0
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

        # Get answer
        answer_num = ""
        answer_text = ""
        if q_idx < len(answers):
            answer_num = answers[q_idx].get("num", "")
            answer_text = answers[q_idx].get("text", "")

        # Convert answer number to circled number
        circled_map = {1: "①", 2: "②", 3: "③", 4: "④", 5: "⑤"}
        if answer_num and answer_num in circled_map:
            answer_num = circled_map[answer_num]

        prob = {
            "id": hashlib.md5(f"kinz/{exam_id}/{num}".encode()).hexdigest()[:32],
            "문제": question_text,
            "보기": "\n".join(choices) if choices else "",
            "정답": str(answer_num) if answer_num else "",
            "해설": answer_text if answer_text else "",
            "사용공식": "",
            "출처": f"https://www.kinz.kr/exam/{exam_id}",
            "회차": cycle,
            "과목": subject,
            "난이도": "",
            "중복출제": "",
            "images": imgs,
        }
        problems.append(prob)
        q_idx += 1

    return problems


def download_images_for_exam(problems: list[dict], session: requests.Session):
    """Download all images for an exam."""
    for prob in problems:
        local_imgs = []
        for img_url in prob.get("images", []):
            local = download_image(session, img_url)
            if local:
                local_imgs.append(local)
        if local_imgs:
            q = prob["문제"]
            for i, local_url in enumerate(local_imgs):
                if i == 0:
                    q = f"{q}\n\n[이미지: {local_url}]"
                else:
                    q = f"{q} [이미지: {local_url}]"
            prob["문제"] = q
        prob.pop("images", None)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--exam-id", type=int, help="Specific exam ID")
    parser.add_argument("--max-exams", type=int, default=0, help="Max exams to process (0=all)")
    parser.add_argument("--output", default="data/problems_kinz_full.json")
    args = parser.parse_args()

    if args.exam_id:
        exams_to_process = {args.exam_id: EXAMS.get(args.exam_id, f"Exam {args.exam_id}")}
    else:
        exams_to_process = EXAMS.copy()

    if args.max_exams > 0:
        items = list(exams_to_process.items())[:args.max_exams]
        exams_to_process = dict(items)

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    all_problems = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)

        for exam_id, cycle in exams_to_process.items():
            try:
                probs = scrape_exam_with_answers(page, exam_id, cycle)
                if probs:
                    download_images_for_exam(probs, session)
                    all_problems.extend(probs)
            except Exception as e:
                print(f"  Error processing exam {exam_id}: {e}")
            time.sleep(1)

        browser.close()

    print(f"\nTotal problems: {len(all_problems)}")

    # Save
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_problems, f, ensure_ascii=False, indent=2)
    print(f"Saved to {out_path}")


if __name__ == "__main__":
    main()
