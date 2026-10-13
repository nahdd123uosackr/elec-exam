#!/usr/bin/env python3
"""cbtbank.kr 원본 페이지에서 문제/보기/정답을 정적으로 추출한다.

구조:
  <p class="exam-title"><span class="exam-number">N</span>. 문항</p>
  <ol class="circlednumbers" correct="1"><li class="correct">...</li>...</ol>

data/verified_cbtbank/<exam_id>.json 으로 저장.
수집 HTML 은 신뢰하지 않고 위 패턴으로만 파싱한다.
"""
import json
import re
import sys
import time
import html as htmlmod
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "verified_cbtbank"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def strip_tags(s: str) -> str:
    s = re.sub(r"<img[^>]*src=\"([^\"]+)\"[^>]*>", r"[이미지: \1]", s)
    s = re.sub(r"<[^>]+>", "", s)
    return htmlmod.unescape(s).strip()


def parse(html: str, exam_id: str) -> dict:
    recs = []
    # 문항 블록: exam-title ~ circlednumbers ol
    for m in re.finditer(
        r'<p class="exam-title">(?P<title>.*?)</p>.*?'
        r'<ol class="circlednumbers"(?P<attrs>[^>]*)>(?P<lis>.*?)</ol>',
        html, re.S,
    ):
        title = strip_tags(m.group("title"))
        tm = re.match(r"^(\d+)\.\s*(.*)$", title, re.S)
        no = int(tm.group(1)) if tm else None
        q = tm.group(2) if tm else title

        attrs = m.group("attrs")
        am = re.search(r'correct="(\d+)"', attrs)
        answer = int(am.group(1)) if am else None

        lis = re.findall(r"<li[^>]*>(.*?)</li>", m.group("lis"), re.S)
        choices = [strip_tags(x) for x in lis]
        if answer is None:
            for i, li in enumerate(re.finditer(r'<li([^>]*)>', m.group("lis")), start=1):
                if re.search(r'class="[^"]*correct', li.group(1)):
                    answer = i
                    break

        pct = None
        recs.append({"no": no, "문제": q, "보기": choices, "정답": answer})
    return {"exam_id": exam_id, "count": len(recs), "questions": recs}


def main(targets=None):
    data = json.loads((ROOT / "data" / "problems.json").read_text(encoding="utf-8"))
    urls = sorted({p.get("출처") for p in data if p.get("출처") and "cbtbank.kr/exam/" in p["출처"]})
    ids = [u.rsplit("/", 1)[-1] for u in urls]
    if targets:
        ids = [i for i in ids if i in targets]
    print(f"cbtbank exams: {ids}", flush=True)
    failed = []
    for eid in ids:
        out = OUT_DIR / f"{eid}.json"
        if out.exists():
            print(f"skip {eid}", flush=True)
            continue
        try:
            r = requests.get(f"https://cbtbank.kr/exam/{eid}", headers={"User-Agent": UA}, timeout=40)
            r.raise_for_status()
            res = parse(r.text, eid)
            n_ans = sum(1 for q in res["questions"] if q["정답"])
            out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"ok {eid}: {res['count']}문제, 정답 {n_ans}", flush=True)
        except Exception as e:
            print(f"FAIL {eid}: {e}", flush=True)
            failed.append(eid)
        time.sleep(1.0)
    print("failed:", failed, flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
