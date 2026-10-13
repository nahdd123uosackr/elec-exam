#!/usr/bin/env python3
"""kinz.kr 시험 페이지의 정적 HTML 에서 구조(지문/보기/이미지)만 추출한다.

정답은 verify_kinz.py 가 이미 data/verified_kinz/<id>.json 에 수집해 두었으므로
나중에 병합한다. (정답 API 는 reCAPTCHA 필요 → 브라우저, 구조는 정적 파싱)

data/verified_kinz_static/<id>.json 으로 저장.
수집 HTML 은 신뢰하지 않고 고정 패턴으로만 파싱한다.
"""
import json
import re
import sys
import time
import html as htmlmod
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "verified_kinz_static"
OUT_DIR.mkdir(parents=True, exist_ok=True)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def text_of(fragment: str) -> str:
    # 이미지는 텍스트 위치에 [이미지: url] 마커로 보존
    fragment = re.sub(r'<img[^>]*src="([^"]+)"[^>]*>', r"[이미지: \1]", fragment)
    # 보기 <li> 안에서 같은 이미지가 두 번 들어가는 경우 중복 제거
    repeated = re.compile(r"(\[이미지: [^\]]+\])(?:\s*\1)+")
    while repeated.search(fragment):
        fragment = repeated.sub(r"\1", fragment)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return htmlmod.unescape(fragment).strip()


def imgs_of(fragment: str) -> list[str]:
    return re.findall(r'<img[^>]*src="([^"]+)"', fragment)


def parse(html: str, exam_id: int) -> dict:
    # 시험일자
    dm = re.search(r"시험일자\s*:\s*(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", html)
    date = f"{dm.group(1)}. {int(dm.group(2))}. {int(dm.group(3))}." if dm else None

    parts = re.split(r'<div class="col-lg exam-question" id="(\d+)">', html)
    questions = []
    for i in range(1, len(parts), 2):
        body = parts[i + 1]
        hm = re.search(r"<h5>(.*?)</h5>", body, re.S)
        if not hm:
            continue
        h5 = hm.group(1)
        num_m = re.match(r"\s*(\d+)\.\s*(.*)", text_of(h5), re.S)
        no = int(num_m.group(1)) if num_m else None
        q = num_m.group(2) if num_m else text_of(h5)
        # h5 바로 뒤 문항 이미지 (첫 ul 전까지)
        head = body[: body.find("<ul")] if "<ul" in body else body
        q_imgs = imgs_of(head)

        # 보기
        um = re.search(r"<ul>(.*?)</ul>", body, re.S)
        choices, choice_imgs = [], []
        if um:
            for lm in re.finditer(r"<li[^>]*>(.*?)</li>", um.group(1), re.S):
                inner = lm.group(1)
                t = text_of(inner)
                ims = imgs_of(inner)
                choice_imgs.extend(ims)
                # text_of 가 이미 [이미지: ...] 마커를 포함하므로 그대로 사용
                choices.append(t)
        # 내비게이션성 보기 제거 ('<' , '>')
        choices = [c for c in choices if c not in ("<", ">", "＜", "＞")]
        questions.append({
            "no": no,
            "문제": q,
            "보기": choices,
            "문항이미지": q_imgs,
            "보기이미지": choice_imgs,
        })
    return {"exam_id": exam_id, "시험일자": date, "count": len(questions), "questions": questions}


def main(targets=None):
    data = json.loads((ROOT / "data" / "problems.json").read_text(encoding="utf-8"))
    urls = sorted({p.get("출처") for p in data if p.get("출처") and "kinz.kr/exam/" in p["출처"]})
    ids = []
    for u in urls:
        m = re.search(r"/exam/(\d+)", u)
        if m and int(m.group(1)) not in ids:
            ids.append(int(m.group(1)))
    if targets:
        ids = [i for i in ids if i in targets]
    print(f"kinz static pages: {len(ids)}", flush=True)
    failed = []
    for eid in ids:
        out = OUT_DIR / f"{eid}.json"
        if out.exists():
            print(f"skip {eid}", flush=True)
            continue
        try:
            r = requests.get(f"https://www.kinz.kr/exam/{eid}", headers={"User-Agent": UA}, timeout=40)
            r.raise_for_status()
            res = parse(r.text, eid)
            out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"ok {eid}: {res['count']}문제, 시험일자 {res['시험일자']}", flush=True)
        except Exception as e:
            print(f"FAIL {eid}: {e}", flush=True)
            failed.append(eid)
        time.sleep(1.0)
    print("failed:", failed, flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main([int(a) for a in sys.argv[1:]] or None))
