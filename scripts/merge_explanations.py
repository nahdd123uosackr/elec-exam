#!/usr/bin/env python3
"""data/explain_part_*.json 샤드 결과를 data/problems.json 에 병합한다.

python3 scripts/merge_explanations.py [--dry]
"""
import glob
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRY = "--dry" in sys.argv


def main():
    files = sorted(glob.glob(str(ROOT / "data/explain_part_*.json")))
    if not files:
        print("병합할 샤드 파일 없음")
        return 1

    merged = {}
    for f in files:
        part = json.loads(Path(f).read_text(encoding="utf-8"))
        # 기존 해설이 있는 항목은 덮어쓰지 않는다 (원본 해설 우선)
        for pid, ex in part.items():
            if pid not in merged or len(ex) > len(merged[pid]):
                merged[pid] = ex
        print(f"  {Path(f).name}: {len(part)}건")

    data = json.loads((ROOT / "data/problems.json").read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in data}
    applied = skipped = 0
    for pid, ex in merged.items():
        p = by_id.get(pid)
        if not p:
            skipped += 1
            continue
        if (p.get("해설") or "").strip():
            skipped += 1  # 이미 해설 있음 → 원본 우선
            continue
        p["해설"] = ex
        applied += 1

    have = sum(1 for p in data if (p.get("해설") or "").strip())
    print(f"적용 {applied}건, 건너뜀 {skipped}건 → 해설 보유 {have}/{len(data)}")
    if DRY:
        print("(dry-run: 저장 안 함)")
        return 0
    (ROOT / "data/problems.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print("병합 저장 완료")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
