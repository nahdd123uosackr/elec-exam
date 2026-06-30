#!/usr/bin/env python3
"""Simplified update script for kinz answers - takes exam_id and JSON file"""
import json, uuid, psycopg2, sys

exam_id = int(sys.argv[1])
with open(sys.argv[2]) as f:
    answers = json.load(f)

mapping = {1:"①",2:"②",3:"③",4:"④"}
conn = psycopg2.connect(host="nhd.us.to", port=5432, user="postgres", password="Hyeongdong1", dbname="elec")
cur = conn.cursor()
updated = 0
for a in answers:
    ans = a["answer"]
    if not ans or ans < 1 or ans > 4: continue
    i = a["i"] + 1
    pid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"kinz/{exam_id}/{i}"))
    cur.execute("UPDATE problems SET 정답=%s WHERE id=%s", (mapping[ans], pid))
    if cur.rowcount > 0: updated += 1
conn.commit()
print(f"Exam {exam_id}: {updated}/{len(answers)} updated")
cur.close(); conn.close()
