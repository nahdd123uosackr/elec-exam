import './globals.css'

export const metadata = {
  title: '전기기사 기출문제 학습',
  description: '전기기사 시험 대비 기출문제 학습 사이트 - AI 해설 도움',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  )
}