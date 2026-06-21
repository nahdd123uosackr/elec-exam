#!/usr/bin/env python3
"""전기기사 기출문제 Notion → JSON 동기화.

- DB schema: 9 properties (문제, 정답, 해설, 사용공식, 출처, 회차, 과목, 난이도, **보기**)
- API: Notion-Version 2025-09-03 (data_sources API)
- 저장: /root/elec-exam/data/problems.json (단일 진실 공급원)
"""
import requests
import json
import sys
from collections import defaultdict

NOTION_API_KEY = "ntn_d56118619483PjQVzpTLOCNriwIUqCQvMfovD6QB3MQg1U"
DATA_SOURCE_ID = "35414e7e-37bc-811c-a4e3-000b57ab5e00"  # data_source (query 대상)
OUTPUT_PATH = "/root/elec-exam/data/problems.json"

API_VERSION = "2025-09-03"
QUERY_URL = f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": API_VERSION,
    "Content-Type": "application/json",
}


def _text(prop):
    if not prop:
        return ""
    if "rich_text" in prop and prop["rich_text"]:
        return "".join(t.get("plain_text", "") for t in prop["rich_text"])
    if "title" in prop and prop["title"]:
        return "".join(t.get("plain_text", "") for t in prop["title"])
    if "select" in prop and prop["select"]:
        return prop["select"].get("name", "")
    return ""


def query_all():
    """data_sources API로 전체 페이지를 페이지네이션하며 가져온다."""
    all_results = []
    next_cursor = None
    while True:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor
        r = requests.post(QUERY_URL, headers=headers, json=payload)
        if r.status_code != 200:
            print(f"Error: {r.status_code} - {r.text[:300]}", file=sys.stderr)
            sys.exit(1)
        data = r.json()
        all_results.extend(data.get("results", []))
        next_cursor = data.get("next_cursor")
        if not data.get("has_more"):
            break
    return all_results


def main():
    pages = query_all()
    print(f"Total pages: {len(pages)}", file=sys.stderr)

    problems = []
    for page in pages:
        props = page.get("properties", {})
        problems.append({
            "id": page.get("id", ""),
            "문제": _text(props.get("문제")),
            "정답": _text(props.get("정답")),
            "해설": _text(props.get("해설")),
            "사용공식": _text(props.get("사용공식")),
            "출처": props.get("출처", {}).get("url", ""),
            "회차": _text(props.get("회차")),
            "과목": _text(props.get("과목")),
            "난이도": _text(props.get("난이도")),
            "보기": _text(props.get("보기")),  # ← 추가
        })

    # 테스트 업로드 자동 제거
    before = len(problems)
    problems = [
        p for p in problems
        if "[테스트]" not in p.get("문제", "")
        and "/exam/test" not in (p.get("출처") or "")
        and p.get("회차") != "9999. 1. 1."
    ]
    removed = before - len(problems)
    if removed:
        print(f"Removed {removed} test/sample uploads", file=sys.stderr)

    # 회차별 카운트
    by_cycle = defaultdict(int)
    for p in problems:
        by_cycle[p["회차"]] += 1
    print("By cycle:", file=sys.stderr)
    for c in sorted(by_cycle.keys(), reverse=True):
        print(f"  {c}: {by_cycle[c]}", file=sys.stderr)

    # 보기 채워진 비율
    with_choices = sum(1 for p in problems if p["보기"].strip())
    print(f"\n보기가 있는 문제: {with_choices}/{len(problems)} ({100*with_choices/len(problems):.1f}%)",
          file=sys.stderr)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(problems, f, ensure_ascii=False)
    print(f"\nSaved to {OUTPUT_PATH}", file=sys.stderr)


if __name__ == "__main__":
    main()
