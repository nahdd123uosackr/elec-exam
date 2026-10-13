#!/usr/bin/env python3
"""해설이 없는 문제에 대해 AI 로 해설을 생성해 data/problems.json 에 채운다.

- 원본(kinz/cbtbank) 수집 해설이 있으면 우선 사용
- 없으면 LLM 으로 생성 (정답 번호는 이미 확정된 값만 사용, 절대 변경하지 않음)
- 이미지가 있는 문제는 이미지를 텍스트로 볼 수 없으므로, 지문·보기 텍스트만으로
  생성하되 답은 그대로 유지 (해설은 개념 설명 중심으로 작성)
- 진행 상태를 data/explain_progress.json 에 저장 → 중단/재개 가능

python3 scripts/generate_explanations.py [--limit N] [--dry]
"""
import difflib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROG = ROOT / "data/explain_progress.json"
DRY = "--dry" in sys.argv

BASE = (os.environ.get("ANTHROPIC_BASE_URL") or "").rstrip("/")
KEY = os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY") or ""
MODEL = os.environ.get("ANTHROPIC_DEFAULT_SONNET_MODEL") or "omni1"

SUBJECT_RULES = {
    "전기자기학": "전자기학 법칙(쿨롱, 가우스, 앙페르, 패러데이 법칙)과 정전용량·인덕턴스·자계 공식을 인용하라.",
    "회로이론 및 제어공학": "회로 법칙/정리, 라플라스·z 변환, 전달함수, 블록선도, 근궤적, 루스-후르비츠 등 판별법을 인용하라.",
    "전기기기": "직류기/변압기/유도전동기/동기기/정류기 등의 원리와 특성곡선을 인용하라.",
    "전력공학": "송배전 공식(송전전력, 전압강하, %임피던스, 역률개선, 차단용량, 피뢰기·계전기)을 인용하라.",
    "전기설비기술기준": "KEC(전기설비기술기준 및 판단기준) 조문의 수치 기준을 인용하라.",
}

SYSTEM = """당신은 전기기사 필기시험 기출문제 해설 작성 전문가다.
주어진 문제·보기·정답을 바탕으로 수험생이 '왜 그 답이 맞는지' 이해할 수 있는 해설을 한국어로 작성한다.

규칙:
- 2~5문장, 200~600자. 불릿/마크다운 없이 평문으로.
- 첫 문장은 결론(정답 보기의 내용)으로 시작.
- 핵심 공식이나 법령 조문 수치를 인용하고, 풀이 과정을 간단히 보일 것.
- 문제에 이미지/수식이 [이미지: ...] 로 표시되어 있어도 내용을 추측하지 말고,
  이미지가 필요한 문제는 개념 설명과 공식만 제시하라.
- 정답 번호를 바꾸거나 새 답을 제시하지 말 것(주어진 정답이 옳다고 전제).
- "정답은 N번" 같은 단정 대신, 보기의 내용을 인용해 설명하라."""


def build_prompt(p):
    subject = (p.get("과목") or "").split()[0]
    rule = ""
    for k, v in SUBJECT_RULES.items():
        if subject.startswith(k[:4]):
            rule = v
            break
    choices = (p.get("보기") or "").replace("\n", " / ")
    return (
        f"[과목] {p.get('과목','')}\n"
        f"[회차] {p.get('회차','')}\n"
        f"[문제] {p.get('문제','')}\n"
        f"[보기] {choices}\n"
        f"[정답] {p.get('정답','')}\n\n"
        f"참고: {rule}\n해설을 작성하라."
    )


def call_llm(prompt: str, max_tokens: int = 2000, retries: int = 4) -> str | None:
    """omni1 은 기본 thinking 블록을 출력하므로 max_tokens 를 넉넉히(기본 2000) 준다."""
    url = f"{BASE}/v1/messages"
    body = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    headers = {
        "content-type": "application/json",
        "x-api-key": KEY,
        "anthropic-version": "2023-06-01",
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=180) as r:
                res = json.loads(r.read().decode("utf-8"))
            if res.get("stop_reason") == "max_tokens":
                # thinking 만 소진된 경우 → 토큰 2배로 1회 재시도
                body = json.dumps({
                    "model": MODEL,
                    "max_tokens": max_tokens * 2,
                    "system": SYSTEM,
                    "messages": [{"role": "user", "content": prompt}],
                }).encode("utf-8")
                time.sleep(1)
                continue
            text = "".join(
                b.get("text", "") for b in res.get("content", []) if b.get("type") == "text"
            ).strip()
            return text or None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529):
                time.sleep(3 * (attempt + 1))
                continue
            print(f"  HTTP {e.code}: {e.read()[:200]!r}", flush=True)
            return None
        except Exception as e:
            time.sleep(2 * (attempt + 1))
    return None


