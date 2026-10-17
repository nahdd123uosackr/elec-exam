import { NextRequest, NextResponse } from 'next/server'
import { queryProblems } from '../../../lib/db'

export const dynamic = 'force-dynamic'
export const revalidate = 0

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const cycle = searchParams.get('cycle') || undefined
    const subject = searchParams.get('subject') || undefined
    const dupCount = searchParams.has('dupCount') ? parseInt(searchParams.get('dupCount')!, 10) : undefined
    const search = searchParams.get('q') || undefined
    const limit = parseInt(searchParams.get('limit') || '20', 10)
    const offset = parseInt(searchParams.get('offset') || '0', 10)
    const idsParam = searchParams.get('ids')
    const ids = idsParam ? idsParam.split(',').map(s => s.trim()).filter(Boolean) : undefined

    const result = await queryProblems({ cycle, subject, dupCount, search, limit, offset, ids })
    return NextResponse.json(result)
  } catch (err: any) {
    console.error('[/api/problems GET]', err)
    return NextResponse.json({ error: err.message || 'DB 조회 실패', rows: [], total: 0 }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json().catch(() => ({}))
    const ids = Array.isArray(body.ids)
      ? body.ids.map((id: any) => String(id).trim()).filter(Boolean)
      : undefined
    const cycle = body.cycle || undefined
    const subject = body.subject || undefined
    const dupCount = typeof body.dupCount === 'number' ? body.dupCount : undefined
    const search = body.search || body.q || undefined
    const limit = typeof body.limit === 'number' ? body.limit : 20
    const offset = typeof body.offset === 'number' ? body.offset : 0

    const result = await queryProblems({ cycle, subject, dupCount, search, limit, offset, ids })
    return NextResponse.json(result)
  } catch (err: any) {
    console.error('[/api/problems POST]', err)
    return NextResponse.json({ error: err.message || 'DB 조회 실패', rows: [], total: 0 }, { status: 500 })
  }
}
