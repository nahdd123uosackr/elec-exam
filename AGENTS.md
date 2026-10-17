# AGENTS.md — 전기기사 기출문제 학습 사이트

## 프로젝트 개요
- 전기기사(필기) 기출문제를 풀 수 있게 만든 웹 사이트. 문제 데이터는 외부 기출문제 사이트에서 수집.
- **출처**: kinz.kr (대부분), cbtbank.kr
- **배포**: GitHub 저장소에 push하면 Vercel이 자동 배포 → https://electrician-exam-web.vercel.app
- 로컬 개발: `npm run build` (Next.js 14.2, App Router)

## 기술 스택
- Next.js 14 (App Router) + TypeScript + Tailwind CSS
- 렌더링: react-markdown + remark-gfm + remark-math + rehype-katex (수식/KaTeX), 자체 `MarkdownMessage` 컴포넌트
- 데이터: **`data/problems.json`이 유일한 source of truth**. 단 프로덕션 라우트는 원격 Postgres(`nhd.us.to:5432`, DB `elec`, oracle1 k3s postgres pod)를 조회 → JSON↔DB 동기화는 `scripts/sync_pg.py` (`--dry`/`--apply`)
- AI 튜터: `/api/chat` → kilo 게이트웨이 `https://api.kilo.ai/api/gateway/v1`, 모델 `kilo-auto/free` (API 키 불필요 — `OMNI_API_KEY` 설정 시에만 Authorization 첨부)
- 웹검색: `/api/search` → DuckDuckGo HTML 스크래핑

## 디렉터리 구조
```
data/
  problems.json          # 문제 DB (앱이 직접 읽음, 유일한 source of truth)
  verified_kinz/         # (검증 산출물) kinz 원본 정답/해설 수집 — Playwright
  verified_kinz_static/  # (검증 산출물) kinz 원본 지문/보기/이미지 — 정적 파싱
  verified_cbtbank/      # (검증 산출물) cbtbank 원본 정답/보기 — 정적 파싱
  explain_progress.json  # 해설 생성 진행 상태 (중단/재개용)
  kinz_batch*.json 등    # 과거 수집/배치 중간 산출물 (참고용)
src/
  app/
    page.tsx             # 홈 (통계 + 내 풀이 현황 + 메뉴)
    subject/page.tsx     # 과목별 풀이
    cycle/page.tsx       # 회차별 풀이
    dup-two/page.tsx     # 2회 출제 문제
    dup-high/page.tsx    # 3회 이상 출제 문제
    wrong/page.tsx       # 오답 문제 풀이 (틀린 문제 전용 복습)
    api/problems/route.ts      # 목록 조회 (GET/POST 지원, ids/cycle/subject/dupCount/search 필터)
    api/problems/[id]/route.ts # 단건 조회
    api/stats/route.ts         # 통계
    api/search/route.ts        # 웹검색 (AI용)
    api/chat/route.ts          # AI 튜터 채팅 (kilo-auto/free + 폴백)
  components/
    ProblemCard.tsx      # 문제 카드 (이전 풀이 뱃지 표시, 보기 분리, 정답 판정, 자동 풀이 저장)
    QuizPage.tsx         # 풀이 화면 (헤더 오답 링크, wrong 모드 지원, API 호출 + 필터)
    ChatBot.tsx          # AI 튜터 패널 (리사이즈, localStorage)
    MarkdownMessage.tsx  # 마크다운+KaTeX 렌더러
  lib/
    data.ts              # problems.json 직접 로드/필터 (ids/cycle/subject 지원)
    db.ts                # Postgres 쿼리 — 프로덕션 라우트가 사용 (ids/cycle/subject 지원)
    storage.ts           # localStorage 기반 풀이 기록/오답 ID 추출/이벤트 구독 유틸
scripts/                 # 수집/정제/검증 파이썬 스크립트
  verify_kinz.py            # kinz 정답/해설 수집 (Playwright, "해설" 버튼 클릭 → /exam/cA)
  extract_kinz_static.py    # kinz 지문/보기/이미지 정적 파싱
  verify_cbtbank.py         # cbtbank 정답/보기 정적 파싱 (correct="N" 속성)
  compare_sources.py        # 원본 수집본 vs problems.json 대조 리포트
  fix_data.py               # 원본 기준으로 일괄 수정 (정답/지문/보기/회차/이미지/중복)
  generate_explanations.py  # 해설 결손분 AI 생성 (원본 해설 우선)
  merge_explanations.py     # 샤드 결과를 problems.json 에 병합
  sync_pg.py                # problems.json → 원격 Postgres 반영 (--dry / --apply)
  prune_legacy_problems.py  # Postgres 레거시 중복(6,199건) 삭제 및 42개 정규 회차 동기화
public/images/kinz/      # kinz 문제·보기 이미지 (gif, ~2900개)
public/images/cbtbank/   # cbtbank 문제·보기 이미지 (gif, 569개)
```

