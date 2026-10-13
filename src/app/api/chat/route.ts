import { NextRequest, NextResponse } from 'next/server'

const OMNI_BASE_URL = process.env.OMNI_BASE_URL || 'https://api.kilo.ai/api/gateway/v1'
const OMNI_API_KEY = process.env.OMNI_API_KEY || ''
const OMNI_MODEL = process.env.OMNI_MODEL || 'kilo-auto/free'

// 주 모델(kilo-auto/free)의 업스트림이 혼잡하면(429/5xx) 자동 전환할 안정 free 모델.
// kilo-auto/free 는 업스트림(Novita 등) 부하에 따라 간헐적으로 실패한다.
const FALLBACK_MODELS = [
  'nvidia/nemotron-3.5-lightning:free',
  'openrouter/free',
  'liquid/lfm-2.5-2.6b:free',
]

export const dynamic = 'force-dynamic'

interface ChatResult {
  ok: boolean
  status: number
  data?: any
  error?: string
  model?: string
}

async function callChat(model: string, messages: any[], signal?: AbortSignal): Promise<ChatResult> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  // kilo-auto/free 등 키 불필요 게이트웨이: 키가 있을 때만 Authorization 첨부
  if (OMNI_API_KEY) headers['Authorization'] = `Bearer ${OMNI_API_KEY}`

  const res = await fetch(`${OMNI_BASE_URL}/chat/completions`, {
    method: 'POST',
    headers,
    signal,
    body: JSON.stringify({
      model,
      messages,
      temperature: 0.7,
      max_tokens: 2048,
      stream: false,
    }),
  })

  if (!res.ok) {
    const errText = await res.text()
    return { ok: false, status: res.status, error: errText, model }
  }
  const data = await res.json()
  // 일부 reasoning 모델은 thinking 토큰을 다 써 content 가 비어온다 → 실패로 간주
  const content = data?.choices?.[0]?.message?.content
  if (!content || !String(content).trim()) {
    return { ok: false, status: 502, error: '빈 응답(content 없음)', data, model }
  }
  return { ok: true, status: 200, data, model }
}

export async function POST(req: NextRequest) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 55_000)
  try {
    const body = await req.json()
    const { messages, problemContext, ragContext } = body

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json({ error: 'messages 배열이 필요합니다' }, { status: 400 })
    }

    // 문제 컨텍스트가 있으면 시스템 프롬프트 강화
    const systemPrefix = messages[0]?.role === 'system' ? messages[0].content : ''
    const enhancedSystem =
      systemPrefix +
      (problemContext ? `\n\n[현재 문제]\n${problemContext}` : '') +
      (ragContext ? `\n\n[DB 검색 결과]\n${ragContext}` : '')

    const finalMessages =
      messages[0]?.role === 'system'
        ? [{ ...messages[0], content: enhancedSystem }, ...messages.slice(1)]
        : [{ role: 'system', content: enhancedSystem }, ...messages]

    const candidates = [OMNI_MODEL, ...FALLBACK_MODELS]
    let lastResult: ChatResult | null = null
    for (const model of candidates) {
      try {
        lastResult = await callChat(model, finalMessages, controller.signal)
      } catch (e: any) {
        if (e?.name === 'AbortError') {
          return NextResponse.json({ error: 'AI 응답 시간이 초과되었습니다' }, { status: 504 })
        }
        lastResult = { ok: false, status: 500, error: e?.message || '네트워크 오류', model }
      }
      if (lastResult.ok) {
        if (lastResult.model !== OMNI_MODEL) {
          console.warn(`[chat] ${OMNI_MODEL} 실패 → ${lastResult.model} 로 폴백`)
        }
        return NextResponse.json(lastResult.data)
      }
      // 429/5xx/빈응답이면 다음 후보 모델로, 그 외(4xx 등)는 즉시 반환
      if (lastResult.status < 500 && lastResult.status !== 502) {
        console.error('Chat API 오류:', lastResult.status, lastResult.error?.slice(0, 200))
        return NextResponse.json(
          { error: `API 오류: ${lastResult.status}` },
          { status: lastResult.status }
        )
      }
      console.warn(`[chat] ${model} 실패(${lastResult.status}) → 다음 모델 시도`)
    }

    const status = lastResult?.status ?? 502
    console.error('Chat API 모든 모델 실패:', status, lastResult?.error?.slice(0, 200))
    return NextResponse.json({ error: `API 오류: ${status}` }, { status })
  } catch (err: any) {
    console.error('Chat API error:', err)
    return NextResponse.json({ error: err.message || '서버 오류' }, { status: 500 })
  } finally {
    clearTimeout(timer)
  }
}
