import type { Problem } from '../types/Problem'

let _cache: Problem[] | null = null

function loadProblems(): Problem[] {
  if (_cache) return _cache
  const fs = require('fs')
  const path = require('path')
  const file = path.join(process.cwd(), 'data', 'problems.json')
  const raw = fs.readFileSync(file, 'utf-8')
  _cache = JSON.parse(raw) as Problem[]
  return _cache
}

export function queryProblems(opts: {
  cycle?: string
  subject?: string
  dupCount?: number
  search?: string
  limit?: number
  offset?: number
  ids?: string[]
}): { rows: Problem[]; total: number } {
  let problems = loadProblems()

  if (opts.ids !== undefined) {
    const idSet = new Set(opts.ids.map(id => String(id).trim()).filter(Boolean))
    problems = problems.filter(p => idSet.has(p.id))
  }

  if (opts.cycle && opts.cycle !== 'all') {
    problems = problems.filter(p => p.회차 === opts.cycle)
  }
  if (opts.subject && opts.subject !== 'all') {
    problems = problems.filter(p => p.과목 === opts.subject)
  }
  if (opts.dupCount !== undefined) {
    if (opts.dupCount === 1) {
      problems = problems.filter(p => !p.중복출제 || p.중복출제 === '')
    } else if (opts.dupCount === 2) {
      problems = problems.filter(p => p.중복출제 && p.중복출제 !== '' && !p.중복출제.includes(','))
    } else {
      problems = problems.filter(p => {
        if (!p.중복출제 || p.중복출제 === '') return false
        const count = p.중복출제.split(',').length + 1
        return count >= opts.dupCount!
      })
    }
  }
  if (opts.search) {
    const q = opts.search.toLowerCase()
    problems = problems.filter(p =>
      (p.문제 || '').toLowerCase().includes(q) ||
      (p.정답 || '').toLowerCase().includes(q) ||
      (p.해설 || '').toLowerCase().includes(q)
    )
  }

  const total = problems.length
  const limit = opts.limit ?? 20
  const offset = opts.offset ?? 0
  const rows = problems.slice(offset, offset + limit)

  return { rows, total }
}

export function getProblemById(id: string): Problem | null {
  const problems = loadProblems()
  return problems.find(p => p.id === id) || null
}

export function searchProblemsForRAG(query: string, limit = 5): Problem[] {
  const problems = loadProblems()
  const q = query.toLowerCase()
  return problems
    .filter(p =>
      (p.문제 || '').toLowerCase().includes(q) ||
      (p.해설 || '').toLowerCase().includes(q) ||
      (p.사용공식 || '').toLowerCase().includes(q)
    )
    .slice(0, limit)
}

export function parseCycleDate(cycle: string): number {
  const m = cycle.match(/(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})/)
  if (!m) return 0
  return parseInt(m[1], 10) * 10000 + parseInt(m[2], 10) * 100 + parseInt(m[3], 10)
}

export function getStats(): {
  total: number
  cycles: number
  subjects: number
  subjectsList: string[]
  cyclesList: string[]
} {
  const problems = loadProblems()
  const cycles = new Set(problems.map(p => p.회차).filter(Boolean) as string[])
  const subjects = new Set(problems.map(p => p.과목).filter(Boolean) as string[])
  const subjectsList = Array.from(subjects).sort()
  const cyclesList = Array.from(cycles).sort((a, b) => parseCycleDate(b) - parseCycleDate(a))
  return {
    total: problems.length,
    cycles: cycles.size,
    subjects: subjects.size,
    subjectsList,
    cyclesList,
  }
}
