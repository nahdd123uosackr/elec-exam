import './globals.css'

export const metadata = {
  title: '전기기사 기출문제 학습',
  description: '전기기사 시험 대비 기출문제 학습 사이트 - AI 해설 도움',
}

import 'katex/dist/katex.min.css'

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
      </head>
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  )
}