## 데이터 스키마 (`data/problems.json` 원소)
| 필드 | 설명 |
|---|---|
| `id` | UUID |
| `문제` | 지문. 이미지는 `[이미지: /images/kinz|/images/cbtbank/<파일>]` (로컬 경로) |
| `보기` | 4개 보기를 `\n`으로 구분, 마커 `①②③④`. 이미지 보기도 `[이미지: ...]` 포함 |
| `정답` | `①`~`④` (원본 기준 교정 완료). UI `normalizeAnswer()`는 숫자·복수답도 허용 |
| `해설` | 풀이 텍스트 |
| `사용공식` | 요약 공식 |
| `출처` | 원본 URL (`https://www.kinz.kr/exam/<id>` / `https://cbtbank.kr/exam/kt<yyyymmdd>`) |
| `회차` | `YYYY. M. D.` 로 정규화됨 |
| `과목` / `난이도` | 분류/배지 |
| `중복출제` | (선택) 콤마 구분 회차 목록 — **현재 JSON에 없음** → dup-two/dup-high 필터는 빈 결과 |

### UI 판정 및 학습 기록 로직
- 보기: 개행 단위 split → 중복 마커(`① ①`), `1. ①`, `1.` 접두어 제거 → 4버튼 생성
- 정답: `①`~`⑤` / 숫자 / 콤마 복수 허용
- 이미지 마커: `[이미지: /images/...]` → `<img>`, LaTeX가 들어 있으면 KaTeX로 렌더
- **풀이 기록 자동 저장 (`src/lib/storage.ts`)**:
  - 문제를 풀 때마다 정답/오답 여부, 선택 번호, 시도 횟수, 오답 횟수를 `localStorage` (`elec_exam_records_v1`)에 영구 저장
  - `ProblemCard` 상단에 이전 풀이 뱃지 실시간 표시 (`✅ 이전 풀이: 정답`, `❌ 이전 풀이: 오답`)
  - 오답이었던 문제를 다시 맞히면 `🎉 오답 탈출 성공!` 축하 뱃지 표시
- **회차별 문제 풀이 (`/cycle`)**:
  - `/api/stats`의 `cyclesList`를 활용해 **가장 최근 회차(예: `2022. 4. 24.`)를 기본값으로 자동 선택**하여 해당 회차의 문제만 로드
  - "전체 회차" 옵션 없이 정규 42개 회차만 드롭다운에 표시되며, 불필요한 전체 덤프(`limit=9999`) 없음
- **오답 문제 복습 모드 (`/wrong`)**:
  - 저장소의 오답 ID 목록을 읽어 `POST /api/problems`로 필터링 조회
  - 미해결 오답 / 전체 오답 이력 탭 전환, 회차/과목/검색 연동, 오답 노트 전체 초기화 지원
  - 메인 페이지 및 헤더에 실시간 오답 개수 카운터 뱃지 제공

## 데이터 수정 원칙 (작업 시 반드시 준수)
1. **원본 우선**: 정답/보기/지문이 틀렸을 때는 `data/verified_*` 수집본을 근거로 교체한다. 추측으로 바꾸지 않는다.
2. **원본 신뢰성 확인됨**: kinz 수집 정답은 독립 출처(moducbt/comcbt/cbtkr)와 KEC 기준으로 교차 검증 완료. 예) 연동선 최소 굵기 2.5mm², 345/154kV 이격거리 5.48m.
3. **정답 변경 금지 아님**: 원본 수집본에 명확히 있을 때만 바꾸고, 변경 로그를 남긴다.
4. **가답안 문제**: 지문에 "가답안 발표시 N번 / 확정답안 …" 이 쓰인 오류 공지 문제는 지문에 명시된 번호를 정답으로 유지한다.
5. **형식 정규화**: 회차는 `YYYY. M. D.`, 보기 마커 중복 제거, 잡라인(`. <`, `. >`) 제거, HTML 엔티티 디코드.
6. **해설**: 근거 없는 생성 해설은 쓰지 않는다. 원본 해설 우선, 없으면 AI로 개념·공식 중심 생성(`generate_explanations.py`).
7. **변경 후 검증**: `python3 scripts/compare_sources.py` 로 원본 대조, `npx tsc --noEmit` + `npm run build` 확인.

## ⚠️ 보안 (필수)
- **DB 비밀번호·API 키를 코드에 절대 하드코딩하지 않는다.** `os.environ["PG_PASSWORD"]` 로만 읽는다.
- `.env` 는 `.gitignore` 처리됨 — 커밋 금지. (2026-10-13 과거 커밋 이력에서 평문 비밀번호 제거 완료 → 해당 DB 비밀번호는 변경된 것으로 간주하고 재사용 금지)
- `scripts/pg_*.py` 는 `.gitignore` 대상(비밀값 포함) — 원격 push 금지.

## 작업 방식
- 문제 데이터 일괄 수정은 `scripts/`에 파이썬 스크립트를 만들어 실행하고 스크립트를 남긴다 (재현 가능해야 함).
- 수집한 외부 HTML은 신뢰하지 않고 고정 패턴으로만 파싱한다.
- 장기 실행 작업(원본 수집, 해설 생성)은 `nohup … &` + 진행 파일로 중단/재개 가능하게 만든다.
- push 직전 `npm run build` 로 빌드 검증.
