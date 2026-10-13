#!/usr/bin/env python3
"""Final data cleanup: compute duplicate counts, clean temp files, validate."""
import json, re, hashlib
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
PROBLEMS_FILE = DATA_DIR / "problems.json"

print("Loading problems...")
problems = json.loads(PROBLEMS_FILE.read_text(encoding="utf-8"))
print(f"  Total: {len(problems)}")

# Compute duplicate counts by normalized question text
def normalize(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[\[\]\(\)\.\,\-\:\;\?\!\'·◆◇※【】]', '', text)
    return text[:60].lower()

# Group by normalized text
groups = {}
for p in problems:
    key = normalize(p.get("문제", ""))
    if not key:
        continue
    groups.setdefault(key, []).append(p)

print(f"Unique questions: {len(groups)}")

# Compute duplicate counts
dup_updated = 0
for key, group in groups.items():
    if len(group) <= 1:
        continue
    cycles = sorted(set(p.get("회차", "") for p in group if p.get("회차")))
    dup_str = ", ".join(cycles)
    for p in group:
        if p.get("중복출제") != dup_str:
            p["중복출제"] = dup_str
            dup_updated += 1

print(f"Updated duplicate counts: {dup_updated}")

# Validate data quality
with_answers = sum(1 for p in problems if p.get("정답"))
with_images = sum(1 for p in problems if "[이미지:" in p.get("문제", ""))
with_explanations = sum(1 for p in problems if p.get("해설") and len(p.get("해설", "")) > 10)
with_subjects = sum(1 for p in problems if p.get("과목"))
with_cycles = sum(1 for p in problems if p.get("회차"))

print(f"\nData quality:")
print(f"  With answers: {with_answers}/{len(problems)} ({with_answers/len(problems)*100:.1f}%)")
print(f"  With images: {with_images}/{len(problems)} ({with_images/len(problems)*100:.1f}%)")
print(f"  With explanations: {with_explanations}/{len(problems)} ({with_explanations/len(problems)*100:.1f}%)")
print(f"  With subjects: {with_subjects}/{len(problems)} ({with_subjects/len(problems)*100:.1f}%)")
print(f"  With cycles: {with_cycles}/{len(problems)} ({with_cycles/len(problems)*100:.1f}%)")

# Check for missing answers
missing_answers = [p for p in problems if not p.get("정답")]
if missing_answers:
    print(f"\n  Missing answers: {len(missing_answers)}")
    for p in missing_answers[:5]:
        print(f"    - {p['id']}: {p['문제'][:50]}...")

# Save updated data
PROBLEMS_FILE.write_text(json.dumps(problems, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {PROBLEMS_FILE}")

# Clean up temp files
temp_files = [
    "data/problems_test.json",
    "data/problems_kinz_test.json",
    "data/problems_kinz_test2.json",
    "data/problems_kinz_batch1.json",
    "data/problems_kinz_full.json",
    "data/problems_final.json",
    "data/kinz_batch1.json",
    "data/kinz_batch2.json",
    "data/kinz_batch3.json",
    "data/kinz_batch4.json",
    "data/kinz_batch5.json",
    "data/kinz_batch6.json",
    "data/problems_single.json",
    "data/problems_test_run.json",
]

cleaned = 0
for tf in temp_files:
    path = DATA_DIR / tf
    if path.exists():
        path.unlink()
        cleaned += 1

print(f"\nCleaned {cleaned} temporary files")
