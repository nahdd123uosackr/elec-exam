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

    const result = await queryProblems({ cycle, subject, dupCount, search, limit, offset })
    return NextResponse.json(result)
  } catch (err: any) {
    console.error('[/api/problems]', err)
    return NextResponse.json({ error: err.message || 'DB 조회 실패', rows: [], total: 0 }, { status: 500 })
  }
}
