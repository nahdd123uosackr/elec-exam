#!/usr/bin/env python3
"""kinz.kr 원본에서 정답/해설/문제/보기/이미지를 재추출하여
data/verified_kinz/<exam_id>.json 으로 저장한다.

기존 extract_kinz_answers.py 의 전략을 그대로 사용:
- 페이지의 모든 "해설" 버튼(.show-answer) 클릭 → /exam/cA 호출
- #correctAnswerN 안의 .correct-answer-number / .correct-answer-text 읽기
- 문제/보기/이미지는 정적 HTML 에서 파싱

주의: 수집한 HTML 은 신뢰하지 않고 특정 패턴으로만 파싱한다.
"""
import json
import re
import sys
import time
import html as htmlmod
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "verified_kinz"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

READ_JS = """
() => {
  const out = [];
  const blocks = document.querySelectorAll('.exam-question');
  blocks.forEach((b, i) => {
    const h5 = b.querySelector('h5');
    const lis = [...b.querySelectorAll('ul li')].map(li => li.textContent.trim());
    const imgs = [...b.querySelectorAll('img')].map(im => im.getAttribute('src'));
    const numEl = document.querySelector('#correctAnswer' + i + ' .correct-answer-number');
    const txtEl = document.querySelector('#correctAnswer' + i + ' .correct-answer-text');
    const pctEl = document.querySelector('#correctAnswer' + i + ' .correct-percent');
    out.push({
      h5: h5 ? h5.textContent.trim() : '',
      choices: lis,
      imgs: imgs,
      answerText: numEl ? numEl.textContent.trim() : '',
      explain: txtEl ? txtEl.textContent.trim() : '',
      percent: pctEl ? pctEl.textContent.trim() : '',
    });
  });
  return out;
}
"""

CLICK_JS = """
(btn) => { btn.click(); return true; }
"""


def parse_block_to_record(raw: dict) -> dict | None:
    h5 = raw.get("h5") or ""
    if not h5:
        return None
    m = re.match(r"^(\d+)\.\s*(.*)$", h5, re.S)
    num = int(m.group(1)) if m else None
    q = htmlmod.unescape(m.group(2) if m else h5).strip()
    ans_raw = raw.get("answerText") or ""
    # '정답 : 3' 또는 '정답: ③' 형태
    am = re.search(r"(\d+)|([①-⑤])", ans_raw)
    answer = None
    if am:
        if am.group(1):
            answer = int(am.group(1))
        else:
            answer = "①②③④⑤".find(am.group(2)) + 1
    return {
        "no": num,
        "문제": q,
        "보기": [htmlmod.unescape(c) for c in raw.get("choices") or []],
        "이미지": raw.get("imgs") or [],
        "정답": answer,
        "해설": (raw.get("explain") or "").strip(),
        "정답률": (raw.get("percent") or "").strip(),
    }


def fetch_exam(page, exam_id: int, click_delay: float = 0.5) -> dict:
    url = f"https://www.kinz.kr/exam/{exam_id}"
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector(".exam-question", timeout=30000)
    # 뷰포트 밖 요소 click 은 실패하므로 페이지 내 JS 로 직접 디스패치
    total = page.evaluate("() => document.querySelectorAll('.show-answer').length")
    for i in range(total):
        page.evaluate(
            """(i) => { const b = document.querySelectorAll('.show-answer')[i];
                         if (b) b.click(); }""",
            i,
        )
        time.sleep(click_delay)
    # 응답 도착 대기
    deadline = time.time() + 45
    while time.time() < deadline:
        filled = page.evaluate(
            """() => [...document.querySelectorAll('[id^=correctAnswer] .correct-answer-number')]
                      .filter(e => e.textContent.trim() !== '').length"""
        )
        if total and filled >= total:
            break
        time.sleep(0.5)
    raws = page.evaluate(READ_JS)
    recs = [r for r in (parse_block_to_record(x) for x in raws) if r]
    return {"exam_id": exam_id, "url": url, "count": len(recs), "questions": recs}


def main(targets: list[int] | None = None):
    data = json.loads((ROOT / "data" / "problems.json").read_text(encoding="utf-8"))
    urls = sorted({p.get("출처") for p in data if p.get("출처") and "kinz.kr/exam/" in p["출처"]})
    ids = []
    for u in urls:
        m = re.search(r"/exam/(\d+)", u)
        if m:
            ids.append(int(m.group(1)))
    if targets:
        ids = [i for i in ids if i in targets]
    print(f"kinz exams to verify: {len(ids)}", flush=True)

    done, failed = 0, []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
        ctx = browser.new_context(user_agent=UA, locale="ko-KR")
        page = ctx.new_page()
        for eid in ids:
            out = OUT_DIR / f"{eid}.json"
            if out.exists():
                print(f"skip {eid} (exists)", flush=True)
                done += 1
                continue
            try:
                res = fetch_exam(page, eid)
                out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
                n_ans = sum(1 for q in res["questions"] if q["정답"])
                print(f"ok {eid}: {res['count']}문제, 정답 {n_ans}개", flush=True)
                done += 1
            except Exception as e:
                print(f"FAIL {eid}: {e}", flush=True)
                failed.append(eid)
            time.sleep(1.5)
        browser.close()
    print(f"done={done} failed={failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]] or None
    sys.exit(main(args))
