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
  const [total, setTotal] = useState(0)
  const [selectedCycle, setSelectedCycle] = useState('all')
  const [selectedSubject, setSelectedSubject] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [chatProblem, setChatProblem] = useState<Problem | null>(null)
  const [chatAutoAsk, setChatAutoAsk] = useState(0)  // autoExplain 트리거 (카운터)
  const [cycles, setCycles] = useState<string[]>([])
  const [subjects, setSubjects] = useState<string[]>([])

  const PAGE_SIZE = 20

  // 통계 로드 (회차/과목 목록)
  useEffect(() => {
    fetch('/api/stats')
      .then(r => r.json())
      .then(data => {
        if (data.subjectsList) setSubjects(data.subjectsList)
      })
      .catch(() => {})
  }, [])

  // 문제 로드 (필터 변경 시마다)
  useEffect(() => {
    const fetchProblems = async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams()
        params.set('limit', String(PAGE_SIZE))
        params.set('offset', String((currentPage - 1) * PAGE_SIZE))
        if (selectedCycle !== 'all') params.set('cycle', selectedCycle)
        if (selectedSubject !== 'all') params.set('subject', selectedSubject)
        if (searchQuery.trim()) params.set('q', searchQuery.trim())

        // 중복 출제 필터
        if (config.type === 'dup-high') params.set('dupCount', '3')
        else if (config.type === 'dup-two') params.set('dupCount', '2')

        const res = await fetch(`/api/problems?${params.toString()}`)
        const data = await res.json()

        if (!res.ok) throw new Error(data.error || '문제 로드 실패')

        // DB row → Problem 타입 변환
        const rows = (data.rows || []).map((r: any) => ({
          id: r.id,
          문제: r['문제'] || '',
          정답: r['정답'] || '',
          해설: r['해설'] || '',
          사용공식: r['사용공식'] || '',
          출처: r['출처'] || '',
          회차: r['회차'] || '',
          과목: r['과목'] || '',
          난이도: r['난이도'] || '',
          보기: r['보기'] || '',
          중복출제: r['중복출제'] || '',
        }))
        setProblems(rows)
        setTotal(data.total || 0)

        // 회차 목록 (첫 페이지 + 첫 로딩 시만 갱신)
        if (currentPage === 1 && cycles.length === 0) {
          const allParams = new URLSearchParams()
          allParams.set('limit', '9999')
          const allRes = await fetch(`/api/problems?${allParams.toString()}`)
          const allData = await allRes.json()
          const uniqueCycles = Array.from(new Set((allData.rows || [])
            .map((r: any) => r['회차']).filter(Boolean))) as string[]
          setCycles(uniqueCycles.sort((a, b) => b.localeCompare(a)))
        }

        setError(null)
      } catch (err: any) {
        setError(err.message || '문제를 불러올 수 없습니다')
      } finally {
        setLoading(false)
      }
    }

    fetchProblems()
  }, [config.type, selectedCycle, selectedSubject, searchQuery, currentPage])

  // 필터 변경 시 페이지 리셋
  useEffect(() => { setCurrentPage(1) }, [selectedCycle, selectedSubject, searchQuery])

  const totalPages = Math.ceil(total / PAGE_SIZE)

  const handleExplain = (problem: Problem) => {
    setChatProblem(problem)
    setChatAutoAsk(prev => prev + 1)
  }

  if (loading && problems.length === 0) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="text-4xl mb-4 animate-pulse">⚡</div>
          <p className="text-gray-600">문제 로딩 중...</p>
        </div>
      </main>
    )
  }

  if (error && problems.length === 0) {
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
      <header className="shrink-0 bg-white border-b border-gray-200 px-4 py-3">
        <div className="max-w-full mx-auto flex items-center gap-4 flex-wrap">
          <Link href="/" className="text-gray-400 hover:text-gray-700 text-xl shrink-0" title="메인으로">
            ⚡
          </Link>
          <div className="shrink-0">
            <h1 className="text-lg font-bold text-gray-900">{config.icon} {config.title}</h1>
            <p className="text-xs text-gray-500">{config.subtitle}</p>
          </div>

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
            <strong className="text-gray-900">{total.toLocaleString()}</strong>개
          </div>
        </div>
      </header>

      <div className="flex-1 flex min-h-0">
        {/* 문제 영역 (스크롤) */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {problems.length === 0 ? (
            <div className="text-center py-16 text-gray-400">
              <div className="text-4xl mb-3">📭</div>
              <p>조건에 맞는 문제가 없습니다</p>
            </div>
          ) : (
            problems.map((problem, idx) => (
              <ProblemCard
                key={problem.id || idx}
                problem={problem}
                index={(currentPage - 1) * PAGE_SIZE + idx}
                onExplain={handleExplain}
              />
            ))
          )}

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

        {/* 데스크톱: 우측 AI 튜터 패널 — md 이상에서만 표시 (fixed로 스크롤과 무관하게 고정) */}
        <div className="hidden md:flex w-96 lg:w-[420px] shrink-0 border-l border-gray-200 bg-white sticky top-0 self-start h-[calc(100vh-4rem)]">
          <ChatBot currentProblem={chatProblem} subject={selectedSubject !== 'all' ? selectedSubject : undefined} autoExplain={chatAutoAsk} />
        </div>
      </div>

      {/* 모바일: ChatBot 플로팅 버튼은 항상 표시 (내부 isOpen + currentProblem 게이팅) */}
      <div className="md:hidden">
        <ChatBot currentProblem={chatProblem} subject={selectedSubject !== 'all' ? selectedSubject : undefined} autoExplain={chatAutoAsk} />
      </div>
    </div>
  )
}
