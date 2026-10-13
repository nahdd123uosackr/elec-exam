#!/usr/bin/env python3
"""원본 수집본(verified_kinz*, verified_cbtbank)과 data/problems.json 를 대조한다.

- 정답/보기/지문 불일치 통계
- 미매칭(중복/절단) 목록
python3 scripts/compare_sources.py
"""
import difflib
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(t):
    return re.sub(r"\s+", "", t or "")


def stripmark(s):
    s = norm(s)
    while True:
        s2 = re.sub(r"^[①-⑤]", "", s)
        s2 = re.sub(r"^\d+\.", "", s2)
        s2 = re.sub(r"^\(\d+\)", "", s2)
        if s2 == s:
            return s2
        s = s2


def normc(c):
    c = stripmark(c)
    return re.sub(r"\[이미지:[^\]]*\]", "[IMG]", c)


def to_num(a):
    a = (a or "").strip()
    if a in "①②③④⑤":
        return "①②③④⑤".find(a) + 1
    if re.fullmatch(r"\d", a):
        return int(a)
    if re.fullmatch(r"\d(,\s*\d)+", a):
        return "multi"
    return None


def load_sources():
    """(kind, id) -> {questions, date, structure?}"""
    src = {}
    for f in glob.glob(str(ROOT / "data/verified_kinz/*.json")):
        j = json.load(open(f, encoding="utf-8"))
        entry = {"kind": "kinz", "questions": j["questions"]}
        sf = ROOT / "data/verified_kinz_static" / Path(f).name
        if sf.exists():
            st = json.load(open(sf, encoding="utf-8"))
            entry["static"] = st
            entry["date"] = st.get("시험일자")
        src[("kinz", str(j["exam_id"]))] = entry
    for f in glob.glob(str(ROOT / "data/verified_cbtbank/*.json")):
        j = json.load(open(f, encoding="utf-8"))
        src[("cbt", j["exam_id"])] = {"kind": "cbt", "questions": j["questions"]}
    return src


def src_key(p):
    s = p.get("출처") or ""
    m = re.search(r"/exam/([\w]+)", s)
    if not m:
        return None
    if "kinz" in s:
        return ("kinz", m.group(1))
    if "cbtbank" in s:
        return ("cbt", m.group(1))
    return None


def best_match(p, questions):
    t = norm(p["문제"])
    if not questions:
        return None, 0.0
    scored = sorted(
        ((difflib.SequenceMatcher(None, t, norm(q["문제"])).ratio(), i) for i, q in enumerate(questions)),
        reverse=True,
    )
    r, i = scored[0]
    return questions[i], r


def main():
    data = json.loads((ROOT / "data/problems.json").read_text(encoding="utf-8"))
    srcs = load_sources()
    stats = Counter()
    per_exam = defaultdict(Counter)
    ans_rows, unmatched, choice_rows = [], [], []

    for p in data:
        k = src_key(p)
        if not k or k not in srcs:
            stats["출처없음"] += 1
            continue
        q, r = best_match(p, srcs[k]["questions"])
        if r < 0.6:
            stats["미매칭"] += 1
            unmatched.append(p)
            continue
        stats["매칭"] += 1
        eid = k[1]
        if to_num(p["정답"]) != q["정답"]:
            stats["정답불일치"] += 1
            per_exam[eid]["정답"] += 1
            ans_rows.append((p, q))
        ours = [
            normc(l)
            for l in (p.get("보기") or "").split("\n")
            if norm(l) and not re.fullmatch(r"[.<>·…\-—*=~]+", norm(l))
        ]
        theirs = [normc(c) for c in q["보기"] if normc(c) not in ("<", ">", "＜", "＞")]
        if ours != theirs:
            stats["보기불일치"] += 1
            per_exam[eid]["보기"] += 1
            choice_rows.append((p, ours, theirs))

    print("STATS:", dict(stats))
    print("\n회차별(출처 id) 정답불일치:")
    for eid, c in sorted(per_exam.items(), key=lambda kv: -kv[1]["정답"]):
        print(f"  {eid}: 정답 {c['정답']}, 보기 {c['보기']}")
    print(f"\n미매칭 {len(unmatched)}건 예시:")
    for p in unmatched[:12]:
        print(f"  [{p['회차']}] {norm(p['문제'])[:70]}")
    print(f"\n보기불일치 {len(choice_rows)}건 예시:")
    for p, o, s in choice_rows[:8]:
        print(f"  [{p['회차']}] {norm(p['문제'])[:50]}")
        print(f"    ours: {o}")
        print(f"    src : {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
