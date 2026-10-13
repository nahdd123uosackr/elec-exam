#!/usr/bin/env python3
"""Merge all kinz batch results into one final dataset."""
import json, re, hashlib
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT = DATA_DIR / "problems_final.json"

# Load existing data
EXISTING = DATA_DIR / "problems.json"
existing = json.loads(EXISTING.read_text(encoding="utf-8")) if EXISTING.exists() else []
print(f"Existing problems: {len(existing)}")

# Load all batch files
batch_files = sorted(DATA_DIR.glob("kinz_batch*.json"))
print(f"Batch files: {len(batch_files)}")

all_scraped = []
for bf in batch_files:
    data = json.loads(bf.read_text(encoding="utf-8"))
    all_scraped.extend(data)
    print(f"  {bf.name}: {len(data)} problems")

print(f"Total scraped: {len(all_scraped)}")

# Deduplicate by id
seen_ids = set()
scraped_dedup = []
for p in all_scraped:
    pid = p.get("id", "")
    if pid and pid not in seen_ids:
        seen_ids.add(pid)
        scraped_dedup.append(p)
    elif not pid:
        scraped_dedup.append(p)

print(f"After dedup: {len(scraped_dedup)}")

# Merge with existing
def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', '', text)
    text = re.sub(r'[\[\]\(\)\.\,\-\:\;\?\!\'·◆◇※【】]', '', text)
    return text[:50].lower()

existing_index = {}
for p in existing:
    key = normalize_text(p.get("문제", ""))
    if key:
        existing_index[key] = p

merged = []
seen_keys = set()
updated = 0
new_count = 0

for p in scraped_dedup:
    key = normalize_text(p.get("문제", ""))
    if not key:
        continue

    merged_prob = {
        "id": p.get("id", hashlib.md5(key.encode()).hexdigest()[:32]),
        "문제": p.get("문제", ""),
        "정답": p.get("정답", "") or "",
        "해설": p.get("해설", "") or "",
        "사용공식": p.get("사용공식", "") or "",
        "출처": p.get("출처", "") or "",
        "회차": p.get("회차", "") or "",
        "과목": p.get("과목", "") or "",
        "난이도": p.get("난이도", "") or "",
        "보기": p.get("보기", "") or "",
        "중복출제": p.get("중복출제", "") or "",
    }

    if key in existing_index:
        existing_p = existing_index[key]
        merged_prob["정답"] = merged_prob["정답"] or existing_p.get("정답", "")
        merged_prob["해설"] = merged_prob["해설"] or existing_p.get("해설", "")
        merged_prob["사용공식"] = merged_prob["사용공식"] or existing_p.get("사용공식", "")
        if not merged_prob["난이도"]:
            merged_prob["난이도"] = existing_p.get("난이도", "")
        if not merged_prob["중복출제"]:
            merged_prob["중복출제"] = existing_p.get("중복출제", "")
        updated += 1
    else:
        new_count += 1

    merged.append(merged_prob)
    seen_keys.add(key)

# Add existing-only problems
existing_only = 0
for p in existing:
    key = normalize_text(p.get("문제", ""))
    if key and key not in seen_keys:
        merged.append(p)
        existing_only += 1

print(f"\nMerge results:")
print(f"  New: {new_count}, Updated: {updated}, Existing-only: {existing_only}")
print(f"  Total merged: {len(merged)}")

# Save final
OUTPUT.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {OUTPUT}")

# Stats
with_answers = sum(1 for p in merged if p.get("정답"))
with_images = sum(1 for p in merged if "[이미지:" in p.get("문제", ""))
with_explanations = sum(1 for p in merged if p.get("해설") and len(p.get("해설", "")) > 10)

print(f"\nFinal statistics:")
print(f"  Total: {len(merged)}")
print(f"  With answers: {with_answers} ({with_answers/len(merged)*100:.1f}%)")
print(f"  With images: {with_images} ({with_images/len(merged)*100:.1f}%)")
print(f"  With explanations: {with_explanations} ({with_explanations/len(merged)*100:.1f}%)")

# Sample
if merged:
    sample = merged[0]
    print(f"\nSample:")
    print(f"  ID: {sample['id']}")
    print(f"  Cycle: {sample['회차']}")
    print(f"  Subject: {sample['과목']}")
    print(f"  Answer: {sample['정답']}")
    print(f"  Question: {sample['문제'][:100]}...")
