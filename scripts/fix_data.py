#!/usr/bin/env python3
"""data/problems.json 을 원본 수집본과 대조해 일괄 수정한다.

수정 대상:
1. 정답 — 원본(kinz/cbtbank) 값을 우선. 단, 문제 텍스트에 "가답안" 선언이 있는
   오류 공지 문제는 기존 복수정답 유지.
2. 문제/보기 — 원본 문항·보기로 교체. 이미지는 로컬 public/images/ 로 매핑해
   [이미지: /images/...] 마커 삽입 (미보유분은 원본 URL 유지).
3. 회차 — 원본 시험일자(또는 cbtbank exam id)로 YYYY. M. D. 정규화.
4. HTML 엔티티(&quot; 등) 디코드.
5. 테스트 문제 행 삭제.
6. 중복 행 제거 — 같은 원본 문항에 매칭된 여러 행은 유사도가 높은 행 1개만 유지.

해설은 이 단계에서 건드리지 않는다 (별도 생성 단계).

python3 scripts/fix_data.py [--dry]
"""
import difflib
import glob
import html as htmlmod
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRY = "--dry" in sys.argv

LOCAL_KINZ = ROOT / "public" / "images" / "kinz"
LOCAL_CBT = ROOT / "public" / "images" / "cbtbank"


def norm(t):
    return re.sub(r"\s+", "", t or "")


def norm_match(t):
    # 유사도 계산 전 이미지 마커/URL/LaTeX·TikZ 블록 을 제거
    t = re.sub(r"\[이미지:[^\]]*\]", " ", t or "")
    t = re.sub(r"\\begin\{[^}]*\}.*?\\end\{[^}]*\}", " ", t, flags=re.S)
    t = re.sub(r"https?://\S+", " ", t)
    return re.sub(r"\s+", "", t)


def to_num(a):
    a = (a or "").strip()
    if a in "①②③④⑤":
        return "①②③④⑤".find(a) + 1
    if re.fullmatch(r"\d", a):
        return int(a)
    if re.fullmatch(r"\d(,\s*\d)+", a):
        return a
    return None


def answer_mark(n):
    return "①②③④⑤"[n - 1] if isinstance(n, int) and 1 <= n <= 5 else None


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


def map_kinz_img(url):
    url = url.strip()
    if url.startswith("/"):
        url = "https://www.kinz.kr" + url
    base = url.rstrip("/").split("/")[-1]
    if (LOCAL_KINZ / base).exists():
        return f"/images/kinz/{base}"
    return url


def map_cbt_img(url):
    url = url.strip()
    if url.startswith("/"):
        base = url.rstrip("/").split("/")[-1]
        if (LOCAL_CBT / base).exists():
            return f"/images/cbtbank/{base}"
        return "https://cbtbank.kr" + url
    return url


def rewrite_images(text, kind):
    if not text:
        return text

    def rep(m):
        u = m.group(1).strip()
        if u.startswith("/images/"):
            return m.group(0)
        return f"[이미지: {map_kinz_img(u) if kind == 'kinz' else map_cbt_img(u)}]"

    return re.sub(r"\[이미지:\s*([^\]]+)\]", rep, text)


def load_kinz_sources():
    """kinz: 정답/해설(Playwright) + 구조(정적) 병합"""
    out = {}
    for f in glob.glob(str(ROOT / "data/verified_kinz/*.json")):
        j = json.load(open(f, encoding="utf-8"))
        out[str(j["exam_id"])] = {"questions": j["questions"], "date": None}
    for f in glob.glob(str(ROOT / "data/verified_kinz_static/*.json")):
        st = json.load(open(f, encoding="utf-8"))
        eid = str(st["exam_id"])
        if eid not in out:
            continue
        out[eid]["date"] = st.get("시험일자")
        byno = {q["no"]: q for q in st["questions"] if q.get("no")}
        for q in out[eid]["questions"]:
            s = byno.get(q.get("no"))
            if s:
                q["문제_정적"] = s["문제"]
                q["보기_정적"] = s["보기"]
                q["문항이미지"] = s.get("문항이미지") or []
    return out


def load_cbt_sources():
    out = {}
    for f in glob.glob(str(ROOT / "data/verified_cbtbank/*.json")):
        j = json.load(open(f, encoding="utf-8"))
        eid = j["exam_id"]  # kt20190804
        m = re.match(r"kt(\d{4})(\d{2})(\d{2})", eid)
        date = f"{int(m.group(1))}. {int(m.group(2))}. {int(m.group(3))}." if m else None
        out[eid] = {"questions": j["questions"], "date": date}
    return out