def load_source_explanations():
    """원본 수집 해설 맵: (출처eid) -> [(정규화 지문, 해설)]"""
    out = {}
    for kind in ("kinz", "cbt"):
        glob = ROOT / f"data/verified_{'kinz' if kind=='kinz' else 'cbtbank'}/*.json"
        for f in sorted(glob.parent.glob(glob.name)):
            j = json.load(open(f, encoding="utf-8"))
            rows = []
            for q in j["questions"]:
                ex = (q.get("해설") or "").strip()
                if ex and ex != "해설이 없습니다":
                    rows.append((re.sub(r"\s+", "", q["문제"]), ex))
            eid = str(j.get("exam_id"))
            out[eid] = rows
    return out


def find_source_explanation(p, srcmap):
    s = p.get("출처") or ""
    m = re.search(r"/exam/([\w]+)", s)
    if not m:
        return None
    rows = srcmap.get(m.group(1), [])
    if not rows:
        return None
    t = re.sub(r"\s+", "", re.sub(r"\[이미지:[^\]]*\]", " ", p["문제"] or ""))
    best, best_r = None, 0.0
    for key, ex in rows:
        r = difflib.SequenceMatcher(None, t, key).ratio()
        if r > best_r:
            best, best_r = ex, r
    return best if best_r >= 0.75 else None


def save_partial(results: dict, shard):
    """생성 결과(problem_id -> 해설)를 샤드별 파일에 저장한다.

    problems.json 은 여러 워커가 동시에 쓰면 마지막 저장분만 살아나므로,
    워커는 이 부분 파일만 쓰고 merge_explanations.py 가 최종 병합한다.
    """
    f = ROOT / f"data/explain_part_{shard if shard is not None else 0}.json"
    prev = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    prev.update(results)
    f.write_text(json.dumps(prev, ensure_ascii=False), encoding="utf-8")


def main():
    if not BASE or not KEY:
        print("ANTHROPIC_BASE_URL / 토큰 필요")
        return 1

    data = json.loads((ROOT / "data/problems.json").read_text(encoding="utf-8"))
    srcmap = load_source_explanations()
    done_ids = set()
    if PROG.exists():
        done_ids = set(json.loads(PROG.read_text()).get("done", []))

    limit = shard = total_shards = None
    for i, a in enumerate(sys.argv):
        if a == "--limit" and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
        if a == "--shard" and i + 2 < len(sys.argv):
            shard, total_shards = int(sys.argv[i + 1]), int(sys.argv[i + 2])

    targets = [p for p in data if not (p.get("해설") or "").strip() and p["id"] not in done_ids]
    if shard is not None:
        targets = [p for i, p in enumerate(targets) if i % total_shards == shard]
    print(f"해설 생성 대상: {len(targets)}건 (이미 처리 {len(done_ids)})", flush=True)
    if limit:
        targets = targets[:limit]

    from_src = from_ai = failed = 0
    pending = {}
    for n, p in enumerate(targets, 1):
        src_ex = find_source_explanation(p, srcmap)
        if src_ex:
            pending[p["id"]] = src_ex
            from_src += 1
            done_ids.add(p["id"])
        else:
            text = call_llm(build_prompt(p))
            if text and len(text) > 30:
                pending[p["id"]] = text
                from_ai += 1
                done_ids.add(p["id"])
            else:
                failed += 1
        if n % 50 == 0:
            print(f"  {n}/{len(targets)} (원본 {from_src}, AI {from_ai}, 실패 {failed})", flush=True)
            if not DRY:
                save_partial(pending, shard)
        if not src_ex:
            time.sleep(0.25)

    if not DRY:
        save_partial(pending, shard)
        PROG.write_text(json.dumps({"done": sorted(done_ids)}, ensure_ascii=False))
    print(f"완료: 원본해설 {from_src}, AI생성 {from_ai}, 실패 {failed}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
