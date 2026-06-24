'use client'

import React, { useState, useEffect, useMemo } from 'react'
import Link from 'next/link'
import type { Problem } from '../types/Problem'
import ProblemCard from './ProblemCard'
import ChatBot from './ChatBot'

interface FilterConfig {
  type: 'cycle' | 'subject' | 'dup-high' | 'dup-two'
  title: string
  subtitle: string
  icon: string
}

export default function QuizPage({ config }: { config: FilterConfig }) {
  const [problems, setProblems] = useState<Problem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedCycle, setSelectedCycle] = useState('all')
  const [selectedSubject, setSelectedSubject] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [chatProblem, setChatProblem] = useState<Problem | null>(null)

  const PAGE_SIZE = 20

  useEffect(() => {
    fetch('/data/problems.json')
      .then(r => { if (!r.ok) throw new Error('Failed to load'); return r.json() })
      .then((data: Problem[]) => { setProblems(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [])

  const cycles = useMemo(() => {
    const set = new Set(problems.map(p => p.회차).filter(Boolean))
    return Array.from(set).sort((a, b) => (b || '').localeCompare(a || ''))
  }, [problems])

  const subjects = useMemo(() => {
    const set = new Set(problems.map(p => p.과목).filter(Boolean))
    return Array.from(set)
  }, [problems])

  const filtered = useMemo(() => {
    let list = problems

    // 타입별 기본 필터
    if (config.type === 'dup-high') {
      list = list.filter(p => {
        if (!p.중복출제) return false
        return p.중복출제.split(',').length >= 2  // 3회 이상 출제
      })
    } else if (config.type === 'dup-two') {
   list = list.filter(p => {
     if (!p.중복출제) return false
     return p.중복출제.split(',').length === 1  // 정확히 2회 출제
   })
 }

    // 사용자 필터
    if (selectedCycle !== 'all') list = list.filter(p => p.회차 === selectedCycle)
    if (selectedSubject !== 'all') list = list.filter(p => p.과목 === selectedSubject)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      list = list.filter(p => `${p.문제 || ''} ${p.정답 || ''} ${p.해설 || ''} ${p.보기 || ''}`.toLowerCase().includes(q))
    }

    return list
  }, [problems, config.type, selectedCycle, selectedSubject, searchQuery])

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE)
  const paged = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  // 필터 변경 시 페이지 리셋
  useEffect(() => { setCurrentPage(1) }, [selectedCycle, selectedSubject, searchQuery])

  // AI 해설 요청 시 챗봇에 문제 전달
  const handleExplain = (problem: Problem) => {
    setChatProblem(problem)
  }

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-pulse">⚡</div>
          <p className="text-gray-600">문제 로딩 중...</p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <p className="text-red-600 text-lg">⚠️ {error}</p>
          <Link href="/" className="text-blue-600 underline mt-4 inline-block">메인으로 돌아가기</Link>
        </div>
      </main>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* 상단 네비게이션 */}
      <header className="shrink-0 bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-full mx-auto flex items-center gap-4">
          <Link href="/" className="text-gray-400 hover:text-gray-700 text-xl shrink-0" title="메인으로">
            ⚡
          </Link>
          <div className="shrink-0">
            <h1 className="text-lg font-bold text-gray-900">{config.icon} {config.title}</h1>
            <p className="text-xs text-gray-500">{config.subtitle}</p>
          </div>

          {/* 필터 */}
          <div className="flex-1 flex items-center gap-3 overflow-x-auto">
            {(config.type === 'cycle' || config.type === 'dup-high' || config.type === 'dup-two') && (
              <select value={selectedCycle} onChange={e => setSelectedCycle(e.target.value)}
                className="rounded-lg border-gray-300 border px-3 py-1.5 text-sm shrink-0">
                <option value="all">전체 회차</option>
                {cycles.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            )}

            {(config.type === 'subject' || config.type === 'dup-high' || config.type === 'dup-two') && (
              <select value={selectedSubject} onChange={e => setSelectedSubject(e.target.value)}
                className="rounded-lg border-gray-300 border px-3 py-1.5 text-sm shrink-0">
                <option value="all">전체 과목</option>
                {subjects.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            )}

            <input type="text" placeholder="🔍 검색..." value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="rounded-lg border-gray-300 border px-3 py-1.5 text-sm w-48 shrink-0" />
          </div>

          <div className="text-sm text-gray-500 shrink-0">
            <strong className="text-gray-900">{filtered.length}</strong>개
          </div>
        </div>
      </header>

      {/* 메인 영역: 문제 목록 + 챗봇 */}
      <div className="flex-1 flex min-h-0">
        {/* 문제 목록 */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {paged.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <div className="text-4xl mb-3">📭</div>
              <p>조건에 맞는 문제가 없습니다</p>
            </div>
          ) : (
            paged.map((problem, idx) => (
              <ProblemCard
                key={problem.id || idx}
                problem={problem}
                index={(currentPage - 1) * PAGE_SIZE + idx}
                onExplain={handleExplain}
              />
            ))
          )}

          {/* 페이지네이션 */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-2 py-6">
              <button onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-100">
                ← 이전
              </button>
              <span className="text-sm text-gray-600">
                {currentPage} / {totalPages}
              </span>
              <button onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 rounded-lg border text-sm disabled:opacity-40 hover:bg-gray-100">
                다음 →
              </button>
            </div>
          )}
        </div>

        {/* AI 챗봇 패널 (고정, 스크롤 분리) */}
        <div className="hidden md:flex w-96 lg:w-[420px] shrink-0 border-l border-gray-200 bg-white">
          <ChatBot currentProblem={chatProblem} subject={selectedSubject !== 'all' ? selectedSubject : undefined} />
        </div>
      </div>

      {/* 모바일 챗봇 (오버레이) */}
      <div className="md:hidden">
        <ChatBot currentProblem={chatProblem} subject={selectedSubject !== 'all' ? selectedSubject : undefined} />
      </div>
    </div>
  )
}
