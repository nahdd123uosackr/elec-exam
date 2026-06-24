import { NextRequest, NextResponse } from 'next/server'

const OMNI_BASE_URL = process.env.OMNI_BASE_URL || 'https://omni.nhd.us.to/v1'
const OMNI_API_KEY = process.env.OMNI_API_KEY || ''

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { messages } = body

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json({ error: 'messages 배열이 필요합니다' }, { status: 400 })
    }

    const res = await fetch(`${OMNI_BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${OMNI_API_KEY}`,
      },
      body: JSON.stringify({
        model: 'gpt-4o-mini',
        messages,
        temperature: 0.7,
        max_tokens: 2048,
      }),
    })

    if (!res.ok) {
      const errText = await res.text()
      console.error('OMNI API error:', res.status, errText)
      return NextResponse.json({ error: `API 오류: ${res.status}` }, { status: res.status })
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (err: any) {
    console.error('Chat API error:', err)
    return NextResponse.json({ error: err.message || '서버 오류' }, { status: 500 })
  }
}