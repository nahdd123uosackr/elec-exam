#!/usr/bin/env python3
"""data/problems.json 의 교정분을 원격 Postgres(elec.problems)에 반영한다.

원격은 k3s(oracle1) 의 postgres pod 에서 psql 로 접근한다.
로컬에서 nhd.us.to:5432 직접 연결은 막혀 있어 kubectl exec 경로를 사용한다.

반영 정책
- 공통 id: 문제/정답/해설/사용공식/보기/난이도/출처/과목/회차 모두 로컬값으로 UPDATE
  (회차는 로컬이 YYYY. M. D. 형식이며 원본 기준으로 정규화된 값)
- DB 에만 있는 행(6199): 삭제하지 않는다 (로컬은 중복제거본이라 상위집합 유지)
- 로컬에만 있는 행: 이번 분석상 0건. 발생 시 INSERT.

python3 scripts/sync_pg.py --dry     # 차이만 출력
python3 scripts/sync_pg.py --apply   # 실제 반영
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

POD = "postgres-86997c74c7-6q772"
NAMESPACE = "postgres"
DB = "elec"
USER = "postgres"

# 로컬 JSON 필드 -> DB 컬럼 (동일 명칭)
FIELDS = ["문제", "정답", "해설", "사용공식", "출처", "회차", "과목", "난이도", "보기"]


def run_sql(sql: str, tuples_only: bool = False):
    """원격 pod 에서 psql 실행.

    subprocess 리스트 인자로 전달하므로 셸 이스케이프는 하지 않는다.
    """
    flags = "-t -A" if tuples_only else ""
    remote = (
        f"k3s kubectl -n {NAMESPACE} exec {POD} -i -- "
        f"psql -U {USER} -d {DB} {flags} -f -"
    )
    r = subprocess.run(
        ["ssh", "oracle1", remote],
        input=sql,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if r.returncode != 0:
        raise RuntimeError(f"psql 실패: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def dump_db():
    sql = ("SELECT coalesce(json_agg(row_to_json(t))::text,'[]') FROM "
           "(SELECT id, 문제, 정답, 해설, 사용공식, 출처, 회차, 과목, 난이도, 보기 FROM problems) t;")
    return json.loads(run_sql(sql, tuples_only=True))


def esc(v: str) -> str:
    """SQL 문자열 리터럴 이스케이프."""
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    apply = args.apply and not args.dry

    local = json.loads((ROOT / "data/problems.json").read_text(encoding="utf-8"))
    print(f"로컬 행수: {len(local)}", flush=True)
    print("원격 DB 덤프 중...", flush=True)
    db = dump_db()
    dbmap = {p["id"]: p for p in db}
    print(f"DB 행수: {len(db)}", flush=True)

    updates, inserts, unchanged = [], [], 0
    for p in local:
        pid = p["id"]
        d = dbmap.get(pid)
        if d is None:
            inserts.append(p)
            continue
        changed = {f: (p.get(f) or "") for f in FIELDS if (p.get(f) or "") != (d.get(f) or "")}
        if changed:
            updates.append((pid, changed))
        else:
            unchanged += 1

    print(f"\n[차이 요약] 변경 {len(updates)}건, 삽입 {len(inserts)}건, 동일 {unchanged}건", flush=True)
    by_field = {}
    for _, ch in updates:
        for f in ch:
            by_field[f] = by_field.get(f, 0) + 1
    print("필드별:", by_field, flush=True)

    if not apply:
        print("\n(dry-run: --apply 로 반영)")
        # 정답 불일치 표본
        n = 0
        for pid, ch in updates:
            if "정답" in ch and n < 5:
                print(f"  정답 {dbmap[pid]['정답']} -> {ch['정답']} | {ch.get('문제', dbmap[pid]['문제'])[:40]}")
                n += 1
        return 0

    # 배치 UPDATE
    ok = 0
    for i, (pid, ch) in enumerate(updates, 1):
        sets = ", ".join(f'"{f}" = {esc(ch[f])}' for f in ch)
        sets += ", updated_at = now()"
        sql = f"UPDATE problems SET {sets} WHERE id = '{pid}';"
        run_sql(sql)
        ok += 1
        if i % 200 == 0:
            print(f"  UPDATE {i}/{len(updates)}", flush=True)

    for p in inserts:
        cols = ["id"] + FIELDS
        vals = ", ".join(esc(p.get(c, "")) if c != "id" else esc(p["id"]) for c in cols)
        colnames = ", ".join(f'"{c}"' for c in cols)
        run_sql(f"INSERT INTO problems ({colnames}, updated_at) VALUES ({vals}, now());")

    print(f"\n반영 완료: UPDATE {ok}건, INSERT {len(inserts)}건", flush=True)
    # 검증
    cnt = run_sql("SELECT count(*) FROM problems;", tuples_only=True)
    print("DB 총 행수:", cnt, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
