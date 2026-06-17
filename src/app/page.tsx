'use client'

import { useState, useEffect, useMemo } from 'react'
import type { Problem } from '../types/Problem'

type SortKey = '회차' | '과목' | '문제번호'

export default function Home() {
  const [problems, setProblems] = useState<Problem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCycle, setSelectedCycle] = useState<string>('all')
  const [selectedSubject, setSelectedSubject] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [showAnswer, setShowAnswer] = useState<Set<number>>(new Set())
  const [sortKey, setSortKey] = useState<SortKey>('회차')

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
        const text = `${p.문제 || ''} ${p.정답 || ''} ${p.해설 || ''}`.toLowerCase()
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

  const toggleAnswer = (index: number) => {
    setShowAnswer((prev) => {
      const next = new Set(prev)
      if (next.has(index)) {
        next.delete(index)
      } else {
        next.add(index)
      }
      return next
    })
  }

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
                placeholder="문제 내용 검색..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-md border-gray-300 border px-3 py-2 text-sm"
              />
            </div>
          </div>

          <div className="text-sm text-gray-600">
            표시된 문제: <span className="font-semibold">{filtered.length}</span>개 / 전체{' '}
            <span className="font-semibold">{problems.length}</span>개
          </div>
        </section>

        <section className="grid gap-4">
          {filtered.map((problem, idx) => {
            const qNo = parseInt((problem.문제 || '').match(/^(\d+)/)?.[1] || '0', 10)
            const isRevealed = showAnswer.has(idx)

            return (
              <article key={problem.id || idx} className="problem-card">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2 text-sm text-gray-500">
                      <span className="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-xs font-medium">
                        {problem.회차}
                      </span>
                      <span className="rounded-full bg-gray-100 text-gray-700 px-2 py-0.5 text-xs font-medium">
                        {problem.과목}
                      </span>
                      {problem.난이도 && (
                        <span className="rounded-full bg-yellow-100 text-yellow-700 px-2 py-0.5 text-xs font-medium">
                          {problem.난이도}
                        </span>
                      )}
                    </div>

                    <h2 className="text-lg font-medium text-gray-900 leading-relaxed">
                      {problem.문제}
                    </h2>

                    {isRevealed && (
                      <div className="mt-4 space-y-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-700">정답:</span>
                          <span className="rounded-md bg-green-50 border border-green-200 px-3 py-1 text-sm font-semibold text-green-700">
                            {problem.정답}
                          </span>
                        </div>

                        {problem.해설 && (
                          <div className="rounded-md bg-gray-50 border border-gray-200 p-3 text-sm text-gray-800 whitespace-pre-line">
                            {problem.해설}
                          </div>
                        )}

                        {problem.사용공식 && (
                          <div className="rounded-md bg-blue-50 border border-blue-200 p-3 text-sm font-mono text-blue-700">
                            {problem.사용공식}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => toggleAnswer(idx)}
                    className="shrink-0 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-gray-100"
                  >
                    {isRevealed ? '정답 숨김' : '정답 보기'}
                  </button>
                </div>
              </article>
            )
          })}
        </section>
      </div>
    </main>
  )
}