def best_match(p, questions, key):
    t = norm_match(p["문제"])
    best, best_r = None, 0.0
    for q in questions:
        qt = norm_match(q.get("문제_정적") or q["문제"])
        r = difflib.SequenceMatcher(None, t, qt).ratio()
        if r > best_r:
            best, best_r = q, r
    return best, best_r


def build_problem_text(q, kind):
    base = q.get("문제_정적") or q.get("문제") or ""
    base = re.sub(r"^\s*\d+\.\s*", "", base)  # 문항 번호 접두어 제거
    imgs = q.get("문항이미지") or []
    if imgs and "[이미지" not in base:
        markers = " ".join(f"[이미지: {u}]" for u in imgs)
        base = f"{base}\n{markers}"
    return rewrite_images(base, kind)


def build_choices(q, kind):
    src = q.get("보기_정적") or q.get("보기") or []
    out = []
    for c in src:
        c = (c or "").strip()
        if not c or c in ("<", ">", "＜", "＞"):
            continue
        out.append(rewrite_images(c, kind))
    return "\n".join(out)


def main():
    data = json.loads((ROOT / "data/problems.json").read_text(encoding="utf-8"))
    kinz = load_kinz_sources()
    cbt = load_cbt_sources()
    stats = defaultdict(int)
    matched_rows = defaultdict(list)  # (src_key, source_index) -> [(row_idx, sim)]

    new_data = list(data)
    for i, p in enumerate(new_data):
        if (p.get("문제") or "").strip() == "테스트 문제":
            new_data[i] = None
            stats["테스트삭제"] += 1
            continue

        k = src_key(p)
        srcs = kinz if (k and k[0] == "kinz") else cbt if (k and k[0] == "cbt") else None
        questions = srcs[k[1]]["questions"] if (srcs and k) else []
        if not questions:
            stats["출처없음"] += 1
            continue
        q, r = best_match(p, questions, k[0])
        if r < 0.6:
            stats["미매칭_보존"] += 1
            continue
        stats["매칭"] += 1

        # 중복 추적: 원본 문항 index
        qi = questions.index(q)
        matched_rows[(k, qi)].append((i, r, p))

        # --- 필드 갱신 ---
        # 회차
        date = srcs[k[1]].get("date")
        if date and p.get("회차") != date:
            stats["회차수정"] += 1
            p["회차"] = date

        # 정답 (문제 텍스트에 가답안 선언이 있으면 선언된 번호를 우선)
        declared = re.search(
            r"여기서는\s*(?:가답안인\s*)?(\d)\s*번", p.get("문제") or ""
        )
        if declared:
            mark = answer_mark(int(declared.group(1)))
            if mark and p.get("정답") != mark:
                stats["정답_가답안적용"] += 1
                p["정답"] = mark
            else:
                stats["정답_가답안보존"] += 1
        else:
            new_ans = answer_mark(q["정답"]) if isinstance(q.get("정답"), int) else None
            if new_ans and to_num(p.get("정답")) != q["정답"]:
                stats["정답수정"] += 1
                p["정답"] = new_ans
            elif new_ans and p.get("정답") != new_ans:
                p["정답"] = new_ans  # 표기 통일

        # 문제 / 보기
        ntext = build_problem_text(q, k[0])
        nchoice = build_choices(q, k[0])
        if norm(ntext) != norm(p.get("문제")):
            stats["문제수정"] += 1
            p["문제"] = ntext
        if nchoice and norm(nchoice) != norm(p.get("보기")):
            stats["보기수정"] += 1
            p["보기"] = nchoice
        elif nchoice:
            p["보기"] = nchoice  # 표기 통일(마커 정규화)

    # 중복 행 정리: 같은 원본 문항에 매칭된 행 중 최고 유사도 1개만 유지
    for (k, qi), rows in matched_rows.items():
        if len(rows) <= 1:
            continue
        rows.sort(key=lambda x: (-x[1],))
        keep = rows[0][0]
        for idx, r, p in rows[1:]:
            if new_data[idx] is None:
                continue
            new_data[idx] = None
            stats["중복삭제"] += 1

    fixed = [p for p in new_data if p is not None]

    # HTML 엔티티 잔여 디코드
    for p in fixed:
        for f in ("문제", "보기", "해설", "사용공식"):
            v = p.get(f)
            if v and "&" in v and re.search(r"&(quot|amp|lt|gt|nbsp|#\d+);", v):
                p[f] = htmlmod.unescape(v)
                stats["엔티티디코드"] += 1

    print("수정 통계:", dict(stats))
    print(f"행 수: {len(data)} -> {len(fixed)}")
    if DRY:
        print("(dry-run: 저장 안 함)")
        return 0
    (ROOT / "data/problems.json").write_text(
        json.dumps(fixed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print("저장 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
