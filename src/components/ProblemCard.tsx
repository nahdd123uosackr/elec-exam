'use client'

import React, { useState } from 'react'
import type { Problem } from '../types/Problem'
import { InlineMath, BlockMath } from 'react-katex'

/** 이미지/수식 렌더링 */
function renderWithImages(text: string): React.ReactNode {
  // 1. KaTeX 블록 ($$...$$) 먼저 처리
  const blocks = text.split(/(\$\$[^$]+\$\$)/g)
  return blocks.map((block, bi) => {
    const m = block.match(/^\$\$([^$]+)\$\$$/)
    if (m) {
      try {
        return <InlineMath key={bi} math={m[1]} />
      } catch {
        return <code key={bi} className="inline-block bg-red-50 text-red-700 px-1 py-0.5 rounded">{m[1]}</code>
      }
    }
    // 2. 이미지 마커 분할
    return block.split(/(🖼️|<img[^>]*>|\[이미지[^\]]*\])/g).map((part, pi) => {
      if (part === '🖼️') {
        // 이미지가 없는 문제는 빈 공간으로 (아무것도 렌더링 안 함)
        return <span key={`${bi}-${pi}`} className="inline-block w-0" />
      }
      const imgMatch = part.match(/<img\s+src="([^"]+)"[^>]*>/)
      if (imgMatch) {
        return (
          <img key={`${bi}-${pi}`} src={imgMatch[1]} alt="문제 이미지"
            className="inline-block max-h-24 align-middle mx-1 rounded border border-gray-200"
            loading="lazy" />
        )
      }
      const latexMatch = part.match(/\[이미지:\s*([^\]]+)\]/)
      if (latexMatch) {
        const latex = latexMatch[1].trim()
        if (latex.includes('\\')) {
          try {
            return <InlineMath key={`${bi}-${pi}`} math={latex} />
          } catch {
            return <code key={`${bi}-${pi}`} className="inline-block bg-blue-50 text-blue-700 text-xs px-1 py-0.5 rounded">{latex}</code>
          }
        }
        // URL이면 img 태그로
        return <img key={`${bi}-${pi}`} src={latex} alt="문제 이미지"
          className="inline-block max-h-24 align-middle mx-1 rounded border border-gray-200"
          loading="lazy" />
      }
      return <span key={`${bi}-${pi}`}>{part}</span>
    })
  })
}

function parseChoice(raw: string, idx: number) {
  const circled = ['①', '②', '③', '④', '⑤']
  let trimmed = raw.trim()
  // 마커(①-⑤)로 시작하면 제거 (이 parseChoice는 마커 없는 텍스트를 받음)
  trimmed = trimmed.replace(/^[①-⑤]\s+/, '')
  // '1.' '1)' '(1)' 마커도 제거 (안전장치)
  trimmed = trimmed.replace(/^\d+\.\s+/, '')
  trimmed = trimmed.replace(/^\d+\)\s+/, '')
  trimmed = trimmed.replace(/^\(\d+\)\s+/, '')
  return { num: idx + 1, text: trimmed, label: circled[idx] || `(${idx + 1})` }
}

function normalizeAnswer(answer: string): number[] {
  if (!answer) return []
  const circledMap: Record<string, number> = { '①': 1, '②': 2, '③': 3, '④': 4, '⑤': 5 }
  return answer.split(/[,\s]+/).map(s => s.trim()).filter(Boolean)
    .map(s => { if (s in circledMap) return circledMap[s]; const n = parseInt(s, 10); return isNaN(n) ? 0 : n })
    .filter(n => n > 0)
}

interface Props {
  problem: Problem
  index: number
  onExplain?: (problem: Problem) => void  // AI 해설 요청 콜백
}

