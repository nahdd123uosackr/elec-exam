import pg from 'pg'

const { Pool } = pg

let _pool: pg.Pool | null = null

function getPool(): pg.Pool {
  if (_pool) return _pool

  const config = {
    host: process.env.DB_HOST || 'nhd.us.to',
    port: parseInt(process.env.DB_PORT || '5432', 10),
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '',
    database: process.env.DB_NAME || 'elec',
    ssl: false,
    max: 5,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
  }

  _pool = new Pool(config)
  return _pool
}

export interface ProblemRow {
  id: string
  문제: string
  정답: string | null
  해설: string | null
  사용공식: string | null
  출처: string | null
  회차: string | null
  과목: string | null
  난이도: string | null
  보기: string | null
  중복출제: string | null
}

export async function queryProblems(opts: {
  cycle?: string
  subject?: string
  dupCount?: number  // N회 이상 출제된 문제
  search?: string
  limit?: number
  offset?: number
}): Promise<{ rows: ProblemRow[]; total: number }> {
  const pool = getPool()
  const params: any[] = []
  const where: string[] = []

  if (opts.cycle && opts.cycle !== 'all') {
    params.push(opts.cycle)
    where.push(`"회차" = $${params.length}`)
  }
  if (opts.subject && opts.subject !== 'all') {
    params.push(opts.subject)
    where.push(`"과목" = $${params.length}`)
  }
  if (opts.dupCount !== undefined) {
    // 중복출제 필드의 콤마 개수 + 1 = 총 출제 횟수
    if (opts.dupCount === 1) {
      // 단독 출제 (1회)
      where.push(`("중복출제" IS NULL OR "중복출제" = '')`)
    } else if (opts.dupCount === 2) {
      // 정확히 2회 (콤마 1개)
      where.push(`"중복출제" IS NOT NULL AND "중복출제" != '' AND (length("중복출제") - length(replace("중복출제", ',', ''))) = 1`)
    } else {
      // 3회 이상 (콤마 2개 이상, 총 출제 횟수 >= N)
      params.push(opts.dupCount)
      where.push(`"중복출제" IS NOT NULL AND "중복출제" != '' AND (length("중복출제") - length(replace("중복출제", ',', '')) + 1) >= $${params.length}`)
    }
  }
  if (opts.search) {
    params.push(`%${opts.search}%`)
    where.push(`("문제" ILIKE $${params.length} OR "정답" ILIKE $${params.length} OR "해설" ILIKE $${params.length})`)
  }

  const whereClause = where.length > 0 ? 'WHERE ' + where.join(' AND ') : ''
  const limit = opts.limit ?? 20
  const offset = opts.offset ?? 0

  const countSql = `SELECT count(*)::int as total FROM problems ${whereClause}`
  const countResult = await pool.query(countSql, params)

  params.push(limit)
  params.push(offset)
  const sql = `
    SELECT id, "문제", "정답", "해설", "사용공식", "출처", "회차", "과목", "난이도", "보기", "중복출제"
    FROM problems
    ${whereClause}
    ORDER BY "회차" DESC NULLS LAST, id ASC
    LIMIT $${params.length - 1} OFFSET $${params.length}
  `
  const result = await pool.query(sql, params)

  return { rows: result.rows as ProblemRow[], total: countResult.rows[0].total }
}

export async function getProblemById(id: string): Promise<ProblemRow | null> {
  const pool = getPool()
  const result = await pool.query(
    `SELECT id, "문제", "정답", "해설", "사용공식", "출처", "회차", "과목", "난이도", "보기", "중복출제"
     FROM problems WHERE id = $1 LIMIT 1`,
    [id]
  )
  return (result.rows[0] as ProblemRow) || null
}

export async function searchProblemsForRAG(query: string, limit = 5): Promise<ProblemRow[]> {
  // RAG용: 문제 텍스트 + 해설에서 키워드 검색
  const pool = getPool()
  const sql = `
    SELECT id, "문제", "정답", "해설", "사용공식", "출처", "회차", "과목", "난이도", "보기", "중복출제"
    FROM problems
    WHERE "문제" ILIKE $1 OR "해설" ILIKE $1 OR "사용공식" ILIKE $1
    ORDER BY id ASC
    LIMIT $2
  `
  const result = await pool.query(sql, [`%${query}%`, limit])
  return result.rows as ProblemRow[]
}

export async function getStats(): Promise<{
  total: number
  cycles: number
  subjects: number
  subjectsList: string[]
}> {
  const pool = getPool()
  const total = (await pool.query('SELECT count(*)::int as c FROM problems')).rows[0].c
  const cycles = (await pool.query('SELECT count(DISTINCT "회차")::int as c FROM problems WHERE "회차" IS NOT NULL')).rows[0].c
  const subjects = (await pool.query('SELECT count(DISTINCT "과목")::int as c FROM problems WHERE "과목" IS NOT NULL')).rows[0].c
  const subjectsList = (await pool.query('SELECT DISTINCT "과목" FROM problems WHERE "과목" IS NOT NULL ORDER BY "과목"')).rows.map(r => r['과목'])
  return { total, cycles, subjects, subjectsList }
}
