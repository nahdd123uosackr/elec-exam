#!/usr/bin/env python3
"""kinz.kr에서 누락 이미지 다운로드"""
import re, os, sys, time, urllib.request
import psycopg2

conn = psycopg2.connect(host="nhd.us.to",port=5432,user="postgres",password="Hyeongdong1",dbname="elec")
cur = conn.cursor()
cur.execute("SELECT 문제 FROM problems WHERE 문제 LIKE '%[이미지: http%'")

img_dir = "/root/elec-exam/public/images/kinz"
os.makedirs(img_dir, exist_ok=True)

existing = set(os.listdir(img_dir))

all_urls = set()
for (txt,) in cur.fetchall():
    for m in re.findall(r'\[이미지: (https?://[^\]]+)\]', txt):
        all_urls.add(m)

downloaded, skipped, failed = 0, 0, 0
for i, url in enumerate(sorted(all_urls), 1):
    fname = url.split('/')[-1]
    if fname in existing:
        skipped += 1
        continue
    path = os.path.join(img_dir, fname)
    try:
        urllib.request.urlretrieve(url, path)
        # verify
        if os.path.getsize(path) < 50:
            os.remove(path)
            failed += 1
        else:
            downloaded += 1
    except Exception as e:
        failed += 1
    if i % 50 == 0:
        print(f"  [{i}/{len(all_urls)}] 다운 {downloaded}, 생략 {skipped}, 실패 {failed}")

print(f"\n완료! 다운로드 {downloaded}, 생략 {skipped}, 실패 {failed}")
cur.close();conn.close()
