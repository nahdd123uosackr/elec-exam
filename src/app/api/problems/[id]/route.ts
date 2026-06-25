import { NextRequest, NextResponse } from 'next/server'
import { getProblemById } from '../../../../lib/db'

export const dynamic = 'force-dynamic'

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const problem = await getProblemById(params.id)
    if (!problem) {
      return NextResponse.json({ error: '문제를 찾을 수 없습니다' }, { status: 404 })
    }
    return NextResponse.json(problem)
  } catch (err: any) {
    console.error('[/api/problems/:id]', err)
    return NextResponse.json({ error: err.message || '조회 실패' }, { status: 500 })
  }
}
