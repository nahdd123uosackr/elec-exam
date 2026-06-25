import { NextRequest, NextResponse } from 'next/server'
import { getStats } from '../../../lib/db'

export const dynamic = 'force-dynamic'

export async function GET(_req: NextRequest) {
  try {
    const stats = await getStats()
    return NextResponse.json(stats)
  } catch (err: any) {
    console.error('[/api/stats]', err)
    return NextResponse.json({ error: err.message || '통계 조회 실패' }, { status: 500 })
  }
}
