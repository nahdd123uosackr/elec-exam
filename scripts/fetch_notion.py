import requests
import json
import sys
from collections import defaultdict

NOTION_API_KEY = "ntn_d56118619483PjQVzpTLOCNriwIUqCQvMfovD6QB3MQg1U"
DATABASE_ID = "35414e7e-37bc-81d6-a478-fddda7a54464"
NOTION_API_VERSION = "2022-06-28"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": NOTION_API_VERSION,
    "Content-Type": "application/json"
}

def query_database():
    all_results = []
    next_cursor = None
    
    while True:
        payload = {"page_size": 100}
        if next_cursor:
            payload["start_cursor"] = next_cursor
            
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{DATABASE_ID}/query",
            headers=headers,
            json=payload
        )
        
        if resp.status_code != 200:
            print(f"Error: {resp.status_code} - {resp.text}", file=sys.stderr)
            sys.exit(1)
            
        data = resp.json()
        all_results.extend(data.get("results", []))
        
        next_cursor = data.get("next_cursor")
        if not data.get("has_more"):
            break
    
    return all_results

def extract_property(page, prop_name):
    props = page.get("properties", {})
    prop = props.get(prop_name, {})
    
    if "title" in prop and prop["title"]:
        return "".join([t.get("plain_text", "") for t in prop["title"]])
    if "rich_text" in prop and prop["rich_text"]:
        return "".join([t.get("plain_text", "") for t in prop["rich_text"]])
    if "select" in prop and prop["select"]:
        return prop["select"].get("name", "")
    if "url" in prop:
        return prop.get("url")
    
    return ""

def main():
    print("Querying Notion database...", file=sys.stderr)
    pages = query_database()
    print(f"Total pages retrieved: {len(pages)}", file=sys.stderr)
    
    problems = []
    for page in pages:
        problem = {
            "id": page.get("id", ""),
            "문제": extract_property(page, "문제"),
            "정답": extract_property(page, "정답"),
            "해설": extract_property(page, "해설"),
            "사용공식": extract_property(page, "사용공식"),
            "출처": extract_property(page, "출처"),
            "회차": extract_property(page, "회차"),
            "과목": extract_property(page, "과목"),
            "난이도": extract_property(page, "난이도"),
        }
        problems.append(problem)
    
    # Count by cycle
    cycle_counts = defaultdict(int)
    for p in problems:
        cycle_counts[p["회차"]] += 1
    
    print("Problems by cycle:", file=sys.stderr)
    for cycle in sorted(cycle_counts.keys(), reverse=True):
        print(f"  {cycle}: {cycle_counts[cycle]} problems", file=sys.stderr)
    
    # Write to file
    with open("/root/electrician-exam-web/data/problems.json", "w", encoding="utf-8") as f:
        json.dump(problems, f, ensure_ascii=False, indent=2)
    
    print(f"Saved {len(problems)} problems to /root/electrician-exam-web/data/problems.json", file=sys.stderr)

if __name__ == "__main__":
    main()