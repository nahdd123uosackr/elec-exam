#!/usr/bin/env python3
"""Merge scraped kinz data with existing problems.json, deduplicate, and produce final dataset."""
import json, re, hashlib, os
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
EXISTING = DATA_DIR / "problems.json"
SCRAPED = DATA_DIR / "problems_kinz_all.json"
OUTPUT = DATA_DIR / "problems_final.json"

# Field name mapping from scraper to final schema
FIELD_MAP = {
    "id": "id",
    "문제": "문제",
    "보기": "보기",
    "정답": "정답",
    "해설": "해설",
    "사용공식": "사용공식",
    "출처": "출처",
    "회차": "회차",
    "과목": "과목",
    "난이도": "난이도",
    "중복출제": "중복출제",
}

# Load existing data
print(f"Loading existing data from {EXISTING}...")
existing = json.loads(EXISTING.read_text(encoding="utf-8"))
print(f"  Existing problems: {len(existing)}")

# Load scraped data
print(f"Loading scraped data from {SCRAPED}...")
scraped = json.loads(SCRAPED.read_text(encoding="utf-8"))
print(f"  Scraped problems: {len(scraped)}")

# Index existing by normalized question text (first 50 chars, no spaces)
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

print(f"  Existing index size: {len(existing_index)}")

# Merge: prefer scraped data (has correct answers + images)
merged = []
seen_keys = set()
dup_count = 0
new_count = 0
updated_count = 0

for p in scraped:
    key = normalize_text(p.get("문제", ""))
    if not key:
        continue
    
    # Convert image placeholders to proper format
    question = p.get("문제", "")
    
    # Ensure all required fields exist
    merged_prob = {
        "id": p.get("id", hashlib.md5(key.encode()).hexdigest()[:32]),
        "문제": question,
        "정답": p.get("정답", ""),
        "해설": p.get("해설", ""),
        "사용공식": p.get("사용공식", ""),
        "출처": p.get("출처", ""),
        "회차": p.get("회차", ""),
        "과목": p.get("과목", ""),
        "난이도": p.get("난이도", ""),
        "보기": p.get("보기", ""),
        "중복출제": p.get("중복출제", ""),
    }
    
    if key in existing_index:
        # Merge with existing
        existing_prob = existing_index[key]
        # Prefer scraped data for answer, explanation, images
        merged_prob["정답"] = merged_prob["정답"] or existing_prob.get("정답", "")
        merged_prob["해설"] = merged_prob["해설"] or existing_prob.get("해설", "")
        merged_prob["사용공식"] = merged_prob["사용공식"] or existing_prob.get("사용공식", "")
        # Keep existing metadata if scraped doesn't have it
        if not merged_prob["난이도"]:
            merged_prob["난이도"] = existing_prob.get("난이도", "")
        if not merged_prob["중복출제"]:
            merged_prob["중복출제"] = existing_prob.get("중복출제", "")
        updated_count += 1
    else:
        new_count += 1
    
    merged.append(merged_prob)
    seen_keys.add(key)

# Add existing problems that weren't in scraped data
for p in existing:
    key = normalize_text(p.get("문제", ""))
    if key and key not in seen_keys:
        merged.append(p)
        dup_count += 1

print(f"\nMerge results:")
print(f"  New problems: {new_count}")
print(f"  Updated problems: {updated_count}")
print(f"  Existing-only problems: {dup_count}")
print(f"  Total merged: {len(merged)}")

# Deduplicate by id
id_index = {}
final = []
for p in merged:
    pid = p.get("id", "")
    if pid in id_index:
        # Keep the one with more data
        existing_p = id_index[pid]
        if len(p.get("문제", "")) > len(existing_p.get("문제", "")):
            id_index[pid] = p
    else:
        id_index[pid] = p
        final.append(p)

print(f"  After dedup: {len(final)}")

# Save final dataset
OUTPUT.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nSaved to {OUTPUT}")

# Statistics
with_answers = sum(1 for p in final if p.get("정답"))
with_images = sum(1 for p in final if "[이미지:" in p.get("문제", ""))
with_explanations = sum(1 for p in final if p.get("해설") and len(p.get("해설", "")) > 10)

print(f"\nFinal statistics:")
print(f"  Total problems: {len(final)}")
print(f"  With answers: {with_answers}")
print(f"  With images: {with_images}")
print(f"  With explanations: {with_explanations}")

# Show sample
if final:
    sample = final[0]
    print(f"\nSample problem:")
    print(f"  ID: {sample['id']}")
    print(f"  Cycle: {sample['회차']}")
    print(f"  Subject: {sample['과목']}")
    print(f"  Answer: {sample['정답']}")
    print(f"  Question: {sample['문제'][:100]}...")
