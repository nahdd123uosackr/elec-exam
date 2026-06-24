'use client'

import React, { useState, useRef, useEffect, useCallback } from 'react'
import type { Problem } from '../types/Problem'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

interface Props {
  currentProblem?: Problem | null
  subject?: string
}

export default function ChatBot({ currentProblem, subject }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [webSearchEnabled, setWebSearchEnabled] = useState(false)
  const [webSearchQuery, setWebSearchQuery] = useState('')
  const [webSearchResults, setWebSearchResults] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages])

  // 현재 문제 컨텍스트 생성
  const buildSystemPrompt = useCallback(() => {
    let prompt = `당신은 전기기사 시험 전문 튜터입니다. 
학생이 전기기사 기출문제를 풀면서 질문하는 것에 대해 도움을 줍니다.
답변은 한국어로 작성하며, 쉬운 예시와 비유를 사용합니다.
수식이나 공식이 필요하면 포함시켜 주세요.
답변은 간결하지만 충분한 설명을 포함해야 합니다.`

    if (subject) {
      prompt += `\n\n현재 과목: ${subject}`
    }

    if (currentProblem) {
      prompt += `\n\n현재 문제:\n`
      prompt += `- 회차: ${currentProblem.회차 || '미상'}\n`
      prompt += `- 과목: ${currentProblem.과목 || '미상'}\n`
      prompt += `- 문제: ${currentProblem.문제}\n`
      if (currentProblem.보기) prompt += `- 보기: ${currentProblem.보기}\n`
      if (currentProblem.정답) prompt += `- 정답: ${currentProblem.정답}\n`
      if (currentProblem.해설) prompt += `- 기존 해설: ${currentProblem.해설}\n`
      if (currentProblem.사용공식) prompt += `- 사용 공식: ${currentProblem.사용공식}\n`
    }

    if (webSearchEnabled && webSearchResults) {
      prompt += `\n\n[웹 검색 결과]\n${webSearchResults}`
    }

    return prompt
  }, [currentProblem, subject, webSearchEnabled, webSearchResults])

  // 웹 검색 실행
  const doWebSearch = async (query: string) => {
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      const data = await res.json()
      setWebSearchResults(data.results || '검색 결과 없음')
      setWebSearchQuery(query)
      return data.results
    } catch {
      return '검색 실패'
    }
  }

  // 메시지 전송
  const sendMessage = async (searchFirst = false) => {
    const text = input.trim()
    if (!text || loading) return

    let searchResults = ''
    if (searchFirst || webSearchEnabled) {
      searchResults = await doWebSearch(text)
      setWebSearchResults(searchResults)
    }

    const userMsg: Message = { role: 'user', content: text }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    try {
      const systemPrompt = buildSystemPrompt()
      const apiMessages = [
        { role: 'system', content: systemPrompt },
        ...newMessages.map(m => ({ role: m.role, content: m.content })),
      ]

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages }),
      })

      const data = await res.json()
      const assistantMsg: Message = {
        role: 'assistant',
        content: data.choices?.[0]?.message?.content || '응답을 생성할 수 없습니다.',
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ 오류가 발생했습니다. 다시 시도해주세요.',
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      {/* 모바일 토글 버튼 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="md:hidden fixed bottom-4 right-4 z-50 bg-blue-600 text-white w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-2xl hover:bg-blue-700 transition"
        title="AI 튜터"
      >
        {isOpen ? '✕' : '🤖'}
      </button>

      {/* 챗봇 패널 */}
      <div className={`
        chat-panel bg-white border-l border-gray-200
        fixed md:static inset-0 md:inset-auto z-40 md:z-auto
        ${isOpen ? 'flex' : 'hidden'} md:flex
        flex-col w-full md:w-96 lg:w-[420px]
      `}>
        {/* 헤더 */}
        <div className="border-b border-gray-200 px-4 py-3 flex items-center justify-between bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center gap-2">
            <span className="text-xl">🤖</span>
            <div>
              <h3 className="font-semibold text-gray-900 text-sm">AI 전기기사 튜터</h3>
              <p className="text-xs text-gray-500">문제에 대해 질문하세요</p>
            </div>
          </div>
          <button onClick={() => setIsOpen(false)} className="md:hidden text-gray-400 hover:text-gray-600 text-xl">✕</button>
        </div>

        {/* 현재 문제 표시 */}
        {currentProblem && (
          <div className="border-b border-gray-100 px-4 py-2 bg-yellow-50 text-xs text-yellow-800">
            📌 현재 문제: {currentProblem.회차} | {currentProblem.과목}
            {currentProblem.문제 && (
              <span className="block mt-1 text-yellow-700 line-clamp-2">{currentProblem.문제.slice(0, 100)}...</span>
            )}
          </div>
        )}

        {/* 메시지 영역 */}
        <div className="chat-messages flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="text-center text-gray-400 text-sm py-8">
              <div className="text-3xl mb-2">💡</div>
              <p>전기기사 문제에 대해</p>
              <p>궁금한 점을 질문해보세요</p>
              <div className="mt-4 space-y-2 text-xs">
                <button onClick={() => { setInput('이 문제의 핵심 개념을 설명해주세요'); }}
                  className="block w-full text-left px-3 py-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                  💡 핵심 개념 설명 요청
                </button>
                <button onClick={() => { setInput('이 문제와 비슷한 예제를 만들어주세요'); }}
                  className="block w-full text-left px-3 py-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                  📝 유사 문제 생성 요청
                </button>
                <button onClick={() => { setInput('이 문제에 사용된 공식을 정리해주세요'); }}
                  className="block w-full text-left px-3 py-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                  📐 공식 정리 요청
                </button>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-md'
                  : 'bg-gray-100 text-gray-900 rounded-bl-md'
              }`}>
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 입력 영역 */}
        <div className="border-t border-gray-200 p-3 bg-white">
          {/* 웹 검색 토글 */}
          <div className="flex items-center gap-2 mb-2">
            <button
              onClick={() => setWebSearchEnabled(!webSearchEnabled)}
              className={`text-xs px-2 py-1 rounded-full border transition ${
                webSearchEnabled
                  ? 'bg-green-100 border-green-300 text-green-700'
                  : 'bg-gray-50 border-gray-200 text-gray-500 hover:bg-gray-100'
              }`}
            >
              🔍 웹 검색 {webSearchEnabled ? 'ON' : 'OFF'}
            </button>
            {webSearchQuery && (
              <span className="text-xs text-gray-400 truncate">검색: {webSearchQuery}</span>
            )}
          </div>

          <div className="flex gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="메시지를 입력하세요..."
              rows={1}
              className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-2.5 text-sm focus:outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
              style={{ minHeight: '42px', maxHeight: '120px' }}
            />
            <button
              onClick={() => sendMessage(webSearchEnabled)}
              disabled={loading || !input.trim()}
              className="shrink-0 bg-blue-600 text-white rounded-xl px-4 py-2.5 text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {loading ? '...' : '전송'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
