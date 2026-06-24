import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  try {
    const { query } = await req.json()
    if (!query) {
      return NextResponse.json({ results: '' })
    }

    // DuckDuckGo HTML 검색
    const searchUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query + ' 전기기사')}`
    const res = await fetch(searchUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
      },
    })

    const html = await res.text()

    // 결과 파싱: 제목과 스니펫 추출
    const results: string[] = []
    const titleRegex = /<a[^>]*class="result__a"[^>]*>([^<]+)<\/a>/g
    const snippetRegex = /<a[^>]*class="result__snippet"[^>]*>([^<]+(?:<[^>]+>[^<]*)*)<\/a>/g

    let match
    const titles: string[] = []
    while ((match = titleRegex.exec(html)) !== null && titles.length < 5) {
      titles.push(match[1].trim())
    }

    const snippets: string[] = []
    while ((match = snippetRegex.exec(html)) !== null && snippets.length < 5) {
      snippets.push(match[1].replace(/<[^>]+>/g, '').trim())
    }

    for (let i = 0; i < Math.min(titles.length, 5); i++) {
      results.push(`${i + 1}. ${titles[i]}${snippets[i] ? '\n   ' + snippets[i] : ''}`)
    }

    return NextResponse.json({
      query,
      results: results.length > 0
        ? `[웹 검색: "${query}"]\n\n${results.join('\n\n')}`
        : `웹 검색 결과 없음: "${query}"`,
    })
  } catch (err: any) {
    return NextResponse.json({ results: `검색 오류: ${err.message}` })
  }
}