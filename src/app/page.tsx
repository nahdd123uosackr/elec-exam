'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'

interface Stats {
  total: number
  cycles: number
  subjects: number
  subjectsList?: string[]
}

export default function Home() {
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    fetch('/api/stats')
      .then(r => r.json())
      .then(setStats)
      .catch(() => {})
  }, [])

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <header className="pt-12 pb-8 px-4 text-center">
        <div className="text-5xl mb-4">⚡</div>
        <h1 className="text-4xl font-bold text-gray-900 mb-3">전기기사 기출문제</h1>
        <p className="text-lg text-gray-600 max-w-xl mx-auto">
          20년 기출문제를 AI와 함께 학습하세요
        </p>
        {stats && (
          <div className="flex justify-center gap-6 mt-6 text-sm text-gray-500">
            <span>📝 <strong className="text-gray-900">{(stats.total ?? 0).toLocaleString()}</strong>문제</span>
            <span>📅 <strong className="text-gray-900">{stats.cycles ?? 0}</strong>회차</span>
            <span>📚 <strong className="text-gray-900">{stats.subjects ?? 0}</strong>과목</span>
          </div>
        )}
        {stats && stats.error && (
          <div className="mt-3 text-xs text-red-400">통계 로드 실패: {stats.error}</div>
        )}
      </header>

      <section className="max-w-4xl mx-auto px-4 pb-16">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Link href="/cycle" className="menu-card group">
            <div className="text-4xl">📋</div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition">회차별 문제 풀이</h2>
              <p className="text-sm text-gray-500 mt-1">원하는 회차를 선택해서 문제를 풀어보세요</p>
            </div>
          </Link>

          <Link href="/subject" className="menu-card group">
            <div className="text-4xl">📚</div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition">과목별 문제 풀이</h2>
              <p className="text-sm text-gray-500 mt-1">전기기기, 전력공학, 전기자기학 등 과목별 학습</p>
            </div>
          </Link>

          <Link href="/dup-high" className="menu-card group">
            <div className="text-4xl">🔁</div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition">3회 이상 출제 문제</h2>
              <p className="text-sm text-gray-500 mt-1">자주 출제되는 핵심 문제 집중 공략</p>
            </div>
          </Link>

          <Link href="/dup-two" className="menu-card group">
            <div className="text-4xl">🕑</div>
            <div>
              <h2 className="text-lg font-bold text-gray-900 group-hover:text-blue-600 transition">2회 출제 문제</h2>
              <p className="text-sm text-gray-500 mt-1">딱 한 번 더 출제된 문제로 실력 확인</p>
            </div>
          </Link>
        </div>

        <div className="mt-12 text-center text-sm text-gray-400">
          <p>각 문제 페이지에서 🤖 AI 튜터에게 질문할 수 있습니다</p>
          <p className="mt-1">기출 DB 검색 + 웹 검색 모두 지원합니다</p>
        </div>
      </section>
    </main>
  )
}