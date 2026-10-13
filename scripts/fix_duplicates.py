#!/usr/bin/env python3
"""Final cleanup: normalize cycles, deduplicate, and validate."""
import json, re
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data"
PROBLEMS_FILE = DATA_DIR / "problems.json"

print("Loading problems...")
problems = json.loads(PROBLEMS_FILE.read_text(encoding="utf-8"))
print(f"  Total: {len(problems)}")

# Separate kinz and original data
kinz_problems = []
original_problems = []

for p in problems:
    source = p.get("출처", "")
    if "kinz.kr/exam/" in source:
        kinz_problems.append(p)
    else:
        original_problems.append(p)

print(f"  Kinz: {len(kinz_problems)}, Original: {len(original_problems)}")

# Normalize question text for dedup
def normalize_question(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'^\d+\.\s*', '', text.strip())
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[\[\]\(\)\.\,\-\:\;\?\!\'·◆◇※【】]', '', text)
    return text[:80].lower()

# Deduplicate by normalized question text
# Priority: kinz data (has correct answers + images)
question_map = {}

for p in kinz_problems:
    norm_q = normalize_question(p.get("문제", ""))
    if not norm_q:
        continue
    if norm_q not in question_map:
        question_map[norm_q] = p

# Add original problems that don't conflict with kinz
added_original = 0
for p in original_problems:
    norm_q = normalize_question(p.get("문제", ""))
    if not norm_q:
        continue
    if norm_q not in question_map:
        question_map[norm_q] = p
        added_original += 1

print(f"  Kinz unique: {len(question_map) - added_original}")
print(f"  Original added: {added_original}")
print(f"  Total after dedup: {len(question_map)}")

# Convert back to list
deduped = list(question_map.values())

# Verify year distribution
from collections import Counter
year_counts = Counter()
for p in deduped:
    cycle = p.get("회차", "")
    years = re.findall(r'(\d{4})\.', cycle)
    for year in years:
        year_counts[year] += 1

print(f"\nYear distribution:")
for year in sorted(year_counts.keys()):
    count = year_counts[year]
    status = "OK" if count <= 300 else f"OVER +{count-300}"
    print(f"  {year}: {count} ({status})")

# Save
PROBLEMS_FILE.write_text(json.dumps(deduped, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {PROBLEMS_FILE}")

# Stats
with_answers = sum(1 for p in deduped if p.get("정답"))
with_images = sum(1 for p in deduped if "[이미지:" in p.get("문제", ""))
with_explanations = sum(1 for p in deduped if p.get("해설") and len(p.get("해설", "")) > 10)
print(f"\nFinal stats:")
print(f"  Total: {len(deduped)}")
print(f"  With answers: {with_answers}")
print(f"  With images: {with_images}")
print(f"  With explanations: {with_explanations}")