export default function ProblemCard({ problem, index, onExplain }: Props) {
  const [pick, setPick] = useState<number | undefined>()
  const [showExplain, setShowExplain] = useState(false)

  const qNo = parseInt((problem.문제 || '').match(/^(\d+)/)?.[1] || '0', 10)
  const problemNumber = (index ?? 0) + 1  // 1-based sequential number
  const correctAnswers = normalizeAnswer(problem.정답 || '')
  const isAnswered = pick !== undefined
  const isCorrect = isAnswered && correctAnswers.includes(pick)

  // 보기 분리: 마커(①②③④⑤ / 1. / 1) / (1)) 앞에서 split, 마커 반복 허용
  const rawChoices = (problem.보기 || '')
    .split(/\n+/)
    .map(s => s.trim())
    .filter(Boolean)
    // 각 라인에서 마커(중복 가능) 제거하여 텍스트만 추출
    .map(line => {
      // 마커만 연속된 경우 (예: '① ① 강압 변압기') - 첫 마커 제거
      // 이후 '①' 또는 '1.' 또는 '(1)' 패턴 제거
      const cleaned = line
        .replace(/^([①-⑤])\s+\1\s+/, '$1 ')  // 중복 마커
        .replace(/^[①-⑤]\s+/, '')
        .replace(/^\d+\.\s+[①-⑤]\s+/, '')
        .replace(/^\d+\.\s+/, '')
        .replace(/^\(\d+\)\s+/, '')
        .replace(/^\d+\)\s+/, '')
      return cleaned.trim()
    })
    .filter(Boolean)
  const choices = rawChoices.length >= 1 ? rawChoices : [] // 빈 경우 빈 배열

  // 중복출제 횟수 계산
  const dupCount = problem.중복출제 ? problem.중복출제.split(',').length + 1 : 1

  return (
    <article className={`bg-white rounded-xl border p-4 shadow-sm transition ${
      isAnswered ? (isCorrect ? 'border-green-300' : 'border-red-300') : 'border-gray-200'
    }`}>
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-gray-500">
          <span className="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-xs font-medium">{problem.회차}</span>
          <span className="rounded-full bg-gray-100 text-gray-700 px-2 py-0.5 text-xs font-medium">{problem.과목}</span>
          {problemNumber > 0 && <span className="rounded-full bg-purple-100 text-purple-700 px-2 py-0.5 text-xs font-medium">#{problemNumber}</span>}
          {qNo > 0 && <span className="rounded-full bg-purple-50 text-purple-500 px-2 py-0.5 text-xs">{qNo}번</span>}
          {problem.난이도 && <span className="rounded-full bg-yellow-100 text-yellow-700 px-2 py-0.5 text-xs font-medium">{problem.난이도}</span>}
          {dupCount >= 3 && (
            <span className="rounded-full bg-orange-100 text-orange-700 px-2 py-0.5 text-xs font-medium" title={`총 ${dupCount}회 출제`}>
              🔁 {dupCount}회 출제
            </span>
          )}
          {problem.중복출제 && (
            <span className="rounded-full bg-orange-50 text-orange-600 px-2 py-0.5 text-xs" title={problem.중복출제}>
              {problem.중복출제}
            </span>
          )}
        </div>
      </div>

      <h2 className="text-lg font-medium text-gray-900 leading-relaxed mb-3 whitespace-pre-line">
        {renderWithImages(problem.문제)}
      </h2>

      {choices.length > 0 ? (
        <div className="grid gap-2 mb-3">
          {choices.map((raw, ci) => {
            const choice = parseChoice(raw, ci)
            const isPicked = pick === choice.num
            const isCorrectChoice = correctAnswers.includes(choice.num)
            let btnClass = 'flex items-start gap-2 rounded-lg border px-3 py-2 text-left text-sm transition w-full '
            if (isAnswered) {
              if (isCorrectChoice) btnClass += 'bg-green-50 border-green-400 text-green-900'
              else if (isPicked && !isCorrectChoice) btnClass += 'bg-red-50 border-red-400 text-red-900'
              else btnClass += 'bg-white border-gray-200 text-gray-700'
            } else {
              btnClass += 'bg-white border-gray-200 hover:border-blue-400 hover:bg-blue-50 cursor-pointer'
            }
            return (
              <button key={ci} type="button" disabled={isAnswered}
                onClick={() => setPick(choice.num)} className={btnClass}>
                <span className="font-bold shrink-0 mt-0.5">{choice.label}</span>
                {choice.text && choice.text !== choice.label ? (
                  <span className="flex-1">{renderWithImages(choice.text)}</span>
                ) : null}
                {isAnswered && isCorrectChoice && <span className="shrink-0 text-xs font-bold text-green-700">정답</span>}
                {isAnswered && isPicked && !isCorrectChoice && <span className="shrink-0 text-xs font-bold text-red-700">내 선택</span>}
              </button>
            )
          })}
        </div>
      ) : (
        <div className="mb-3">
          <input type="text" placeholder="정답을 입력하세요" disabled={isAnswered}
            onChange={(e) => {
              const v = e.target.value.trim()
              if (!v) return
              const n = parseInt(v, 10)
              if (!isNaN(n) && n >= 1 && n <= 5) setPick(n)
            }}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
        </div>
      )}

      {isAnswered && (
        <div className="mt-3 space-y-3 border-t pt-3">
          <div className="flex items-center gap-2">
            <span className={`inline-block rounded-md px-3 py-1 text-sm font-bold ${isCorrect ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
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
              {renderWithImages(problem.해설)}
            </div>
          )}

          {problem.사용공식 && (
            <div className="rounded-md bg-blue-50 border border-blue-200 p-3 text-sm font-mono text-blue-700">
              <div className="text-xs font-semibold text-gray-500 mb-1 font-sans">사용 공식</div>
              {problem.사용공식}
            </div>
          )}

          <div className="flex items-center gap-3">
            {!isCorrect && (
              <button type="button" onClick={() => setPick(undefined)}
                className="text-xs text-gray-500 underline hover:text-blue-600">다른 답 선택하기</button>
            )}
            <button type="button" onClick={() => onExplain?.(problem)}
              className="text-xs bg-blue-500 text-white px-3 py-1 rounded-full hover:bg-blue-600 transition">
              🤖 AI에게 해설 요청
            </button>
          </div>
        </div>
      )}
    </article>
  )
}
