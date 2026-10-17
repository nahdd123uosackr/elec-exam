'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { getStorageStats, subscribeStorage } from '../lib/storage'

interface Stats {
  total?: number
  cycles?: number
  subjects?: number
  subjectsList?: string[]
  error?: string
}

export default function Home() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [storageStats, setStorageStats] = useState({
    totalSolved: 0,
    totalCorrect: 0,
    totalWrong: 0,
    activeWrong: 0,
  })

  useEffect(() => {
    fetch('/api/stats')
      .then(r => r.json())
      .then(setStats)
      .catch(() => {})
  }, [])

  useEffect(() => {
    setStorageStats(getStorageStats())
    return subscribeStorage(() => {
      setStorageStats(getStorageStats())
    })
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
        {storageStats.totalSolved > 0 && (
          <div className="flex justify-center items-center gap-4 mt-3 text-xs text-gray-600">
            <span className="bg-white/80 border border-gray-200 px-3.5 py-1.5 rounded-full shadow-xs">
              내 풀이: <strong className="text-gray-900">{storageStats.totalSolved}</strong>문제 중{' '}
              <strong className="text-emerald-600 font-semibold">{storageStats.totalCorrect}정답</strong> ·{' '}
              <strong className="text-rose-600 font-semibold">{storageStats.activeWrong}오답</strong>
            </span>
          </div>
        )}
        {stats && stats.error && (
          <div className="mt-3 text-xs text-red-400">통계 로드 실패: {stats.error}</div>
        )}
      </header>

      <section className="max-w-4xl mx-auto px-4 pb-16">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Link href="/wrong" className="menu-card group md:col-span-2 border-rose-200 hover:border-rose-400 bg-gradient-to-r from-rose-50/50 via-white to-orange-50/30">
            <div className="text-4xl">📝</div>
            <div className="flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-lg font-bold text-gray-900 group-hover:text-rose-600 transition">오답 문제 풀이</h2>
                {storageStats.activeWrong > 0 ? (
                  <span className="bg-rose-600 text-white text-xs font-bold px-2 py-0.5 rounded-full shadow-xs">
                    {storageStats.activeWrong}개 오답 복습
                  </span>
                ) : storageStats.totalSolved > 0 ? (
                  <span className="bg-emerald-100 text-emerald-800 text-xs font-semibold px-2 py-0.5 rounded-full">
                    ✅ 오답 없음
                  </span>
                ) : (
                  <span className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded-full">
                    오답 자동 수집
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-1">이전에 틀렸던 문제만 모아서 집중 복습하고 취약점을 보완하세요</p>
            </div>
          </Link>

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