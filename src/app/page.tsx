'use client'

import { useState, useEffect, useMemo } from 'react'
import type { Problem } from '../types/Problem'

type SortKey = '회차' | '과목' | '문제번호'

/** "① 내용" / "1. 내용" / "(1) 내용" → [1, "내용"] 형태로 정규화 */
function parseChoice(raw: string, idx: number): { num: number; text: string; label: string } {
  // 보기에 ①②③④⑤ 같은 원문자 또는 1. 2. 3. 4. 같은 표기가 섞여 있을 수 있음
  // 안전하게 표시 라벨은 ①~④로 고정
  const circled = ['①', '②', '③', '④', '⑤']
  const trimmed = raw.trim()
  const m = trimmed.match(/^[①-⑤]\s*(.*)$/) || trimmed.match(/^[\(]?(\d)[\)\.]?\s*(.*)$/)
  if (m) {
    const text = (m[2] ?? m[1] ?? '').trim()
    return { num: idx + 1, text: text || trimmed, label: circled[idx] || `(${idx + 1})` }
  }
  return { num: idx + 1, text: trimmed, label: circled[idx] || `(${idx + 1})` }
}

/** 정답 표시를 1-based 인덱스로 정규화 ("①"→1, "1"→1, "1,2"→[1,2]) */
function normalizeAnswer(answer: string): number[] {
  if (!answer) return []
  const circledMap: Record<string, number> = { '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5 }
  return answer
    .split(/[,\s]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => {
      if (s in circledMap) return circledMap[s]
      const n = parseInt(s, 10)
      return isNaN(n) ? 0 : n
    })
    .filter((n) => n > 0)
}

export default function Home() {
  const [problems, setProblems] = useState<Problem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCycle, setSelectedCycle] = useState<string>('all')
  const [selectedSubject, setSelectedSubject] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('회차')
  // 각 문제의 사용자 선택 (idx → 1..4) 와 채점 결과 캐시
  const [picks, setPicks] = useState<Record<number, number>>({})

  useEffect(() => {
    fetch('/data/problems.json')
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load problems.json')
        return res.json()
      })
      .then((data: Problem[]) => {
        setProblems(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  const cycles = useMemo(() => {
    const set = new Set(problems.map((p) => p.회차).filter(Boolean))
    return Array.from(set).sort((a, b) => (a || '').localeCompare(b || '')).reverse()
  }, [problems])

  const subjects = useMemo(() => {
    const set = new Set(problems.map((p) => p.과목).filter(Boolean))
    return Array.from(set)
  }, [problems])

  const filtered = useMemo(() => {
    let list = problems
    if (selectedCycle !== 'all') {
      list = list.filter((p) => p.회차 === selectedCycle)
    }
    if (selectedSubject !== 'all') {
      list = list.filter((p) => p.과목 === selectedSubject)
    }
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase()
      list = list.filter((p) => {
        const text = `${p.문제 || ''} ${p.정답 || ''} ${p.해설 || ''} ${p.보기 || ''}`.toLowerCase()
        return text.includes(q)
      })
    }
    list = [...list]
    list.sort((a, b) => {
      if (sortKey === '회차') {
        return (b.회차 || '').localeCompare(a.회차 || '')
      }
      if (sortKey === '과목') {
        return (a.과목 || '').localeCompare(b.과목 || '')
      }
      const aNum = Number((a.문제 || '').match(/^(\d+)/)?.[1] || 0)
      const bNum = Number((b.문제 || '').match(/^(\d+)/)?.[1] || 0)
      return aNum - bNum
    })
    return list
  }, [problems, selectedCycle, selectedSubject, searchQuery, sortKey])

  // 점수 통계
  const score = useMemo(() => {
    let answered = 0
    let correct = 0
    for (let i = 0; i < filtered.length; i++) {
      const pick = picks[i]
      if (pick === undefined) continue
      answered++
      const ans = normalizeAnswer(filtered[i].정답 || '')
      if (ans.includes(pick)) correct++
    }
    return { answered, correct }
  }, [filtered, picks])

  if (loading) {
    return (
      <main className="min-h-screen p-4 md:p-8 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold mb-4">전기기사 기출문제</h1>
          <p className="text-gray-600">문제 로딩 중...</p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen p-4 md:p-8 bg-gray-50">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold mb-4">전기기사 기출문제</h1>
          <p className="text-red-600">문제 로딩 실패: {error}</p>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen p-4 md:p-8 bg-gray-50">
      <div className="max-w-4xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">전기기사 기출문제</h1>
          <p className="text-gray-600">
            총 {problems.length}개의 기출문제 • 실시간 업데이트
          </p>
        </header>

        <section className="mb-8 space-y-4 bg-white p-4 rounded-xl border border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">회차</label>
              <select
                value={selectedCycle}
                onChange={(e) => setSelectedCycle(e.target.value)}
                className="w-full rounded-md border-gray-300 border px-3 py-2 text-sm"
              >
                <option value="all">전체 회차</option>
                {cycles.map((cycle) => (
                  <option key={cycle} value={cycle}>
                    {cycle}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">과목</label>
              <select
                value={selectedSubject}
                onChange={(e) => setSelectedSubject(e.target.value)}
                className="w-full rounded-md border-gray-300 border px-3 py-2 text-sm"
              >
                <option value="all">전체 과목</option>
                {subjects.map((subject) => (
                  <option key={subject} value={subject}>
                    {subject}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">정렬</label>
              <select
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as SortKey)}
                className="w-full rounded-md border-gray-300 border px-3 py-2 text-sm"
              >
                <option value="회차">회차순</option>
                <option value="과목">과목순</option>
                <option value="문제번호">문제번호순</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">검색</label>
              <input
                type="text"
                placeholder="문제·해설·보기 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-md border-gray-300 border px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="flex items-center justify-between text-sm">
            <div className="text-gray-600">
              표시: <span className="font-semibold">{filtered.length}</span>개 / 전체{' '}
              <span className="font-semibold">{problems.length}</span>개
            </div>
            <div className="text-gray-700">
              채점: <span className="font-semibold text-green-700">{score.correct}</span>
              <span className="text-gray-400 mx-1">/</span>
              <span className="font-semibold">{score.answered}</span>
              {score.answered > 0 && (
                <span className="ml-2 text-xs text-gray-500">
                  ({Math.round((100 * score.correct) / score.answered)}%)
                </span>
              )}
            </div>
          </div>
        </section>

        <section className="grid gap-4">
          {filtered.map((problem, idx) => {
            const qNo = parseInt((problem.문제 || '').match(/^(\d+)/)?.[1] || '0', 10)
            const userPick = picks[idx]
            const correctAnswers = normalizeAnswer(problem.정답 || '')
            const isAnswered = userPick !== undefined
            const isCorrect = isAnswered && correctAnswers.includes(userPick)

            // 보기 파싱: "① 텍스트 ② 텍스트 ③ 텍스트 ④ 텍스트" 또는 "1. 텍스트\n2. 텍스트\n..."
            const rawChoices = (problem.보기 || '')
              .split(/\s*(?=[①②③④⑤]|\d+[\.\)])\s*/)
              .map((s) => s.trim())
              .filter(Boolean)
            // 위 split 이 빈 결과면 줄바꿈으로 fallback
            const choices =
              rawChoices.length >= 2
                ? rawChoices
                : (problem.보기 || '').split(/\n+/).map((s) => s.trim()).filter(Boolean)

            return (
              <article
                key={problem.id || idx}
                className={`problem-card bg-white rounded-xl border p-4 shadow-sm ${
                  isAnswered
                    ? isCorrect
                      ? 'border-green-300'
                      : 'border-red-300'
                    : 'border-gray-200'
                }`}
              >
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500">
                    <span className="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-xs font-medium">
                      {problem.회차}
                    </span>
                    <span className="rounded-full bg-gray-100 text-gray-700 px-2 py-0.5 text-xs font-medium">
                      {problem.과목}
                    </span>
                    {qNo > 0 && (
                      <span className="rounded-full bg-purple-100 text-purple-700 px-2 py-0.5 text-xs font-medium">
                        {qNo}번
                      </span>
                    )}
                    {problem.난이도 && (
                      <span className="rounded-full bg-yellow-100 text-yellow-700 px-2 py-0.5 text-xs font-medium">
                        {problem.난이도}
                      </span>
                    )}
                  </div>
                </div>

                <h2 className="text-lg font-medium text-gray-900 leading-relaxed mb-3 whitespace-pre-line">
                  {problem.문제}
                </h2>

                {/* 보기 영역 */}
                {choices.length > 0 ? (
                  <div className="grid gap-2 mb-3">
                    {choices.map((raw, ci) => {
                      const choice = parseChoice(raw, ci)
                      const isPicked = userPick === choice.num
                      const isCorrectChoice = correctAnswers.includes(choice.num)
                      let btnClass =
                        'flex items-start gap-2 rounded-lg border px-3 py-2 text-left text-sm transition w-full '
                      if (isAnswered) {
                        if (isCorrectChoice) {
                          btnClass += 'bg-green-50 border-green-400 text-green-900'
                        } else if (isPicked && !isCorrectChoice) {
                          btnClass += 'bg-red-50 border-red-400 text-red-900'
                        } else {
                          btnClass += 'bg-white border-gray-200 text-gray-700'
                        }
                      } else {
                        btnClass +=
                          'bg-white border-gray-200 hover:border-blue-400 hover:bg-blue-50 cursor-pointer'
                      }
                      return (
                        <button
                          key={ci}
                          type="button"
                          disabled={isAnswered}
                          onClick={() => setPicks((prev) => ({ ...prev, [idx]: choice.num }))}
                          className={btnClass}
                        >
                          <span className="font-bold shrink-0 mt-0.5">{choice.label}</span>
                          <span className="flex-1">{choice.text}</span>
                          {isAnswered && isCorrectChoice && (
                            <span className="shrink-0 text-xs font-bold text-green-700">정답</span>
                          )}
                          {isAnswered && isPicked && !isCorrectChoice && (
                            <span className="shrink-0 text-xs font-bold text-red-700">내 선택</span>
                          )}
                        </button>
                      )
                    })}
                  </div>
                ) : (
                  // 보기가 없는 문제 (단답형/주관식): 텍스트 입력 받기
                  <div className="mb-3">
                    <input
                      type="text"
                      placeholder="정답을 입력하세요"
                      disabled={isAnswered}
                      onChange={(e) => {
                        const v = e.target.value.trim()
                        if (!v) return
                        const num = parseInt(v, 10)
                        if (!isNaN(num) && num >= 1 && num <= 5) {
                          setPicks((prev) => ({ ...prev, [idx]: num }))
                        }
                      }}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                    />
                  </div>
                )}

                {/* 채점 결과 & 해설 (선택 후 펼쳐짐) */}
                {isAnswered && (
                  <div className="mt-3 space-y-3 border-t pt-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-block rounded-md px-3 py-1 text-sm font-bold ${
                          isCorrect
                            ? 'bg-green-100 text-green-700'
                            : 'bg-red-100 text-red-700'
                        }`}
                      >
                        {isCorrect ? '✅ 정답' : '❌ 오답'}
                      </span>
                      <span className="text-sm text-gray-600">정답:</span>
                      <span className="rounded-md bg-green-50 border border-green-200 px-3 py-1 text-sm font-semibold text-green-700">
                        {problem.정답 || '(미등록)'}
                      </span>
                    </div>

                    {problem.해설 && (
                      <div className="rounded-md bg-gray-50 border border-gray-200 p-3 text-sm text-gray-800 whitespace-pre-line">
                        <div className="text-xs font-semibold text-gray-500 mb-1">해설</div>
                        {problem.해설}
                      </div>
                    )}

                    {problem.사용공식 && (
                      <div className="rounded-md bg-blue-50 border border-blue-200 p-3 text-sm font-mono text-blue-700">
                        <div className="text-xs font-semibold text-gray-500 mb-1 font-sans">
                          사용 공식
                        </div>
                        {problem.사용공식}
                      </div>
                    )}

                    {problem.출처 && (
                      <div className="text-xs text-gray-500">
                        출처:{' '}
                        <a
                          href={problem.출처}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="underline hover:text-blue-600"
                        >
                          {problem.출처}
                        </a>
                      </div>
                    )}

                    {!isCorrect && (
                      <button
                        type="button"
                        onClick={() =>
                          setPicks((prev) => {
                            const next = { ...prev }
                            delete next[idx]
                            return next
                          })
                        }
                        className="text-xs text-gray-500 underline hover:text-blue-600"
                      >
                        다른 답 선택하기
                      </button>
                    )}
                  </div>
                )}
              </article>
            )
          })}
        </section>
      </div>
    </main>
  )
}
