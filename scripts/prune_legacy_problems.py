#!/usr/bin/env python3
"""Postgres DB(elec.problems)에서 검증된 3,800개 ID 이외의 6,199개 레거시/중복 행을 정리한다.

원격 k3s postgres(oracle1)에 kubectl exec 로 안전하게 단일 트랜잭션으로 반영한다.
사전 백업 테이블(problems_backup_20261013, 9999행)을 확인한 뒤 실행한다.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

POD = "postgres-86997c74c7-6q772"
NAMESPACE = "postgres"
DB = "elec"
USER = "postgres"


def run_sql(sql: str, tuples_only: bool = True) -> str:
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


def main():
    print("=== 1. 사전 백업 테이블 확인 ===", flush=True)
    backup_count = run_sql("SELECT count(*) FROM problems_backup_20261013;")
    print(f"백업 테이블 행 수: {backup_count}", flush=True)
    if backup_count != "9999":
        print(f"오류: 백업 테이블 행 수({backup_count})가 9999가 아닙니다! 중단합니다.", file=sys.stderr)
        return 1

    print("\n=== 2. 로컬 검증 ID 로드 ===", flush=True)
    local_data = json.loads((ROOT / "data/problems.json").read_text(encoding="utf-8"))
    verified_ids = [p["id"] for p in local_data if p.get("id")]
    print(f"검증된 ID 수: {len(verified_ids)}", flush=True)
    if len(verified_ids) != 3800:
        print(f"오류: 검증된 ID 수({len(verified_ids)})가 3800이 아닙니다! 중단합니다.", file=sys.stderr)
        return 1

    print("\n=== 3. 정리 전 DB 현황 ===", flush=True)
    before_count = run_sql("SELECT count(*) FROM problems;")
    before_cycles = run_sql("SELECT count(DISTINCT \"회차\") FROM problems WHERE \"회차\" IS NOT NULL;")
    print(f"현재 행 수: {before_count}, 회차 수: {before_cycles}", flush=True)

    print("\n=== 4. 레거시 행 정리 트랜잭션 실행 ===", flush=True)
    # 임시 테이블에 verified_ids 적재 후 DELETE 수행
    values_clause = ", ".join(f"('{pid}')" for pid in verified_ids)
    sql = f"""
    CREATE TEMP TABLE verified_ids (id text PRIMARY KEY);
    INSERT INTO verified_ids (id) VALUES {values_clause};

    BEGIN;
    DELETE FROM problems WHERE id NOT IN (SELECT id FROM verified_ids);

    -- 검증 1: 남은 행 수 3800
    DO $$
    DECLARE
        c int;
        cyc int;
        bad int;
    BEGIN
        SELECT count(*) INTO c FROM problems;
        IF c != 3800 THEN
            RAISE EXCEPTION '남은 행 수가 3800이 아님: %', c;
        END IF;

        SELECT count(DISTINCT "회차") INTO cyc FROM problems WHERE "회차" IS NOT NULL;
        IF cyc != 42 THEN
            RAISE EXCEPTION '남은 회차 수가 42가 아님: %', cyc;
        END IF;

        SELECT count(*) INTO bad FROM problems WHERE "회차" LIKE '%2026-01%' OR "회차" ~ '^[0-9]{{4}}-[0-9]{{2}}$';
        IF bad != 0 THEN
            RAISE EXCEPTION '비표준 회차가 남아있음: %', bad;
        END IF;
    END $$;

    COMMIT;

    VACUUM ANALYZE problems;
    """

    out = run_sql(sql, tuples_only=False)
    print("SQL 실행 결과:")
    print(out, flush=True)

    print("\n=== 5. 정리 후 검증 ===", flush=True)
    after_count = run_sql("SELECT count(*) FROM problems;")
    after_cycles = run_sql("SELECT count(DISTINCT \"회차\") FROM problems WHERE \"회차\" IS NOT NULL;")
    bad_cycles = run_sql("SELECT count(*) FROM problems WHERE \"회차\" LIKE '%2026-01%' OR \"회차\" ~ '^[0-9]{4}-[0-9]{2}$';")

    print(f"정리 후 행 수: {after_count} (목표: 3800)")
    print(f"정리 후 회차 수: {after_cycles} (목표: 42)")
    print(f"비표준 회차 수: {bad_cycles} (목표: 0)")

    if after_count == "3800" and after_cycles == "42" and bad_cycles == "0":
        print("\n✅ DB 레거시 중복 데이터 정리 성공!")
        return 0
    else:
        print("\n❌ 검증 실패!", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
